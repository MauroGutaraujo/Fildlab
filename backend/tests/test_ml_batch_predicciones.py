from datetime import date, datetime, timedelta, timezone

import pytest
import hashlib

from sqlalchemy import func, select

from app.ml.batch_predicciones import correr_batch
from app.models.cliente import Cliente
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul
from ml_helpers import dataset_estable


@pytest.fixture(autouse=True)
def entrada_controlada(monkeypatch,tmp_path):
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            # En UTC ya es 23, pero en Lima es todavía 22.
            return datetime(2026, 10, 23, 2, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr("app.ml.batch_predicciones.datetime", Reloj)
    monkeypatch.setattr("app.schemas.prediccion_rul.datetime", Reloj)
    from app.ml.artefacto_rul import exportar_modelo
    archivo=tmp_path/"modelo.json"
    sha=exportar_modelo(dataset_estable(),archivo)
    monkeypatch.setenv("RUL_MODELO_PATH",str(archivo))
    monkeypatch.setenv("RUL_MODELO_SHA256",sha)


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
    await _equipo(db, crear_cliente, serie="EQ-1", tipo_sistema="OSMOSIS_INVERSA", fecha_instalacion=date(2026, 7, 14))
    await _equipo(db, crear_cliente, serie="EQ-2", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 10, 22))
    await db.commit()

    await correr_batch(session=db)

    filas = (await db.execute(select(PrediccionRul))).scalars().all()
    assert {f.equipo_serie for f in filas} == {"EQ-1", "EQ-2"}
    por_serie = {f.equipo_serie: f for f in filas}
    assert por_serie["EQ-1"].dias_vida_util_remanente == 80
    assert por_serie["EQ-2"].dias_vida_util_remanente == 80
    assert por_serie["EQ-1"].version_calculo == "COX_INSTALACION_V3"
    assert por_serie["EQ-1"].fecha_referencia == date(2026, 7, 14)


async def test_batch_fecha_futura_registra_abstencion_y_no_conserva_cifra_vieja(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-FUTURO", tipo_sistema="FILTRO",
                 fecha_instalacion=date(2026, 10, 24))
    db.add(PrediccionRul(equipo_serie="EQ-FUTURO", dias_vida_util_remanente=200, nivel_alerta="VERDE"))
    await db.commit()

    await correr_batch(session=db)

    db.expire_all()
    p = await db.get(PrediccionRul, "EQ-FUTURO")
    assert p.dias_vida_util_remanente is None and p.nivel_alerta is None
    assert p.motivo_no_estimable == "FECHA_FUTURA"


async def test_batch_es_idempotente(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-1", tipo_sistema="ABLANDADOR", fecha_instalacion=date(2026, 10, 22))
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


async def test_batch_ignora_mantenimiento_global_y_conserva_antiguedad_del_sistema(db, crear_cliente):
    instalado_hace_mucho = date(2020, 1, 1)
    mantenido_hace_poco = date(2026, 10, 17)
    await _equipo(db, crear_cliente, serie="EQ-MANTENIDO", tipo_sistema="FILTRO",
                 fecha_instalacion=instalado_hace_mucho, fecha_ultima_mantencion=mantenido_hace_poco)
    await _equipo(db, crear_cliente, serie="EQ-SIN-MANTENER", tipo_sistema="FILTRO",
                 fecha_instalacion=instalado_hace_mucho)
    await db.commit()

    await correr_batch(session=db)

    mantenido = await db.get(PrediccionRul, "EQ-MANTENIDO")
    sin_mantener = await db.get(PrediccionRul, "EQ-SIN-MANTENER")
    assert mantenido.dias_vida_util_remanente is None
    assert mantenido.motivo_no_estimable == "EDAD_FUERA_SOPORTE"
    assert mantenido.fecha_referencia == date(2020, 1, 1)
    assert sin_mantener.dias_vida_util_remanente is None
    assert sin_mantener.motivo_no_estimable == "EDAD_FUERA_SOPORTE"


async def test_batch_tipo_desconocido_registra_abstencion(db, crear_cliente, monkeypatch):
    """El CHECK constraint de la BD ya impide guardar un tipo_sistema invalido en equipos —
    esta prueba parchea la lista de tipos reconocidos del propio modulo batch para forzar
    la rama defensiva (REQ-19) sin depender de poder insertar un dato realmente imposible."""
    await _equipo(db, crear_cliente, serie="EQ-FILTRO", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 1, 1))
    await db.commit()

    monkeypatch.setattr("app.ml.batch_predicciones.TIPOS_SISTEMA", ("OSMOSIS_INVERSA", "ABLANDADOR"))
    await correr_batch(session=db)

    p = await db.get(PrediccionRul, "EQ-FILTRO")
    assert p.dias_vida_util_remanente is None
    assert p.motivo_no_estimable == "TIPO_DESCONOCIDO"


async def test_batch_modelo_invalido_conserva_resultado_anterior_sin_renovar(db, crear_cliente, monkeypatch):
    monkeypatch.setenv("RUL_MODELO_SHA256","0"*64)
    await _equipo(db, crear_cliente, serie="EQ-INESTABLE", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 10, 22))
    db.add(PrediccionRul(equipo_serie="EQ-INESTABLE", dias_vida_util_remanente=100, nivel_alerta="VERDE"))
    await db.commit()
    with pytest.raises(ValueError):
        await correr_batch(session=db)
    db.expire_all()
    p = await db.get(PrediccionRul, "EQ-INESTABLE")
    assert p.dias_vida_util_remanente == 100 and p.nivel_alerta == "VERDE"
    assert p.motivo_no_estimable is None


async def test_batch_real_usa_simulacion_corregida_y_api_publica_version(db, crear_cliente, monkeypatch, client, gerente_h):
    from app.ml.dataset_sintetico import SUPUESTOS_SIMULACION, generar_dataset
    # Usar el manifiesto publicado, no generar/ajustar dentro del batch.
    monkeypatch.delenv("RUL_MODELO_PATH")
    monkeypatch.delenv("RUL_MODELO_SHA256")
    for tipo in SUPUESTOS_SIMULACION:
        await _equipo(db, crear_cliente, serie=tipo, tipo_sistema=tipo, fecha_instalacion=date(2026, 10, 22))
    await db.commit()
    await correr_batch(session=db)
    db.expire_all()
    respuesta = await client.get("/api/v1/equipos/predicciones-rul", headers=gerente_h)
    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert len(filas) == 3
    for p in filas:
        mediana = SUPUESTOS_SIMULACION[p["equipo_serie"]]["mediana_dias"]
        assert mediana * .8 <= p["dias_vida_util_remanente"] <= mediana * 1.2
        assert p["estado_estimacion"] == "ESTIMADA"
        assert p["experimental"] is True and p["origen_datos"] == "SINTETICOS"
        assert p["version_calculo"] == "COX_INSTALACION_V3"
        assert p["fecha_referencia"] == "2026-10-22"
        assert p["alcance_estimacion"] == "SISTEMA_DESDE_INSTALACION"
        assert p["version_dataset"] == "WEIBULL_CENSURA_V2"


async def test_modelo_ausente_aborta_sin_publicar_resultado(db, crear_cliente, monkeypatch,tmp_path):
    await _equipo(db, crear_cliente, serie="EQ-DATO", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 10, 22))
    await db.commit()
    monkeypatch.setenv("RUL_MODELO_PATH",str(tmp_path/"ausente.json"))
    with pytest.raises(ValueError, match="Modelo ausente"):
        await correr_batch(session=db)
    assert await db.get(PrediccionRul, "EQ-DATO") is None
