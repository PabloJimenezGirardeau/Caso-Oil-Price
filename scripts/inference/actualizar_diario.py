"""Actualización automática diaria: la lanza GitHub Actions cada mañana (.github/workflows/actualizar.yml) hasta
el 30/11/2026 (config.ACTUALIZACION_HASTA); después no hace nada.

1. Descarga los datos de FRED y Yahoo Finance (data/actual/, sin tocar la foto del estudio).
2. Si FRED ha publicado días de Brent nuevos (por tandas), prevé desde cada uno con los modelos finales, ya
   entrenados (no se reentrena nada), en los tres plazos, y lo añade a resultados/en_vivo.csv. Solo los días
   cuya fecha prevista a 1 semana todavía no ha llegado (inference/en_vivo.py). Cada previsión usa solo los
   datos hasta su día de origen.
3. Comprueba las previsiones a 1 semana pendientes cuyo precio ya ha publicado FRED
   (resultados/en_vivo_comprobacion.csv).

El flujo de GitHub Actions guarda los cambios con un commit **antes** de regenerar y publicar la web, para
que cada previsión quede fechada en el repositorio antes de conocerse su precio.

Uso (también en local):
    python scripts/inference/actualizar_diario.py
"""
import os
from zoneinfo import ZoneInfo

import pandas as pd

from oil_price.utils import config
from oil_price.data import descarga
from oil_price.inference import aplicacion as ap
from oil_price.inference import datos_web as dw
from oil_price.inference import en_vivo as ev
from oil_price.inference import modelo_final as mf

EN_VIVO = config.DIR_RESULTADOS / "en_vivo.csv"
COMPROBACION = config.DIR_RESULTADOS / "en_vivo_comprobacion.csv"


def salida(**valores):
    """Resultados para los pasos siguientes del flujo de GitHub Actions (si se ejecuta allí)."""
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.writelines(f"{k}={v}\n" for k, v in valores.items())


def main():
    ahora = pd.Timestamp.now(tz=ZoneInfo("Europe/Madrid")).tz_localize(None).floor("s")
    if not ev.activa(ahora):
        print(f"La actualización automática terminó el {ap.fecha(config.ACTUALIZACION_HASTA)}: no se hace nada.")
        salida(activa="no", cambios="no")
        return

    try:
        descarga.actualizar()
    except Exception as error:
        print(f"::warning::No se han podido descargar los datos ({error}). Se mantiene la última previsión.")
        salida(activa="si", cambios="no")
        return

    limpio = descarga.cargar()
    bases, ctx = ap.preparar(limpio)
    modelos = ap.cargar_modelos()
    previas = pd.read_csv(EN_VIVO)
    comprobadas = pd.read_csv(COMPROBACION) if COMPROBACION.exists() else pd.DataFrame(columns=ev.COLUMNAS_COMPROBACION)
    marca = ahora.isoformat()

    origenes, motivo = ev.origenes_nuevos(limpio.index, previas, ahora)
    print(motivo)
    nuevas = pd.concat([ev.marcar(mf.prever(modelos, bases, ctx, fecha=dia), marca, limpio.index[-1].date())
                        for dia in origenes], ignore_index=True) if origenes else pd.DataFrame()
    if len(nuevas):
        previas = pd.concat([previas, nuevas], ignore_index=True)
        previas.to_csv(EN_VIVO, index=False)
        print(nuevas[["horizonte", "red", "fecha origen", "fecha objetivo (estimada)", "precio hoy", "precio previsto",
                      "rango bajo", "rango alto"]].round(2).to_string(index=False))

    nuevas_comprobaciones = ev.comprobar(previas, comprobadas, dw.brent_real()["brent"], marca)
    if len(nuevas_comprobaciones):
        pd.concat([comprobadas, nuevas_comprobaciones], ignore_index=True).to_csv(COMPROBACION, index=False)
        for _, c in nuevas_comprobaciones.iterrows():
            print(f"Comprobada ({c['version']}): desde el {c['fecha origen']} para el {c['fecha real']}, real "
                  f"{c['precio real']:.2f} $, red {c['precio previsto']:.2f} $, {'dentro' if c['dentro del rango'] else 'fuera'} del rango.")
    else:
        print("Ninguna previsión pendiente tiene todavía su precio publicado.")

    salida(activa="si", cambios="si" if len(nuevas) or len(nuevas_comprobaciones) else "no")


if __name__ == "__main__":
    main()
