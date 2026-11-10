"""Fase B (D16, D22): busca la mejor configuración de cada red con Optuna.

Para cada horizonte y cada red, 40 intentos (a 1 semana, 20) con los datos elegidos en la fase A y
sin tendencia. A 1 año, cada intento se mide con 3 semillas; a 1 semana y a 3 meses, con una, y
después las finalistas de cada red (las 3 mejores y la estructura base) se repiten con las
semillas 43 y 44.

Guarda cada entrenamiento en resultados/fase_b.csv y cada intento en resultados/fase_b_intentos.csv
en cuanto terminan (la confirmación, en resultados/fase_b_semillas.csv). Si se interrumpe, al
volver a lanzarlo continúa donde se quedó. El progreso se guarda también en resultados/fase_b.log.

Uso:
    python scripts/fase_b.py --solo-mostrar                    # plan y tiempo previsto
    python scripts/fase_b.py --horizontes largo medio          # 1 año y 3 meses (unas 2,5 h)
    python scripts/fase_b.py --horizontes corto                # 1 semana (la más lenta: de noche)
    python scripts/fase_b.py --horizontes medio corto          # confirma la base a 3 meses (D23) y hace 1 semana
    python scripts/fase_b.py --horizontes corto --hilos 4      # más fresco, algo más lento
"""
import argparse
from pathlib import Path

from oil_price import config
from oil_price.busqueda import ejecutar_fase_b


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None,
                        help="horizontes, en el orden en que se hacen (por defecto, los tres)")
    parser.add_argument("--modelos", nargs="+", choices=config.CELDAS, default=None,
                        help="solo estas redes (por defecto, las tres)")
    parser.add_argument("--intentos", type=int, default=None,
                        help=f"intentos por red en cada horizonte (por defecto {config.INTENTOS_FASE_B})")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU, help="núcleos de CPU a usar")
    parser.add_argument("--salida", type=Path, default=config.DIR_RESULTADOS, help="carpeta de resultados")
    parser.add_argument("--solo-mostrar", action="store_true", help="solo muestra el plan y el tiempo previsto")
    args = parser.parse_args()

    opciones = dict(horizontes=args.horizontes, modelos=args.modelos, intentos=args.intentos, hilos=args.hilos)
    if args.solo_mostrar:
        ejecutar_fase_b(args.salida, solo_mostrar=True, **opciones)
        return
    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / "fase_b.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        try:
            ejecutar_fase_b(args.salida, registrar=registrar, **opciones)
        except KeyboardInterrupt:
            registrar("Interrumpido. Lo ya terminado está guardado; al relanzar continúa donde se quedó.")


if __name__ == "__main__":
    main()
