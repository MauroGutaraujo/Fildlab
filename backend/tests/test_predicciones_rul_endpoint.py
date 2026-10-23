from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul
from app.models.ejecucion_rul import EjecucionRul


async def _equipo_con_prediccion(db, crear_cliente, *, serie="EQ-1", nivel="ROJO", version="COX_INSTALACION_V3"):
    await crear_cliente("20612493821")
    db.add(Equipo(serie=serie, cliente_ruc="20612493821", tipo_sistema="FILTRO",
                  fecha_instalacion=date(2026, 1, 1), parametros_nominales={}))
    await db.flush()
    ahora = datetime.now(timezone.utc) - timedelta(minutes=1)
    corrida = EjecucionRul(id=uuid4(), iniciado_en=ahora, finalizado_en=ahora, estado="COMPLETADA",
        version_calculo=version, version_dataset="WEIBULL_CENSURA_V2", politica_alerta="RUL_30_90_V1",
        entorno={}, vigencia_horas=48, total=1, estimadas=1, abstenciones=0)
    db.add(corrida)
    await db.flush()
    dias = {"ROJO": 5, "AMARILLO": 45, "VERDE": 100}[nivel]
    p = PrediccionRul(equipo_serie=serie, dias_vida_util_remanente=dias, nivel_alerta=nivel)
    p.version_calculo = version
    p.fecha_referencia = date(2026, 1, 1)
    p.tipo_referencia = "FILTRO"
    p.ejecucion_id = corrida.id
    p.actualizado_en = ahora
    p.vence_en = ahora + timedelta(hours=48)
    db.add(p)
    await db.flush()


async def test_listar_predicciones_gerencia_y_tecnico(client, gerente_h, tecnico_h, db, crear_cliente):
    await _equipo_con_prediccion(db, crear_cliente)
    await db.commit()

    r1 = await client.get("/api/v1/equipos/predicciones-rul", headers=gerente_h)
    r2 = await client.get("/api/v1/equipos/predicciones-rul", headers=tecnico_h)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()[0]["equipo_serie"] == "EQ-1"
    assert r1.json()[0]["nivel_alerta"] == "ROJO"
    assert r1.json()[0]["experimental"] is True
    assert r1.json()[0]["estado_estimacion"] == "ESTIMADA"
    assert r1.json()[0]["origen_datos"] == "SINTETICOS"
    assert r1.json()[0]["version_dataset"] == "WEIBULL_CENSURA_V2"


async def test_listar_predicciones_sin_token_401(client):
    assert (await client.get("/api/v1/equipos/predicciones-rul")).status_code == 401


async def test_leer_prediccion_de_un_equipo(client, gerente_h, db, crear_cliente):
    await _equipo_con_prediccion(db, crear_cliente, serie="EQ-2", nivel="VERDE")
    await db.commit()

    r = await client.get("/api/v1/equipos/EQ-2/prediccion-rul", headers=gerente_h)
    assert r.status_code == 200
    assert r.json()["nivel_alerta"] == "VERDE"


async def test_leer_prediccion_equipo_inexistente_404(client, gerente_h):
    r = await client.get("/api/v1/equipos/NO-EXISTE/prediccion-rul", headers=gerente_h)
    assert r.status_code == 404
    assert r.json()["detail"] == "Equipo no encontrado"


async def test_leer_prediccion_equipo_sin_evaluar_404(client, gerente_h, db, crear_cliente):
    await crear_cliente("20612493821")
    db.add(Equipo(serie="EQ-SIN-EVALUAR", cliente_ruc="20612493821", tipo_sistema="FILTRO",
                  fecha_instalacion=date(2026, 1, 1), parametros_nominales={}))
    await db.commit()

    r = await client.get("/api/v1/equipos/EQ-SIN-EVALUAR/prediccion-rul", headers=gerente_h)
    assert r.status_code == 404
    assert r.json()["detail"] == "Aún no hay predicción RUL para este equipo"


@pytest.mark.parametrize("version", ["LEGADO", "CONDICIONAL_V1", "COX_CONDICIONAL_V2"])
async def test_api_no_expone_verde_heredado_como_estimacion_corregida(client, gerente_h, db, crear_cliente, version):
    await _equipo_con_prediccion(db, crear_cliente, nivel="VERDE", version=version)
    await db.commit()
    r = await client.get("/api/v1/equipos/EQ-1/prediccion-rul", headers=gerente_h)
    assert r.status_code == 200
    assert r.json()["estado_estimacion"] == "REQUIERE_RECALCULO"
    assert r.json()["dias_vida_util_remanente"] is None
    assert r.json()["nivel_alerta"] is None
    assert r.json()["version_dataset"] is None


async def test_instalacion_editada_oculta_prediccion_anterior_en_ambas_rutas(client, gerente_h, db, crear_cliente):
    await _equipo_con_prediccion(db, crear_cliente, nivel="VERDE")
    await db.commit()
    antes = await client.get("/api/v1/equipos/EQ-1/prediccion-rul", headers=gerente_h)
    assert antes.json()["estado_estimacion"] == "ESTIMADA"
    r = await client.put("/api/v1/equipos/EQ-1", headers=gerente_h, json={"fecha_instalacion":"2026-01-02"})
    assert r.status_code == 200
    detalle = (await client.get("/api/v1/equipos/EQ-1/prediccion-rul", headers=gerente_h)).json()
    lista = (await client.get("/api/v1/equipos/predicciones-rul", headers=gerente_h)).json()[0]
    for salida in (detalle, lista):
        assert salida["estado_estimacion"] == "REQUIERE_RECALCULO"
        assert salida["dias_vida_util_remanente"] is None and salida["nivel_alerta"] is None
    # El valor previo se conserva en base; la API impide presentarlo con referencia nueva.
    assert (await db.get(PrediccionRul, "EQ-1")).dias_vida_util_remanente == 100
