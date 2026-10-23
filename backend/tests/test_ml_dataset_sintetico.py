import pandas as pd
import pytest
from lifelines import KaplanMeierFitter

from app.ml.dataset_sintetico import SUPUESTOS_SIMULACION, generar_dataset


def test_misma_semilla_mismo_dataset():
    a = generar_dataset(n_por_tipo=50, semilla=123)
    b = generar_dataset(n_por_tipo=50, semilla=123)
    pd.testing.assert_frame_equal(a, b)


def test_fallas_tempranas_se_conservan_sin_masa_en_inicio_de_censura():
    df = generar_dataset(n_por_tipo=200, semilla=7)
    for tipo, cal in SUPUESTOS_SIMULACION.items():
        sub = df[df["tipo_sistema"] == tipo]
        assert sub["duracion_dias"].min() > 0
        assert sub["duracion_dias"].max() <= cal["censura_hasta_dias"]
        assert ((sub["duracion_dias"] < cal["censura_desde_dias"]) & (sub["evento"] == 1)).any()
        assert (sub["duracion_dias"] == cal["censura_desde_dias"]).sum() == 0
        assert (sub.loc[sub["evento"] == 0, "duracion_dias"] >= cal["censura_desde_dias"]).all()


@pytest.mark.parametrize("n", [0, -1, True, 1.5, "3"])
def test_tamano_invalido_rechazado(n):
    with pytest.raises(ValueError):
        generar_dataset(n_por_tipo=n)


@pytest.mark.parametrize("semilla", [-1, True, 1.5, "3"])
def test_semilla_invalida_rechazada(semilla):
    with pytest.raises(ValueError):
        generar_dataset(semilla=semilla)


def test_proporcion_evento_censurado_aproximada():
    df = generar_dataset(n_por_tipo=2000, semilla=7)
    proporcion = df["evento"].mean()
    assert 0.60 <= proporcion <= 0.80


def test_mediana_kaplan_meier_recupera_supuestos_de_simulacion():
    """Comprueba la simulación y su censura; no valida equipos reales."""
    df = generar_dataset(n_por_tipo=3000, semilla=99)
    for tipo, cal in SUPUESTOS_SIMULACION.items():
        sub = df[df["tipo_sistema"] == tipo]
        kmf = KaplanMeierFitter()
        kmf.fit(sub["duracion_dias"], sub["evento"])
        mediana = kmf.median_survival_time_
        esperado = cal["mediana_dias"]
        assert esperado * 0.85 <= mediana <= esperado * 1.15, (tipo, mediana, esperado)


def test_censura_y_evento_conservan_menor_de_tiempos_independientes():
    # Seed 7, primeras tres unidades de ósmosis: falla [552.513,707.489,477.556]
    # y fin de seguimiento [455.796,517.637,990.682], calculados aparte.
    sub = generar_dataset(n_por_tipo=3, semilla=7).iloc[:3]
    assert sub["duracion_dias"].tolist() == pytest.approx([455.7959317422383, 517.637185051761, 477.5563458749139])
    assert sub["evento"].tolist() == [0, 0, 1]
