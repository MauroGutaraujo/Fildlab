from numbers import Integral

import numpy as np
import pandas as pd

# Supuestos del prototipo, sin fuente de campo o fabricante verificada.
# No representan calibración para Trujillo/SEDALIB ni límites físicos de falla.
# Los intervalos describen fin de seguimiento (censura), no vida mínima/máxima.
SUPUESTOS_SIMULACION = {
    "OSMOSIS_INVERSA": {"mediana_dias": 545, "forma_weibull": 1.5, "censura_desde_dias": 270, "censura_hasta_dias": 1095},
    "ABLANDADOR": {"mediana_dias": 1460, "forma_weibull": 1.5, "censura_desde_dias": 730, "censura_hasta_dias": 2920},
    "FILTRO": {"mediana_dias": 120, "forma_weibull": 1.5, "censura_desde_dias": 60, "censura_hasta_dias": 270},
}
SEMILLA = 20261009


def generar_dataset(n_por_tipo: int = 500, semilla: int = SEMILLA) -> pd.DataFrame:
    """Genera un dataset sintetico de supervivencia: una fila por unidad simulada,
    con columnas duracion_dias, evento (1=fallo, 0=censurado), tipo_sistema.
    El seguimiento termina independientemente del tiempo de falla. Los eventos
    tempranos se conservan; no se desplazan al comienzo del intervalo de censura.
    Determinista en el mismo entorno y versión de generador."""
    if isinstance(n_por_tipo, bool) or not isinstance(n_por_tipo, Integral) or n_por_tipo <= 0:
        raise ValueError("n_por_tipo debe ser un entero positivo")
    if isinstance(semilla, bool) or not isinstance(semilla, Integral) or semilla < 0:
        raise ValueError("semilla debe ser un entero no negativo")
    rng = np.random.default_rng(semilla)
    filas = []
    for tipo, cal in SUPUESTOS_SIMULACION.items():
        forma = cal["forma_weibull"]
        escala = cal["mediana_dias"] / (np.log(2) ** (1 / forma))
        fallas = rng.weibull(forma, n_por_tipo) * escala
        # El tiempo de censura es independiente del tiempo de falla real — practica estandar
        # en analisis de supervivencia. Si se censura justo en el mismo instante de la falla
        # (lo que hacia la version anterior), Kaplan-Meier/Cox leen eso como "sobrevivio mas
        # alla de ese punto sin saberse que paso despues", inflando la mediana estimada muy
        # por encima de la mediana supuesta.
        censura = rng.uniform(cal["censura_desde_dias"], cal["censura_hasta_dias"], n_por_tipo)
        duraciones = np.minimum(fallas, censura)
        eventos = fallas <= censura
        for d, e in zip(duraciones, eventos):
            filas.append({"duracion_dias": float(d), "evento": int(e), "tipo_sistema": tipo})
    return pd.DataFrame(filas)
