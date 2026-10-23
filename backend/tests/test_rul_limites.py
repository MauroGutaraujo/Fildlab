import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.ml.batch_predicciones as batch
from app.ml.registro_rul import cerrar_ejecucion
from app.models.ejecucion_rul import EjecucionRul, ResultadoRul
from app.models.prediccion_rul import PrediccionRul
from test_ml_batch_predicciones import entrada_controlada  # noqa: F401
from test_rul_historial import preparar


def tareas_latido():
    return [t for t in asyncio.all_tasks() if getattr(t.get_coro(),"__name__","")=="latir" and not t.done()]


@pytest.fixture
async def flota_independiente(engine,monkeypatch):
    import app.ml.latido_rul as modulo_latido
    from app.models.cliente import Cliente
    from app.models.equipo import Equipo
    sesiones=async_sessionmaker(engine,expire_on_commit=False)
    latido_listo=asyncio.Event()
    emitir_real=modulo_latido.emitir_latido
    cobertura_real=batch.verificar_cobertura
    async def emitir_y_senalar(*args):
        resultado=await emitir_real(*args)
        latido_listo.set()
        return resultado
    async def esperar_latido_y_verificar(*args):
        await asyncio.wait_for(latido_listo.wait(),timeout=5)
        return await cobertura_real(*args)
    monkeypatch.setattr(modulo_latido,"emitir_latido",emitir_y_senalar)
    monkeypatch.setattr(batch,"verificar_cobertura",esperar_latido_y_verificar)
    serie=f"EQ-SUP-{uuid4().hex[:20]}"
    ruc="20"+str(uuid4().int%10**9).zfill(9)
    async with sesiones() as s:
        anteriores=set((await s.scalars(select(EjecucionRul.id))).all())
        s.add(Cliente(ruc=ruc,razon_social="Prueba supervisión",direccion="Lima"))
        await s.flush()
        s.add(Equipo(serie=serie,cliente_ruc=ruc,tipo_sistema="FILTRO",fecha_instalacion=datetime.now(timezone.utc).date(),parametros_nominales={}))
        await s.commit()
    try:
        yield sesiones,serie,anteriores,latido_listo
    finally:
        pendientes=tareas_latido()
        for t in pendientes: t.cancel()
        if pendientes: await asyncio.gather(*pendientes,return_exceptions=True)
        async with sesiones() as s:
            await s.execute(delete(PrediccionRul).where(PrediccionRul.equipo_serie==serie))
            await s.execute(delete(ResultadoRul).where(ResultadoRul.equipo_serie==serie))
            await s.execute(delete(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))
            await s.execute(delete(Equipo).where(Equipo.serie==serie))
            await s.execute(delete(Cliente).where(Cliente.ruc==ruc))
            await s.commit()


@pytest.mark.parametrize("excepcion",[OSError,asyncio.CancelledError])
async def test_commit_confirmado_en_bd_no_se_reclasifica_si_pierde_respuesta(flota_independiente,monkeypatch,excepcion):
    sesiones,serie,anteriores,_=flota_independiente
    async with sesiones() as s:
        commit_real=s.commit
        llamadas=0
        async def commit_sin_confirmacion():
            nonlocal llamadas
            await commit_real()
            llamadas+=1
            if llamadas==2:
                raise excepcion("Confirmación de publicación perdida después de COMMIT")
        monkeypatch.setattr(s,"commit",commit_sin_confirmacion)
        with pytest.raises(excepcion):
            await asyncio.wait_for(batch._ejecutar(s,sesiones),timeout=15)
    async with sesiones() as consulta:
        c=(await consulta.scalars(select(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))).one()
        assert c.estado=="COMPLETADA" and c.total==1 and c.error_codigo is None
        p=await consulta.get(PrediccionRul,serie)
        r=(await consulta.scalars(select(ResultadoRul).where(ResultadoRul.equipo_serie==serie))).one()
        assert p.ejecucion_id==r.ejecucion_id==c.id
    assert not tareas_latido()


