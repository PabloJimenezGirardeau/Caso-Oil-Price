"""Qué ven las redes: reentrena las elegidas con 5 semillas y mide qué variables usan.

Para el promedio de 5 semillas de cada red (D27) y para el lineal, a 3 meses y a 1 año:
- cuánto empeora la nota al desordenar cada variable entre fichas (si no la usa, nada);
- cuánto cambia de media la previsión si la volatilidad fuese el doble o la mitad, o si el Brent y
  el WTI estuvieran un 10 % más abajo que hace un mes.
Solo validación; no elige nada. Guarda resultados/importancia.csv y resultados/efectos.csv
(el análisis está en el notebook 03). Tarda unos 10 minutos con 6 hilos.

Uso:
    python scripts/importancia.py
    python scripts/importancia.py --horizontes medio --hilos 4
"""
import argparse
from pathlib import Path

from oil_price import config, estabilidad as es, explicacion as xp


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=["medio", "largo"])
    parser.add_argument("--repeticiones", type=int, default=5, help="desórdenes por variable")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS, help="carpeta de resultados")
    args = parser.parse_args()

    importancia, efectos = xp.importancia_y_efectos(args.horizontes, repeticiones=args.repeticiones,
                                                    hilos=args.hilos)
    importancia.to_csv(args.salida / xp.ARCHIVOS["importancia"], index=False, float_format="%.6g")
    efectos.to_csv(args.salida / xp.ARCHIVOS["efectos"], index=False, float_format="%.6g")

    # Comprobación: la nota de cada red sin desordenar debe ser la de su promedio de las semillas
    # 42-46 en la estabilidad (mismos entrenamientos)
    guardadas = es.nota(es.promedio(es.leer_previsiones(args.salida), config.SEMILLAS_ESTABILIDAD[:5]))
    for (h, m), nota in importancia.groupby(["horizonte", "modelo"])["nota"].first().items():
        if m in config.CELDAS:
            print(f"Comprobación {h} {m}: {nota:.4f} aquí · {guardadas.loc[(h, m)]:.4f} en la estabilidad")
    print(f"Guardado en {args.salida / xp.ARCHIVOS['importancia']} y {args.salida / xp.ARCHIVOS['efectos']}")


if __name__ == "__main__":
    main()
