"""Historial operativo anexo a actas; ninguna operación modifica el documento firmado."""
import hashlib
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from fastapi.encoders import jsonable_encoder

from app.models.componente import AnulacionIntervencion, CambioComponente, ComponenteEquipo, IntervencionComponente
from app.models.equipo import Equipo
from app.models.orden import ActaInmutable, OrdenServicio
from app.models.usuario import Usuario


class MantenimientoError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def hoy_lima():
    return datetime.now(ZoneInfo("America/Lima")).date()


def _columnas(registro):
    return {c.name: getattr(registro, c.name) for c in registro.__table__.columns}


async def _equipo(session, serie, *, bloquear=False):
    q = select(Equipo).where(Equipo.serie == serie)
    if bloquear:
        q = q.with_for_update().execution_options(populate_existing=True)
    equipo = (await session.execute(q)).scalar_one_or_none()
    if equipo is None:
        raise MantenimientoError(404, "Equipo no encontrado")
    return equipo


async def _componente(session, serie, componente_id, *, bloquear=False):
    equipo = await _equipo(session, serie, bloquear=bloquear)
    q = select(ComponenteEquipo).where(ComponenteEquipo.id == componente_id, ComponenteEquipo.equipo_serie == serie)
    if bloquear:
        q = q.with_for_update().execution_options(populate_existing=True)
    componente = (await session.execute(q)).scalar_one_or_none()
    if componente is None:
        raise MantenimientoError(404, "Componente no encontrado en este equipo")
    return equipo, componente


async def listar_componentes(session, serie, incluir_anulados=False):
    await _equipo(session, serie)
    ultima = func.max(IntervencionComponente.fecha_efectiva).filter(
        IntervencionComponente.tipo == "SUSTITUCION", AnulacionIntervencion.id.is_(None))
    q = (select(ComponenteEquipo, ultima).outerjoin(IntervencionComponente,
            IntervencionComponente.componente_id == ComponenteEquipo.id)
         .outerjoin(AnulacionIntervencion, AnulacionIntervencion.intervencion_id == IntervencionComponente.id)
         .where(ComponenteEquipo.equipo_serie == serie)
         .group_by(ComponenteEquipo.id)
         .order_by(func.lower(ComponenteEquipo.nombre)))
    if not incluir_anulados:
        q = q.where(ComponenteEquipo.anulado_en.is_(None))
    resultado = []
    for componente, sustitucion in (await session.execute(q)).all():
        fechas = [d for d in (componente.fecha_instalacion, sustitucion) if d is not None]
        resultado.append({**_columnas(componente), "ciclo_actual_desde": None if componente.anulado_en else (max(fechas) if fechas else None)})
    return resultado


async def crear_componente(session, serie, datos, usuario):
    equipo = await _equipo(session, serie, bloquear=True)
    if datos.fecha_instalacion is not None and not equipo.fecha_instalacion <= datos.fecha_instalacion <= hoy_lima():
        raise MantenimientoError(422, "La instalación del componente debe estar entre la instalación del equipo y hoy")
    repetido = await session.scalar(select(ComponenteEquipo.id).where(
        ComponenteEquipo.equipo_serie == serie, ComponenteEquipo.anulado_en.is_(None),
        func.lower(ComponenteEquipo.nombre) == func.lower(datos.nombre)))
    if repetido is not None:
        raise MantenimientoError(409, "Ya hay un componente con ese nombre en este equipo")
    componente = ComponenteEquipo(equipo_serie=serie, creado_por_id=usuario.id, **datos.model_dump())
    session.add(componente)
    await session.flush()
    return {**_columnas(componente), "ciclo_actual_desde": componente.fecha_instalacion}


def _instantanea(componente, ciclo_actual_desde=None):
    return jsonable_encoder({**_columnas(componente), "ciclo_actual_desde": ciclo_actual_desde})


def _desde_instantanea(instantanea):
    return instantanea


