from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.ml.batch_predicciones import correr_batch
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul
from test_rul_historial import preparar
from test_ml_batch_predicciones import entrada_controlada  # noqa: F401


async def test_historial_paginado_conserva_resultado_aunque_referencia_cambie(db, crear_cliente, client, tecnico_h):
    await preparar(db, crear_cliente)
    await correr_batch(session=db)
    await correr_batch(session=db)
    await db.execute(update(Equipo).where(Equipo.serie == "EQ-HIST").values(tipo_sistema="ABLANDADOR"))
    await db.commit()
    actual = (await client.get("/api/v1/equipos/EQ-HIST/prediccion-rul", headers=tecnico_h)).json()
    assert actual["estado_estimacion"] == "REQUIERE_RECALCULO" and actual["dias_vida_util_remanente"] is None
    lista = (await client.get("/api/v1/equipos/predicciones-rul", headers=tecnico_h)).json()
    assert lista[0]["estado_estimacion"] == "REQUIERE_RECALCULO"
    r = await client.get("/api/v1/equipos/EQ-HIST/historial-rul?limit=1", headers=tecnico_h)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2 and len(data["items"]) == 1
    item = data["items"][0]
    assert item["tipo_referencia"] == "FILTRO" and item["dias_vida_util_remanente"] == 80
    assert item["uso"] == "HISTORICO_NO_VIGENTE" and len(item["dataset_sha256"]) == 64
    assert len(item["modelo_sha256"])==64
    segunda = (await client.get("/api/v1/equipos/EQ-HIST/historial-rul?limit=1&offset=1", headers=tecnico_h)).json()
    assert segunda["items"][0]["id"] != item["id"]


async def test_historial_no_mezcla_equipos(db, crear_cliente, client, gerente_h):
    await preparar(db, crear_cliente)
    await preparar(db, crear_cliente, "EQ-OTRO")
    await correr_batch(session=db)
    r = await client.get("/api/v1/equipos/EQ-HIST/historial-rul", headers=gerente_h)
    assert r.status_code == 200 and r.json()["total"] == 1
    assert {v["equipo_serie"] for v in r.json()["items"]} == {"EQ-HIST"}


async def test_historial_vacio_y_equipo_inexistente(db, crear_cliente, client, gerente_h):
    await preparar(db, crear_cliente)
    assert (await client.get("/api/v1/equipos/EQ-HIST/historial-rul", headers=gerente_h)).json()["items"] == []
    assert (await client.get("/api/v1/equipos/NO/historial-rul", headers=gerente_h)).status_code == 404


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_paginacion_historial_rechaza_limites_invalidos(client, gerente_h, query):
    assert (await client.get(f"/api/v1/equipos/EQ-HIST/historial-rul?{query}", headers=gerente_h)).status_code == 422


async def test_ejecuciones_solo_gerencia_y_sin_datos_sensibles(db, client, gerente_h, tecnico_h):
    await correr_batch(session=db)
    r = await client.get("/api/v1/equipos/ejecuciones-rul", headers=gerente_h)
    assert r.status_code == 200 and r.json()["total"] == 1
    assert r.json()["items"][0]["estado"] == "COMPLETADA"
    assert (await client.get("/api/v1/equipos/ejecuciones-rul", headers=tecnico_h)).status_code == 403
    assert (await client.get("/api/v1/equipos/ejecuciones-rul")).status_code == 401
    assert (await client.get("/api/v1/equipos/EQ-HIST/historial-rul")).status_code == 401


async def test_vencimiento_api_oculta_lista_y_detalle_sin_modificar_valor_guardado(db, crear_cliente, client, gerente_h):
    await preparar(db, crear_cliente)
    await correr_batch(session=db)
    p = await db.scalar(select(PrediccionRul))
    p.actualizado_en -= timedelta(hours=60)
    p.vence_en -= timedelta(hours=60)
    await db.commit()
    detalle = (await client.get("/api/v1/equipos/EQ-HIST/prediccion-rul", headers=gerente_h)).json()
    lista = (await client.get("/api/v1/equipos/predicciones-rul", headers=gerente_h)).json()[0]
    for v in (detalle, lista):
        assert v["estado_estimacion"] == "VENCIDA"
        assert v["dias_vida_util_remanente"] is None and v["nivel_alerta"] is None
    db.expire_all()
    assert (await db.scalar(select(PrediccionRul))).dias_vida_util_remanente == 80
