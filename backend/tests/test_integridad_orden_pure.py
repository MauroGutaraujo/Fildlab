import base64
import hashlib
import json
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.orden import OrdenSincronizarIn
from app.services.ordenes import payload_raw_canonico
from orden_helpers import firma_png


def datos_orden(**overrides):
    body = dict(
        id=uuid.UUID("7aabfca6-4451-4219-8e73-f30f70cb29b0"), contrato_id=1,
        equipo_serie="RO-1", tecnico_id=1, tipo_intervencion="PREVENTIVO",
        fecha_creacion_cliente="2026-10-21T15:00:00-05:00", firma_base64=firma_png(),
        lecturas_agua=dict(tds_entrada_ppm=350, tds_post_membrana_ppm=8, tds_producto_final_ppm=5,
                          ph=7, conductividad_us_cm=15, resistividad_mohm_cm=1.2,
                          litros_consumidos_red=500, litros_agua_pura=420),
        gps_latitud="-8.1116000", gps_longitud="-79.0288000",
    )
    body.update(overrides)
    return OrdenSincronizarIn(**body)


def test_consumibles_forman_parte_del_hash_versionado():
    sin = payload_raw_canonico(datos_orden())
    con = payload_raw_canonico(datos_orden(repuestos_consumidos=[{"repuesto_codigo": "FILT", "cantidad": 2}]))
    assert hashlib.sha256(sin.encode()).hexdigest() != hashlib.sha256(con.encode()).hexdigest()
    payload = json.loads(con)
    assert payload["version"] == 2
    assert payload["repuestos_consumidos"] == [{"repuesto_codigo": "FILT", "cantidad": 2}]


@pytest.mark.parametrize("firma", [
    "not an image", "AAAA", "data:image/jpeg;base64,AAAA",
    "data:image/png;base64," + base64.b64encode(b"not a PNG").decode(),
    firma_png(vacia=True), firma_png(vacia=True, fondo=(0, 0, 0, 0)),
    firma_png(size=(2049, 40)), firma_png(size=(1500, 1500)),
    firma_png(formato="JPEG"), "A" * 700_000,
    firma_png()[:-20],
], ids=["texto", "base64_no_png", "mime", "contenido", "blanca", "transparente", "ancho", "pixeles", "jpeg", "bytes", "truncada"])
def test_firma_invalida_o_vacia_rechazada(firma):
    with pytest.raises(ValidationError):
        datos_orden(firma_base64=firma)


@pytest.mark.parametrize("prefijo", [True, False])
def test_firma_png_con_trazo_valida(prefijo):
    firma = firma_png(fondo=(0, 0, 0, 0))
    if not prefijo:
        firma = firma.split(",", 1)[1]
    assert datos_orden(firma_base64=firma).firma_base64 == firma


@pytest.mark.parametrize("fechas", [
    {"fecha_solicitud": "2026-10-21T09:00:00-05:00"},
    {"fecha_primera_atencion": "2026-10-21T10:00:00-05:00"},
    {"fecha_solicitud": "2026-10-21T09:00:00", "fecha_primera_atencion": "2026-10-21T10:00:00-05:00"},
    {"fecha_solicitud": "2026-10-21T11:00:00-05:00", "fecha_primera_atencion": "2026-10-21T10:00:00-05:00"},
    {"fecha_solicitud": "2026-10-21T09:00:00-05:00", "fecha_primera_atencion": "2026-10-21T16:00:00-05:00"},
    {"fecha_creacion_cliente": "2026-10-21T15:00:00"},
])
def test_fechas_sla_requieren_pareja_zona_y_orden_temporal(fechas):
    with pytest.raises(ValidationError):
        datos_orden(**fechas)


def test_fechas_sla_forman_parte_del_contenido_protegido():
    sin = payload_raw_canonico(datos_orden())
    con = payload_raw_canonico(datos_orden(fecha_solicitud="2026-10-21T14:00:00Z",
                                        fecha_primera_atencion="2026-10-21T10:00:00-05:00"))
    assert sin != con
    assert json.loads(con)["fecha_solicitud"] == "2026-10-21T14:00:00+00:00"