async def _ciclo_actual(session, componente):
    if componente.anulado_en is not None:
        return None
    sustitucion = await session.scalar(select(func.max(IntervencionComponente.fecha_efectiva)).outerjoin(
        AnulacionIntervencion, AnulacionIntervencion.intervencion_id == IntervencionComponente.id).where(
            IntervencionComponente.componente_id == componente.id,
            IntervencionComponente.tipo == "SUSTITUCION", AnulacionIntervencion.id.is_(None)))
    fechas = [f for f in (componente.fecha_instalacion, sustitucion) if f is not None]
    return max(fechas) if fechas else None


async def _bloqueo_solicitud(session, solicitud_id):
    llave = int.from_bytes(solicitud_id.bytes[:8], byteorder="big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:llave)"), {"llave": llave})


async def _operacion_previa(session, solicitud_id, componente_id, accion, solicitud):
    existente = await session.get(CambioComponente, solicitud_id)
    if existente is None:
        return None
    if existente.componente_id != componente_id or existente.accion != accion or existente.solicitud != solicitud:
        raise MantenimientoError(409, "Ese identificador de solicitud ya se usó con otro contenido")
    return _desde_instantanea(existente.despues)


async def _validar_ficha(session, equipo, componente, nombre, fecha_instalacion):
    if fecha_instalacion is not None:
        if not equipo.fecha_instalacion <= fecha_instalacion <= hoy_lima():
            raise MantenimientoError(422, "La instalación del componente debe estar entre la instalación del equipo y hoy en Lima")
        anterior_a_intervencion = await session.scalar(select(IntervencionComponente.id).where(
            IntervencionComponente.componente_id == componente.id,
            IntervencionComponente.fecha_efectiva < fecha_instalacion).limit(1))
        if anterior_a_intervencion is not None:
            raise MantenimientoError(422, "La instalación no puede ser posterior a ninguna intervención registrada")
    colision = await session.scalar(select(ComponenteEquipo.id).where(
        ComponenteEquipo.equipo_serie == componente.equipo_serie,
        ComponenteEquipo.id != componente.id,
        ComponenteEquipo.anulado_en.is_(None),
        func.lower(ComponenteEquipo.nombre) == func.lower(nombre)).limit(1))
    if colision is not None:
        raise MantenimientoError(409, "Ya hay un componente activo con ese nombre en este equipo")


def _solicitud_normalizada(componente_id, accion, datos):
    cuerpo = datos.model_dump(mode="json")
    cuerpo.pop("solicitud_id", None)
    return {"componente_id": str(componente_id), "accion": accion, **cuerpo}


async def _registrar_cambio(session, componente, usuario, solicitud_id, accion, solicitud, motivo, antes, despues):
    cambio = CambioComponente(solicitud_id=solicitud_id, componente_id=componente.id, accion=accion,
        revision_anterior=componente.revision - 1, revision_nueva=componente.revision,
        antes=antes, despues=despues, solicitud=solicitud, motivo=motivo, registrado_por_id=usuario.id)
    session.add(cambio)
    await session.flush()
    return despues


async def corregir_componente(session, serie, componente_id, datos, usuario):
    await _bloqueo_solicitud(session, datos.solicitud_id)
    equipo, componente = await _componente(session, serie, componente_id, bloquear=True)
    accion = "CORREGIR"
    solicitud = _solicitud_normalizada(componente_id, accion, datos)
    previa = await _operacion_previa(session, datos.solicitud_id, componente_id, accion, solicitud)
    if previa is not None:
        return previa, False
    if datos.revision_esperada != componente.revision:
        raise MantenimientoError(409, "La ficha cambió. Recarga su revisión antes de corregirla")
    if componente.anulado_en is not None:
        raise MantenimientoError(409, "Restablece el alta antes de corregir la ficha")
    campos = {k: getattr(datos, k) for k in ("nombre", "tipo_componente", "fecha_instalacion", "fabricante_modelo")}
    if all(getattr(componente, k) == v for k, v in campos.items()):
        raise MantenimientoError(422, "La corrección no contiene cambios efectivos")
    await _validar_ficha(session, equipo, componente, datos.nombre, datos.fecha_instalacion)
    antes = _instantanea(componente, await _ciclo_actual(session, componente))
    for campo, valor in campos.items():
        setattr(componente, campo, valor)
    componente.revision += 1
    await session.flush()
    ciclo = await _ciclo_actual(session, componente)
    despues = _instantanea(componente, ciclo)
    respuesta = await _registrar_cambio(session, componente, usuario, datos.solicitud_id, accion, solicitud, datos.motivo, antes, despues)
    return respuesta, True