async def test_cancelacion_antes_de_publicar_con_latido_real_no_deja_parciales(flota_independiente,monkeypatch):
    sesiones,serie,anteriores,latido_listo=flota_independiente
    async def cancelar(*args):
        await asyncio.wait_for(latido_listo.wait(),timeout=5)
        raise asyncio.CancelledError()
    monkeypatch.setattr(batch,"verificar_cobertura",cancelar)
    async with sesiones() as s:
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(batch._ejecutar(s,sesiones),timeout=15)
    async with sesiones() as consulta:
        c=(await consulta.scalars(select(EjecucionRul).where(EjecucionRul.id.not_in(anteriores)))).one()
        assert c.estado=="FALLIDA" and c.error_codigo=="CANCELADA" and c.total==0
        assert await consulta.get(PrediccionRul,serie) is None
        assert await consulta.scalar(select(func.count()).select_from(ResultadoRul).where(ResultadoRul.equipo_serie==serie))==0
    assert not tareas_latido()


async def test_timeout_retrocede_resultados_y_conserva_cache_anterior(db,crear_cliente,monkeypatch):
    await preparar(db,crear_cliente)
    await batch.correr_batch(session=db)
    anterior=await db.get(PrediccionRul,"EQ-HIST")
    referencia=(anterior.ejecucion_id,anterior.actualizado_en,anterior.vence_en)
    async def lento(*args):
        await asyncio.sleep(2)
        return 1
    monkeypatch.setattr(batch,"verificar_cobertura",lento,raising=False)
    monkeypatch.setenv("RUL_DURACION_MAX_SEGUNDOS","1")
    with pytest.raises(TimeoutError): await batch.correr_batch(session=db)
    db.expire_all()
    anterior=await db.get(PrediccionRul,"EQ-HIST")
    assert (anterior.ejecucion_id,anterior.actualizado_en,anterior.vence_en)==referencia
    fallo=await db.scalar(select(EjecucionRul).where(EjecucionRul.estado=="FALLIDA"))
    assert fallo.error_codigo=="LIMITE_DURACION" and fallo.total==0
    assert fallo.esperados==1 and fallo.procesados==1
    assert await db.scalar(select(func.count()).select_from(ResultadoRul))==1


async def test_cobertura_incompleta_aborta_publicacion(db,crear_cliente,monkeypatch):
    await preparar(db,crear_cliente)
    real=getattr(batch,"verificar_cobertura",None)
    async def perder_resultado(session,ejecucion_id,series):
        await session.flush()
        await session.execute(delete(ResultadoRul).where(ResultadoRul.ejecucion_id==ejecucion_id))
        if real: return await real(session,ejecucion_id,series)
        return 0
    monkeypatch.setattr(batch,"verificar_cobertura",perder_resultado,raising=False)
    with pytest.raises(ValueError): await batch.correr_batch(session=db)
    assert await db.get(PrediccionRul,"EQ-HIST") is None
    c=await db.scalar(select(EjecucionRul))
    assert c.estado=="FALLIDA" and c.error_codigo=="COBERTURA_INCOMPLETA"


async def test_cancelacion_se_audita_y_se_propaga(db,crear_cliente,monkeypatch):
    await preparar(db,crear_cliente)
    async def cancelar(*args): raise asyncio.CancelledError()
    monkeypatch.setattr(batch,"verificar_cobertura",cancelar,raising=False)
    with pytest.raises(asyncio.CancelledError): await batch.correr_batch(session=db)
    db.expire_all()
    c=await db.scalar(select(EjecucionRul))
    assert c.estado=="FALLIDA" and c.error_codigo=="CANCELADA" and c.total==0
    assert await db.get(PrediccionRul,"EQ-HIST") is None


async def test_cierre_tardio_no_reclasifica_ejecucion_publicada(db):
    await batch.correr_batch(session=db)
    c=await db.scalar(select(EjecucionRul))
    await cerrar_ejecucion(db,c.id,estado="FALLIDA",finalizado_en=datetime(2026,10,23,3,tzinfo=timezone.utc),error_codigo="ERROR_CALCULO")
    await db.commit()
    db.expire_all()
    c=await db.scalar(select(EjecucionRul))
    assert c.estado=="COMPLETADA" and c.error_codigo is None
