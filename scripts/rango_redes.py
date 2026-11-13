"""Redes que dan el rango (D30, candidato B): percentiles 10, 50 y 90 en lugar de un número.

Las redes elegidas en la fase B, con la pérdida por cuantiles, en los años 2010-2021 (validación
hacia atrás y validación), a 3 meses y a 1 año, con las semillas 42-46. El test no se toca. El
análisis está en el notebook 03.

Guarda cada entrenamiento en resultados/rango_redes.csv, sus percentiles en
resultados/rango_redes_previsiones.csv y lo que pasó en cada ficha en resultados/rango_redes_fichas.csv,
en cuanto terminan. Si se interrumpe, al volver a lanzarlo continúa donde se quedó. El progreso se
guarda también en resultados/rango_redes.log.

Uso:
    python scripts/rango_redes.py --solo-mostrar      # plan y tiempo previsto
    python scripts/rango_redes.py                     # 3 meses y 1 año (unos 20-30 min)
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.rango_redes import HORIZONTES, ejecutar


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None,
                        help=f"horizontes (por defecto {' '.join(HORIZONTES)})")
    parser.add_argument("--modelos", nargs="+", choices=config.CELDAS, default=None,
                        help="solo estas redes (por defecto, las tres)")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS, help="carpeta de resultados")
    parser.add_argument("--solo-mostrar", action="store_true", help="solo muestra el plan y el tiempo previsto")
    args = parser.parse_args()

    opciones = dict(horizontes=args.horizontes, modelos=args.modelos, hilos=args.hilos)
    if args.solo_mostrar:
        ejecutar(args.salida, solo_mostrar=True, **opciones)
        return
    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / "rango_redes.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar(args.salida, registrar=registrar, **opciones)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
