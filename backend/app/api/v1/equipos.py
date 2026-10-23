from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.core.politica_rul import VERSION_CALCULO
from app.models.cliente import Cliente
from app.models.componente import ComponenteEquipo, IntervencionComponente
from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul
from app.schemas.equipo import EquipoIn, EquipoOut, EquipoUpdate
from app.schemas.prediccion_rul import PrediccionRulOut

router = APIRouter(prefix="/equipos", tags=["equipos"], dependencies=[Depends(get_current_user)])
solo_gerencia = Depends(require_role("GERENCIA"))


async def _validar_contrato(session: AsyncSession, contrato_id: int | None, cliente_ruc: str) -> None:
    if contrato_id is None:
        return
    contrato = await session.get(Contrato, contrato_id)
    if contrato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato no encontrado")
    if contrato.cliente_ruc != cliente_ruc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El contrato pertenece a otro cliente")
    if contrato.estado == "ANULADO":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El contrato está anulado")


async def _obtener(session: AsyncSession, serie: str) -> Equipo:
    equipo = await session.get(Equipo, serie)
    if equipo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    return equipo


@router.get("/predicciones-rul", response_model=list[PrediccionRulOut])
async def listar_predicciones_rul(session: AsyncSession = Depends(get_session)):
    filas = (await session.execute(select(PrediccionRul, Equipo.fecha_instalacion, Equipo.tipo_sistema)
             .join(Equipo, Equipo.serie == PrediccionRul.equipo_serie))).all()
    return [_presentar_prediccion(p, fecha, tipo) for p, fecha, tipo in filas]


def _presentar_prediccion(prediccion: PrediccionRul, fecha_actual: date, tipo_actual: str) -> PrediccionRulOut:
    datos = {c.name: getattr(prediccion, c.name) for c in prediccion.__table__.columns}
    if prediccion.version_calculo == VERSION_CALCULO and (prediccion.fecha_referencia != fecha_actual
            or prediccion.tipo_referencia != tipo_actual):
        datos["motivo_no_estimable"] = "REQUIERE_RECALCULO"
    return PrediccionRulOut.model_validate(datos)


@router.get("/{serie}/prediccion-rul", response_model=PrediccionRulOut)
async def leer_prediccion_rul(serie: str, session: AsyncSession = Depends(get_session)):
    equipo = await _obtener(session, serie)
    prediccion = await session.get(PrediccionRul, serie)
    if prediccion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aún no hay predicción RUL para este equipo")
    return _presentar_prediccion(prediccion, equipo.fecha_instalacion, equipo.tipo_sistema)


@router.get("", response_model=list[EquipoOut])
async def listar(cliente_ruc: str | None = None, session: AsyncSession = Depends(get_session)):
    q = select(Equipo).order_by(Equipo.serie)
    if cliente_ruc:
        q = q.where(Equipo.cliente_ruc == cliente_ruc)
    return (await session.execute(q)).scalars().all()


@router.get("/{serie}", response_model=EquipoOut)
async def leer(serie: str, session: AsyncSession = Depends(get_session)):
    return await _obtener(session, serie)


@router.post("", response_model=EquipoOut, status_code=status.HTTP_201_CREATED, dependencies=[solo_gerencia])
async def crear(datos: EquipoIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Cliente, datos.cliente_ruc) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    await _validar_contrato(session, datos.contrato_id, datos.cliente_ruc)
    if await session.get(Equipo, datos.serie) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un equipo con esa serie")
    equipo = Equipo(**datos.model_dump())
    session.add(equipo)
    await session.flush()
    return equipo


@router.put("/{serie}", response_model=EquipoOut, dependencies=[solo_gerencia])
async def actualizar(serie: str, datos: EquipoUpdate, session: AsyncSession = Depends(get_session)):
    equipo = (await session.scalars(select(Equipo).where(Equipo.serie == serie)
              .with_for_update().execution_options(populate_existing=True))).one_or_none()
    if equipo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    cambios = datos.model_dump(exclude_unset=True)
    fecha = cambios.get("fecha_instalacion")
    if fecha is not None:
        previo = await session.scalar(select(ComponenteEquipo.id).where(
            ComponenteEquipo.equipo_serie == serie, ComponenteEquipo.fecha_instalacion < fecha).limit(1))
        evento = await session.scalar(select(IntervencionComponente.id).join(ComponenteEquipo,
            ComponenteEquipo.id == IntervencionComponente.componente_id).where(
            ComponenteEquipo.equipo_serie == serie, IntervencionComponente.fecha_efectiva < fecha).limit(1))
        if previo is not None or evento is not None:
            raise HTTPException(422, "La instalación no puede ser posterior al historial de componentes")
    if "contrato_id" in cambios:
        await _validar_contrato(session, cambios["contrato_id"], equipo.cliente_ruc)
    for campo, valor in cambios.items():
        if valor is None and campo != "contrato_id":
            continue  # fecha/parámetros no se pueden borrar
        setattr(equipo, campo, valor)
    await session.flush()
    return equipo


@router.post("/{serie}/marcar-mantenimiento", deprecated=True, dependencies=[solo_gerencia])
async def marcar_mantenimiento(serie: str, session: AsyncSession = Depends(get_session)):
    await _obtener(session, serie)
    raise HTTPException(410, "Registra la intervención del componente y su orden en Componentes y mantenimiento")
