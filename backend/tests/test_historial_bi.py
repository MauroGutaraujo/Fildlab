from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repuesto import Repuesto
from app.services.inventario import registrar_movimiento, StockInsuficiente
from test_analytics import _consumo, _contrato, _orden
from test_ordenes_concurrencia import concurrente


def mes_anterior():
    hoy = datetime.now(ZoneInfo("America/Lima")).date()
    return (hoy.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


async def test_stock_precargado_revalida_saldo_tras_cambio_de_otra_sesion(engine, concurrente):
    codigo = concurrente["codigos"][0]
    async with AsyncSession(engine, expire_on_commit=False) as primera:
        precargado = await primera.get(Repuesto, codigo)
        assert precargado.stock_almacen_central == 10
        async with AsyncSession(engine) as segunda:
            await registrar_movimiento(segunda, codigo, "AJUSTE_SALIDA", 7, concurrente["tecnico"])
            await segunda.commit()
        with pytest.raises(StockInsuficiente):
            await registrar_movimiento(primera, codigo, "AJUSTE_SALIDA", 4, concurrente["tecnico"])
        await primera.rollback()


async def test_cambiar_tarifa_no_reescribe_mes_anterior(client, gerente_h, crear_cliente):
    await crear_cliente()
    datos = dict(cliente_ruc="20612493821", fecha_inicio="2020-01-01", fecha_fin="2099-12-31",
                 monto_mensual_soles="1000.00", sla_horas_max_respuesta=4)
    creada = (await client.post("/api/v1/contratos", json=datos, headers=gerente_h)).json()
    datos.pop("cliente_ruc")
    datos["monto_mensual_soles"] = "2500.00"
    respuesta = await client.put(f"/api/v1/contratos/{creada['id']}", json=datos, headers=gerente_h)
    assert respuesta.status_code == 200
    rows = (await client.get(f"/api/v1/analytics/rentabilidad?periodo={mes_anterior()}", headers=gerente_h)).json()["contratos"]
    assert rows[0]["ingreso_soles"] == "1000.00"


async def test_anular_no_elimina_rentabilidad_de_meses_previos(client, gerente_h, crear_cliente):
    await crear_cliente()
    datos = dict(cliente_ruc="20612493821", fecha_inicio="2020-01-01", fecha_fin="2099-12-31",
                 monto_mensual_soles="1000.00", sla_horas_max_respuesta=4)
    creada = (await client.post("/api/v1/contratos", json=datos, headers=gerente_h)).json()
    assert (await client.post(f"/api/v1/contratos/{creada['id']}/anular", headers=gerente_h)).status_code == 200
    rows = (await client.get(f"/api/v1/analytics/rentabilidad?periodo={mes_anterior()}", headers=gerente_h)).json()["contratos"]
    assert len(rows) == 1
    assert rows[0]["ingreso_soles"] == "1000.00"


async def test_costo_movimiento_no_cambia_al_actualizar_catalogo(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    rep = Repuesto(codigo="FILT-HIST", descripcion="Filtro", costo_unitario_soles=Decimal("5"), stock_almacen_central=10)
    db.add(rep)
    await db.flush()
    await registrar_movimiento(db, rep.codigo, "SALIDA_ORDEN", 3, orden.tecnico_id, orden_id=orden.id)
    rep.costo_unitario_soles = Decimal("99")
    await db.flush()
    rows = (await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)).json()["contratos"]
    assert rows[0]["costo_repuestos_soles"] == "15.00"


async def test_datos_heredados_informan_falta_de_historial(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id)
    rows = (await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)).json()["contratos"]
    assert rows[0]["historial_completo"] is False
