from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.schemas.cliente import ClienteIn, ClienteOut, ClienteUpdate

router = APIRouter(prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_current_user)])
solo_gerencia = Depends(require_role("GERENCIA"))  # RN-01


async def _obtener(session: AsyncSession, ruc: str) -> Cliente:
    cliente = await session.get(Cliente, ruc)
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return cliente


@router.get("", response_model=list[ClienteOut])
async def listar(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Cliente).order_by(Cliente.razon_social))).scalars().all()


@router.get("/{ruc}", response_model=ClienteOut)
async def leer(ruc: str, session: AsyncSession = Depends(get_session)):
    return await _obtener(session, ruc)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED, dependencies=[solo_gerencia])
async def crear(datos: ClienteIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Cliente, datos.ruc) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese RUC")
    cliente = Cliente(**datos.model_dump())
    session.add(cliente)
    await session.flush()
    return cliente


@router.put("/{ruc}", response_model=ClienteOut, dependencies=[solo_gerencia])
async def actualizar(ruc: str, datos: ClienteUpdate, session: AsyncSession = Depends(get_session)):
    cliente = await _obtener(session, ruc)
    cliente.razon_social = datos.razon_social
    cliente.direccion = datos.direccion
    await session.flush()
    return cliente


@router.delete("/{ruc}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[solo_gerencia])
async def anular(ruc: str, session: AsyncSession = Depends(get_session)):
    cliente = await _obtener(session, ruc)
    con_contrato = await session.execute(
        select(Contrato.id).where(Contrato.cliente_ruc == ruc, Contrato.estado == "ACTIVO").limit(1)
    )
    if con_contrato.first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El cliente tiene contratos activos")
    cliente.activo = False
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
