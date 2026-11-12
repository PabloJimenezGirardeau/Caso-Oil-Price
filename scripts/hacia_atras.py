"""Validación hacia atrás (D29): las configuraciones elegidas, evaluadas en 2010-2017.

Cada año de 2010 a 2017 se prevé entrenando solo con lo anterior, con las redes elegidas en la
fase B (semillas 42-46, sin volver a elegir nada), a 3 meses y a 1 año. No se usa nada posterior
al 31/12/2017, así que el test no se toca. El análisis está en el notebook 03.

Guarda cada entrenamiento en resultados/hacia_atras.csv, sus previsiones en
resultados/hacia_atras_previsiones.csv y lo que pasó en cada ficha en resultados/hacia_atras_fichas.csv,
en cuanto terminan. Si se interrumpe, al volver a lanzarlo continúa donde se quedó. El progreso
se guarda también en resultados/hacia_atras.log.

Uso:
    python scripts/hacia_atras.py --solo-mostrar      # plan y tiempo previsto
    python scripts/hacia_atras.py                     # 3 meses y 1 año (unos 20-30 min)
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.hacia_atras import HORIZONTES, ejecutar


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
    with open(args.salida / "hacia_atras.log", "a", encoding="utf-8") as log:
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
