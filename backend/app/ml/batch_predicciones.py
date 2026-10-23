import asyncio
import os
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from contextlib import suppress
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.db import make_engine
from app.core.politica_rul import POLITICA_ALERTA, VERSION_CALCULO, VERSION_DATASET
from app.core.vigencia_rul import PoliticaVigencia
from app.core.supervision_rul import PoliticaSupervision
from app.ml.artefacto_rul import ModeloInvalido, ModeloPublicado, cargar_modelo
from app.ml.latido_rul import latir
from app.ml.modelo_rul import ParametrosImposibles, calificar_equipo
from app.ml.registro_rul import adquirir_batch, cerrar_ejecucion, entorno_calculo
from app.models.ejecucion_rul import EjecucionRul, ResultadoRul
from app.models.equipo import TIPOS_SISTEMA, Equipo
from app.models.prediccion_rul import PrediccionRul

class CoberturaIncompleta(ValueError):
    pass


@dataclass
class Progreso:
    modelo: ModeloPublicado | None = None
    esperados: int | None = None
    procesados: int = 0


async def verificar_cobertura(session, ejecucion_id, series: set[str]) -> int:
    await session.flush()
    historicas=set((await session.scalars(select(ResultadoRul.equipo_serie).where(ResultadoRul.ejecucion_id==ejecucion_id))).all())
    actuales=set((await session.scalars(select(PrediccionRul.equipo_serie).where(PrediccionRul.ejecucion_id==ejecucion_id))).all())
    if historicas != series or actuales != series:
        raise CoberturaIncompleta("Los resultados no cubren la instantánea de equipos")
    return len(historicas)


async def _procesar(session, ejecucion_id, vigencia, politica, progreso):
    await session.execute(text("SELECT set_config('statement_timeout',:ms,true)"),{"ms":str(politica.duracion_max_segundos*1000)})
    if not await adquirir_batch(session):
        await cerrar_ejecucion(session, ejecucion_id, estado="OMITIDA_CONCURRENCIA",finalizado_en=datetime.now(timezone.utc))
        await session.commit()
        return "Omitida: otra ejecución RUL está procesando."
    cph=await asyncio.to_thread(cargar_modelo)
    progreso.modelo=cph
    equipos=(await session.scalars(select(Equipo).order_by(Equipo.serie).with_for_update().execution_options(populate_existing=True))).all()
    progreso.esperados=len(equipos)
    calculado=datetime.now(timezone.utc)
    hoy=calculado.astimezone(ZoneInfo("America/Lima")).date()
    vence=calculado+timedelta(hours=vigencia)
    estimadas=0
    for e in equipos:
        try:
            if e.tipo_sistema not in TIPOS_SISTEMA:
                raise ParametrosImposibles("TIPO_DESCONOCIDO")
            r=calificar_equipo(cph,e.tipo_sistema,e.fecha_instalacion,hoy)
            dias,nivel,motivo=r["dias_vida_util_remanente"],r["nivel_alerta"],None
            estimadas+=1
        except ParametrosImposibles as exc:
            dias,nivel,motivo=None,None,exc.motivo
        valores=dict(equipo_serie=e.serie,ejecucion_id=ejecucion_id,fecha_referencia=e.fecha_instalacion,tipo_referencia=e.tipo_sistema,
            dias_vida_util_remanente=dias,nivel_alerta=nivel,motivo_no_estimable=motivo,version_calculo=VERSION_CALCULO,vence_en=vence)
        session.add(ResultadoRul(**valores,origen="BATCH",calculado_en=calculado,fecha_evaluacion=hoy))
        consulta=insert(PrediccionRul).values(**valores,actualizado_en=calculado)
        await session.execute(consulta.on_conflict_do_update(index_elements=[PrediccionRul.equipo_serie],
            set_={k:getattr(consulta.excluded,k) for k in (*valores,"actualizado_en") if k!="equipo_serie"}))
        progreso.procesados+=1
    await verificar_cobertura(session,ejecucion_id,{e.serie for e in equipos})
    await cerrar_ejecucion(session,ejecucion_id,estado="COMPLETADA",finalizado_en=datetime.now(timezone.utc),
        modelo_sha256=cph.sha256,entorno_modelo=cph.metadatos.entorno,dataset_sha256=cph.metadatos.dataset_sha256,
        total=len(equipos),estimadas=estimadas,abstenciones=len(equipos)-estimadas,esperados=progreso.esperados,procesados=progreso.procesados)
    await session.commit()
    return f"OK: {len(equipos)} equipos; {estimadas} estimaciones, {len(equipos)-estimadas} abstenciones."


