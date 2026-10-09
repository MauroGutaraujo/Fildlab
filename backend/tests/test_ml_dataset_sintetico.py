import pandas as pd

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
