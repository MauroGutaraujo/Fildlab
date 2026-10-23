from datetime import datetime,timedelta,timezone
from uuid import uuid4

from sqlalchemy import delete,select,update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.ml.latido_rul import emitir_latido
from app.models.ejecucion_rul import EjecucionRul


async def test_pipeline_con_latido_real_cierra_y_no_deja_tarea_pendiente(engine):
    import asyncio
    from app.ml.batch_predicciones import _ejecutar
    sesiones=async_sessionmaker(engine,expire_on_commit=False)
    async with sesiones() as s:
        anteriores=set((await s.scalars(select(EjecucionRul.id))).all())
    try:
        async with sesiones() as s:
            await asyncio.wait_for(_ejecutar(s,sesiones),timeout=15)
        async with sesiones() as s:
            corrida=(await s.scalars(select(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))).one()
            assert corrida.estado=="COMPLETADA" and corrida.esperados==corrida.procesados==corrida.total==0
            assert corrida.latido_en>=corrida.iniciado_en
        assert not [t for t in asyncio.all_tasks() if getattr(t.get_coro(),"__name__","")=="latir" and not t.done()]
    finally:
        async with sesiones() as s:
            await s.execute(delete(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))
            await s.commit()


async def test_latido_independiente_visible_y_terminal_no_se_reanima(engine):
    sesiones=async_sessionmaker(engine,expire_on_commit=False)
    identidad=uuid4()
    antiguo=datetime.now(timezone.utc)-timedelta(minutes=5)
    try:
        async with sesiones() as s:
            s.add(EjecucionRul(id=identidad,iniciado_en=antiguo,latido_en=antiguo,limite_en=antiguo+timedelta(minutes=10),
                estado="EN_CURSO",version_calculo="COX_INSTALACION_V3",version_dataset="WEIBULL_CENSURA_V2",
                politica_alerta="RUL_30_90_V1",entorno={},vigencia_horas=48))
            await s.commit()
        assert await emitir_latido(sesiones,identidad)==1
        async with sesiones() as otra:
            corrida=await otra.get(EjecucionRul,identidad)
            assert corrida.latido_en>antiguo
            guardado=corrida.latido_en
            await otra.execute(update(EjecucionRul).where(EjecucionRul.id==identidad).values(estado="COMPLETADA",finalizado_en=datetime.now(timezone.utc)))
            await otra.commit()
        assert await emitir_latido(sesiones,identidad)==0
        async with sesiones() as otra:
            corrida=await otra.get(EjecucionRul,identidad)
            assert corrida.estado=="COMPLETADA" and corrida.latido_en==guardado
    finally:
        async with sesiones() as s:
            await s.execute(delete(EjecucionRul).where(EjecucionRul.id==identidad))
            await s.commit()
