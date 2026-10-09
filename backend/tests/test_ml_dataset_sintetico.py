import pandas as pd
from lifelines import KaplanMeierFitter

from app.ml.dataset_sintetico import CALIBRACION, generar_dataset


def test_misma_semilla_mismo_dataset():
    a = generar_dataset(n_por_tipo=50, semilla=123)
    b = generar_dataset(n_por_tipo=50, semilla=123)
    pd.testing.assert_frame_equal(a, b)


def test_duraciones_dentro_del_rango_por_tipo():
    df = generar_dataset(n_por_tipo=200, semilla=7)
    for tipo, cal in CALIBRACION.items():
        sub = df[df["tipo_sistema"] == tipo]
        assert sub["duracion_dias"].min() >= cal["min_dias"]
        assert sub["duracion_dias"].max() <= cal["max_dias"]


def test_proporcion_evento_censurado_aproximada():
    df = generar_dataset(n_por_tipo=2000, semilla=7)
    proporcion = df["evento"].mean()
    assert 0.60 <= proporcion <= 0.80


def test_mediana_kaplan_meier_coincide_con_la_calibracion():
    """Hallazgo Important #1 de la revision final: si una fila censurada se corta
    justo en su tiempo de falla real (en vez de antes), Kaplan-Meier/Cox leen eso
    como "sobrevivio mas alla de ese punto sin saberse que paso despues", inflando
    la mediana estimada muy por encima de CALIBRACION. Esta prueba ajusta un
    Kaplan-Meier real sobre el dataset generado y confirma que su mediana cae
    cerca (±15%) de la mediana documentada, no ~30% por encima."""
    df = generar_dataset(n_por_tipo=3000, semilla=99)
    for tipo, cal in CALIBRACION.items():
        sub = df[df["tipo_sistema"] == tipo]
        kmf = KaplanMeierFitter()
        kmf.fit(sub["duracion_dias"], sub["evento"])
        mediana = kmf.median_survival_time_
        esperado = cal["mediana_dias"]
        assert esperado * 0.85 <= mediana <= esperado * 1.15, (tipo, mediana, esperado)
