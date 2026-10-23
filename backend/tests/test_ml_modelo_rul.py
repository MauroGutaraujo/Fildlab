from datetime import date, timedelta

import pandas as pd
import pytest

from app.ml import modelo_rul as rul
from app.ml.dataset_sintetico import SUPUESTOS_SIMULACION, generar_dataset
from ml_helpers import dataset_estable


@pytest.fixture(scope="module")
def modelo():
    # Igual distribución por tipo: sin separación ni efecto de tipo. Baseline
    # cruza .5 en 80; al sobrevivir 100 cruza S(100)/2 en 180: quedan 80 días.
    df = pd.DataFrame([
        {"tipo_sistema": tipo, "duracion_dias": t, "evento": 1}
        for tipo in ("ABLANDADOR", "FILTRO", "OSMOSIS_INVERSA")
        for t in (10, 20, 40, 80, 120, 180)
    ])
    return rul.ajustar_modelo(df)


@pytest.mark.parametrize("dias,nivel", [(0, "ROJO"), (29, "ROJO"), (30, "AMARILLO"),
                                       (89, "AMARILLO"), (90, "VERDE"), (200, "VERDE")])
def test_nivel_alerta_umbrales(dias, nivel):
    assert rul.nivel_alerta(dias) == nivel


@pytest.mark.parametrize("dias", [float("nan"), float("inf"), -1])
def test_alerta_rechaza_duracion_invalida(dias):
    with pytest.raises(ValueError):
        rul.nivel_alerta(dias)


def test_superar_mediana_total_no_implica_cero_dias_restantes(modelo):
    hoy = date(2026, 10, 22)
    r = rul.calificar_equipo(modelo, "FILTRO", hoy - timedelta(days=100), hoy)
    assert r == {"dias_vida_util_remanente": 80, "nivel_alerta": "AMARILLO"}


def test_calificar_equipo_fecha_futura(modelo):
    hoy = date(2026, 10, 22)
    with pytest.raises(rul.ParametrosImposibles):
        rul.calificar_equipo(modelo, "FILTRO", hoy + timedelta(days=1), hoy)


def test_tipo_desconocido_no_se_trata_como_referencia(modelo):
    hoy = date(2026, 10, 22)
    with pytest.raises(rul.ParametrosImposibles):
        rul.calificar_equipo(modelo, "DESCONOCIDO", hoy, hoy)


def test_edad_fuera_de_soporte_no_se_convierte_en_cero(modelo):
    hoy = date(2026, 10, 22)
    with pytest.raises(rul.ParametrosImposibles):
        rul.calificar_equipo(modelo, "FILTRO", hoy - timedelta(days=181), hoy)


def test_regresion_clip_antiguo_sigue_bloqueando_ajuste_inestable():
    df = generar_dataset()
    for tipo, p in SUPUESTOS_SIMULACION.items():
        filas = df.tipo_sistema == tipo
        df.loc[filas, "duracion_dias"] = df.loc[filas, "duracion_dias"].clip(lower=p["censura_desde_dias"])
    modelo = rul.ajustar_modelo(df)
    with pytest.raises(rul.ParametrosImposibles, match="MODELO_INESTABLE"):
        rul.calificar_equipo(modelo, "FILTRO", date(2026, 10, 22), date(2026, 10, 22))


@pytest.mark.parametrize("semilla", [20261009, 42, 7, 123, 99])
def test_generador_corregido_ajusta_sin_advertencias_en_todos_los_tipos(semilla):
    modelo = rul.ajustar_modelo(generar_dataset(semilla=semilla))
    assert modelo.advertencias == ()
    hoy = date(2026, 10, 22)
    for tipo, parametros in SUPUESTOS_SIMULACION.items():
        r = rul.calificar_equipo(modelo, tipo, hoy, hoy)
        assert parametros["mediana_dias"] * .8 <= r["dias_vida_util_remanente"] <= parametros["mediana_dias"] * 1.2


@pytest.mark.parametrize("duracion,dias,nivel", [
    (29.49, 29, "ROJO"), (29.5, 30, "AMARILLO"), (29.6, 30, "AMARILLO"),
    (89.49, 89, "AMARILLO"), (89.5, 90, "VERDE"), (89.6, 90, "VERDE"),
])
def test_calificacion_fraccional_usa_dias_redondeados(duracion, dias, nivel):
    df = dataset_estable()
    df["duracion_dias"] = df.duracion_dias.map({10: 3., 20: 7., 40: 12., 80: duracion, 120: duracion+20, 180: duracion+40})
    modelo = rul.ajustar_modelo(df)
    assert rul.calificar_equipo(modelo, "FILTRO", date(2026, 10, 22), date(2026, 10, 22)) == {
        "dias_vida_util_remanente": dias, "nivel_alerta": nivel}


@pytest.mark.parametrize("columna,valor", [
    ("duracion_dias", 0), ("duracion_dias", -1), ("duracion_dias", float("nan")),
    ("duracion_dias", float("inf")), ("duracion_dias", "abc"),
    ("evento", 2), ("evento", -1), ("evento", float("nan")),
    ("tipo_sistema", "DESCONOCIDO"), ("tipo_sistema", None),
])
def test_ajuste_rechaza_dataset_fuera_de_contrato(columna, valor):
    df = dataset_estable()
    if isinstance(valor, str):
        df[columna] = df[columna].astype(object)
    elif isinstance(valor, float):
        df[columna] = df[columna].astype(float)
    df.loc[0, columna] = valor
    with pytest.raises(ValueError, match="Dataset inválido"):
        rul.ajustar_modelo(df)


@pytest.mark.parametrize("df", [pd.DataFrame(), dataset_estable().iloc[:0], dataset_estable().assign(identificador=1)])
def test_ajuste_rechaza_dataset_vacio_o_columnas_no_previstas(df):
    with pytest.raises(ValueError, match="Dataset inválido"):
        rul.ajustar_modelo(df)


def test_convergence_error_no_publica_cifras():
    # Sin eventos, Cox no puede identificar coeficientes y lifelines falla el ajuste.
    modelo = rul.ajustar_modelo(dataset_estable().assign(evento=0))
    with pytest.raises(rul.ParametrosImposibles, match="MODELO_INESTABLE"):
        rul.calificar_equipo(modelo, "FILTRO", date(2026, 10, 22), date(2026, 10, 22))


def test_mediana_es_condicional_y_escalonada():
    curva = pd.Series([1., .8, .4, .2], index=[0., 10., 30., 60.])
    assert rul.mediana_condicional(curva, edad=35, limite=60) == 25
    assert rul.mediana_condicional(curva, edad=10, limite=60) == 20


def test_antes_de_la_primera_observacion_supervivencia_es_uno():
    curva = pd.Series([.6, .4, .2], index=[10., 30., 60.])
    assert rul.mediana_condicional(curva, edad=0, limite=60) == 30


@pytest.mark.parametrize("curva,edad,limite", [
    (pd.Series([1., .8, .6], index=[0., 10., 30.]), 10, 30),
    (pd.Series([1., .4, .1], index=[0., 20., 60.]), 25, 30),
    (pd.Series([1., 0.], index=[0., 10.]), 10, 20),
    (pd.Series([1., float("nan")], index=[0., 10.]), 0, 20),
    (pd.Series([1., float("inf")], index=[0., 10.]), 0, 20),
    (pd.Series([.4, .8], index=[0., 10.]), 0, 20),
])
def test_sin_mediana_valida_se_abstiene(curva, edad, limite):
    with pytest.raises(rul.ParametrosImposibles):
        rul.mediana_condicional(curva, edad=edad, limite=limite)