async def anular_alta(session, serie, componente_id, datos, usuario):
    await _bloqueo_solicitud(session, datos.solicitud_id)
    _, componente = await _componente(session, serie, componente_id, bloquear=True)
    accion = "ANULAR_ALTA"
    solicitud = _solicitud_normalizada(componente_id, accion, datos)
    previa = await _operacion_previa(session, datos.solicitud_id, componente_id, accion, solicitud)
    if previa is not None:
        return previa, False
    if datos.revision_esperada != componente.revision:
        raise MantenimientoError(409, "La ficha cambió. Recarga su revisión antes de anularla")
    if componente.anulado_en is not None:
        raise MantenimientoError(409, "El alta ya está anulada")
    vigente = await session.scalar(select(IntervencionComponente.id).outerjoin(
        AnulacionIntervencion, AnulacionIntervencion.intervencion_id == IntervencionComponente.id).where(
            IntervencionComponente.componente_id == componente.id, AnulacionIntervencion.id.is_(None)).limit(1))
    if vigente is not None:
        raise MantenimientoError(409, "Anula primero las intervenciones vigentes del componente")
    antes = _instantanea(componente, await _ciclo_actual(session, componente))
    componente.revision += 1
    componente.anulado_en = datetime.now(ZoneInfo("America/Lima"))
    await session.flush()
    despues = _instantanea(componente, None)
    return await _registrar_cambio(session, componente, usuario, datos.solicitud_id, accion, solicitud, datos.motivo, antes, despues), True


async def restablecer_alta(session, serie, componente_id, datos, usuario):
    await _bloqueo_solicitud(session, datos.solicitud_id)
    equipo, componente = await _componente(session, serie, componente_id, bloquear=True)
    accion = "RESTABLECER_ALTA"
    solicitud = _solicitud_normalizada(componente_id, accion, datos)
    previa = await _operacion_previa(session, datos.solicitud_id, componente_id, accion, solicitud)
    if previa is not None:
        return previa, False
    if datos.revision_esperada != componente.revision:
        raise MantenimientoError(409, "La ficha cambió. Recarga su revisión antes de restablecerla")
    if componente.anulado_en is None:
        raise MantenimientoError(409, "El alta no está anulada")
    await _validar_ficha(session, equipo, componente, datos.nombre, datos.fecha_instalacion)
    antes = _instantanea(componente, None)
    for campo in ("nombre", "tipo_componente", "fecha_instalacion", "fabricante_modelo"):
        setattr(componente, campo, getattr(datos, campo))
    componente.revision += 1
    componente.anulado_en = None
    await session.flush()
    despues = _instantanea(componente, await _ciclo_actual(session, componente))
    return await _registrar_cambio(session, componente, usuario, datos.solicitud_id, accion, solicitud, datos.motivo, antes, despues), True


async def cambios_componente(session, serie, componente_id, limit=50, offset=0):
    await _componente(session, serie, componente_id)
    q = (select(CambioComponente).where(CambioComponente.componente_id == componente_id)
         .order_by(CambioComponente.revision_nueva).limit(limit).offset(offset))
    return (await session.scalars(q)).all()


async def ordenes_firmadas(session, serie):
    await _equipo(session, serie)
    q = (select(OrdenServicio).join(ActaInmutable, ActaInmutable.orden_id == OrdenServicio.id)
         .where(OrdenServicio.equipo_serie == serie).order_by(OrdenServicio.fecha_creacion_cliente.desc()))
    return [{"id": o.id, "tipo_intervencion": o.tipo_intervencion,
             "fecha_creacion_cliente": o.fecha_creacion_cliente} for o in (await session.scalars(q)).all()]


