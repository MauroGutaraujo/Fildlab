import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.equipo import Equipo
from app.models.orden import ActaInmutable
from orden_helpers import firma_png


@pytest.fixture
async def servicio(db, crear_orden):
    orden = await crear_orden(estado="SINCRONIZADA")
    orden.fecha_creacion_cliente = datetime(2026, 2, 5, 17, tzinfo=timezone.utc)
    raw = json.dumps({"orden_id": str(orden.id), "lectura": 7}, sort_keys=True)
    acta = ActaInmutable(orden_id=orden.id, equipo_serie=orden.equipo_serie,
        payload_raw=raw, hash_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        firma_base64=firma_png(), gps_latitud=-8, gps_longitud=-79)
    db.add(acta)
    await db.flush()
    return orden, acta


def ruta(orden):
    return f"/api/v1/equipos/{orden.equipo_serie}/componentes"


async def agregar(client, gerente_h, orden, **extra):
    r = await client.post(ruta(orden), headers=gerente_h, json={
        "nombre": "Membrana etapa 1", "tipo_componente": "MEMBRANA",
        "fecha_instalacion": "2026-01-03", "fabricante_modelo": "Modelo declarado", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def datos(orden, **extra):
    return {"id": str(uuid4()), "orden_id": str(orden.id), "tipo": "SUSTITUCION",
            "fecha_efectiva": "2026-02-01", "observacion": "Se sustituyó la pieza indicada en la orden", **extra}


async def test_alta_consulta_roles_y_fecha_desconocida(client, gerente_h, tecnico_h, servicio):
    orden, _ = servicio
    c = await agregar(client, gerente_h, orden, fecha_instalacion=None)
    assert c["ciclo_actual_desde"] is None
    assert c["creado_por_id"] is not None
    r = await client.get(ruta(orden), headers=tecnico_h)
    assert r.status_code == 200 and r.json()[0]["id"] == c["id"]
    assert (await client.post(ruta(orden), headers=tecnico_h, json={"nombre":"Filtro","tipo_componente":"FILTRO"})).status_code == 403
    assert (await client.get(ruta(orden))).status_code == 401


async def test_nombre_duplicado_ignorando_mayusculas(client, gerente_h, servicio):
    orden, _ = servicio
    await agregar(client, gerente_h, orden)
    r = await client.post(ruta(orden), headers=gerente_h, json={"nombre":"  MEMBRANA ETAPA 1 ","tipo_componente":"MEMBRANA"})
    assert r.status_code == 409


@pytest.mark.parametrize("fecha", ["2026-01-01", "2999-01-01"])
async def test_fecha_instalacion_invalida(client, gerente_h, servicio, fecha):
    orden, _ = servicio
    r = await client.post(ruta(orden), headers=gerente_h, json={"nombre":"Pieza","tipo_componente":"OTRO","fecha_instalacion":fecha})
    assert r.status_code == 422


@pytest.mark.parametrize("tipo", ["INSPECCION", "LIMPIEZA", "REPARACION_PARCIAL"])
async def test_trabajos_parciales_no_reinician_ciclo_ni_acta(client, gerente_h, db, servicio, tipo):
    orden, acta = servicio
    antes = (acta.payload_raw, acta.hash_sha256)
    c = await agregar(client, gerente_h, orden)
    r = await client.post(f"{ruta(orden)}/{c['id']}/intervenciones", headers=gerente_h, json=datos(orden, tipo=tipo))
    assert r.status_code == 201, r.text
    lista = (await client.get(ruta(orden), headers=gerente_h)).json()
    assert lista[0]["ciclo_actual_desde"] == "2026-01-03"
    await db.refresh(acta)
    assert (acta.payload_raw, acta.hash_sha256) == antes
    assert (await db.get(Equipo, orden.equipo_serie)).fecha_ultima_mantencion is None


async def test_sustitucion_afecta_solo_componente_y_conserva_evidencia(client, gerente_h, servicio):
    orden, acta = servicio
    c = await agregar(client, gerente_h, orden)
    otro = await agregar(client, gerente_h, orden, nombre="Prefiltro", tipo_componente="FILTRO", fecha_instalacion="2026-01-04")
    base = f"{ruta(orden)}/{c['id']}/intervenciones"
    cuerpo = datos(orden)
    r = await client.post(base, headers=gerente_h, json=cuerpo)
    assert r.status_code == 201, r.text
    assert r.json()["acta_hash"] == acta.hash_sha256
    assert r.json()["registrado_por_id"] is not None
    assert r.json()["registrado_en"]
    assert (await client.post(base, headers=gerente_h, json=cuerpo)).status_code == 200
    assert len((await client.get(base, headers=gerente_h)).json()) == 1
    cambiada = await client.post(base, headers=gerente_h, json={**cuerpo,"observacion":"Contenido diferente"})
    assert cambiada.status_code == 409
    lista = {x["id"]:x for x in (await client.get(ruta(orden), headers=gerente_h)).json()}
    assert lista[c["id"]]["ciclo_actual_desde"] == "2026-02-01"
    assert lista[otro["id"]]["ciclo_actual_desde"] == "2026-01-04"


async def test_captura_tardia_y_anulacion_preservan_historial(client, gerente_h, tecnico_h, servicio):
    orden, _ = servicio
    c = await agregar(client, gerente_h, orden)
    base = f"{ruta(orden)}/{c['id']}/intervenciones"
    nueva = (await client.post(base, headers=gerente_h, json=datos(orden, fecha_efectiva="2026-02-03"))).json()
    vieja = await client.post(base, headers=gerente_h, json=datos(orden, fecha_efectiva="2026-02-01"))
    assert vieja.status_code == 201
    assert (await client.get(ruta(orden), headers=gerente_h)).json()[0]["ciclo_actual_desde"] == "2026-02-03"
    anulacion = f"{base}/{nueva['id']}/anular"
    assert (await client.post(anulacion, headers=tecnico_h, json={"motivo":"Error"})).status_code == 403
    r = await client.post(anulacion, headers=gerente_h, json={"motivo":"Se vinculó la pieza incorrecta"})
    assert r.status_code == 201, r.text
    assert (await client.post(anulacion, headers=gerente_h, json={"motivo":"Se vinculó la pieza incorrecta"})).status_code == 200
    assert (await client.get(ruta(orden), headers=gerente_h)).json()[0]["ciclo_actual_desde"] == "2026-02-01"
    hist = (await client.get(base, headers=gerente_h)).json()
    assert len(hist) == 2
    assert next(x for x in hist if x["id"] == nueva["id"])["anulacion"]["motivo"] == "Se vinculó la pieza incorrecta"


@pytest.mark.parametrize("fecha", ["2026-01-02", "2026-02-06", "2999-01-01"])
async def test_intervencion_fuera_de_fechas(client, gerente_h, servicio, fecha):
    orden, _ = servicio
    c = await agregar(client, gerente_h, orden)
    r = await client.post(f"{ruta(orden)}/{c['id']}/intervenciones", headers=gerente_h, json=datos(orden, fecha_efectiva=fecha))
    assert r.status_code == 422


async def test_orden_de_otro_equipo_rechazada(client, gerente_h, servicio, crear_orden):
    orden, _ = servicio
    c = await agregar(client, gerente_h, orden)
    otra = await crear_orden()
    r = await client.post(f"{ruta(orden)}/{c['id']}/intervenciones", headers=gerente_h, json=datos(otra))
    assert r.status_code == 409


@pytest.mark.parametrize("alterar", [False, True])
async def test_orden_sin_acta_o_con_acta_alterada_no_respalda_evento(client, gerente_h, db, servicio, alterar):
    orden, acta = servicio
    c = await agregar(client, gerente_h, orden)
    if alterar:
        acta.payload_raw += "alterado"
    else:
        await db.delete(acta)
    await db.flush()
    r = await client.post(f"{ruta(orden)}/{c['id']}/intervenciones", headers=gerente_h, json=datos(orden))
    assert r.status_code == 409


async def test_cambio_instalacion_no_puede_contradecir_historial(client, gerente_h, servicio):
    orden, _ = servicio
    await agregar(client, gerente_h, orden)
    r = await client.put(f"/api/v1/equipos/{orden.equipo_serie}", headers=gerente_h, json={"fecha_instalacion":"2026-01-05"})
    assert r.status_code == 422


def solicitud(ruta_componente, accion, **extra):
    return f"{ruta_componente}/{accion}"


async def test_corregir_componente_audita_e_idempotencia_persiste(client, gerente_h, tecnico_h, servicio):
    orden, _ = servicio
    original = await agregar(client, gerente_h, orden)
    base = f"{ruta(orden)}/{original['id']}"
    assert original["revision"] == 1 and original["anulado_en"] is None
    sustitucion = await client.post(f"{base}/intervenciones", headers=gerente_h, json=datos(orden, fecha_efectiva="2026-02-01"))
    assert sustitucion.status_code == 201
    cuerpo = {"solicitud_id": str(uuid4()), "revision_esperada": 1,
        "motivo": "La etiqueta física confirma el modelo y la posición", "nombre": "Membrana etapa A",
        "tipo_componente": "MEMBRANA", "fecha_instalacion": "2026-01-04", "fabricante_modelo": "Modelo verificado"}
    corregida = await client.post(solicitud(base, "correcciones"), headers=gerente_h, json=cuerpo)
    assert corregida.status_code == 201, corregida.text
    assert corregida.json()["revision"] == 2
    assert corregida.json()["ciclo_actual_desde"] == "2026-02-01"
    assert corregida.json()["creado_por_id"] == original["creado_por_id"]
    assert corregida.json()["creado_en"] == original["creado_en"]
    await client.post(solicitud(base, "correcciones"), headers=gerente_h, json={
        **cuerpo, "solicitud_id": str(uuid4()), "revision_esperada": 2, "nombre": "Membrana etapa B"})
    repetida = await client.post(solicitud(base, "correcciones"), headers=gerente_h, json=cuerpo)
    assert repetida.status_code == 200 and repetida.json() == corregida.json()
    cambios = await client.get(solicitud(base, "cambios"), headers=tecnico_h)
    assert cambios.status_code == 200
    assert len(cambios.json()) == 2
    primera = next(c for c in cambios.json() if c["solicitud_id"] == cuerpo["solicitud_id"])
    assert primera["accion"] == "CORREGIR"
    assert primera["revision_anterior"] == 1 and primera["revision_nueva"] == 2
    assert primera["antes"]["nombre"] == "Membrana etapa 1"
    assert primera["despues"]["nombre"] == "Membrana etapa A"
    assert primera["motivo"] == cuerpo["motivo"]
    assert primera["antes"]["ciclo_actual_desde"] == "2026-02-01"
    assert primera["registrado_por_id"] is not None and primera["registrado_en"]
    assert (await client.get(solicitud(base, "cambios"), headers=gerente_h, params={"limit": 1, "offset": 1})).json()[0]["revision_nueva"] == 3


async def test_revision_obsoleta_o_uuid_con_contenido_distinto_no_sobrescribe(client, gerente_h, servicio):
    orden, _ = servicio
    original = await agregar(client, gerente_h, orden)
    base = f"{ruta(orden)}/{original['id']}"
    cuerpo = {"solicitud_id": str(uuid4()), "revision_esperada": 1, "motivo": "Corrección documentada",
        "nombre": "Membrana corregida", "tipo_componente": "MEMBRANA", "fecha_instalacion": "2026-01-03", "fabricante_modelo": "Modelo declarado"}
    primera = await client.post(solicitud(base, "correcciones"), headers=gerente_h, json=cuerpo)
    assert primera.status_code == 201, primera.text
    serie_incorrecta = await client.post(f"/api/v1/equipos/OTRO/componentes/{original['id']}/correcciones", headers=gerente_h, json=cuerpo)
    assert serie_incorrecta.status_code == 404
    obsoleta = await client.post(solicitud(base, "correcciones"), headers=gerente_h, json={
        **cuerpo, "solicitud_id": str(uuid4()), "nombre": "No debe guardarse"})
    assert obsoleta.status_code == 409
    conflicto = await client.post(solicitud(base, "correcciones"), headers=gerente_h, json={**cuerpo, "nombre": "UUID reutilizado"})
    assert conflicto.status_code == 409
    ficha = (await client.get(ruta(orden), headers=gerente_h)).json()[0]
    assert ficha["nombre"] == "Membrana corregida" and ficha["revision"] == 2


async def test_anular_restaurar_y_reutilizar_nombre_conserva_historial(client, gerente_h, tecnico_h, servicio):
    orden, _ = servicio
    original = await agregar(client, gerente_h, orden)
    base = f"{ruta(orden)}/{original['id']}"
    cuerpo_anular = {"solicitud_id": str(uuid4()), "revision_esperada": 1, "motivo": "El alta correspondía a otro equipo"}
    anulada = await client.post(solicitud(base, "anular-alta"), headers=gerente_h, json=cuerpo_anular)
    assert anulada.status_code == 201, anulada.text
    assert anulada.json()["revision"] == 2 and anulada.json()["anulado_en"]
    assert anulada.json()["ciclo_actual_desde"] is None
    assert (await client.get(ruta(orden), headers=tecnico_h)).json() == []
    incluidos = await client.get(ruta(orden), headers=tecnico_h, params={"incluir_anulados": "true"})
    assert incluidos.status_code == 200 and incluidos.json()[0]["id"] == original["id"]
    assert (await client.post(f"{base}/intervenciones", headers=gerente_h, json=datos(orden))).status_code == 409
    otra = await agregar(client, gerente_h, orden, nombre="Membrana etapa 1")
    restaurar = {"solicitud_id": str(uuid4()), "revision_esperada": 2, "motivo": "Se identificó el equipo correcto",
        "nombre": "Membrana etapa 1", "tipo_componente": "MEMBRANA", "fecha_instalacion": "2026-01-03", "fabricante_modelo": "Modelo declarado"}
    colision = await client.post(solicitud(base, "restablecer-alta"), headers=gerente_h, json=restaurar)
    assert colision.status_code == 409
    await client.post(f"{ruta(orden)}/{otra['id']}/anular-alta", headers=gerente_h, json={
        "solicitud_id": str(uuid4()), "revision_esperada": 1, "motivo": "Permitir corregir la asignación"})
    restaurada = await client.post(f"{base}/restablecer-alta", headers=gerente_h, json=restaurar)
    assert restaurada.status_code == 201, restaurada.text
    assert restaurada.json()["revision"] == 3 and restaurada.json()["anulado_en"] is None
    assert restaurada.json()["creado_en"] == original["creado_en"]
    hist = await client.get(f"{base}/cambios", headers=tecnico_h)
    assert [x["accion"] for x in hist.json()] == ["ANULAR_ALTA", "RESTABLECER_ALTA"]


async def test_anulacion_requiere_intervenciones_anuladas_y_reintento_precede_bloqueo(client, gerente_h, servicio):
    orden, _ = servicio
    c = await agregar(client, gerente_h, orden)
    base = f"{ruta(orden)}/{c['id']}"
    intervenciones = f"{base}/intervenciones"
    cuerpo_intervencion = datos(orden)
    registro = await client.post(intervenciones, headers=gerente_h, json=cuerpo_intervencion)
    assert registro.status_code == 201
    anular_alta = {"solicitud_id": str(uuid4()), "revision_esperada": 1, "motivo": "Alta que no corresponde"}
    bloqueada = await client.post(f"{base}/anular-alta", headers=gerente_h, json=anular_alta)
    assert bloqueada.status_code == 409
    anulacion = await client.post(f"{intervenciones}/{registro.json()['id']}/anular", headers=gerente_h, json={"motivo":"Intervención duplicada"})
    assert anulacion.status_code == 201
    baja = await client.post(f"{base}/anular-alta", headers=gerente_h, json=anular_alta)
    assert baja.status_code == 201, baja.text
    assert (await client.post(intervenciones, headers=gerente_h, json=cuerpo_intervencion)).status_code == 200
    nueva = await client.post(intervenciones, headers=gerente_h, json=datos(orden))
    assert nueva.status_code == 409


async def test_fecha_corregida_no_supera_intervencion_anulada_y_campos_sin_cambio_se_rechazan(client, gerente_h, servicio):
    orden, _ = servicio
    c = await agregar(client, gerente_h, orden)
    base = f"{ruta(orden)}/{c['id']}"
    intervencion = await client.post(f"{base}/intervenciones", headers=gerente_h, json=datos(orden, fecha_efectiva="2026-02-01"))
    assert intervencion.status_code == 201
    await client.post(f"{base}/intervenciones/{intervencion.json()['id']}/anular", headers=gerente_h, json={"motivo":"Fecha ingresada por error"})
    comun = {"revision_esperada":1,"motivo":"Verificación de instalación","nombre":c["nombre"],
        "tipo_componente":c["tipo_componente"],"fabricante_modelo":c["fabricante_modelo"]}
    posterior = await client.post(f"{base}/correcciones", headers=gerente_h, json={**comun,
        "solicitud_id":str(uuid4()),"fecha_instalacion":"2026-02-02"})
    assert posterior.status_code == 422
    sin_cambios = await client.post(f"{base}/correcciones", headers=gerente_h, json={**comun,
        "solicitud_id":str(uuid4()),"fecha_instalacion":c["fecha_instalacion"]})
    assert sin_cambios.status_code == 422
    vacio = await client.post(f"{base}/anular-alta", headers=gerente_h, json={
        "solicitud_id":str(uuid4()),"revision_esperada":1,"motivo":"   "})
    assert vacio.status_code == 422
