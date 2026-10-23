from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.ejecucion_rul import EjecucionRul, ResultadoRul
from app.models.equipo import Equipo
from app.schemas.historial_rul import EjecucionRulOut, PaginaRul, ResultadoHistoricoOut
from app.schemas.supervision_rul import SupervisionRulOut
from app.services.supervision_rul import supervisar

router = APIRouter(prefix="/equipos", tags=["historial RUL"], dependencies=[Depends(get_current_user)])


@router.get("/supervision-rul",response_model=SupervisionRulOut,dependencies=[Depends(require_role("GERENCIA"))])
async def supervision(session:AsyncSession=Depends(get_session)):
    return await supervisar(session)


@router.get("/ejecuciones-rul", response_model=PaginaRul[EjecucionRulOut], dependencies=[Depends(require_role("GERENCIA"))])
async def ejecuciones(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                      session: AsyncSession = Depends(get_session)):
    total = await session.scalar(select(func.count()).select_from(EjecucionRul))
    filas = (await session.scalars(select(EjecucionRul).order_by(EjecucionRul.iniciado_en.desc(), EjecucionRul.id.desc())
                                  .limit(limit).offset(offset))).all()
    return dict(items=filas, total=total, limit=limit, offset=offset)


@router.get("/{serie}/historial-rul", response_model=PaginaRul[ResultadoHistoricoOut])
async def historial(serie: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                    session: AsyncSession = Depends(get_session)):
    if await session.get(Equipo, serie) is None:
        raise HTTPException(404, "Equipo no encontrado")
    total = await session.scalar(select(func.count()).select_from(ResultadoRul).where(ResultadoRul.equipo_serie == serie))
    filas = (await session.execute(select(ResultadoRul, EjecucionRul.version_dataset, EjecucionRul.politica_alerta,
        EjecucionRul.dataset_sha256, EjecucionRul.modelo_sha256).outerjoin(EjecucionRul, ResultadoRul.ejecucion_id == EjecucionRul.id)
        .where(ResultadoRul.equipo_serie == serie)
        .order_by(ResultadoRul.calculado_en.desc(), ResultadoRul.id.desc()).limit(limit).offset(offset))).all()
    items = [{**{c.name: getattr(r, c.name) for c in ResultadoRul.__table__.columns},
              "version_dataset": version, "politica_alerta": politica, "dataset_sha256": huella, "modelo_sha256": modelo}
             for r, version, politica, huella, modelo in filas]
    return dict(items=items, total=total, limit=limit, offset=offset)
