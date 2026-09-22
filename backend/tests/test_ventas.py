import pytest
from sqlalchemy import func, select

from app.models.repuesto import MovimientoInventario
from app.models.venta import Venta

RUC = "20612493821"


@pytest.fixture
async def base(client, gerente_h, crear_cliente):
    await crear_cliente(RUC)
    for codigo, stock in (("FILT-05", 10), ("MEMB-01", 2)):
        await client.post("/api/v1/repuestos", json={"codigo": codigo, "descripcion": codigo, "costo_unitario_soles": "10"},
                          headers=gerente_h)
        await client.post("/api/v1/inventario/movimientos",
                          json={"repuesto_codigo": codigo, "tipo": "ENTRADA", "cantidad": stock}, headers=gerente_h)


def venta(*items, ruc=RUC):
    return {"cliente_ruc": ruc, "items": [
        {"repuesto_codigo": c, "cantidad": q, "precio_unitario_soles": p} for c, q, p in items]}


async def _stock(client, h, codigo):
    return (await client.get(f"/api/v1/repuestos/{codigo}", headers=h)).json()["stock_almacen_central"]


async def test_venta_descuenta_stock_y_calcula_total(client, gerente_h, base, db):
    r = await client.post("/api/v1/ventas", json=venta(("FILT-05", 3, "20.00"), ("MEMB-01", 1, "99.90")), headers=gerente_h)
    assert r.status_code == 201
    b = r.json()
    assert b["total_soles"] == "159.90" and len(b["items"]) == 2 and b["cliente_ruc"] == RUC
    assert await _stock(client, gerente_h, "FILT-05") == 7
    assert await _stock(client, gerente_h, "MEMB-01") == 1
    tipos = (await db.execute(select(MovimientoInventario.tipo, MovimientoInventario.venta_id)
                              .where(MovimientoInventario.tipo == "SALIDA_VENTA"))).all()
    assert len(tipos) == 2 and all(v == b["id"] for _, v in tipos)


async def test_venta_sin_items_422(client, gerente_h, base):
    assert (await client.post("/api/v1/ventas", json=venta(), headers=gerente_h)).status_code == 422


@pytest.mark.parametrize("cant,precio", [(0, "1"), (-1, "1"), (1, "-1"), (1, "abc")])
async def test_item_invalido_422(client, gerente_h, base, cant, precio):
    r = await client.post("/api/v1/ventas", json=venta(("FILT-05", cant, precio)), headers=gerente_h)
    assert r.status_code == 422


async def test_stock_insuficiente_409_sin_venta_ni_movimientos_ni_descuentos(client, gerente_h, base, db):
    # El primer item alcanza; el segundo no: nada debe quedar aplicado.
    r = await client.post("/api/v1/ventas", json=venta(("FILT-05", 3, "1"), ("MEMB-01", 5, "1")), headers=gerente_h)
    assert r.status_code == 409
    assert await _stock(client, gerente_h, "FILT-05") == 10
    assert await _stock(client, gerente_h, "MEMB-01") == 2
    assert (await db.execute(select(func.count()).select_from(Venta))).scalar() == 0
    n = (await db.execute(select(func.count()).select_from(MovimientoInventario)
                          .where(MovimientoInventario.tipo == "SALIDA_VENTA"))).scalar()
    assert n == 0


async def test_repuesto_duplicado_en_items_se_acumula_contra_el_stock(client, gerente_h, base):
    # MEMB-01 tiene 2: 1 + 2 = 3 > 2 aunque cada linea por separado alcanzaria.
    r = await client.post("/api/v1/ventas", json=venta(("MEMB-01", 1, "5"), ("MEMB-01", 2, "5")), headers=gerente_h)
    assert r.status_code == 409
    assert await _stock(client, gerente_h, "MEMB-01") == 2


async def test_repuesto_inexistente_404_sin_venta(client, gerente_h, base, db):
    r = await client.post("/api/v1/ventas", json=venta(("NOPE", 1, "5")), headers=gerente_h)
    assert r.status_code == 404
    assert (await db.execute(select(func.count()).select_from(Venta))).scalar() == 0


async def test_cliente_inexistente_404_y_anulado_409(client, gerente_h, base):
    r = await client.post("/api/v1/ventas", json=venta(("FILT-05", 1, "5"), ruc="20999999999"), headers=gerente_h)
    assert r.status_code == 404
    await client.delete(f"/api/v1/clientes/{RUC}", headers=gerente_h)
    r = await client.post("/api/v1/ventas", json=venta(("FILT-05", 1, "5")), headers=gerente_h)
    assert r.status_code == 409


async def test_solo_gerencia_escribe_tecnico_lee(client, gerente_h, tecnico_h, base):
    assert (await client.post("/api/v1/ventas", json=venta(("FILT-05", 1, "5")), headers=tecnico_h)).status_code == 403
    v = (await client.post("/api/v1/ventas", json=venta(("FILT-05", 1, "5")), headers=gerente_h)).json()
    lista = await client.get("/api/v1/ventas", headers=tecnico_h)
    assert lista.status_code == 200 and [x["id"] for x in lista.json()] == [v["id"]]
    detalle = await client.get(f"/api/v1/ventas/{v['id']}", headers=tecnico_h)
    assert detalle.status_code == 200 and detalle.json()["items"][0]["repuesto_codigo"] == "FILT-05"


async def test_venta_inexistente_404(client, gerente_h):
    assert (await client.get("/api/v1/ventas/999999", headers=gerente_h)).status_code == 404


async def test_sin_token_401(client):
    assert (await client.get("/api/v1/ventas")).status_code == 401
    assert (await client.post("/api/v1/ventas", json={})).status_code == 401
