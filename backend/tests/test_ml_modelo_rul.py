from datetime import date, timedelta

import pytest

from app.ml.dataset_sintetico import generar_dataset
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, calificar_equipo, nivel_alerta


@pytest.fixture(scope="module")
def modelo():
    return ajustar_modelo(generar_dataset(n_por_tipo=500, semilla=42))


def test_nivel_alerta_umbrales():
    assert nivel_alerta(29) == "ROJO"
    assert nivel_alerta(30) == "AMARILLO"
    assert nivel_alerta(89) == "AMARILLO"
    assert nivel_alerta(90) == "VERDE"
    assert nivel_alerta(200) == "VERDE"


def test_calificar_equipo_fecha_futura_lanza_parametros_imposibles(modelo):
    hoy = date(2026, 1, 1)
    futura = hoy + timedelta(days=5)
    with pytest.raises(ParametrosImposibles):
        calificar_equipo(modelo, "FILTRO", futura, hoy)


def test_calificar_equipo_recien_instalado_cerca_de_la_vida_util_mediana(modelo):
    hoy = date(2026, 1, 1)
    r = calificar_equipo(modelo, "OSMOSIS_INVERSA", hoy, hoy)  # instalado hoy mismo
    assert 300 <= r["dias_vida_util_remanente"] <= 800
    assert r["nivel_alerta"] in ("VERDE", "AMARILLO", "ROJO")


def test_calificar_equipo_antiguo_tiene_menos_dias_restantes_que_uno_nuevo(modelo):
    hoy = date(2026, 1, 1)
    nuevo = calificar_equipo(modelo, "FILTRO", hoy, hoy)
    antiguo = calificar_equipo(modelo, "FILTRO", hoy - timedelta(days=100), hoy)
    assert antiguo["dias_vida_util_remanente"] < nuevo["dias_vida_util_remanente"]
