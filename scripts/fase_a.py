"""Lanza (o continúa) la fase A: estudio de ventana × recorte × indicador de nivel (D6, D16).

Guarda cada resultado en resultados/fase_a.csv en cuanto termina; si se interrumpe, al
volver a lanzarlo continúa donde se quedó. El progreso se muestra en pantalla y se guarda
en resultados/fase_a.log.

Con --sin-tendencia (D21), las redes se entrenan sin la subida media del train y todo se
guarda en resultados/fase_a_sin_tendencia.csv (y .log); el lineal no se repite, porque sin
tendencia ya está en resultados/tendencia.csv.

Uso:
    python scripts/fase_a.py                    # fase completa (6 hilos de CPU)
    python scripts/fase_a.py --hilos 8          # usar más núcleos
    python scripts/fase_a.py --ventanas 10 20 40 60   # solo esas ventanas
    python scripts/fase_a.py --horizontes largo --sin-tendencia   # 1 año sin tendencia (D21)
    python scripts/fase_a.py --limite 2 --salida resultados/prueba   # prueba corta
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.experimentos import ejecutar_fase_a, nombre_fase_a


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--limite", type=int, default=None, help="máximo de combinaciones (pruebas)")
    parser.add_argument("--ventanas", type=int, nargs="+", default=None,
                        help=f"solo estas ventanas (por defecto, todas: {config.VENTANAS})")
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None,
                        help="solo estos horizontes (por defecto, los tres)")
    parser.add_argument("--sin-tendencia", action="store_true",
                        help="redes sin la subida media del train (D20, D21)")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS, help="carpeta de resultados")
    args = parser.parse_args()

    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / f"{nombre_fase_a(args.sin_tendencia)}.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar_fase_a(args.salida, args.hilos, args.limite, registrar, args.ventanas,
                            horizontes=args.horizontes, sin_tendencia=args.sin_tendencia)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
