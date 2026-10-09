from datetime import date, timedelta

from sqlalchemy import func, select

from app.ml.batch_predicciones import correr_batch
from app.models.cliente import Cliente
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul


async def _equipo(db, crear_cliente, *, serie, tipo_sistema, fecha_instalacion, ruc="20612493821",
                   fecha_ultima_mantencion=None):
    if await db.get(Cliente, ruc) is None:
        await crear_cliente(ruc)
    e = Equipo(serie=serie, cliente_ruc=ruc, tipo_sistema=tipo_sistema,
              fecha_instalacion=fecha_instalacion, parametros_nominales={},
              fecha_ultima_mantencion=fecha_ultima_mantencion)
    db.add(e)
    await db.flush()
    return e


async def test_batch_puebla_predicciones_para_equipos_calificables(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-1", tipo_sistema="OSMOSIS_INVERSA", fecha_instalacion=date(2025, 1, 1))
    await _equipo(db, crear_cliente, serie="EQ-2", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 1, 1))
    await db.commit()

    await correr_batch(session=db)

    filas = (await db.execute(select(PrediccionRul))).scalars().all()
    assert {f.equipo_serie for f in filas} == {"EQ-1", "EQ-2"}


async def test_batch_omite_equipo_con_fecha_futura(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-FUTURO", tipo_sistema="FILTRO",
                 fecha_instalacion=date.today() + timedelta(days=10))
    await db.commit()

    await correr_batch(session=db)

    assert (await db.get(PrediccionRul, "EQ-FUTURO")) is None


async def test_batch_es_idempotente(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-1", tipo_sistema="ABLANDADOR", fecha_instalacion=date(2024, 1, 1))
    await db.commit()

    await correr_batch(session=db)
    db.expire_all()
    primera = await db.get(PrediccionRul, "EQ-1")
    dias_primera = primera.dias_vida_util_remanente

    await correr_batch(session=db)
    db.expire_all()
    segunda = await db.get(PrediccionRul, "EQ-1")

    assert segunda.dias_vida_util_remanente == dias_primera
    total = (await db.execute(select(func.count()).select_from(PrediccionRul))).scalar()
    assert total == 1


async def test_batch_sin_equipos_no_falla(db):
    await correr_batch(session=db)
    total = (await db.execute(select(func.count()).select_from(PrediccionRul))).scalar()
    assert total == 0


async def test_batch_cuenta_antiguedad_desde_la_ultima_mantencion_no_desde_instalacion(db, crear_cliente):
    """Equipo instalado hace mucho tiempo (quedaria en 0 dias/ROJO), pero con un
    mantenimiento reciente registrado — el reloj debe reiniciarse desde esa fecha."""
    instalado_hace_mucho = date(2020, 1, 1)
    mantenido_hace_poco = date.today() - timedelta(days=5)
    await _equipo(db, crear_cliente, serie="EQ-MANTENIDO", tipo_sistema="FILTRO",
                 fecha_instalacion=instalado_hace_mucho, fecha_ultima_mantencion=mantenido_hace_poco)
    await _equipo(db, crear_cliente, serie="EQ-SIN-MANTENER", tipo_sistema="FILTRO",
                 fecha_instalacion=instalado_hace_mucho)
    await db.commit()

    await correr_batch(session=db)

    mantenido = await db.get(PrediccionRul, "EQ-MANTENIDO")
    sin_mantener = await db.get(PrediccionRul, "EQ-SIN-MANTENER")
    assert mantenido.dias_vida_util_remanente > sin_mantener.dias_vida_util_remanente
    assert sin_mantener.dias_vida_util_remanente == 0


async def test_batch_omite_tipo_sistema_no_reconocido(db, crear_cliente, monkeypatch):
    """El CHECK constraint de la BD ya impide guardar un tipo_sistema invalido en equipos —
    esta prueba parchea la lista de tipos reconocidos del propio modulo batch para forzar
    la rama defensiva (REQ-19) sin depender de poder insertar un dato realmente imposible."""
    await _equipo(db, crear_cliente, serie="EQ-FILTRO", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 1, 1))
    await db.commit()

    monkeypatch.setattr("app.ml.batch_predicciones.TIPOS_SISTEMA", ("OSMOSIS_INVERSA", "ABLANDADOR"))
    await correr_batch(session=db)

    assert (await db.get(PrediccionRul, "EQ-FILTRO")) is None
