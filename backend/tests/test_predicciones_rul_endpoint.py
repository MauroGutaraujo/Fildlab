from datetime import date

from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul


async def _equipo_con_prediccion(db, crear_cliente, *, serie="EQ-1", nivel="ROJO"):
    await crear_cliente("20612493821")
    db.add(Equipo(serie=serie, cliente_ruc="20612493821", tipo_sistema="FILTRO",
                  fecha_instalacion=date(2026, 1, 1), parametros_nominales={}))
    await db.flush()
    db.add(PrediccionRul(equipo_serie=serie, dias_vida_util_remanente=5, nivel_alerta=nivel))
    await db.flush()


async def test_listar_predicciones_gerencia_y_tecnico(client, gerente_h, tecnico_h, db, crear_cliente):
    await _equipo_con_prediccion(db, crear_cliente)
    await db.commit()

    r1 = await client.get("/api/v1/equipos/predicciones-rul", headers=gerente_h)
    r2 = await client.get("/api/v1/equipos/predicciones-rul", headers=tecnico_h)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()[0]["equipo_serie"] == "EQ-1"
    assert r1.json()[0]["nivel_alerta"] == "ROJO"


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
