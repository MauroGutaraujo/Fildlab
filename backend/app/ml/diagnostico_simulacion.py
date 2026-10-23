"""Comparación reproducible de simulación; no usa ni escribe una base de datos.

python -m app.ml.diagnostico_simulacion --salida comparacion.json
Los errores comparan con la distribución generadora conocida. No son métricas
de fallas reales ni autorizan usar las alertas para decisiones autónomas.
"""
import argparse
import json
import platform
import warnings
from pathlib import Path

import lifelines
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter, WeibullFitter
from lifelines.exceptions import ConvergenceError
from lifelines.statistics import proportional_hazard_test

from app.core.politica_rul import VERSION_CALCULO, VERSION_DATASET
from app.ml.dataset_sintetico import SEMILLA, SUPUESTOS_SIMULACION, generar_dataset
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, mediana_condicional


def _finito(valor):
    return float(valor) if np.isfinite(valor) else None


def _escalon(curva, puntos):
    posiciones = np.searchsorted(curva.index.to_numpy(dtype=float), puntos, side="right") - 1
    return np.array([float(curva.iloc[i]) if i >= 0 else 1. for i in posiciones])


def _resultado(puntos, predicciones, verdad, mediana, limite, advertencias):
    valido = not advertencias and np.isfinite(predicciones).all()
    return {
        "advertencias": list(advertencias),
        "mediana_dias": _finito(mediana) if valido and mediana <= limite else None,
        "horizontes_evaluados": len(puntos),
        "error_curva_simulada": float(np.abs(predicciones - verdad).mean()) if valido and len(puntos) else None,
    }


def _baseline(clase, sub, puntos, verdad, limite):
    try:
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            modelo = clase().fit(sub.duracion_dias, sub.evento)
        advertencias = [str(a.message) for a in avisos]
        predicciones = (modelo.survival_function_at_times(puntos).to_numpy()
                        if clase is WeibullFitter else _escalon(modelo.survival_function_.iloc[:, 0], puntos))
        return _resultado(puntos, predicciones, verdad, modelo.median_survival_time_, limite, advertencias)
    except (ConvergenceError, ValueError, np.linalg.LinAlgError) as exc:
        return _resultado(puntos, np.array([]), np.array([]), np.inf, limite, [str(exc)])


def diagnosticar_simulacion(n_por_tipo=500, semillas=(SEMILLA, 42, 7, 123, 99)):
    if not semillas or len(set(semillas)) != len(semillas):
        raise ValueError("Usa semillas diferentes y al menos una")
    ensayos = []
    for semilla in semillas:
        df = generar_dataset(n_por_tipo=n_por_tipo, semilla=semilla)
        modelo = ajustar_modelo(df)
        cph = modelo.ajuste
        estable = cph is not None and not modelo.advertencias
        diagnostico_ph = None
        if estable:
            dummies = pd.get_dummies(df, columns=["tipo_sistema"], drop_first=True)
            diagnostico_ph = {k: _finito(v) for k, v in proportional_hazard_test(
                cph, dummies, time_transform="rank").summary.p.items()}
        tipos = {}
        for tipo, parametros in SUPUESTOS_SIMULACION.items():
            sub = df[df.tipo_sistema == tipo]
            limite = float(sub.duracion_dias.max())
            puntos = np.array([.5, 1., 1.5]) * parametros["mediana_dias"]
            puntos = puntos[puntos <= limite]
            verdad = np.exp(-np.log(2) * (puntos / parametros["mediana_dias"]) ** parametros["forma_weibull"])
            mediana_cox = np.inf
            pred_cox = np.zeros(len(puntos))
            if estable:
                fila = pd.DataFrame(0., index=[0], columns=cph.params_.index)
                columna = f"tipo_sistema_{tipo}"
                if columna in fila:
                    fila[columna] = 1.
                curva = cph.predict_survival_function(fila).iloc[:, 0]
                pred_cox = _escalon(curva, puntos)
                try:
                    mediana_cox = mediana_condicional(curva, edad=0, limite=limite)
                except ParametrosImposibles:
                    pass
            tipos[tipo] = {
                "observaciones": len(sub), "soporte_hasta_dias": limite,
                "proporcion_eventos": float(sub.evento.mean()),
                "masa_inicio_censura": int((sub.duracion_dias == parametros["censura_desde_dias"]).sum()),
                "fallas_tempranas": int(((sub.duracion_dias < parametros["censura_desde_dias"]) & (sub.evento == 1)).sum()),
                "horizontes_dias": puntos.tolist(),
                "candidatos": {
                    "COX": _resultado(puntos, pred_cox, verdad, mediana_cox, limite,
                                      modelo.advertencias or (() if estable else ("AJUSTE_INVALIDO",))),
                    "KAPLAN_MEIER": _baseline(KaplanMeierFitter, sub, puntos, verdad, limite),
                    "WEIBULL": _baseline(WeibullFitter, sub, puntos, verdad, limite),
                },
            }
        ensayos.append({"semilla": int(semilla), "filas": len(df), "advertencias_cox": list(modelo.advertencias),
                        "ph_pvalues_rank": diagnostico_ph, "tipos": tipos})
    return {
        "validacion_real": False,
        "alcance": "Recuperación de la distribución simulada; no evalúa fallas reales",
        "version_dataset": VERSION_DATASET, "version_calculo": VERSION_CALCULO,
        "entorno": {"python": platform.python_version(), "numpy": np.__version__,
                    "pandas": pd.__version__, "lifelines": lifelines.__version__},
        "supuestos_simulacion": {tipo: dict(p) for tipo, p in SUPUESTOS_SIMULACION.items()},
        "ensayos": ensayos,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-por-tipo", type=int, default=500)
    parser.add_argument("--semillas", type=int, nargs="+", default=[SEMILLA, 42, 7, 123, 99])
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    contenido = json.dumps(diagnosticar_simulacion(args.n_por_tipo, args.semillas),
                           ensure_ascii=False, indent=2, allow_nan=False)
    if args.salida:
        args.salida.write_text(contenido + "\n", encoding="utf-8")
        print(args.salida)
    else:
        print(contenido)


if __name__ == "__main__":
    main()
