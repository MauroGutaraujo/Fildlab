import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import ActaInmutable, OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto
from app.services.inventario import StockInsuficiente
from app.services.ordenes import OrdenSyncError, TecnicoNoAutorizado, sincronizar_orden
from test_ordenes_service import _datos, escenario


@pytest.mark.parametrize("cambio", ["otro_cliente", "otro_contrato", "sin_contrato", "anulado", "antes", "despues"])
async def test_contrato_incoherente_rechazado_sin_filas_parciales(db, escenario, crear_usuario, crear_cliente, cambio):
    tec = await crear_usuario("TECNICO")
    equipo = await db.get(Equipo, "RO-1")
    fecha = datetime(2026, 10, 21, 15, tzinfo=timezone.utc)
    if cambio == "otro_cliente":
        await crear_cliente("20999999999")
        escenario.cliente_ruc = "20999999999"
    elif cambio == "otro_contrato":
        otro = Contrato(cliente_ruc=escenario.cliente_ruc, fecha_inicio=date(2026, 1, 1),
                        fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
        db.add(otro)
        await db.flush()
        equipo.contrato_id = otro.id
    elif cambio == "sin_contrato":
        equipo.contrato_id = None
    elif cambio == "anulado":
        escenario.estado = "ANULADO"
    elif cambio == "antes":
        fecha = datetime(2026, 1, 1, 4, 59, tzinfo=timezone.utc)  # 31 diciembre en Lima
    elif cambio == "despues":
        fecha = datetime(2027, 1, 1, 5, tzinfo=timezone.utc)
    await db.flush()
    with pytest.raises(OrdenSyncError):
        await sincronizar_orden(db, _datos(tec.id, escenario.id, fecha_creacion_cliente=fecha), tec)
    for model in (OrdenServicio, ActaInmutable, MovimientoInventario):
        assert (await db.scalar(select(func.count()).select_from(model))) == 0


async def test_servicio_ultimo_dia_lima_se_acepta_aunque_sync_tardia(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    escenario.estado = "VENCIDO"
    orden = await sincronizar_orden(db, _datos(tec.id, escenario.id,
        fecha_creacion_cliente="2027-01-01T04:59:00Z"), tec)
    assert orden.contrato_id == escenario.id


async def test_sla_se_calcula_con_fechas_reales_y_se_congela(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    orden = await sincronizar_orden(db, _datos(tec.id, escenario.id,
        fecha_solicitud="2026-10-21T08:00:00-05:00", fecha_primera_atencion="2026-10-21T14:30:00Z"), tec)
    assert orden.tiempo_respuesta_horas == Decimal("1.50")
    assert orden.sla_horas_max_respuesta == 4
    acta = await db.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == orden.id))
    payload = json.loads(acta.payload_raw)
    assert payload["sla_horas_max_respuesta"] == 4
    assert payload["fecha_solicitud"] == "2026-10-21T08:00:00-05:00"


async def test_continuar_acta_heredada_no_reescribe_payload_ni_hash(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    vieja = OrdenServicio(id=uuid.uuid4(), contrato_id=escenario.id, equipo_serie="RO-1", tecnico_id=tec.id,
                         tipo_intervencion="PREVENTIVO", fecha_creacion_cliente=datetime(2026, 5, 1, tzinfo=timezone.utc))
    db.add(vieja)
    await db.flush()
    raw = '{"firma_base64":"AAAA", "legado":true}'
    legacy = ActaInmutable(orden_id=vieja.id, payload_raw=raw, hash_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                          firma_base64="AAAA", gps_latitud=-8, gps_longitud=-79)
    db.add(legacy)
    await db.flush()
    original = (legacy.payload_raw, legacy.hash_sha256)
    nueva = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    acta = await db.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == nueva.id))
    await db.refresh(legacy)
    assert (legacy.payload_raw, legacy.hash_sha256) == original
    assert acta.previous_hash == original[1]
    assert acta.secuencia == 2


async def test_cadena_usa_cabeza_y_no_fecha_inicio_transaccion(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    first = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    second = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    acta1 = await db.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == first.id))
    acta2 = await db.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == second.id))
    acta1.creado_en = datetime(2026, 10, 22, tzinfo=timezone.utc)
    acta2.creado_en = datetime(2026, 10, 20, tzinfo=timezone.utc)
    await db.flush()
    third = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    acta3 = await db.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == third.id))
    assert acta3.previous_hash == acta2.hash_sha256
    assert [acta1.secuencia, acta2.secuencia, acta3.secuencia] == [1, 2, 3]


async def test_reintento_uuid_de_otro_tecnico_no_devuelve_orden_ajena(db, escenario, crear_usuario):
    owner = await crear_usuario("TECNICO")
    other = await crear_usuario("TECNICO")
    original = await sincronizar_orden(db, _datos(owner.id, escenario.id), owner)
    with pytest.raises(TecnicoNoAutorizado):
        await sincronizar_orden(db, _datos(other.id, escenario.id, id=original.id), other)


async def test_fallo_de_stock_revierte_cabeza_y_secuencia_antes_de_reintento(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    repuesto = Repuesto(codigo="FILT-RETRY", descripcion="Filtro", costo_unitario_soles=1, stock_almacen_central=0)
    db.add(repuesto)
    await db.flush()
    body = _datos(tec.id, escenario.id, repuestos_consumidos=[{"repuesto_codigo": repuesto.codigo, "cantidad": 1}])
    with pytest.raises(StockInsuficiente):
        await sincronizar_orden(db, body, tec)
    equipo = await db.get(Equipo, "RO-1")
    assert equipo.ultimo_hash_acta is None and equipo.secuencia_acta == 0
    repuesto.stock_almacen_central = 1
    await db.flush()
    orden = await sincronizar_orden(db, body, tec)
    acta = await db.scalar(select(ActaInmutable).where(ActaInmutable.orden_id == orden.id))
    assert acta.previous_hash is None and acta.secuencia == 1
