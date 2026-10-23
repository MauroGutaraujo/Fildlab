from datetime import date, datetime, timedelta, timezone

import pytest

from app.schemas.prediccion_rul import PrediccionRulOut


def datos(**extra):
    return {"equipo_serie":"EQ-1", "dias_vida_util_remanente":200, "nivel_alerta":"VERDE",
            "actualizado_en":datetime.now(timezone.utc) - timedelta(minutes=1),
            "vence_en":datetime.now(timezone.utc) + timedelta(hours=24),
            "ejecucion_id":"00000000-0000-0000-0000-000000000001", "tipo_referencia":"FILTRO",
            "fecha_referencia":date(2026, 1, 1), **extra}


@pytest.mark.parametrize("version", ["LEGADO", "CONDICIONAL_V1", "COX_CONDICIONAL_V2", "VERSION_DESCONOCIDA"])
def test_version_sin_calculo_corregido_no_muestra_numero_ni_color(version):
    out = PrediccionRulOut.model_validate(datos(version_calculo=version)).model_dump()
    assert out["dias_vida_util_remanente"] is None
    assert out["nivel_alerta"] is None
    assert out["estado_estimacion"] == "REQUIERE_RECALCULO"
    assert out["version_dataset"] is None


def test_resultado_experimental_publica_origen_fecha_y_politica():
    out = PrediccionRulOut.model_validate(datos(version_calculo="COX_INSTALACION_V3")).model_dump()
    assert out["estado_estimacion"] == "ESTIMADA"
    assert out["experimental"] is True
    assert out["origen_datos"] == "SINTETICOS"
    assert out["politica_alerta"] == "RUL_30_90_V1"
    assert out["version_dataset"] == "WEIBULL_CENSURA_V2"
    assert out["fecha_referencia"] == date(2026, 1, 1)
    assert out["alcance_estimacion"] == "SISTEMA_DESDE_INSTALACION"
    assert out["actualizado_en"].tzinfo is not None


def test_abstencion_oculta_un_resultado_previo():
    out = PrediccionRulOut.model_validate(datos(version_calculo="COX_INSTALACION_V3", motivo_no_estimable="MODELO_INESTABLE")).model_dump()
    assert out["estado_estimacion"] == "NO_ESTIMABLE"
    assert out["dias_vida_util_remanente"] is None and out["nivel_alerta"] is None


def test_api_clasifica_el_numero_mostrado_con_politica_unica():
    d = datos(version_calculo="COX_INSTALACION_V3")
    d.update(dias_vida_util_remanente=30, nivel_alerta="ROJO")
    assert PrediccionRulOut.model_validate(d).nivel_alerta == "AMARILLO"


def test_sin_fecha_referencia_no_presenta_antiguedad_inferida():
    out = PrediccionRulOut.model_validate(datos(version_calculo="COX_INSTALACION_V3", fecha_referencia=None))
    assert out.estado_estimacion == "REQUIERE_RECALCULO"
    assert out.dias_vida_util_remanente is None
