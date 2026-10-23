from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.models.usuario import Usuario
from app.schemas.componente import (AnulacionIn, AnulacionOut, AnularAltaIn, CambioComponenteOut,
    ComponenteIn, ComponenteOut, CorregirComponenteIn, IntervencionIn, IntervencionOut,
    OrdenFirmadaOut, RestablecerComponenteIn)
from app.services import componentes as servicio

router = APIRouter(prefix="/equipos", tags=["componentes"], dependencies=[Depends(get_current_user)])
gerencia = require_role("GERENCIA")


async def _respuesta(operacion):
    try:
        return await operacion
    except servicio.MantenimientoError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/{serie}/componentes", response_model=list[ComponenteOut])
async def listar(serie: str, incluir_anulados: bool = False, session: AsyncSession = Depends(get_session)):
    return await _respuesta(servicio.listar_componentes(session, serie, incluir_anulados))


@router.post("/{serie}/componentes", response_model=ComponenteOut, status_code=201)
async def crear(serie: str, datos: ComponenteIn, usuario: Usuario = Depends(gerencia), session: AsyncSession = Depends(get_session)):
    return await _respuesta(servicio.crear_componente(session, serie, datos, usuario))


@router.post("/{serie}/componentes/{componente_id}/correcciones", response_model=ComponenteOut, status_code=201)
async def corregir(serie: str, componente_id: UUID, datos: CorregirComponenteIn, response: Response,
                   usuario: Usuario = Depends(gerencia), session: AsyncSession = Depends(get_session)):
    ficha, nueva = await _respuesta(servicio.corregir_componente(session, serie, componente_id, datos, usuario))
    response.status_code = 201 if nueva else 200
    return ficha


@router.post("/{serie}/componentes/{componente_id}/anular-alta", response_model=ComponenteOut, status_code=201)
async def anular_alta(serie: str, componente_id: UUID, datos: AnularAltaIn, response: Response,
                      usuario: Usuario = Depends(gerencia), session: AsyncSession = Depends(get_session)):
    ficha, nueva = await _respuesta(servicio.anular_alta(session, serie, componente_id, datos, usuario))
    response.status_code = 201 if nueva else 200
    return ficha


@router.post("/{serie}/componentes/{componente_id}/restablecer-alta", response_model=ComponenteOut, status_code=201)
async def restablecer_alta(serie: str, componente_id: UUID, datos: RestablecerComponenteIn, response: Response,
                           usuario: Usuario = Depends(gerencia), session: AsyncSession = Depends(get_session)):
    ficha, nueva = await _respuesta(servicio.restablecer_alta(session, serie, componente_id, datos, usuario))
    response.status_code = 201 if nueva else 200
    return ficha


@router.get("/{serie}/componentes/{componente_id}/cambios", response_model=list[CambioComponenteOut])
async def cambios(serie: str, componente_id: UUID, limit: int = Query(default=50, ge=1, le=100),
                  offset: int = Query(default=0, ge=0), session: AsyncSession = Depends(get_session)):
    return await _respuesta(servicio.cambios_componente(session, serie, componente_id, limit, offset))


@router.get("/{serie}/ordenes-firmadas", response_model=list[OrdenFirmadaOut], dependencies=[Depends(gerencia)])
async def ordenes(serie: str, session: AsyncSession = Depends(get_session)):
    return await _respuesta(servicio.ordenes_firmadas(session, serie))


@router.get("/{serie}/componentes/{componente_id}/intervenciones", response_model=list[IntervencionOut])
async def historial(serie: str, componente_id: UUID, session: AsyncSession = Depends(get_session)):
    return await _respuesta(servicio.historial(session, serie, componente_id))


@router.post("/{serie}/componentes/{componente_id}/intervenciones", response_model=IntervencionOut, status_code=201)
async def registrar(serie: str, componente_id: UUID, datos: IntervencionIn, response: Response,
                    usuario: Usuario = Depends(gerencia), session: AsyncSession = Depends(get_session)):
    evento, nuevo = await _respuesta(servicio.registrar_intervencion(session, serie, componente_id, datos, usuario))
    response.status_code = 201 if nuevo else 200
    return evento


@router.post("/{serie}/componentes/{componente_id}/intervenciones/{intervencion_id}/anular", response_model=AnulacionOut, status_code=201)
async def anular(serie: str, componente_id: UUID, intervencion_id: UUID, datos: AnulacionIn, response: Response,
                 usuario: Usuario = Depends(gerencia), session: AsyncSession = Depends(get_session)):
    anulacion, nueva = await _respuesta(servicio.anular_intervencion(session, serie, componente_id, intervencion_id, datos, usuario))
    response.status_code = 201 if nueva else 200
    return anulacion
