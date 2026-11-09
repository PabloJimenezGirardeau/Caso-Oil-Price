"""Lanza (o continúa) la fase A: estudio de ventana × recorte × indicador de nivel (D6, D16).

Guarda cada resultado en resultados/fase_a.csv en cuanto termina; si se interrumpe, al
volver a lanzarlo continúa donde se quedó. El progreso se muestra en pantalla y se guarda
en resultados/fase_a.log.

Uso:
    python scripts/fase_a.py                    # fase completa (6 hilos de CPU)
    python scripts/fase_a.py --hilos 8          # usar más núcleos
    python scripts/fase_a.py --ventanas 10 20 40 60   # solo esas ventanas
    python scripts/fase_a.py --limite 2 --salida resultados/prueba   # prueba corta
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.experimentos import ejecutar_fase_a


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--limite", type=int, default=None, help="máximo de combinaciones (pruebas)")
    parser.add_argument("--ventanas", type=int, nargs="+", default=None,
                        help=f"solo estas ventanas (por defecto, todas: {config.VENTANAS})")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS, help="carpeta de resultados")
    args = parser.parse_args()

    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / "fase_a.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar_fase_a(args.salida, args.hilos, args.limite, registrar, args.ventanas)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
