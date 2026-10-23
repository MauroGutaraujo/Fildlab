import asyncio
import hashlib
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.componente import AnulacionIntervencion, CambioComponente, ComponenteEquipo, IntervencionComponente
from app.models.orden import ActaInmutable, OrdenServicio
from app.models.usuario import Usuario
from app.schemas.componente import CorregirComponenteIn, IntervencionIn
from app.services.componentes import MantenimientoError, corregir_componente, registrar_intervencion
from test_ordenes_concurrencia import concurrente  # fixture aislado con filas identificadas


@pytest.fixture
async def componente_concurrente(engine, concurrente):
    seed = concurrente
    async with AsyncSession(engine, expire_on_commit=False) as s:
        gerente = Usuario(nombre="Gerencia", email=f"{uuid.uuid4()}@test.pe", password_hash="test", rol="GERENCIA")
        s.add(gerente)
        await s.flush()
        componente = ComponenteEquipo(equipo_serie=seed["series"][0], nombre="Membrana", tipo_componente="MEMBRANA", fecha_instalacion=date(2026,1,1), creado_por_id=gerente.id)
        orden = OrdenServicio(id=uuid.uuid4(), contrato_id=seed["contrato"], equipo_serie=seed["series"][0], tecnico_id=seed["tecnico"], tipo_intervencion="PREVENTIVO", estado="SINCRONIZADA", fecha_creacion_cliente=datetime(2026,2,5,17,tzinfo=timezone.utc))
        s.add_all([componente, orden])
        await s.flush()
        s.add(ActaInmutable(orden_id=orden.id, equipo_serie=orden.equipo_serie, payload_raw="{}", hash_sha256=hashlib.sha256(b"{}").hexdigest(), firma_base64="legacy", gps_latitud=-8, gps_longitud=-79))
        await s.commit()
    try:
        yield dict(serie=seed["series"][0], componente=componente.id, orden=orden.id, gerente=gerente.id)
    finally:
        async with AsyncSession(engine) as s:
            eventos = select(IntervencionComponente.id).where(IntervencionComponente.componente_id == componente.id)
            await s.execute(delete(CambioComponente).where(CambioComponente.componente_id == componente.id))
            await s.execute(delete(AnulacionIntervencion).where(AnulacionIntervencion.intervencion_id.in_(eventos)))
            await s.execute(delete(IntervencionComponente).where(IntervencionComponente.componente_id == componente.id))
            await s.execute(delete(ComponenteEquipo).where(ComponenteEquipo.id == componente.id))
            await s.execute(delete(ActaInmutable).where(ActaInmutable.orden_id == orden.id))
            await s.execute(delete(OrdenServicio).where(OrdenServicio.id == orden.id))
            await s.execute(delete(Usuario).where(Usuario.id == gerente.id))
            await s.commit()


async def test_uuid_simultaneo_registra_una_sola_sustitucion(engine, componente_concurrente):
    seed = componente_concurrente
    datos = IntervencionIn(id=uuid.uuid4(), orden_id=seed["orden"], tipo="SUSTITUCION", fecha_efectiva=date(2026,2,1), observacion="Pieza sustituida")
    async def registrar():
        async with AsyncSession(engine, expire_on_commit=False) as s:
            actor = await s.get(Usuario, seed["gerente"])
            evento, nuevo = await registrar_intervencion(s, seed["serie"], seed["componente"], datos, actor)
            await s.commit()
            return evento["id"], nuevo
    resultados = await asyncio.wait_for(asyncio.gather(registrar(), registrar()), timeout=10)
    assert [r[0] for r in resultados] == [datos.id, datos.id]
    assert sorted(r[1] for r in resultados) == [False, True]
    async with AsyncSession(engine) as s:
        assert await s.scalar(select(func.count()).select_from(IntervencionComponente).where(IntervencionComponente.componente_id == seed["componente"])) == 1


async def test_misma_correccion_simultanea_es_idempotente(engine, componente_concurrente):
    seed = componente_concurrente
    datos = CorregirComponenteIn(solicitud_id=uuid.uuid4(), revision_esperada=1, motivo="Etiqueta contrastada",
        nombre="Membrana etapa 1 corregida", tipo_componente="MEMBRANA", fecha_instalacion=date(2026,1,2), fabricante_modelo="Modelo verificado")
    async def corregir():
        async with AsyncSession(engine, expire_on_commit=False) as s:
            actor = await s.get(Usuario, seed["gerente"])
            ficha, nueva = await corregir_componente(s, seed["serie"], seed["componente"], datos, actor)
            await s.commit()
            return ficha["revision"], nueva
    resultados = await asyncio.wait_for(asyncio.gather(corregir(), corregir()), timeout=10)
    assert sorted(r[1] for r in resultados) == [False, True]
    assert [r[0] for r in resultados] == [2,2]
    async with AsyncSession(engine) as s:
        assert await s.scalar(select(func.count()).select_from(CambioComponente).where(CambioComponente.componente_id == seed["componente"])) == 1


async def test_ediciones_simultaneas_una_sola_gana_revision(engine, componente_concurrente):
    seed = componente_concurrente
    async def corregir(nombre):
        datos = CorregirComponenteIn(solicitud_id=uuid.uuid4(), revision_esperada=1, motivo="Ficha confirmada",
            nombre=nombre, tipo_componente="MEMBRANA", fecha_instalacion=date(2026,1,2), fabricante_modelo="Modelo verificado")
        async with AsyncSession(engine, expire_on_commit=False) as s:
            actor = await s.get(Usuario, seed["gerente"])
            try:
                ficha, _ = await corregir_componente(s, seed["serie"], seed["componente"], datos, actor)
                await s.commit()
                return ficha["revision"], None
            except MantenimientoError as exc:
                await s.rollback()
                return None, exc.status_code
    resultados = await asyncio.wait_for(asyncio.gather(corregir("Membrana A"), corregir("Membrana B")), timeout=10)
    assert sorted(r[1] for r in resultados if r[1] is not None) == [409]
    assert sorted(r[0] for r in resultados if r[0] is not None) == [2]
    async with AsyncSession(engine) as s:
        assert await s.scalar(select(func.count()).select_from(CambioComponente).where(CambioComponente.componente_id == seed["componente"])) == 1
