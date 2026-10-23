import asyncio

from sqlalchemy import func, text, update

from app.models.ejecucion_rul import EjecucionRul


async def emitir_latido(sesiones, ejecucion_id):
    # Sesión independiente: nunca compartir la transacción de publicación.
    async with sesiones() as session:
        await session.execute(text("SELECT set_config('statement_timeout','5000',true)"))
        resultado = await session.execute(update(EjecucionRul).where(
            EjecucionRul.id == ejecucion_id, EjecucionRul.estado == "EN_CURSO")
            .values(latido_en=func.greatest(EjecucionRul.latido_en,func.clock_timestamp())))
        await session.commit()
        return resultado.rowcount


async def latir(sesiones, ejecucion_id, intervalo):
    while True:
        try:
            if not await emitir_latido(sesiones,ejecucion_id):
                return
        except Exception:
            # El supervisor detectará señal perdida. Un fallo del canal de
            # supervisión no convierte una publicación válida en fallida.
            return
        await asyncio.sleep(intervalo)
