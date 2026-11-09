"""Experimento sin tendencia (D20): ¿mejoran los modelos si no proyectan la subida media del train?

Por defecto, las redes y el lineal aprenden la subida media del periodo de entrenamiento y la
proyectan al futuro (a 1 año, entre un +3 % y un +12 % anual según el pliegue). Aquí se
entrenan sin ella: aprenden solo la variación respecto a esa media y suponen tendencia cero,
como el ingenuo.

- Redes: la combinación de datos elegida de cada horizonte (D19), con las semillas 42, 43 y 44.
- Lineal: todas las combinaciones y fuerzas de regularización de la fase A (unos minutos).

Lo mismo con tendencia ya está en resultados/fase_a.csv y resultados/fase_a_semillas.csv.
Guarda cada resultado en resultados/tendencia.csv en cuanto termina; si se interrumpe, al
volver a lanzarlo continúa donde se quedó. El progreso se guarda también en
resultados/tendencia.log.

Uso:
    python scripts/tendencia.py --solo-mostrar                 # qué se va a entrenar y cuánto tardará
    python scripts/tendencia.py                                # todo (6 hilos de CPU)
    python scripts/tendencia.py --horizontes medio largo       # solo esos horizontes
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.experimentos import ejecutar_tendencia


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None,
                        help="horizontes a entrenar (por defecto, los tres)")
    parser.add_argument("--semillas", type=int, nargs="+", default=None,
                        help=f"semillas (por defecto {[config.SEMILLA, *config.SEMILLAS_EXTRA]})")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS,
                        help="carpeta de resultados (debe contener fase_a.csv y fase_a_semillas.csv)")
    parser.add_argument("--solo-mostrar", action="store_true",
                        help="solo muestra qué se va a entrenar y el tiempo previsto, sin entrenar")
    args = parser.parse_args()

    opciones = dict(semillas=args.semillas, horizontes=args.horizontes, hilos=args.hilos)
    if args.solo_mostrar:
        ejecutar_tendencia(args.salida, solo_mostrar=True, **opciones)
        return
    with open(args.salida / "tendencia.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar_tendencia(args.salida, registrar=registrar, **opciones)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
