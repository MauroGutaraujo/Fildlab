import pandas as pd


def dataset_estable():
    """Muestra controlada para integración de Cox sin separación entre tipos."""
    return pd.DataFrame([
        {"tipo_sistema": tipo, "duracion_dias": t, "evento": 1}
        for tipo in ("ABLANDADOR", "FILTRO", "OSMOSIS_INVERSA")
        for t in (10, 20, 40, 80, 120, 180)
    ])
