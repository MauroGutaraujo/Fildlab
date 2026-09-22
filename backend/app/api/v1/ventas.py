from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.schemas.venta import VentaIn, VentaOut
from app.services import inventario as inv
from app.services import ventas as svc

router = APIRouter(prefix="/ventas", tags=["ventas"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[VentaOut])
async def listar(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Venta).order_by(Venta.id.desc()))).scalars().all()


@router.get("/{venta_id}", response_model=VentaOut)
async def leer(venta_id: int, session: AsyncSession = Depends(get_session)):
    venta = await session.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    return venta


@router.post("", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
async def crear(
    datos: VentaIn,
    session: AsyncSession = Depends(get_session),
    usuario: Usuario = Depends(require_role("GERENCIA")),
):
    try:
        return await svc.crear_venta(session, datos, usuario.id)
    except (svc.ClienteNoEncontrado, inv.RepuestoNoEncontrado) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No encontrado: {e}") from None
    except svc.ClienteAnulado:
        raise HTTPException(status.HTTP_409_CONFLICT, "El cliente está anulado") from None
    except inv.StockInsuficiente as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
