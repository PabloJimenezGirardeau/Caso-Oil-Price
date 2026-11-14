"""Previsión con los modelos guardados y los datos descargados (previsión en vivo; base de la aplicación).

Carga los modelos de modelos/<carpeta>/ (sin reentrenar) y los datos de data/actual/ (descargados
con `descarga.actualizar`), y prevé desde cada día de origen indicado: el precio previsto, su
variación y el rango del 80 % centrado en el precio de ese día. Cada previsión usa solo datos hasta
su día de origen. Añade las filas a resultados/en_vivo.csv con la fecha y hora en que se hicieron.

Uso:
    python scripts/prever.py --desde 2026-11-11
    python scripts/prever.py --desde 2026-11-05 2026-11-06 --horizontes corto
"""
import argparse

import pandas as pd

from oil_price import config, descarga, incertidumbre as inc, modelo_final as mf, preprocesado as pp

VERSIONES = {"final": "modelos finales (hasta el 3/11/2026)", "hasta_2021": "modelos del test (hasta 2021)"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--desde", nargs="+", required=True, help="días de origen (AAAA-MM-DD)")
    parser.add_argument("--horizontes", nargs="+", choices=list(config.HORIZONTES), default=None)
    parser.add_argument("--modelos", nargs="+", choices=list(VERSIONES), default=list(VERSIONES))
    parser.add_argument("--no-guardar", action="store_true", help="solo mostrar, sin añadir a resultados/en_vivo.csv")
    args = parser.parse_args()

    limpio = descarga.cargar()
    bases = {nivel: pp.preparar_base(limpio, con_nivel=nivel) for nivel in (True, False)}
    ctx = inc.contexto(bases)
    ultimo = limpio.index[-1].date()
    tablas = []
    for carpeta in args.modelos:
        modelos = mf.cargar(mf.DIR_MODELOS / carpeta)
        if args.horizontes:
            modelos = {h: m for h, m in modelos.items() if h in args.horizontes}
        for dia in args.desde:
            tablas.append(mf.prever(modelos, bases, ctx, fecha=dia).assign(
                version=VERSIONES[carpeta], creada=pd.Timestamp.now().isoformat(timespec="seconds"),
                **{"último Brent publicado": ultimo}))
    tabla = pd.concat(tablas, ignore_index=True)
    pd.set_option("display.width", 220)
    print(tabla[["version", "horizonte", "red", "fecha origen", "fecha objetivo (estimada)", "precio hoy",
                 "precio previsto", "rango bajo", "rango alto"]].round(2).to_string(index=False))
    if not args.no_guardar:
        ruta = config.DIR_RESULTADOS / "en_vivo.csv"
        previas = pd.read_csv(ruta) if ruta.exists() else pd.DataFrame()
        pd.concat([previas, tabla], ignore_index=True).to_csv(ruta, index=False)
        print(f"Añadido a {ruta}")


if __name__ == "__main__":
    main()
