"""Repite las finalistas de la fase A con otras semillas para medir el ruido (D16, D19).

Toma las 3 mejores combinaciones de datos de cada horizonte en resultados/fase_a.csv (media de
las tres redes) y las vuelve a entrenar con las semillas 43 y 44; la 42 ya está en la fase A.
Guarda cada resultado en resultados/fase_a_semillas.csv en cuanto termina; si se interrumpe,
al volver a lanzarlo continúa donde se quedó. El progreso se guarda también en
resultados/fase_a_semillas.log.

Uso:
    python scripts/fase_a_semillas.py --solo-mostrar   # lista las finalistas y el tiempo previsto
    python scripts/fase_a_semillas.py                  # lanza la repetición (6 hilos de CPU)
    python scripts/fase_a_semillas.py --semillas 43 44 45
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.experimentos import ejecutar_confirmacion


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--semillas", type=int, nargs="+", default=config.SEMILLAS_EXTRA,
                        help=f"semillas nuevas (por defecto {config.SEMILLAS_EXTRA})")
    parser.add_argument("--finalistas", type=int, default=config.N_FINALISTAS,
                        help=f"finalistas por horizonte (por defecto {config.N_FINALISTAS})")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS,
                        help="carpeta de resultados (debe contener fase_a.csv)")
    parser.add_argument("--solo-mostrar", action="store_true",
                        help="solo lista las finalistas y el tiempo previsto, sin entrenar")
    args = parser.parse_args()

    if args.solo_mostrar:
        ejecutar_confirmacion(args.salida, args.semillas, args.finalistas, args.hilos, solo_mostrar=True)
        return
    with open(args.salida / "fase_a_semillas.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar_confirmacion(args.salida, args.semillas, args.finalistas, args.hilos, registrar)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
