"""Modelos finales y previsión desde el último dato de la foto (D34).

Entrena las redes elegidas (LSTM a 1 semana, RNN a 3 meses y a 1 año; semillas 42-46) en dos
versiones y prevé desde el 3/11/2026 (el último dato de data/petroleo_dataset.csv):
- modelos del test: con todo hasta el 31/12/2021 (sin ningún año del test). Como comprobación, sus
  previsiones en las fichas del examen deben coincidir con las del examen (resultados/examen_*.csv);
- modelos finales: con todo lo que tiene respuesta hasta el 3/11/2026. Son los de la aplicación.

Guarda los modelos en modelos/hasta_2021/ y modelos/final/, y la previsión en
resultados/en_vivo.csv (con la fecha y hora en que se hizo). No descarga ni lee datos posteriores
al 3/11/2026.

Uso:
    python scripts/prevision_en_vivo.py
"""
import time

import numpy as np
import pandas as pd

from oil_price import config, examen_final as exa, experimentos as ex, incertidumbre as inc, modelo_final as mf
from oil_price import entrenamiento as ent

VERSIONES = {"modelos del test (hasta 2021)": ("hasta_2021", pd.Timestamp("2021-12-31")),
             "modelos finales (hasta el 3/11/2026)": ("final", config.FECHA_CORTE)}


def comprobar_con_el_examen(modelos, bases, registrar):
    """Las previsiones de los modelos del test en las fichas del examen, frente a las guardadas."""
    guardadas = exa.leer_previsiones()
    for h, m in modelos.items():
        _, evaluado = exa.particion(bases, h)
        nuevas = np.mean([ent.predecir(r, evaluado.X)[:, 0] for r in m.redes.values()], axis=0)
        g = guardadas[(guardadas["horizonte"] == h) & (guardadas["modelo"] == m.celda)]
        viejas = g.groupby("fecha")["variación prevista"].mean().reindex(pd.DatetimeIndex(evaluado.fechas)).to_numpy()
        registrar(f"  comprobación {h} {m.celda}: diferencia máxima con el examen {np.nanmax(np.abs(nuevas - viejas)):.2e}")


def main():
    inicio = time.time()
    registrar = lambda msg: print(f"[{(time.time() - inicio) / 60:5.1f} min] {msg}", flush=True)
    bases = ex._bases()
    ctx = inc.contexto(bases)
    tablas = []
    for version, (carpeta, fin_train) in VERSIONES.items():
        registrar(f"{version}: entrenando")
        modelos = mf.entrenar(fin_train, bases, registrar=registrar)
        mf.guardar(modelos, mf.DIR_MODELOS / carpeta)
        if carpeta == "hasta_2021":
            comprobar_con_el_examen(modelos, bases, registrar)
        tablas.append(mf.prever(modelos, bases, ctx, fecha=config.FECHA_CORTE).assign(
            version=version, creada=pd.Timestamp.now().isoformat(timespec="seconds")))
    tabla = pd.concat(tablas, ignore_index=True)
    ruta = config.DIR_RESULTADOS / "en_vivo.csv"
    tabla.to_csv(ruta, mode="a", header=not ruta.exists(), index=False)
    pd.set_option("display.width", 200)
    print(tabla[["version", "horizonte", "red", "fecha origen", "fecha objetivo (estimada)", "precio hoy",
                 "precio previsto", "rango bajo", "rango alto"]].round(2).to_string(index=False))
    registrar(f"Guardado en {ruta}")


if __name__ == "__main__":
    main()
