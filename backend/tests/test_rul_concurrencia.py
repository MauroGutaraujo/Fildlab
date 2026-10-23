import asyncio

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.batch_predicciones import correr_batch
from app.models.ejecucion_rul import EjecucionRul, ResultadoRul
from app.models.prediccion_rul import PrediccionRul
from test_ml_batch_predicciones import entrada_controlada  # noqa: F401


async def test_otro_proceso_con_lock_impide_publicar_batch_simultaneo(engine):
    # Dos conexiones reales: simular un batch que aún posee su lock de publicación.
    async with AsyncSession(engine) as consulta:
        anteriores = set((await consulta.scalars(select(EjecucionRul.id))).all())
    try:
        async with engine.begin() as bloqueador:
            await bloqueador.execute(text("SELECT pg_advisory_xact_lock(hashtext('fildlab:rul-batch'))"))
            async with AsyncSession(engine, expire_on_commit=False) as otra:
                await asyncio.wait_for(correr_batch(session=otra), timeout=10)
                corrida = (await otra.scalars(select(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))).one()
                assert corrida.estado == "OMITIDA_CONCURRENCIA" and corrida.total == 0
                assert corrida.finalizado_en is not None
                assert not (await otra.scalars(select(ResultadoRul).where(ResultadoRul.ejecucion_id == corrida.id))).all()
    finally:
        async with AsyncSession(engine) as limpiar:
            nuevas = select(EjecucionRul.id).where(EjecucionRul.id.not_in(anteriores))
            await limpiar.execute(delete(PrediccionRul).where(PrediccionRul.ejecucion_id.in_(nuevas)))
            await limpiar.execute(delete(ResultadoRul).where(ResultadoRul.ejecucion_id.in_(nuevas)))
            await limpiar.execute(delete(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))
            await limpiar.commit()