async def _ejecutar(session: AsyncSession, sesiones_latido=None) -> str:
    vigencia=PoliticaVigencia().vigencia_horas
    politica=PoliticaSupervision()
    ejecucion_id=uuid4()
    inicio=datetime.now(timezone.utc)
    session.add(EjecucionRul(id=ejecucion_id,iniciado_en=inicio,estado="EN_CURSO",version_calculo=VERSION_CALCULO,
        version_dataset=VERSION_DATASET,politica_alerta=POLITICA_ALERTA,entorno=entorno_calculo(),vigencia_horas=vigencia,
        latido_en=inicio,limite_en=inicio+timedelta(seconds=politica.duracion_max_segundos)))
    await session.commit()
    progreso=Progreso()
    tarea=asyncio.create_task(latir(sesiones_latido,ejecucion_id,politica.latido_segundos)) if sesiones_latido else None
    try:
        async with asyncio.timeout(politica.duracion_max_segundos):
            return await _procesar(session,ejecucion_id,vigencia,politica,progreso)
    except (Exception,asyncio.CancelledError) as exc:
        await session.rollback()
        codigo="ERROR_CALCULO"
        if isinstance(exc,ModeloInvalido): codigo="MODELO_INVALIDO"
        elif isinstance(exc,CoberturaIncompleta): codigo="COBERTURA_INCOMPLETA"
        elif isinstance(exc,asyncio.CancelledError): codigo="CANCELADA"
        elif isinstance(exc,TimeoutError) or getattr(getattr(exc,"orig",None),"sqlstate",None)=="57014": codigo="LIMITE_DURACION"
        cph=progreso.modelo
        await cerrar_ejecucion(session,ejecucion_id,estado="FALLIDA",finalizado_en=datetime.now(timezone.utc),
            dataset_sha256=cph.metadatos.dataset_sha256 if cph else None,modelo_sha256=cph.sha256 if cph else None,
            entorno_modelo=cph.metadatos.entorno if cph else None,error_codigo=codigo,esperados=progreso.esperados,procesados=progreso.procesados)
        await session.commit()
        raise
    finally:
        if tarea:
            tarea.cancel()
            with suppress(asyncio.CancelledError):
                await tarea


async def correr_batch(session: AsyncSession | None = None) -> None:
    """Punto de entrada. Sin `session` (uso real/CLI): crea su propio engine desde
    DATABASE_URL del entorno. Con `session` (pruebas): reutiliza esa sesion
    transaccional directamente, sin crear un engine nuevo â€” asi las pruebas de
    integracion quedan aisladas por el rollback del fixture `db`, en vez de escribir
    fuera de esa transaccion y contaminar la base de pruebas compartida."""
    if session is not None:
        mensaje = await _ejecutar(session)
    else:
        engine: AsyncEngine = make_engine(os.environ["DATABASE_URL"])
        try:
            async with AsyncSession(engine, expire_on_commit=False) as s:
                mensaje = await _ejecutar(s,async_sessionmaker(engine,expire_on_commit=False))
        finally:
            await engine.dispose()
    # La salida es informativa: no altera una transacciÃ³n ya publicada.
    try:
        print(mensaje)
    except (OSError, ValueError):
        pass  # stdout cerrado/desconectado; la base conserva el resultado real.


if __name__ == "__main__":
    asyncio.run(correr_batch())
