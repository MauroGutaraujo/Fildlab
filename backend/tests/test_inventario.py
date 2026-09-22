import asyncio
import os

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repuesto import MovimientoInventario, Repuesto
from app.models.usuario import Usuario
from app.services.inventario import StockInsuficiente, registrar_movimiento

REP = {"codigo": "FILT-05", "descripcion": "Filtro de sedimentos 5 micras", "costo_unitario_soles": "12.50"}


async def _repuesto(client, headers, **extra):
    return await client.post("/api/v1/repuestos", json={**REP, **extra}, headers=headers)


async def test_crear_repuesto_con_stock_inicial_0(client, gerente_h):
    r = await _repuesto(client, gerente_h)
    assert r.status_code == 201
    assert r.json()["stock_almacen_central"] == 0 and r.json()["costo_unitario_soles"] == "12.50"


async def test_crear_repuesto_ignora_stock_enviado_por_el_cliente(client, gerente_h):
    r = await _repuesto(client, gerente_h, stock_almacen_central=999)
    assert r.json()["stock_almacen_central"] == 0


@pytest.mark.parametrize("costo", ["-1", "abc", "100000000"])
async def test_costo_invalido_422(client, gerente_h, costo):
    assert (await _repuesto(client, gerente_h, costo_unitario_soles=costo)).status_code == 422


async def test_codigo_duplicado_409(client, gerente_h):
    await _repuesto(client, gerente_h)
    assert (await _repuesto(client, gerente_h)).status_code == 409


async def test_codigo_o_descripcion_vacios_422(client, gerente_h):
    assert (await _repuesto(client, gerente_h, codigo="  ")).status_code == 422
    assert (await _repuesto(client, gerente_h, descripcion="")).status_code == 422
    assert (await _repuesto(client, gerente_h, codigo="X" * 31)).status_code == 422


async def _mov(client, headers, **body):
    return await client.post("/api/v1/inventario/movimientos", json=body, headers=headers)


async def _stock(client, headers, codigo="FILT-05"):
    return (await client.get(f"/api/v1/repuestos/{codigo}", headers=headers)).json()["stock_almacen_central"]


async def test_entrada_incrementa_y_salida_decrementa_stock(client, gerente_h, crear_orden):
    await _repuesto(client, gerente_h)
    orden = await crear_orden()
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=10)
    assert r.status_code == 201
    assert await _stock(client, gerente_h) == 10
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="SALIDA_ORDEN", cantidad=4, orden_id=str(orden.id))
    assert r.status_code == 201
    assert await _stock(client, gerente_h) == 6


async def test_salida_mayor_al_stock_409_y_stock_intacto(client, gerente_h, crear_orden, db):
    await _repuesto(client, gerente_h)
    orden = await crear_orden()
    await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=3)
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="SALIDA_ORDEN", cantidad=4, orden_id=str(orden.id))
    assert r.status_code == 409
    assert await _stock(client, gerente_h) == 3
    n = (await db.execute(select(func.count()).select_from(MovimientoInventario))).scalar()
    assert n == 1  # solo la entrada


async def test_salida_orden_sin_orden_id_422(client, gerente_h):
    await _repuesto(client, gerente_h)
    await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=3)
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="SALIDA_ORDEN", cantidad=1)
    assert r.status_code == 422
    assert await _stock(client, gerente_h) == 3


async def test_salida_con_orden_inexistente_404(client, gerente_h):
    await _repuesto(client, gerente_h)
    await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=3)
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="SALIDA_ORDEN", cantidad=1,
                   orden_id="00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.parametrize("cantidad", [0, -5, 1.5])
async def test_cantidad_invalida_422(client, gerente_h, cantidad):
    await _repuesto(client, gerente_h)
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=cantidad)
    assert r.status_code == 422


async def test_tipo_salida_venta_no_se_acepta_por_este_endpoint_422(client, gerente_h):
    await _repuesto(client, gerente_h)
    r = await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="SALIDA_VENTA", cantidad=1)
    assert r.status_code == 422