async def _historial(session, componente_id, *, intervencion_id=None):
    q = (select(IntervencionComponente, Usuario.nombre, AnulacionIntervencion)
         .join(Usuario, Usuario.id == IntervencionComponente.registrado_por_id)
         .outerjoin(AnulacionIntervencion, AnulacionIntervencion.intervencion_id == IntervencionComponente.id)
         .where(IntervencionComponente.componente_id == componente_id)
         .order_by(IntervencionComponente.fecha_efectiva.desc(), IntervencionComponente.registrado_en.desc(), IntervencionComponente.id))
    if intervencion_id is not None:
        q = q.where(IntervencionComponente.id == intervencion_id)
    return [{**_columnas(i), "registrado_por_nombre": nombre, "anulacion": _columnas(a) if a else None}
            for i, nombre, a in (await session.execute(q)).all()]


async def historial(session, serie, componente_id):
    await _componente(session, serie, componente_id)
    return await _historial(session, componente_id)


async def registrar_intervencion(session, serie, componente_id, datos, usuario):
    llave = int.from_bytes(datos.id.bytes[:8], byteorder="big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:llave)"), {"llave": llave})
    equipo, componente = await _componente(session, serie, componente_id, bloquear=True)
    existente = await session.get(IntervencionComponente, datos.id)
    if existente is not None:
        if existente.componente_id != componente.id or any(
                getattr(existente, campo) != valor for campo, valor in datos.model_dump().items()):
            raise MantenimientoError(409, "Ese identificador ya tiene otro contenido; revisa el historial")
        return (await _historial(session, componente.id, intervencion_id=existente.id))[0], False
    if componente.anulado_en is not None:
        raise MantenimientoError(409, "No se admiten nuevas intervenciones sobre un componente con alta anulada")
    orden = await session.get(OrdenServicio, datos.orden_id)
    if orden is None:
        raise MantenimientoError(404, "Orden no encontrada")
    if orden.equipo_serie != serie:
        raise MantenimientoError(409, "La orden corresponde a otro equipo")
    acta = await session.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == orden.id))
    if acta is None or hashlib.sha256(acta.payload_raw.encode("utf-8")).hexdigest() != acta.hash_sha256:
        raise MantenimientoError(409, "Se requiere un acta disponible con integridad verificada")
    inicio = componente.fecha_instalacion or equipo.fecha_instalacion
    cierre = orden.fecha_creacion_cliente.astimezone(ZoneInfo("America/Lima")).date()
    if not inicio <= datos.fecha_efectiva <= min(cierre, hoy_lima()):
        raise MantenimientoError(422, "La fecha debe estar entre la instalación conocida y el cierre de la orden, sin ser futura")
    evento = IntervencionComponente(componente_id=componente.id, acta_hash=acta.hash_sha256,
                                   registrado_por_id=usuario.id, **datos.model_dump())
    session.add(evento)
    await session.flush()
    return (await _historial(session, componente.id, intervencion_id=evento.id))[0], True


async def anular_intervencion(session, serie, componente_id, intervencion_id, datos, usuario):
    await _componente(session, serie, componente_id, bloquear=True)
    evento = await session.get(IntervencionComponente, intervencion_id)
    if evento is None or evento.componente_id != componente_id:
        raise MantenimientoError(404, "Intervención no encontrada en este componente")
    existente = await session.scalar(select(AnulacionIntervencion).where(AnulacionIntervencion.intervencion_id == evento.id))
    if existente is not None:
        if existente.motivo != datos.motivo:
            raise MantenimientoError(409, "La intervención ya fue anulada con otro motivo")
        return existente, False
    anulacion = AnulacionIntervencion(intervencion_id=evento.id, motivo=datos.motivo, registrado_por_id=usuario.id)
    session.add(anulacion)
    await session.flush()
    return anulacion, True
