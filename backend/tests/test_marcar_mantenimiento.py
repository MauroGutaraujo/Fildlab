from datetime import date

from app.models.equipo import Equipo


async def _equipo(db, crear_cliente, *, serie="EQ-1", ruc="20612493821", fecha_instalacion=date(2026, 1, 1)):
    await crear_cliente(ruc)
    e = Equipo(serie=serie, cliente_ruc=ruc, tipo_sistema="FILTRO",
              fecha_instalacion=fecha_instalacion, parametros_nominales={})
    db.add(e)
    await db.flush()
    return e


async def test_marcar_mantenimiento_solo_gerencia(client, tecnico_h, db, crear_cliente):
    await _equipo(db, crear_cliente)
    await db.commit()
    r = await client.post("/api/v1/equipos/EQ-1/marcar-mantenimiento", headers=tecnico_h)
    assert r.status_code == 403


async def test_marcar_mantenimiento_sin_token_401(client):
    assert (await client.post("/api/v1/equipos/EQ-1/marcar-mantenimiento")).status_code == 401


async def test_endpoint_antiguo_retirado_no_reinicia_fecha(client, gerente_h, db, crear_cliente):
    equipo = await _equipo(db, crear_cliente)
    equipo.fecha_ultima_mantencion = date(2026, 1, 10)
    await db.commit()
    r = await client.post("/api/v1/equipos/EQ-1/marcar-mantenimiento", headers=gerente_h)
    assert r.status_code == 410
    await db.refresh(equipo)
    assert equipo.fecha_ultima_mantencion == date(2026, 1, 10)


async def test_marcar_mantenimiento_equipo_inexistente_404(client, gerente_h):
    r = await client.post("/api/v1/equipos/NO-EXISTE/marcar-mantenimiento", headers=gerente_h)
    assert r.status_code == 404
    assert r.json()["detail"] == "Equipo no encontrado"


async def test_equipo_recien_creado_no_tiene_fecha_ultima_mantencion(client, gerente_h, db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-2")
    await db.commit()
    r = await client.get("/api/v1/equipos/EQ-2", headers=gerente_h)
    assert r.json()["fecha_ultima_mantencion"] is None
