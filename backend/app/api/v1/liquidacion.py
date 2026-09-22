import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.orden import AdendaCorreccion, OrdenServicio
from app.models.usuario import Usuario
from app.schemas.liquidacion import AdendaIn, AdendaOut, EstadoOrden, OrdenOut
from app.services import inventario as inv
from app.services import liquidacion as svc

router = APIRouter(prefix="/ordenes", tags=["liquidacion"], dependencies=[Depends(get_current_user)])
solo_gerencia = Depends(require_role("GERENCIA"))


def _no_encontrada() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Orden no encontrada")


@router.get("", response_model=list[OrdenOut])
async def listar(estado: EstadoOrden | None = None, session: AsyncSession = Depends(get_session)):
    q = select(OrdenServicio).order_by(OrdenServicio.fecha_sincronizacion.desc())
    if estado:
        q = q.where(OrdenServicio.estado == estado)
    return (await session.execute(q)).scalars().all()


@router.get("/{orden_id}", response_model=OrdenOut)
async def leer(orden_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    orden = await session.get(OrdenServicio, orden_id)
    if orden is None:
        raise _no_encontrada()
    return orden


@router.post("/{orden_id}/liquidar", response_model=OrdenOut, dependencies=[solo_gerencia])
async def liquidar(orden_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    try:
        return await svc.liquidar(session, orden_id)
    except svc.OrdenNoEncontrada:
        raise _no_encontrada() from None
    except svc.OrdenYaLiquidada:
        raise HTTPException(status.HTTP_409_CONFLICT, "La orden ya está liquidada") from None


@router.get("/{orden_id}/adendas", response_model=list[AdendaOut])
async def listar_adendas(orden_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if await session.get(OrdenServicio, orden_id) is None:
        raise _no_encontrada()
    q = select(AdendaCorreccion).where(AdendaCorreccion.orden_id == orden_id).order_by(AdendaCorreccion.id)
    return (await session.execute(q)).scalars().all()


@router.post("/{orden_id}/adendas", response_model=AdendaOut, status_code=status.HTTP_201_CREATED)
async def crear_adenda(
    orden_id: uuid.UUID,
    datos: AdendaIn,
    session: AsyncSession = Depends(get_session),
    gerente: Usuario = Depends(require_role("GERENCIA")),
):
    try:
        return await svc.crear_adenda(session, orden_id, gerente.id, datos)
    except svc.OrdenNoEncontrada:
        raise _no_encontrada() from None
    except inv.RepuestoNoEncontrado as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Repuesto no encontrado: {e}") from None
    except inv.StockInsuficiente as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
