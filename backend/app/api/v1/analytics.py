from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.schemas.analytics import Periodo, RentabilidadOut, SlaOut
from app.services import analytics as svc

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_role("GERENCIA"))])


@router.get("/rentabilidad", response_model=RentabilidadOut)
async def rentabilidad(periodo: Periodo, session: AsyncSession = Depends(get_session)):
    contratos = await svc.rentabilidad_por_contrato(session, periodo)
    return {"periodo": periodo, "contratos": contratos}


@router.get("/sla", response_model=SlaOut)
async def sla(periodo: Periodo, session: AsyncSession = Depends(get_session)):
    datos = await svc.cumplimiento_sla(session, periodo)
    return {"periodo": periodo, **datos}
