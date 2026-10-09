import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.db import make_engine
from app.ml.dataset_sintetico import generar_dataset
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, calificar_equipo
from app.models.equipo import TIPOS_SISTEMA, Equipo

_UPSERT_SQL = text(
    """
    INSERT INTO predicciones_rul (equipo_serie, dias_vida_util_remanente, nivel_alerta, actualizado_en)
    VALUES (:serie, :dias, :nivel, now())
    ON CONFLICT (equipo_serie) DO UPDATE
    SET dias_vida_util_remanente = EXCLUDED.dias_vida_util_remanente,
        nivel_alerta = EXCLUDED.nivel_alerta,
        actualizado_en = EXCLUDED.actualizado_en
    """
)


async def _ejecutar(session: AsyncSession) -> None:
    dataset = generar_dataset()
    cph = ajustar_modelo(dataset)

    equipos = (await session.execute(select(Equipo))).scalars().all()
    hoy = datetime.now(timezone.utc).date()

    resultados = []
    for e in equipos:
        if e.tipo_sistema not in TIPOS_SISTEMA:
            print(f"WARN: equipo {e.serie} omitido — tipo_sistema desconocido: {e.tipo_sistema}")
            continue
        # El reloj de vida util remanente se reinicia desde el ultimo mantenimiento
        # registrado (app/api/v1/equipos.py::marcar_mantenimiento), si existe uno.
        fecha_referencia = e.fecha_ultima_mantencion or e.fecha_instalacion
        try:
            r = calificar_equipo(cph, e.tipo_sistema, fecha_referencia, hoy)
        except ParametrosImposibles as exc:
            print(f"WARN: equipo {e.serie} omitido — {exc}")
            continue
        resultados.append((e.serie, r["dias_vida_util_remanente"], r["nivel_alerta"]))

    if not resultados:
        print("No hay equipos reales para calificar.")
        await session.commit()
        return

    for serie, dias, nivel in resultados:
        await session.execute(_UPSERT_SQL, {"serie": serie, "dias": dias, "nivel": nivel})
    await session.commit()
    print(f"OK: {len(resultados)} equipos calificados.")


async def correr_batch(session: AsyncSession | None = None) -> None:
    """Punto de entrada. Sin `session` (uso real/CLI): crea su propio engine desde
    DATABASE_URL del entorno. Con `session` (pruebas): reutiliza esa sesion
    transaccional directamente, sin crear un engine nuevo — asi las pruebas de
    integracion quedan aisladas por el rollback del fixture `db`, en vez de escribir
    fuera de esa transaccion y contaminar la base de pruebas compartida."""
    if session is not None:
        await _ejecutar(session)
        return

    engine: AsyncEngine = make_engine(os.environ["DATABASE_URL"])
    try:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            await _ejecutar(s)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(correr_batch())
