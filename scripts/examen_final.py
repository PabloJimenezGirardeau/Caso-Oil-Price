"""Examen final en test (D33): se ejecuta una sola vez, con el protocolo fijado antes de tocarlo.

Cada red se entrena una vez con todo lo anterior al 1/1/2022 (semillas 42-46) y prevé 2022 hasta el
3/11/2026; también el lineal de referencia. Guarda cada entrenamiento en resultados/examen.csv,
sus previsiones en resultados/examen_previsiones.csv y lo que pasó en cada ficha en
resultados/examen_fichas.csv, en cuanto terminan. Si se interrumpe, al relanzarlo continúa donde se
quedó, sin repetir nada. El progreso se guarda también en resultados/examen.log. El análisis está
en el notebook 03.

Sin --ejecutar, solo muestra el plan (fichas de cada horizonte, entrenamientos pendientes y tiempo
previsto): no entrena ni evalúa nada.

Uso:
    python scripts/examen_final.py              # solo el plan
    python scripts/examen_final.py --ejecutar   # el examen (una sola vez)
"""
import argparse

from oil_price import config
from oil_price.examen_final import ejecutar


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ejecutar", action="store_true", help="hace el examen (sin esto, solo el plan)")
    parser.add_argument("--hilos", type=int, default=config.HILOS_CPU)
    args = parser.parse_args()

    if not args.ejecutar:
        ejecutar(hilos=args.hilos, solo_mostrar=True)
        print("\nSolo el plan. Para hacer el examen: python scripts/examen_final.py --ejecutar")
        return
    config.DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    with open(config.DIR_RESULTADOS / "examen.log", "a", encoding="utf-8") as log:
        def registrar(mensaje):
            print(mensaje, flush=True)
            log.write(mensaje + "\n")
            log.flush()
        ejecutar(hilos=args.hilos, registrar=registrar)


if __name__ == "__main__":
    main()
