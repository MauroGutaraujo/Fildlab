from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.orden import OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto
from app.models.usuario import Usuario
from app.schemas.inventario import MovimientoIn, MovimientoOut, RepuestoIn, RepuestoOut
from app.services import inventario as svc

router = APIRouter(tags=["inventario"], dependencies=[Depends(get_current_user)])
solo_gerencia = Depends(require_role("GERENCIA"))


@router.get("/repuestos", response_model=list[RepuestoOut])
async def listar_repuestos(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Repuesto).order_by(Repuesto.codigo))).scalars().all()


@router.get("/repuestos/{codigo}", response_model=RepuestoOut)
async def leer_repuesto(codigo: str, session: AsyncSession = Depends(get_session)):
    repuesto = await session.get(Repuesto, codigo)
    if repuesto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Repuesto no encontrado")
    return repuesto


@router.post("/repuestos", response_model=RepuestoOut, status_code=status.HTTP_201_CREATED, dependencies=[solo_gerencia])
async def crear_repuesto(datos: RepuestoIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Repuesto, datos.codigo) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un repuesto con ese código")
    repuesto = Repuesto(**datos.model_dump(), stock_almacen_central=0)
    session.add(repuesto)
    await session.flush()
    await session.refresh(repuesto)
    return repuesto


@router.get("/inventario/movimientos", response_model=list[MovimientoOut])
async def listar_movimientos(repuesto: str | None = None, session: AsyncSession = Depends(get_session)):
    q = select(MovimientoInventario).order_by(MovimientoInventario.id.desc())
    if repuesto:
        q = q.where(MovimientoInventario.repuesto_codigo == repuesto)
    return (await session.execute(q)).scalars().all()


@router.post("/inventario/movimientos", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def registrar(
    datos: MovimientoIn,
    session: AsyncSession = Depends(get_session),
    usuario: Usuario = Depends(require_role("GERENCIA")),
):
    if datos.orden_id is not None and await session.get(OrdenServicio, datos.orden_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden no encontrada")
    try:
        return await svc.registrar_movimiento(
            session, datos.repuesto_codigo, datos.tipo, datos.cantidad, usuario.id, orden_id=datos.orden_id
        )
    except svc.RepuestoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Repuesto no encontrado") from None
    except svc.StockInsuficiente as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
    except svc.MovimientoInvalido as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from None
