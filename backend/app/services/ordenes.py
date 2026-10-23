import hashlib
import json
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import ActaInmutable, OrdenServicio
from app.models.usuario import Usuario
from app.schemas.orden import OrdenSincronizarIn
from app.services.condiciones import condiciones_en_fecha
from app.services.inventario import registrar_movimiento


class OrdenSyncError(Exception):
    """Base de errores de dominio de la sincronizacion de ordenes."""


class TecnicoNoAutorizado(OrdenSyncError):
    pass


class EquipoNoEncontrado(OrdenSyncError):
    pass


class ContratoNoEncontrado(OrdenSyncError):
    pass


class ContratoInvalido(OrdenSyncError):
    pass


def payload_raw_canonico(datos: OrdenSincronizarIn, *, sla_horas_max_respuesta: int | None = None) -> str:
    """Serializacion deterministica del contenido probatorio del acta (RN-04): mismo contenido
    -> mismo string, sin importar el orden de las claves recibidas (json.dumps con sort_keys).

    Incluye id/tecnico/contrato/firma/GPS ademas de las lecturas: sin esto, alguien con acceso
    a la BD podria sustituir la firma o mover el GPS sin invalidar el hash, y dos ordenes
    distintas con las mismas lecturas producirian el mismo hash_sha256."""
    cuerpo = {
        "version": 2,
        "id": str(datos.id),
        "contrato_id": datos.contrato_id,
        "equipo_serie": datos.equipo_serie,
        "tecnico_id": datos.tecnico_id,
        "tipo_intervencion": datos.tipo_intervencion,
        "fecha_creacion_cliente": datos.fecha_creacion_cliente.isoformat(),
        "fecha_solicitud": datos.fecha_solicitud.isoformat() if datos.fecha_solicitud else None,
        "fecha_primera_atencion": datos.fecha_primera_atencion.isoformat() if datos.fecha_primera_atencion else None,
        "sla_horas_max_respuesta": sla_horas_max_respuesta,
        "lecturas_agua": datos.lecturas_agua.model_dump(),
        "firma_base64": datos.firma_base64,
        "gps_latitud": str(datos.gps_latitud),
        "gps_longitud": str(datos.gps_longitud),
        "repuestos_consumidos": [item.model_dump() for item in datos.repuestos_consumidos],
    }
    return json.dumps(cuerpo, sort_keys=True)


def _hash(payload_raw: str) -> str:
    return hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()


