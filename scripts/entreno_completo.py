"""Las redes, reentrenadas con todo el entrenamiento (D31): sin trozo de parada y con épocas fijas.

En 2010-2021 (validación hacia atrás y validación), a 3 meses y a 1 año, con las semillas 42-46;
la RNN, también con 3 y con 10 épocas, como información. El test no se toca. El análisis está en
el notebook 03.

Guarda cada entrenamiento en resultados/completo.csv, sus previsiones en
resultados/completo_previsiones.csv y lo que pasó en cada ficha en resultados/completo_fichas.csv,
en cuanto terminan. Si se interrumpe, al volver a lanzarlo continúa donde se quedó. El progreso se
guarda también en resultados/completo.log.

Uso:
    python scripts/entreno_completo.py --solo-mostrar
    python scripts/entreno_completo.py
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.entreno_completo import HORIZONTES, ejecutar


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None,
                        help=f"horizontes (por defecto {' '.join(HORIZONTES)})")
    parser.add_argument("--modelos", nargs="+", choices=config.CELDAS, default=None)
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU)
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS)
    parser.add_argument("--solo-mostrar", action="store_true")
    args = parser.parse_args()

    opciones = dict(horizontes=args.horizontes, modelos=args.modelos, hilos=args.hilos)
    if args.solo_mostrar:
        ejecutar(args.salida, solo_mostrar=True, **opciones)
        return
    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / "completo.log", "a", encoding="utf-8") as log:
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
