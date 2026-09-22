import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import ActaInmutable, OrdenServicio
from app.models.usuario import Usuario
from app.schemas.orden import OrdenSincronizarIn
from app.services.inventario import registrar_movimiento


class OrdenSyncError(Exception):
    """Base de errores de dominio de la sincronizacion de ordenes."""


class TecnicoNoAutorizado(OrdenSyncError):
    pass


class EquipoNoEncontrado(OrdenSyncError):
    pass


class ContratoNoEncontrado(OrdenSyncError):
    pass


def payload_raw_canonico(datos: OrdenSincronizarIn) -> str:
    """Serializacion deterministica de las lecturas de agua: mismo contenido -> mismo string,
    sin importar el orden de las claves recibidas (json.dumps con sort_keys)."""
    cuerpo = {
        "equipo_serie": datos.equipo_serie,
        "tipo_intervencion": datos.tipo_intervencion,
        "fecha_creacion_cliente": datos.fecha_creacion_cliente.isoformat(),
        "lecturas_agua": datos.lecturas_agua.model_dump(),
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
        return existente

    if await session.get(Contrato, datos.contrato_id) is None:
        raise ContratoNoEncontrado(str(datos.contrato_id))
    if await session.get(Equipo, datos.equipo_serie) is None:
        raise EquipoNoEncontrado(datos.equipo_serie)

    async with session.begin_nested():
        orden = OrdenServicio(
            id=datos.id,
            contrato_id=datos.contrato_id,
            equipo_serie=datos.equipo_serie,
            tecnico_id=datos.tecnico_id,
            tipo_intervencion=datos.tipo_intervencion,
            estado="SINCRONIZADA",
            fecha_creacion_cliente=datos.fecha_creacion_cliente,
        )
        session.add(orden)
        await session.flush()

        payload_raw = payload_raw_canonico(datos)
        previous_hash = (
            await session.execute(
                select(ActaInmutable.hash_sha256)
                .join(OrdenServicio, ActaInmutable.orden_id == OrdenServicio.id)
                .where(OrdenServicio.equipo_serie == datos.equipo_serie, OrdenServicio.id != orden.id)
                .order_by(ActaInmutable.creado_en.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        session.add(
            ActaInmutable(
                orden_id=orden.id,
                payload_raw=payload_raw,
                hash_sha256=_hash(payload_raw),
                previous_hash=previous_hash,
                firma_base64=datos.firma_base64,
                gps_latitud=datos.gps_latitud,
                gps_longitud=datos.gps_longitud,
            )
        )

        for item in datos.repuestos_consumidos:
            await registrar_movimiento(
                session, item.repuesto_codigo, "SALIDA_ORDEN", item.cantidad, datos.tecnico_id, orden_id=orden.id
            )

    await session.refresh(orden)
    return orden
