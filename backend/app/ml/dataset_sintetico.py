import numpy as np
import pandas as pd

# Vida util mediana y rango por tipo_sistema, calibrados con literatura de tratamiento
# de agua y ajustados a las condiciones de Trujillo (SEDALIB: agua mas dura y con mas
# turbidez estacional que el promedio generico internacional). Ajustable si hay cifras
# mas precisas de campo — documentado aqui, no enterrado en numeros magicos.
CALIBRACION = {
    "OSMOSIS_INVERSA": {"mediana_dias": 545, "min_dias": 270, "max_dias": 1095},
    "ABLANDADOR": {"mediana_dias": 1460, "min_dias": 730, "max_dias": 2920},
    "FILTRO": {"mediana_dias": 120, "min_dias": 60, "max_dias": 270},
}
PROPORCION_EVENTO = 0.70  # 70% falla (evento observado), 30% censurado
SEMILLA = 20261009


def generar_dataset(n_por_tipo: int = 500, semilla: int = SEMILLA) -> pd.DataFrame:
    """Genera un dataset sintetico de supervivencia: una fila por unidad simulada,
    con columnas duracion_dias, evento (1=fallo, 0=censurado), tipo_sistema.
    Deterministico: misma semilla -> mismo dataset, siempre."""
    rng = np.random.default_rng(semilla)
    filas = []
    for tipo, cal in CALIBRACION.items():
        forma = 1.5  # forma de Weibull calibrada para que la mediana caiga en mediana_dias
        escala = cal["mediana_dias"] / (np.log(2) ** (1 / forma))
        duraciones = rng.weibull(forma, n_por_tipo) * escala
        duraciones = np.clip(duraciones, cal["min_dias"], cal["max_dias"])
        eventos = rng.random(n_por_tipo) < PROPORCION_EVENTO
        for d, e in zip(duraciones, eventos):
            filas.append({"duracion_dias": float(d), "evento": int(e), "tipo_sistema": tipo})
    return pd.DataFrame(filas)
