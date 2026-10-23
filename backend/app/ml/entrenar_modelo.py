"""Entrenamiento explícito del prototipo sintético; nunca lo activa automáticamente."""
import argparse
from pathlib import Path

from app.ml.artefacto_rul import exportar_modelo
from app.ml.dataset_sintetico import generar_dataset


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida",required=True,type=Path)
    args=parser.parse_args()
    sha=exportar_modelo(generar_dataset(),args.salida)
    print(f"Artefacto experimental exportado. SHA256: {sha}. No activado automáticamente.")


if __name__=="__main__":
    main()
