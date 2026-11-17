"""Datos en el formato que lee la web (web/data/*.json).

Los usan las dos formas de llenar la web, para que den siempre lo mismo:
- el exportador (`scripts/inference/exportar_web.py`), que escribe los JSON que se publican;
- la aplicación (`app/app.py`), que con el botón «Actualizar datos» descarga datos nuevos, los pasa por los
  modelos ya entrenados (sin reentrenar) y devuelve la previsión, el histórico y la cinta de cotizaciones.
"""
from datetime import datetime

import numpy as np
import pandas as pd

from oil_price.utils import config
from oil_price.data import datos, descarga
from oil_price.inference import aplicacion as ap

ORDEN = ["corto", "medio", "largo"]
COTIZACIONES = {"brent": "Brent", "wti": "WTI", "gas_natural": "Gas natural", "oro": "Oro",
                "cobre": "Cobre", "vix": "VIX"}


def fecha_iso(valor):
    return pd.Timestamp(valor).strftime("%Y-%m-%d")


def redondear(valor, decimales=4):
    return None if valor is None or pd.isna(valor) else round(float(valor), decimales)


def lista(valores, decimales=2):
    return [redondear(v, decimales) for v in valores]


# --- Precios ---------------------------------------------------------------------------------------

def brent_real(directorio=descarga.DIR_ACTUAL):
    """Tabla del CSV solo en los días en que cotizó el Brent, hasta el último dato real. Con datos
    descargados (en `directorio`), esos, hasta el último Brent publicado; si no, la foto del estudio."""
    directorio = descarga.DIR_ACTUAL if directorio is None else directorio
    try:
        if (directorio / "petroleo_dataset.csv").exists():
            tabla = datos.cargar_dataset(directorio / "petroleo_dataset.csv")
            dias = datos.cargar_dias_brent(directorio / "dias_brent.csv")
            return tabla.loc[tabla.index.isin(dias)].dropna(subset=["brent"])
    except Exception:
        pass
    tabla = datos.cargar_dataset()
    tabla = tabla.loc[tabla.index.isin(datos.cargar_dias_brent())]
    return tabla.loc[:config.FECHA_CORTE].dropna(subset=["brent"])


def historico(tabla):
    return {"fechas": [fecha_iso(f) for f in tabla.index], "precios": lista(tabla["brent"])}


def cotizaciones(tabla):
    ultimo, anterior = tabla.iloc[-1], tabla.iloc[-2]
    return {"fecha": fecha_iso(tabla.index[-1]),
            "valores": [{"clave": c, "nombre": n, "valor": redondear(ultimo[c], 2),
                         "variacion": redondear(100 * (ultimo[c] / anterior[c] - 1), 2)}
                        for c, n in COTIZACIONES.items()]}


# --- Previsión -------------------------------------------------------------------------------------

def prevision(filas, plazos_estudio, precios, estado="definitiva", explicaciones=None):
    """La previsión en el formato de la web (prevision.json).

    - `filas`: una fila por horizonte (índice) con las columnas de `modelo_final.prever` (las mismas que se
      guardan en resultados/en_vivo.csv): fecha de origen, precio de hoy, previsto, rango y fecha objetivo;
    - `plazos_estudio`: por horizonte, lo que dijo el estudio del rango (cobertura, margen, orientativo);
    - `precios`: el Brent de los días reales de cotización, para la volatilidad de los últimos 21 días."""
    dia = pd.Timestamp(filas["fecha origen"].iloc[0])
    precio = float(filas["precio hoy"].iloc[0])
    r = np.log(precios.loc[:dia]).diff().iloc[-config.DIAS_VOLATILIDAD:]
    plazos = {}
    for h in ORDEN:
        f, e = filas.loc[h], plazos_estudio[h]
        plazos[h] = {"sesiones": config.HORIZONTES[h], "fecha_objetivo": fecha_iso(f["fecha objetivo (estimada)"]),
                     # días laborables: exacta a 1 semana salvo festivo; aproximada a 3 meses y a 1 año
                     "fecha_aproximada": h != "corto", "red": f["red"],
                     "prevision_red": redondear(f["precio previsto"], 2), "ingenuo": redondear(precio, 2),
                     "bajo": redondear(f["rango bajo"], 2), "alto": redondear(f["rango alto"], 2),
                     "cobertura": e["cobertura"], "margen": e["margen"], "orientativo": e["orientativo"]}
    salida = {"estado": estado, "fecha": fecha_iso(dia), "precio": redondear(precio, 2),
              "volatilidad": redondear(r.std() * np.sqrt(252), 3), "ajuste_hasta": fecha_iso(dia), "plazos": plazos}
    if explicaciones is not None:
        salida["explicaciones"] = explicaciones
    return salida


def explicaciones(filas, estudio, precios):
    """Por horizonte, los tres apartados de la explicación en lenguaje sencillo (`aplicacion.explicar`)."""
    dia = pd.Timestamp(filas["fecha origen"].iloc[0])
    return {h: ap.explicar({**filas.loc[h].to_dict(), "horizonte": h}, estudio, precios.loc[:dia]) for h in ORDEN}


def actualizacion(app, publicada):
    """Lo que devuelve el botón «Actualizar datos» de la aplicación, con `app` (una `Aplicacion`) ya cargada:
    la previsión al momento, el histórico y la cinta en el formato de la web, y de dónde salen los datos.
    De la previsión publicada (`publicada`, prevision.json) solo se toma lo que dijo el estudio del rango."""
    filas = app.tabla
    tabla = brent_real(app.directorio_datos).loc[:pd.Timestamp(filas["fecha origen"].iloc[0])]
    plazos_estudio = {h: {k: publicada["plazos"][h][k] for k in ("cobertura", "margen", "orientativo")} for h in ORDEN}
    return {
        "prevision": prevision(filas, plazos_estudio, tabla["brent"], estado="al momento",
                               explicaciones=explicaciones(filas, app.estudio, app.precios)),
        "historico": historico(tabla),
        "cotizaciones": cotizaciones(tabla),
        "estado": {"origen": app.origen, "avisos": app.avisos, "datos_hasta": fecha_iso(app.ultimo_dia),
                   "modelos_hasta": fecha_iso(app.modelos_hasta), "hora": datetime.now().strftime("%H:%M")},
    }
