import hashlib
import platform
from importlib.metadata import version

from sqlalchemy import text, update

from app.models.ejecucion_rul import EjecucionRul


def entorno_calculo() -> dict:
    return {"python": platform.python_version(), **{p: version(p) for p in ("lifelines", "numpy", "pandas")}}


def huella_dataset(dataset) -> str:
    return hashlib.sha256(dataset.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


async def adquirir_batch(session) -> bool:
    return await session.scalar(text("SELECT pg_try_advisory_xact_lock(hashtext('fildlab:rul-batch'))"))


async def cerrar_ejecucion(session, ejecucion_id, *, estado, finalizado_en, **campos):
    resultado = await session.execute(update(EjecucionRul).where(EjecucionRul.id == ejecucion_id, EjecucionRul.estado == "EN_CURSO")
        .values(estado=estado, finalizado_en=finalizado_en, **campos)
        .execution_options(synchronize_session=False))
    return resultado.rowcount
