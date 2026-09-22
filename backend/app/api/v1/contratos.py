from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.schemas.contrato import ContratoIn, ContratoOut, ContratoUpdate

router = APIRouter(prefix="/contratos", tags=["contratos"], dependencies=[Depends(get_current_user)])
solo_gerencia = Depends(require_role("GERENCIA"))  # RN-01


async def _obtener(session: AsyncSession, contrato_id: int) -> Contrato:
    contrato = await session.get(Contrato, contrato_id)
    if contrato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato no encontrado")
    return contrato


@router.get("", response_model=list[ContratoOut])
async def listar(cliente_ruc: str | None = None, session: AsyncSession = Depends(get_session)):
    q = select(Contrato).order_by(Contrato.id)
    if cliente_ruc:
        q = q.where(Contrato.cliente_ruc == cliente_ruc)
    return (await session.execute(q)).scalars().all()


@router.get("/{contrato_id}", response_model=ContratoOut)
async def leer(contrato_id: int, session: AsyncSession = Depends(get_session)):
    return await _obtener(session, contrato_id)


@router.post("", response_model=ContratoOut, status_code=status.HTTP_201_CREATED, dependencies=[solo_gerencia])
async def crear(datos: ContratoIn, session: AsyncSession = Depends(get_session)):
    cliente = await session.get(Cliente, datos.cliente_ruc)
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    if not cliente.activo:
        raise HTTPException(status.HTTP_409_CONFLICT, "El cliente está anulado")
    contrato = Contrato(**datos.model_dump())
    session.add(contrato)
    await session.flush()
    await session.refresh(contrato)
    return contrato


@router.put("/{contrato_id}", response_model=ContratoOut, dependencies=[solo_gerencia])
async def actualizar(contrato_id: int, datos: ContratoUpdate, session: AsyncSession = Depends(get_session)):
    contrato = await _obtener(session, contrato_id)
    if contrato.estado == "ANULADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "Un contrato anulado no se puede modificar")
    for campo, valor in datos.model_dump().items():
        setattr(contrato, campo, valor)
    await session.flush()
    await session.refresh(contrato)
    return contrato


@router.post("/{contrato_id}/anular", response_model=ContratoOut, dependencies=[solo_gerencia])
async def anular(contrato_id: int, session: AsyncSession = Depends(get_session)):
    contrato = await _obtener(session, contrato_id)
    if contrato.estado == "ANULADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "El contrato ya está anulado")
    contrato.estado = "ANULADO"
    await session.flush()
    return contrato
