"""Política RUL compartida por batch y API, sin dependencias de ML."""
from math import isfinite

VERSION_CALCULO = "COX_INSTALACION_V3"
VERSION_DATASET = "WEIBULL_CENSURA_V2"
POLITICA_ALERTA = "RUL_30_90_V1"
UMBRAL_ROJO_DIAS = 30
UMBRAL_AMARILLO_DIAS = 90


def nivel_alerta(dias_restantes: float) -> str:
    if not isfinite(dias_restantes) or dias_restantes < 0:
        raise ValueError("La duración debe ser finita y no negativa")
    if dias_restantes < UMBRAL_ROJO_DIAS:
        return "ROJO"
    if dias_restantes < UMBRAL_AMARILLO_DIAS:
        return "AMARILLO"
    return "VERDE"
