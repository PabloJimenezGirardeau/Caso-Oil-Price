"""Experimento de control con precios (D15, H4): la RNN elegida, entrenada para prever el precio.

A 1 semana y a 3 meses, en la validación 2018-2021, con las semillas 42-46. El test no se toca.
Guarda la previsión de cada ficha en resultados/control_precios.csv en cuanto termina cada
entrenamiento; si se interrumpe, al volver a lanzarlo continúa donde se quedó. El análisis está en
el notebook 03.

Uso:
    python scripts/control_precios.py
    python scripts/control_precios.py --horizontes medio
"""
import argparse
import time

from oil_price import config
from oil_price.control_precios import HORIZONTES, ejecutar


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=HORIZONTES, default=None)
    args = parser.parse_args()
    inicio = time.time()
    with open(config.DIR_RESULTADOS / "control_precios.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            mensaje = f"[{(time.time() - inicio) / 60:5.1f} min] {mensaje}"
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        ejecutar(horizontes=args.horizontes, registrar=registrar)
        registrar("Terminado.")


if __name__ == "__main__":
    main()
