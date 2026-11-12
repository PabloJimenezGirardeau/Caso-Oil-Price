"""Estabilidad (D27): entrena la configuración elegida de cada red con 10 semillas y guarda sus previsiones.

Con ellas se mide cuánto estabiliza promediar las previsiones de varias semillas (el análisis
está en el notebook 03). No se vuelve a elegir ninguna configuración: son las de la fase B.

Guarda cada entrenamiento en resultados/estabilidad.csv, sus previsiones en
resultados/estabilidad_previsiones.csv y lo que pasó en cada ficha en resultados/estabilidad_fichas.csv,
en cuanto terminan. Si se interrumpe, al volver a lanzarlo continúa donde se quedó. El progreso se
guarda también en resultados/estabilidad.log. Las semillas 42, 43 y 44 deben reproducir exactamente
la fase B: el registro lo comprueba al terminar cada red.

Uso:
    python scripts/estabilidad.py --solo-mostrar                 # plan y tiempo previsto
    python scripts/estabilidad.py                                # todo: 1 año, 3 meses y 1 semana (unas 5 h)
    python scripts/estabilidad.py --horizontes largo medio       # solo los rápidos (unos 20 min)
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.estabilidad import ORDEN, ejecutar_estabilidad


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None,
                        help=f"horizontes, en el orden en que se hacen (por defecto {' '.join(ORDEN)})")
    parser.add_argument("--modelos", nargs="+", choices=config.CELDAS, default=None,
                        help="solo estas redes (por defecto, las tres)")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS, help="carpeta de resultados")
    parser.add_argument("--solo-mostrar", action="store_true", help="solo muestra el plan y el tiempo previsto")
    args = parser.parse_args()

    opciones = dict(horizontes=args.horizontes, modelos=args.modelos, hilos=args.hilos)
    if args.solo_mostrar:
        ejecutar_estabilidad(args.salida, solo_mostrar=True, **opciones)
        return
    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / "estabilidad.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar_estabilidad(args.salida, registrar=registrar, **opciones)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