async def test_movimiento_de_repuesto_inexistente_404(client, gerente_h):
    r = await _mov(client, gerente_h, repuesto_codigo="NOPE", tipo="ENTRADA", cantidad=1)
    assert r.status_code == 404


async def test_movimiento_deja_registro_con_usuario_y_fecha(client, crear_usuario, auth_headers):
    g = await crear_usuario("GERENCIA")
    h = auth_headers(g)
    await _repuesto(client, h)
    await _mov(client, h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=2)
    lista = (await client.get("/api/v1/inventario/movimientos?repuesto=FILT-05", headers=h)).json()
    assert len(lista) == 1
    assert lista[0]["usuario_id"] == g.id and lista[0]["creado_en"] and lista[0]["cantidad"] == 2


async def test_ajustes_con_direccion(client, gerente_h):
    await _repuesto(client, gerente_h)
    await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=5)
    assert (await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="AJUSTE_SALIDA", cantidad=2)).status_code == 201
    assert (await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="AJUSTE_ENTRADA", cantidad=1)).status_code == 201
    assert await _stock(client, gerente_h) == 4
    assert (await _mov(client, gerente_h, repuesto_codigo="FILT-05", tipo="AJUSTE_SALIDA", cantidad=99)).status_code == 409


async def test_permisos_tecnico_solo_lectura(client, gerente_h, tecnico_h):
    await _repuesto(client, gerente_h)
    assert (await _repuesto(client, tecnico_h, codigo="OTRO")).status_code == 403
    assert (await _mov(client, tecnico_h, repuesto_codigo="FILT-05", tipo="ENTRADA", cantidad=1)).status_code == 403
    assert (await client.get("/api/v1/repuestos", headers=tecnico_h)).status_code == 200
    assert (await client.get("/api/v1/repuestos/FILT-05", headers=tecnico_h)).status_code == 200
    assert (await client.get("/api/v1/inventario/movimientos", headers=tecnico_h)).status_code == 200


async def test_sin_token_401(client):
    assert (await client.get("/api/v1/repuestos")).status_code == 401


async def test_repuesto_inexistente_404(client, gerente_h):
    assert (await client.get("/api/v1/repuestos/NOPE", headers=gerente_h)).status_code == 404


async def test_dos_salidas_concurrentes_no_dejan_stock_negativo(engine):
    """Dos transacciones reales (commit) compiten por el mismo stock: solo una gana."""
    async with AsyncSession(engine, expire_on_commit=False) as s:
        u = Usuario(nombre="Conc", email="conc@test.pe", password_hash="x", rol="GERENCIA")
        s.add(u)
        s.add(Repuesto(codigo="CONC-1", descripcion="Concurrencia", costo_unitario_soles=1, stock_almacen_central=5))
        await s.commit()
        uid = u.id

    async def salida(n):
        async with AsyncSession(engine, expire_on_commit=False) as s:
            try:
                await registrar_movimiento(s, "CONC-1", "AJUSTE_SALIDA", 3, uid)
                await asyncio.sleep(0.3)  # mantiene el bloqueo para forzar la carrera
                await s.commit()
                return "ok"
            except StockInsuficiente:
                await s.rollback()
                return "sin_stock"

    try:
        resultados = await asyncio.gather(salida(1), salida(2))
        assert sorted(resultados) == ["ok", "sin_stock"]
        async with AsyncSession(engine) as s:
            assert (await s.get(Repuesto, "CONC-1")).stock_almacen_central == 2
    finally:
        async with AsyncSession(engine) as s:
            await s.execute(delete(MovimientoInventario).where(MovimientoInventario.repuesto_codigo == "CONC-1"))
            await s.execute(delete(Repuesto).where(Repuesto.codigo == "CONC-1"))
            await s.execute(delete(Usuario).where(Usuario.email == "conc@test.pe"))
            await s.commit()