async def sincronizar_orden(session: AsyncSession, datos: OrdenSincronizarIn, usuario: Usuario) -> OrdenServicio:
    """RN-04: encadena el hash del acta al de la ultima acta del mismo equipo.
    Idempotente por datos.id: un reintento del mismo UUID devuelve la orden ya creada,
    sin reprocesar ni duplicar nada."""
    if usuario.rol != "GERENCIA" and datos.tecnico_id != usuario.id:
        raise TecnicoNoAutorizado(f"{usuario.id} no puede sincronizar ordenes de {datos.tecnico_id}")

    existente = await session.get(OrdenServicio, datos.id)
    if existente is not None:
        if usuario.rol != "GERENCIA" and existente.tecnico_id != usuario.id:
            raise TecnicoNoAutorizado(str(usuario.id))
        return existente

    async with session.begin_nested():
        # El UUID también se serializa cuando dos reintentos declaran equipos distintos.
        # Una colisión de 64 bits únicamente serializa dos UUID, nunca los confunde.
        lock_id = int.from_bytes(datos.id.bytes[:8], byteorder="big", signed=True)
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        existente = await session.get(OrdenServicio, datos.id)
        if existente is not None:
            if usuario.rol != "GERENCIA" and existente.tecnico_id != usuario.id:
                raise TecnicoNoAutorizado(str(usuario.id))
            return existente

        # Contrato → equipo → repuestos ordenados es el orden global de locks.
        contrato = (await session.execute(select(Contrato).where(Contrato.id == datos.contrato_id)
                    .with_for_update(read=True).execution_options(populate_existing=True))).scalar_one_or_none()
        if contrato is None:
            raise ContratoNoEncontrado(str(datos.contrato_id))
        equipo = (await session.execute(select(Equipo).where(Equipo.serie == datos.equipo_serie)
                  .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if equipo is None:
            raise EquipoNoEncontrado(datos.equipo_serie)
        # Revalidar después de adquirir el lock, nunca confiar en la lectura previa.
        existente = await session.get(OrdenServicio, datos.id)
        if existente is not None:
            return existente
        if equipo.contrato_id != contrato.id or equipo.cliente_ruc != contrato.cliente_ruc:
            raise ContratoInvalido("Asocia el equipo a un contrato de su mismo cliente antes de sincronizar")
        if contrato.estado == "ANULADO" and (
            contrato.anulado_en is None or datos.fecha_creacion_cliente >= contrato.anulado_en
        ):
            raise ContratoInvalido("El contrato estaba anulado al realizar el servicio")
        fecha_servicio = datos.fecha_creacion_cliente.astimezone(ZoneInfo("America/Lima")).date()
        condiciones = await condiciones_en_fecha(session, contrato, fecha_servicio)
        if condiciones.estado == "ANULADO" or not condiciones.fecha_inicio <= fecha_servicio <= condiciones.fecha_fin:
            raise ContratoInvalido("El contrato no está vigente en la fecha del servicio (America/Lima)")

        # Legado importado o creado antes de la migración: continuar sin cambiar el acta.
        # El id registra inserción; creado_en usa inicio de transacción y no es una cabeza fiable.
        if equipo.ultimo_hash_acta is None and equipo.secuencia_acta == 0:
            legacy = select(ActaInmutable).join(OrdenServicio, ActaInmutable.orden_id == OrdenServicio.id).where(
                OrdenServicio.equipo_serie == equipo.serie)
            equipo.ultimo_hash_acta = (await session.execute(legacy.with_only_columns(ActaInmutable.hash_sha256)
                                       .order_by(ActaInmutable.id.desc()).limit(1))).scalar_one_or_none()
            equipo.secuencia_acta = await session.scalar(legacy.with_only_columns(func.count()))

        respuesta = None
        if datos.fecha_solicitud is not None:
            segundos = Decimal(str((datos.fecha_primera_atencion - datos.fecha_solicitud).total_seconds()))
            respuesta = (segundos / Decimal(3600)).quantize(Decimal("0.01"))

        orden = OrdenServicio(
            id=datos.id,
            contrato_id=datos.contrato_id,
            equipo_serie=datos.equipo_serie,
            tecnico_id=datos.tecnico_id,
            tipo_intervencion=datos.tipo_intervencion,
            estado="SINCRONIZADA",
            fecha_creacion_cliente=datos.fecha_creacion_cliente,
            fecha_solicitud=datos.fecha_solicitud,
            fecha_primera_atencion=datos.fecha_primera_atencion,
            tiempo_respuesta_horas=respuesta,
            sla_horas_max_respuesta=condiciones.sla_horas_max_respuesta,
        )
        session.add(orden)
        await session.flush()

        payload_raw = payload_raw_canonico(datos, sla_horas_max_respuesta=condiciones.sla_horas_max_respuesta)
        previous_hash = equipo.ultimo_hash_acta
        equipo.secuencia_acta += 1
        equipo.ultimo_hash_acta = _hash(payload_raw)

        session.add(
            ActaInmutable(
                orden_id=orden.id,
                payload_raw=payload_raw,
                hash_sha256=equipo.ultimo_hash_acta,
                previous_hash=previous_hash,
                equipo_serie=equipo.serie,
                secuencia=equipo.secuencia_acta,
                firma_base64=datos.firma_base64,
                gps_latitud=datos.gps_latitud,
                gps_longitud=datos.gps_longitud,
            )
        )

        for item in sorted(datos.repuestos_consumidos, key=lambda item: item.repuesto_codigo):
            await registrar_movimiento(
                session, item.repuesto_codigo, "SALIDA_ORDEN", item.cantidad, datos.tecnico_id, orden_id=orden.id
            )

    await session.refresh(orden)
    return orden
