from datetime import date, timedelta

import pytest
from sqlalchemy import select, func

from app.ml.batch_predicciones import correr_batch
from app.models.ejecucion_rul import EjecucionRul, ResultadoRul
from app.models.prediccion_rul import PrediccionRul
from test_ml_batch_predicciones import _equipo, entrada_controlada  # noqa: F401


async def preparar(db, crear_cliente, serie="EQ-HIST"):
    await _equipo(db, crear_cliente, serie=serie, tipo_sistema="FILTRO", fecha_instalacion=date(2026,10,22))
    await db.commit()


async def test_cada_ejecucion_conserva_resultado_entradas_y_procedencia(db, crear_cliente):
    await preparar(db, crear_cliente)
    await correr_batch(session=db)
    await correr_batch(session=db)
    db.expire_all()
    corridas = (await db.scalars(select(EjecucionRul))).all()
    assert len(corridas) == 2
    historial = (await db.scalars(select(ResultadoRul))).all()
    assert len(historial) == 2
    assert len({r.ejecucion_id for r in historial}) == 2
    for c in corridas:
        assert c.estado == "COMPLETADA" and c.total == c.estimadas == 1 and c.abstenciones == 0
        assert len(c.dataset_sha256) == 64
        assert c.finalizado_en >= c.iniciado_en
        assert c.entorno["lifelines"] and c.entorno["python"]
    assert corridas[0].dataset_sha256 == corridas[1].dataset_sha256
    for r in historial:
        assert r.fecha_evaluacion == date(2026,10,22) and r.fecha_referencia == date(2026,10,22)
        assert r.tipo_referencia == "FILTRO" and r.origen == "BATCH"
        assert r.vence_en - r.calculado_en == timedelta(hours=48)
        assert r.dias_vida_util_remanente == 80
    actual = await db.get(PrediccionRul, "EQ-HIST")
    assert actual.ejecucion_id in {r.ejecucion_id for r in historial}
    assert await db.scalar(select(func.count()).select_from(PrediccionRul)) == 1


async def test_fallo_no_publica_parcial_ni_refresca_resultado_previo(db, crear_cliente, monkeypatch):
    await preparar(db, crear_cliente)
    await correr_batch(session=db)
    anterior = await db.get(PrediccionRul, "EQ-HIST")
    id_anterior, fecha_anterior = anterior.ejecucion_id, anterior.actualizado_en
    await preparar(db, crear_cliente, "EQ-SEGUNDO")
    from app.ml.batch_predicciones import calificar_equipo
    llamadas = 0
    def fallar_despues_de_uno(*args):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise RuntimeError("secreto-que-no-debe-publicarse")
        return calificar_equipo(*args)
    monkeypatch.setattr("app.ml.batch_predicciones.calificar_equipo", fallar_despues_de_uno)
    with pytest.raises(RuntimeError):
        await correr_batch(session=db)
    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(ResultadoRul)) == 1
    actual = await db.get(PrediccionRul, "EQ-HIST")
    assert actual.ejecucion_id == id_anterior and actual.actualizado_en == fecha_anterior
    assert await db.get(PrediccionRul, "EQ-SEGUNDO") is None
    fallida = await db.scalar(select(EjecucionRul).where(EjecucionRul.estado == "FALLIDA"))
    assert fallida.total == 0 and fallida.finalizado_en is not None
    assert fallida.error_codigo == "ERROR_CALCULO"
    assert len(fallida.dataset_sha256) == 64
    assert "secreto" not in str(fallida.entorno)


async def test_ejecucion_sin_equipos_tambien_queda_registrada(db):
    await correr_batch(session=db)
    c = await db.scalar(select(EjecucionRul))
    assert c.estado == "COMPLETADA" and c.total == 0


async def test_abstencion_se_guarda_en_historial(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-VIEJO", tipo_sistema="FILTRO", fecha_instalacion=date(2000,1,1))
    await db.commit()
    await correr_batch(session=db)
    r = await db.scalar(select(ResultadoRul))
    c = await db.scalar(select(EjecucionRul))
    assert r.motivo_no_estimable == "EDAD_FUERA_SOPORTE" and r.dias_vida_util_remanente is None
    assert c.abstenciones == 1 and c.estimadas == 0


async def test_vigencia_configurada_se_congela_en_resultado(db, crear_cliente, monkeypatch):
    await preparar(db, crear_cliente)
    monkeypatch.setenv("RUL_VIGENCIA_HORAS", "12")
    await correr_batch(session=db)
    r = await db.scalar(select(ResultadoRul))
    assert r.vence_en - r.calculado_en == timedelta(hours=12)
    assert (await db.scalar(select(EjecucionRul))).vigencia_horas == 12


async def test_error_de_salida_no_cambia_ejecucion_ya_publicada(db, crear_cliente, monkeypatch):
    await preparar(db, crear_cliente)
    def salida_rota(*args, **kwargs):
        raise BrokenPipeError("stdout desconectado")
    monkeypatch.setattr("builtins.print", salida_rota)
    await correr_batch(session=db)
    db.expire_all()
    corrida = await db.scalar(select(EjecucionRul))
    assert corrida.estado == "COMPLETADA" and corrida.total == 1 and corrida.error_codigo is None
    assert (await db.scalar(select(ResultadoRul))).ejecucion_id == corrida.id


async def test_fallo_de_inferencia_conserva_huella_del_dataset_y_modelo(db, crear_cliente, monkeypatch):
    await preparar(db, crear_cliente)
    def inferencia_fallida(*args):
        raise RuntimeError("fallo inesperado de inferencia")
    monkeypatch.setattr("app.ml.batch_predicciones.calificar_equipo", inferencia_fallida)
    with pytest.raises(RuntimeError):
        await correr_batch(session=db)
    c = await db.scalar(select(EjecucionRul))
    assert c.estado == "FALLIDA" and c.total == 0 and len(c.dataset_sha256) == 64
    assert len(c.modelo_sha256)==64 and c.entorno_modelo["numpy"]
    assert await db.scalar(select(func.count()).select_from(ResultadoRul)) == 0
