"""Controles del procedimiento con el lineal: negativo (sin señal) y positivo (señal plantada).

En 2010-2021 (validación hacia atrás y validación), en los tres horizontes. El test no se toca.
Guarda una fila por horizonte, control, mejora plantada y repetición en resultados/controles.csv.
El análisis está en el notebook 03.

Uso:
    python scripts/controles.py
    python scripts/controles.py --horizontes medio --rep-negativo 2 --rep-positivo 1   # prueba rápida
"""
import argparse
import time
from pathlib import Path

from oil_price import config
from oil_price.controles import REPETICIONES_NEGATIVO, REPETICIONES_POSITIVO, ejecutar


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None)
    parser.add_argument("--rep-negativo", type=int, default=REPETICIONES_NEGATIVO)
    parser.add_argument("--rep-positivo", type=int, default=REPETICIONES_POSITIVO)
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS / "controles.csv")
    args = parser.parse_args()

    inicio = time.time()
    filas = ejecutar(args.horizontes, rep_negativo=args.rep_negativo, rep_positivo=args.rep_positivo,
                     registrar=lambda m: print(f"[{(time.time() - inicio) / 60:5.1f} min] {m}", flush=True))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    filas.to_csv(args.salida, index=False)
    print(f"Guardado en {args.salida} ({len(filas)} filas) en {(time.time() - inicio) / 60:.1f} min.")


if __name__ == "__main__":
    main()
