import os
import uuid
from pathlib import Path

import pytest

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.db import assert_safe_test_target, make_engine
from app.models import Base


def migrar(connection, revision, *, bajar=False):
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    config.attributes["connection"] = connection
    (command.downgrade if bajar else command.upgrade)(config, revision)


async def test_migraciones_conservan_acta_legacy_y_congelan_base_conocida(engine):
    # engine obliga a pasar la validación positiva del fixture; todo vive en otro esquema único.
    url = os.environ["DATABASE_URL_TEST"]
    assert_safe_test_target(url)
    schema = f"test_{uuid.uuid4().hex}"
    aislado = make_engine(url, schema=schema)
    creado = False
    try:
        async with aislado.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        creado = True
        async with aislado.begin() as conn:
            await conn.run_sync(migrar, "7fe488f9399d")
            await conn.execute(text("INSERT INTO clientes(ruc,razon_social,direccion) VALUES ('20612493821','Legacy','Lima')"))
            await conn.execute(text("INSERT INTO usuarios(id,nombre,email,password_hash,rol) VALUES (1,'Legacy','legacy@test.pe','dummy','TECNICO')"))
            await conn.execute(text("INSERT INTO contratos(id,cliente_ruc,fecha_inicio,fecha_fin,monto_mensual_soles) VALUES (1,'20612493821','2026-01-01','2026-12-31',1000)"))
            await conn.execute(text("INSERT INTO equipos(serie,cliente_ruc,contrato_id,tipo_sistema,fecha_instalacion,parametros_nominales) VALUES ('LEGACY','20612493821',1,'FILTRO','2026-01-01','{}')"))
            await conn.execute(text("UPDATE equipos SET fecha_ultima_mantencion='2026-01-20'"))
            await conn.execute(text("INSERT INTO predicciones_rul(equipo_serie,dias_vida_util_remanente,nivel_alerta) VALUES ('LEGACY',50,'AMARILLO')"))
            await conn.execute(text("INSERT INTO ordenes_servicio(id,contrato_id,equipo_serie,tecnico_id,tipo_intervencion,fecha_creacion_cliente) VALUES ('00000000-0000-0000-0000-000000000001',1,'LEGACY',1,'PREVENTIVO','2026-09-01T10:00:00Z')"))
            await conn.execute(text("INSERT INTO actas_inmutables(orden_id,payload_raw,hash_sha256,firma_base64,gps_latitud,gps_longitud) VALUES ('00000000-0000-0000-0000-000000000001',:payload,:hash,'legacy',-8,-79)"), {"payload": '{"legacy":true}', "hash": "a" * 64})
            await conn.execute(text("INSERT INTO repuestos(codigo,descripcion,costo_unitario_soles) VALUES ('LEG','Legacy',7)"))
            await conn.execute(text("INSERT INTO movimientos_inventario(repuesto_codigo,tipo,cantidad,orden_id,usuario_id) VALUES ('LEG','SALIDA_ORDEN',2,'00000000-0000-0000-0000-000000000001',1)"))
        async with aislado.begin() as conn:
            await conn.run_sync(migrar, "head")
            def columnas_coherentes(connection):
                inspector = inspect(connection)
                for tabla in Base.metadata.sorted_tables:
                    assert {c["name"] for c in inspector.get_columns(tabla.name)} == set(tabla.columns.keys()), tabla.name
            await conn.run_sync(columnas_coherentes)
            acta = (await conn.execute(text("SELECT payload_raw, hash_sha256, previous_hash, secuencia FROM actas_inmutables"))).one()
            assert tuple(acta) == ('{"legacy":true}', "a" * 64, None, None)
            assert (await conn.execute(text("SELECT ultimo_hash_acta, secuencia_acta FROM equipos"))).one() == ("a" * 64, 1)
            assert (await conn.execute(text("SELECT origen, monto_mensual_soles FROM condiciones_contrato"))).one() == ("BASE_LEGADA", 1000)
            assert (await conn.execute(text("SELECT costo_unitario_soles,costo_historico_confirmado FROM movimientos_inventario"))).one() == (7, False)
            assert (await conn.execute(text("SELECT version_calculo,dias_vida_util_remanente,nivel_alerta FROM predicciones_rul"))).one() == ("LEGADO", 50, "AMARILLO")
            assert (await conn.execute(text("SELECT fecha_referencia FROM predicciones_rul"))).scalar() is None
            legado = (await conn.execute(text("SELECT origen,ejecucion_id,calculado_en,fecha_evaluacion,tipo_referencia,vence_en,dias_vida_util_remanente FROM resultados_rul"))).one()
            assert legado.origen == "LEGADO" and legado.ejecucion_id is None
            assert legado.fecha_evaluacion is None and legado.tipo_referencia is None and legado.vence_en is None
            assert legado.dias_vida_util_remanente == 50
            assert legado.calculado_en == (await conn.execute(text("SELECT actualizado_en FROM predicciones_rul"))).scalar()
            assert str((await conn.execute(text("SELECT fecha_ultima_mantencion FROM equipos"))).scalar()) == "2026-01-20"
            assert (await conn.execute(text("SELECT count(*) FROM componentes_equipo"))).scalar() == 0
            assert (await conn.execute(text("SELECT revision, anulado_en FROM componentes_equipo LIMIT 1"))).first() is None
            assert (await conn.execute(text("SELECT count(*) FROM cambios_componentes"))).scalar() == 0
            await conn.execute(text("INSERT INTO componentes_equipo(id,equipo_serie,nombre,tipo_componente,creado_por_id) VALUES ('00000000-0000-0000-0000-000000000010','LEGACY','Membrana','MEMBRANA',1)"))
            assert (await conn.execute(text("SELECT revision, anulado_en FROM componentes_equipo WHERE id='00000000-0000-0000-0000-000000000010'"))).one() == (1, None)
            await conn.execute(text("UPDATE componentes_equipo SET revision=2,anulado_en=now() WHERE id='00000000-0000-0000-0000-000000000010'"))
            await conn.execute(text("INSERT INTO cambios_componentes(solicitud_id,componente_id,accion,revision_anterior,revision_nueva,antes,despues,solicitud,motivo,registrado_por_id) VALUES ('00000000-0000-0000-0000-000000000011','00000000-0000-0000-0000-000000000010','ANULAR_ALTA',1,2,'{}','{}','{}','Anulación de prueba',1)"))
            with pytest.raises(RuntimeError, match="auditorías, revisiones o estados"):
                await conn.run_sync(migrar, "20261022_supervision_rul", bajar=True)
            await conn.execute(text("DELETE FROM cambios_componentes WHERE solicitud_id='00000000-0000-0000-0000-000000000011'"))
            await conn.execute(text("UPDATE componentes_equipo SET revision=1,anulado_en=NULL WHERE id='00000000-0000-0000-0000-000000000010'"))
            with pytest.raises(RuntimeError, match="historial de componentes"):
                await conn.run_sync(migrar, "20261022_rul", bajar=True)
            assert (await conn.execute(text("SELECT count(*) FROM componentes_equipo"))).scalar() == 1
            await conn.execute(text("DELETE FROM componentes_equipo WHERE id='00000000-0000-0000-0000-000000000010'"))
            await conn.execute(text("UPDATE predicciones_rul SET dias_vida_util_remanente=NULL,nivel_alerta=NULL,version_calculo='CONDICIONAL_V1',motivo_no_estimable='MODELO_INESTABLE'"))
            with pytest.raises(RuntimeError, match="abstenciones"):
                await conn.run_sync(migrar, "20261021_historia", bajar=True)
            # La negativa no borra ni convierte en cero la abstención.
            assert (await conn.execute(text("SELECT motivo_no_estimable FROM predicciones_rul"))).scalar() == "MODELO_INESTABLE"
            await conn.execute(text("UPDATE predicciones_rul SET dias_vida_util_remanente=50,nivel_alerta='AMARILLO',version_calculo='LEGADO',motivo_no_estimable=NULL"))
            await conn.run_sync(migrar, "7fe488f9399d", bajar=True)
            await conn.run_sync(migrar, "head")
            assert (await conn.execute(text("SELECT payload_raw, hash_sha256 FROM actas_inmutables"))).one() == ('{"legacy":true}', "a" * 64)
            # Comprobar también el ciclo limpio que ejecuta CI, sólo en este esquema efímero.
            await conn.run_sync(migrar, "base", bajar=True)
            await conn.run_sync(migrar, "head")
            await conn.run_sync(columnas_coherentes)
    finally:
        try:
            if creado:
                async with aislado.begin() as conn:
                    await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            await aislado.dispose()
