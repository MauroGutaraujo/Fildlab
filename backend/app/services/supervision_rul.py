"""Avisos de lectura: ausencia de latido no certifica que un proceso murió."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func,select

from app.core.supervision_rul import PoliticaSupervision
from app.models.ejecucion_rul import EjecucionRul,ResultadoRul
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul


def evaluar_supervision(*,ahora,reciente,exitosa,fallida,activas,cantidad_activas,total_equipos,sin_evaluar,resultados_exito,politica):
    avisos=[]
    def agregar(codigo,mensaje,c=None,severidad="AVISO"):
        avisos.append(dict(codigo=codigo,mensaje=mensaje,severidad=severidad,ejecucion_id=c.id if c else None))
    curso_actual=False
    local=ahora.astimezone(ZoneInfo("America/Lima"))
    exigible=local.replace(hour=3,minute=0,second=0,microsecond=0)
    if local < exigible+timedelta(hours=politica.gracia_cron_horas):
        exigible-=timedelta(days=1)
    for c in activas:
        if c.latido_en is None or c.limite_en is None:
            agregar("SUPERVISION_DESCONOCIDA","Ejecución sin cierre y sin metadatos de actividad: revisar su estado.",c)
        elif c.latido_en > ahora or c.iniciado_en > ahora:
            agregar("RELOJ_INCONSISTENTE","La señal de actividad tiene una fecha futura; revisar relojes del servicio.",c)
        elif (ahora-c.latido_en).total_seconds() >= politica.silencio_segundos:
            agregar("ACTIVIDAD_NO_CONFIRMADA","Se perdió la señal de actividad. Puede haber una interrupción o un problema de conexión; revisar la ejecución.",c)
        elif ahora >= c.limite_en:
            agregar("PLAZO_SUPERADO","La ejecución supera su plazo y aún presenta actividad reciente; revisar antes de reintentar.",c)
        else:
            curso_actual |= c.iniciado_en >= exigible
            agregar("EJECUCION_ACTIVA","Ejecución con señal reciente y dentro del plazo.",c,"INFO")
    if cantidad_activas > len(activas):
        agregar("MAS_EJECUCIONES_SIN_CIERRE",f"Hay {cantidad_activas} ejecuciones sin cierre; se muestran las más antiguas. Revisar historial.")
    if fallida and (not exitosa or fallida.iniciado_en >= exitosa.iniciado_en):
        agregar("EJECUCION_FALLIDA",f"La última ejecución fallida registra {fallida.error_codigo or 'ERROR_NO_ESPECIFICADO'}; aún no hay un éxito posterior.",fallida)
    if exitosa:
        if exitosa.finalizado_en > ahora:
            agregar("RELOJ_INCONSISTENTE","La última finalización tiene fecha futura; no se puede confirmar su vigencia.",exitosa)
        if resultados_exito != exitosa.total or (exitosa.esperados is not None and
                (exitosa.total != exitosa.esperados or exitosa.procesados != exitosa.esperados)):
            agregar("RESULTADOS_INCOMPLETOS","La cobertura de la última ejecución completada no coincide con lo registrado; revisar resultados.",exitosa)
        elif exitosa.esperados is None or exitosa.procesados is None:
            agregar("COBERTURA_DESCONOCIDA","La ejecución anterior no registró cobertura de su instantánea.",exitosa,"INFO")
    if total_equipos:
        if reciente is None:
            agregar("SIN_EJECUCIONES","Hay equipos y todavía no existen ejecuciones registradas de IA.")
        elif not curso_actual and (exitosa is None or exitosa.iniciado_en < exigible):
            agregar("ACTUALIZACION_DIARIA_AUSENTE","No hay una actualización exitosa para el ciclo diario después de la tolerancia del cron de Lima.")
    estado="ATENCION" if any(a["severidad"]=="AVISO" for a in avisos) else "NORMAL" if total_equipos else "SIN_EQUIPOS"
    return dict(consultado_en=ahora,estado=estado,avisos=avisos,ultima_exitosa_en=exitosa.finalizado_en if exitosa else None,
        total_equipos=total_equipos,equipos_sin_evaluar=sin_evaluar,ejecuciones_sin_cierre=cantidad_activas)


async def supervisar(session):
    async def ultima(estado=None):
        q=select(EjecucionRul)
        if estado: q=q.where(EjecucionRul.estado==estado)
        return await session.scalar(q.order_by(EjecucionRul.iniciado_en.desc(),EjecucionRul.id.desc()).limit(1))
    reciente=await ultima()
    exitosa=await ultima("COMPLETADA")
    fallida=await ultima("FALLIDA")
    activas=(await session.scalars(select(EjecucionRul).where(EjecucionRul.estado=="EN_CURSO")
        .order_by(EjecucionRul.iniciado_en,EjecucionRul.id).limit(20))).all()
    cantidad=await session.scalar(select(func.count()).select_from(EjecucionRul).where(EjecucionRul.estado=="EN_CURSO"))
    equipos=await session.scalar(select(func.count()).select_from(Equipo))
    sin=await session.scalar(select(func.count()).select_from(Equipo).outerjoin(PrediccionRul,Equipo.serie==PrediccionRul.equipo_serie)
        .where(PrediccionRul.equipo_serie.is_(None)))
    resultados=await session.scalar(select(func.count()).select_from(ResultadoRul).where(ResultadoRul.ejecucion_id==exitosa.id)) if exitosa else 0
    return evaluar_supervision(ahora=datetime.now(timezone.utc),reciente=reciente,exitosa=exitosa,fallida=fallida,
        activas=activas,cantidad_activas=cantidad,total_equipos=equipos,sin_evaluar=sin,resultados_exito=resultados,politica=PoliticaSupervision())
