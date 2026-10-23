import hashlib
import json
import uuid

from orden_helpers import firma_png


async def test_alta_servicio_reintento_acta_adenda_liquidacion_y_bi(client, gerente_h, crear_usuario, auth_headers):
    tecnico = await crear_usuario("TECNICO")
    tecnico_h = auth_headers(tecnico)
    ruc = "20612493821"
    assert (await client.post("/api/v1/clientes", headers=gerente_h, json={"ruc": ruc, "razon_social": "Prueba integral", "direccion": "Trujillo"})).status_code == 201
    contrato_resp = await client.post("/api/v1/contratos", headers=gerente_h, json={
        "cliente_ruc": ruc, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31", "monto_mensual_soles": "1000.00", "sla_horas_max_respuesta": 4,
    })
    assert contrato_resp.status_code == 201
    contrato = contrato_resp.json()["id"]
    lecturas = dict(tds_entrada_ppm=350, tds_post_membrana_ppm=8, tds_producto_final_ppm=5, ph=7,
                    conductividad_us_cm=15, resistividad_mohm_cm=1.2, litros_consumidos_red=500, litros_agua_pura=420)
    equipo_resp = await client.post("/api/v1/equipos", headers=gerente_h, json={
        "serie": "FLUJO-1", "cliente_ruc": ruc, "contrato_id": contrato, "tipo_sistema": "FILTRO",
        "fecha_instalacion": "2026-01-01", "parametros_nominales": lecturas,
    })
    assert equipo_resp.status_code == 201
    assert equipo_resp.json()["contrato_id"] == contrato
    assert (await client.post("/api/v1/repuestos", headers=gerente_h, json={"codigo": "FLUJO-FILT", "descripcion": "Filtro", "costo_unitario_soles": "5.00"})).status_code == 201
    assert (await client.post("/api/v1/inventario/movimientos", headers=gerente_h, json={"repuesto_codigo": "FLUJO-FILT", "tipo": "ENTRADA", "cantidad": 10})).status_code == 201
    orden_id = str(uuid.uuid4())
    body = dict(id=orden_id, contrato_id=contrato, equipo_serie="FLUJO-1", tecnico_id=tecnico.id,
                tipo_intervencion="PREVENTIVO", fecha_creacion_cliente="2026-09-15T17:00:00Z",
                fecha_solicitud="2026-09-15T10:00:00Z", fecha_primera_atencion="2026-09-15T12:00:00Z",
                lecturas_agua=lecturas, firma_base64=firma_png(), gps_latitud=-8.11, gps_longitud=-79.02,
                repuestos_consumidos=[{"repuesto_codigo": "FLUJO-FILT", "cantidad": 3}])
    respuesta = await client.post("/api/v1/ordenes", headers=tecnico_h, json=body)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["tiempo_respuesta_horas"] == "2.00"
    assert (await client.post("/api/v1/ordenes", headers=tecnico_h, json=body)).status_code == 200
    assert (await client.get("/api/v1/repuestos/FLUJO-FILT", headers=gerente_h)).json()["stock_almacen_central"] == 7
    acta = (await client.get(f"/api/v1/ordenes/{orden_id}/acta", headers=gerente_h)).json()
    assert hashlib.sha256(acta["payload_raw"].encode()).hexdigest() == acta["hash_sha256"]
    assert json.loads(acta["payload_raw"])["repuestos_consumidos"] == body["repuestos_consumidos"]
    directo = await client.post("/api/v1/inventario/movimientos", headers=gerente_h, json={
        "repuesto_codigo": "FLUJO-FILT", "tipo": "AJUSTE_ENTRADA", "cantidad": 1, "orden_id": orden_id,
    })
    assert directo.status_code == 409
    adenda = await client.post(f"/api/v1/ordenes/{orden_id}/adendas", headers=gerente_h, json={
        "observacion": "Se devuelve un filtro sin utilizar", "ajuste_repuestos": [{"repuesto_codigo": "FLUJO-FILT", "delta": 1}],
    })
    assert adenda.status_code == 201
    assert (await client.post(f"/api/v1/ordenes/{orden_id}/liquidar", headers=gerente_h)).status_code == 200
    assert (await client.get(f"/api/v1/ordenes/{orden_id}/acta", headers=gerente_h)).json() == acta
    assert (await client.get("/api/v1/repuestos/FLUJO-FILT", headers=gerente_h)).json()["stock_almacen_central"] == 8
    bi = (await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)).json()["contratos"][0]
    assert bi["costo_repuestos_soles"] == "10.00"
    assert bi["historial_completo"] is True
    sla = (await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)).json()
    assert sla["pct_cumplimiento"] == 100
    assert sla["ordenes_sin_medicion"] == 0
