from datetime import date

import pandas as pd
from lifelines import CoxPHFitter

UMBRAL_ROJO_DIAS = 30
UMBRAL_AMARILLO_DIAS = 90


class ParametrosImposibles(Exception):
    pass


def ajustar_modelo(dataset: pd.DataFrame) -> CoxPHFitter:
    df = pd.get_dummies(dataset, columns=["tipo_sistema"], drop_first=True)
    cph = CoxPHFitter()
    cph.fit(df, duration_col="duracion_dias", event_col="evento")
    return cph


def nivel_alerta(dias_restantes: float) -> str:
    if dias_restantes < UMBRAL_ROJO_DIAS:
        return "ROJO"
    if dias_restantes < UMBRAL_AMARILLO_DIAS:
        return "AMARILLO"
    return "VERDE"


def calificar_equipo(cph: CoxPHFitter, tipo_sistema: str, fecha_instalacion: date, hoy: date) -> dict:
    """Devuelve {dias_vida_util_remanente, nivel_alerta} para un equipo real.
    Lanza ParametrosImposibles si fecha_instalacion es invalida (REQ-19)."""
    dias_en_servicio = (hoy - fecha_instalacion).days
    if dias_en_servicio < 0:
        raise ParametrosImposibles(f"fecha_instalacion futura: {fecha_instalacion}")

    # No se puede usar pd.get_dummies sobre esta fila suelta: con una sola categoria
    # presente, no genera las mismas columnas dummy que durante el entrenamiento, y un
    # reindex posterior rellena todo con 0 (tratando en silencio cualquier tipo como si
    # fuera la categoria de referencia). Se arma la fila directamente contra las columnas
    # que el modelo realmente aprendio.
    fila = pd.DataFrame(0, index=[0], columns=cph.params_.index, dtype=float)
    columna = f"tipo_sistema_{tipo_sistema}"
    if columna in fila.columns:
        fila[columna] = 1.0

    resultado = cph.predict_median(fila)
    vida_util_total = float(resultado.iloc[0]) if hasattr(resultado, "iloc") else float(resultado)
    dias_restantes = max(0.0, vida_util_total - dias_en_servicio)
    return {"dias_vida_util_remanente": round(dias_restantes), "nivel_alerta": nivel_alerta(dias_restantes)}
