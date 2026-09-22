from datetime import date, timedelta

import pytest

from app.models.contrato import Contrato

RUC = "20612493821"
PARAMETROS_COMPLETOS = {
    "tds_entrada_ppm": 350,
    "tds_post_membrana_ppm": 8,
    "tds_producto_final_ppm": 5,
    "ph": 7.0,
    "conductividad_us_cm": 15,
    "resistividad_mohm_cm": 1.2,
    "litros_consumidos_red": 500,
    "litros_agua_pura": 420,
}
BODY = {
    "serie": "RO-2026-0001",
    "cliente_ruc": RUC,
    "tipo_sistema": "OSMOSIS_INVERSA",
    "fecha_instalacion": "2026-01-15",
    "parametros_nominales": PARAMETROS_COMPLETOS,
}


@pytest.fixture
async def cliente(crear_cliente):
    return await crear_cliente(RUC)


@pytest.fixture
async def crear_contrato(db):
    async def _c(ruc=RUC):
        c = Contrato(cliente_ruc=ruc, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
        db.add(c)
        await db.flush()
        return c

    return _c


async def test_crear_equipo_osmosis_con_parametros_nominales_201(client, gerente_h, cliente):
    r = await client.post("/api/v1/equipos", json=BODY, headers=gerente_h)
    assert r.status_code == 201
    b = r.json()
    assert b["serie"] == "RO-2026-0001" and b["tipo_sistema"] == "OSMOSIS_INVERSA"
    assert b["parametros_nominales"]["tds_entrada_ppm"] == 350 and b["contrato_id"] is None


@pytest.mark.parametrize("tipo", ["OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO"])
async def test_los_tres_tipos_validos(client, gerente_h, cliente, tipo):
    r = await client.post("/api/v1/equipos", json={**BODY, "tipo_sistema": tipo}, headers=gerente_h)
    assert r.status_code == 201


async def test_tipo_sistema_invalido_422(client, gerente_h, cliente):
    r = await client.post("/api/v1/equipos", json={**BODY, "tipo_sistema": "BOMBA"}, headers=gerente_h)
    assert r.status_code == 422


async def test_serie_duplicada_409(client, gerente_h, cliente):
    await client.post("/api/v1/equipos", json=BODY, headers=gerente_h)
    assert (await client.post("/api/v1/equipos", json=BODY, headers=gerente_h)).status_code == 409


@pytest.mark.parametrize("serie", ["", "   ", "S" * 51])
async def test_serie_invalida_422(client, gerente_h, cliente, serie):
    assert (await client.post("/api/v1/equipos", json={**BODY, "serie": serie}, headers=gerente_h)).status_code == 422


async def test_parametros_nominales_obligatorios_y_no_vacios_422(client, gerente_h, cliente):
    sin = {k: v for k, v in BODY.items() if k != "parametros_nominales"}
    assert (await client.post("/api/v1/equipos", json=sin, headers=gerente_h)).status_code == 422
    assert (await client.post("/api/v1/equipos", json={**BODY, "parametros_nominales": {}}, headers=gerente_h)).status_code == 422
    assert (await client.post("/api/v1/equipos", json={**BODY, "parametros_nominales": [1]}, headers=gerente_h)).status_code == 422


@pytest.mark.parametrize("campo", list(PARAMETROS_COMPLETOS.keys()))
async def test_parametros_nominales_req03_todos_obligatorios_422(client, gerente_h, cliente, campo):
    """REQ-03: TDS entrada/post-membrana/producto final, pH, conductividad, resistividad,
    litros de red y litros de agua pura son obligatorios en la ficha técnica."""
    incompleto = {k: v for k, v in PARAMETROS_COMPLETOS.items() if k != campo}
    r = await client.post("/api/v1/equipos", json={**BODY, "parametros_nominales": incompleto}, headers=gerente_h)
    assert r.status_code == 422


async def test_ph_fuera_de_rango_422(client, gerente_h, cliente):
    r = await client.post(
        "/api/v1/equipos", json={**BODY, "parametros_nominales": {**PARAMETROS_COMPLETOS, "ph": 15}}, headers=gerente_h
    )
    assert r.status_code == 422


async def test_parametro_negativo_422(client, gerente_h, cliente):
    r = await client.post(
        "/api/v1/equipos",
        json={**BODY, "parametros_nominales": {**PARAMETROS_COMPLETOS, "tds_entrada_ppm": -1}},
        headers=gerente_h,
    )
    assert r.status_code == 422


async def test_parametros_nominales_admite_campos_adicionales(client, gerente_h, cliente):
    extra = {**PARAMETROS_COMPLETOS, "presion_psi": 60}
    r = await client.post("/api/v1/equipos", json={**BODY, "parametros_nominales": extra}, headers=gerente_h)
    assert r.status_code == 201 and r.json()["parametros_nominales"]["presion_psi"] == 60


async def test_cliente_inexistente_404_y_contrato_inexistente_404(client, gerente_h, cliente):
    r = await client.post("/api/v1/equipos", json={**BODY, "cliente_ruc": "20999999999"}, headers=gerente_h)
    assert r.status_code == 404
    r = await client.post("/api/v1/equipos", json={**BODY, "contrato_id": 999999}, headers=gerente_h)
    assert r.status_code == 404


async def test_contrato_de_otro_cliente_422(client, gerente_h, cliente, crear_cliente, crear_contrato):
    await crear_cliente("20111111111")
    ajeno = await crear_contrato("20111111111")
    r = await client.post("/api/v1/equipos", json={**BODY, "contrato_id": ajeno.id}, headers=gerente_h)
    assert r.status_code == 422


async def test_contrato_del_mismo_cliente_ok(client, gerente_h, cliente, crear_contrato):
    c = await crear_contrato()
    r = await client.post("/api/v1/equipos", json={**BODY, "contrato_id": c.id}, headers=gerente_h)
    assert r.status_code == 201 and r.json()["contrato_id"] == c.id


async def test_fecha_instalacion_futura_422(client, gerente_h, cliente):
    manana = (date.today() + timedelta(days=1)).isoformat()
    assert (await client.post("/api/v1/equipos", json={**BODY, "fecha_instalacion": manana}, headers=gerente_h)).status_code == 422
    assert (await client.post("/api/v1/equipos", json={**BODY, "fecha_instalacion": "no-es-fecha"}, headers=gerente_h)).status_code == 422


async def test_tecnico_lee_pero_no_escribe(client, gerente_h, tecnico_h, cliente):
    assert (await client.post("/api/v1/equipos", json=BODY, headers=tecnico_h)).status_code == 403
    await client.post("/api/v1/equipos", json=BODY, headers=gerente_h)
    assert (await client.get("/api/v1/equipos", headers=tecnico_h)).status_code == 200
    assert (await client.get(f"/api/v1/equipos/{BODY['serie']}", headers=tecnico_h)).status_code == 200
    cambio = {"parametros_nominales": {**PARAMETROS_COMPLETOS, "ph": 7.2}}
    assert (await client.put(f"/api/v1/equipos/{BODY['serie']}", json=cambio, headers=tecnico_h)).status_code == 403


async def test_listar_filtra_por_cliente(client, gerente_h, cliente, crear_cliente):
    await crear_cliente("20111111111")
    await client.post("/api/v1/equipos", json=BODY, headers=gerente_h)
    await client.post("/api/v1/equipos", json={**BODY, "serie": "F-1", "cliente_ruc": "20111111111"}, headers=gerente_h)
    r = await client.get(f"/api/v1/equipos?cliente_ruc={RUC}", headers=gerente_h)
    assert [e["serie"] for e in r.json()] == ["RO-2026-0001"]
    assert len((await client.get("/api/v1/equipos", headers=gerente_h)).json()) == 2


async def test_actualizar_parametros_y_contrato(client, gerente_h, cliente, crear_contrato):
    await client.post("/api/v1/equipos", json=BODY, headers=gerente_h)
    c = await crear_contrato()
    nuevos = {**PARAMETROS_COMPLETOS, "ph": 7.2}
    r = await client.put(f"/api/v1/equipos/{BODY['serie']}", json={"parametros_nominales": nuevos, "contrato_id": c.id},
                         headers=gerente_h)
    assert r.status_code == 200 and r.json()["parametros_nominales"]["ph"] == 7.2 and r.json()["contrato_id"] == c.id
    vacio = await client.put(f"/api/v1/equipos/{BODY['serie']}", json={"parametros_nominales": {}}, headers=gerente_h)
    assert vacio.status_code == 422
    incompleto = await client.put(
        f"/api/v1/equipos/{BODY['serie']}", json={"parametros_nominales": {"ph": 7.2}}, headers=gerente_h
    )
    assert incompleto.status_code == 422


async def test_equipo_inexistente_404_y_sin_token_401(client, gerente_h):
    assert (await client.get("/api/v1/equipos/NOPE", headers=gerente_h)).status_code == 404
    assert (await client.put("/api/v1/equipos/NOPE", json={"parametros_nominales": PARAMETROS_COMPLETOS}, headers=gerente_h)).status_code == 404
    assert (await client.get("/api/v1/equipos")).status_code == 401
