import hashlib

import pytest
from sqlalchemy import select

from app.ml.batch_predicciones import correr_batch
from app.models.ejecucion_rul import EjecucionRul
from app.models.prediccion_rul import PrediccionRul
from test_ml_batch_predicciones import entrada_controlada  # noqa: F401
from test_rul_historial import preparar


async def test_batch_no_genera_ni_entrena_y_registra_modelo_identico(db,crear_cliente,monkeypatch):
    await preparar(db,crear_cliente)
    def prohibido(*args,**kwargs): raise AssertionError("Inferencia no debe entrenar ni simular")
    monkeypatch.setattr("app.ml.batch_predicciones.generar_dataset",prohibido,raising=False)
    monkeypatch.setattr("app.ml.batch_predicciones.ajustar_modelo",prohibido,raising=False)
    await correr_batch(session=db)
    await correr_batch(session=db)
    corridas=(await db.scalars(select(EjecucionRul))).all()
    assert len(corridas)==2 and corridas[0].modelo_sha256==corridas[1].modelo_sha256
    assert len(corridas[0].modelo_sha256)==64 and corridas[0].entorno_modelo["lifelines"]


async def test_modelo_alterado_falla_sin_renovar_cache(db,crear_cliente,monkeypatch,tmp_path):
    await preparar(db,crear_cliente)
    await correr_batch(session=db)
    p=await db.get(PrediccionRul,"EQ-HIST")
    previo=(p.ejecucion_id,p.actualizado_en,p.vence_en)
    archivo=tmp_path/"alterado.json"
    archivo.write_text('{"no":"modelo"}')
    monkeypatch.setenv("RUL_MODELO_PATH",str(archivo))
    monkeypatch.setenv("RUL_MODELO_SHA256","0"*64)
    with pytest.raises(ValueError): await correr_batch(session=db)
    db.expire_all()
    p=await db.get(PrediccionRul,"EQ-HIST")
    assert (p.ejecucion_id,p.actualizado_en,p.vence_en)==previo
    c=await db.scalar(select(EjecucionRul).where(EjecucionRul.estado=="FALLIDA"))
    assert c.error_codigo=="MODELO_INVALIDO" and c.total==0
