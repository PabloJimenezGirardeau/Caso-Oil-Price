"""Descarga de datos nuevos (actualización dinámica que pide el enunciado).

Hace lo mismo que `scripts/download_data.py` (el script del curso: mismas series de FRED y Yahoo
Finance, misma unión y mismo relleno de festivos), pero **guarda en otra carpeta**
(`data/actual/` por defecto): la foto del estudio (`data/petroleo_dataset.csv`, D12) no se toca.
Descarga también el calendario de días reales del Brent (D13), y `cargar` devuelve la tabla limpia
como `datos.cargar_datos_limpios`, hasta el último día con Brent.
"""
from datetime import datetime

import pandas as pd

from . import config, datos

INICIO = "2000-01-01"
DIR_ACTUAL = config.DIR_DATOS / "actual"
SERIES_FRED = {"DCOILBRENTEU": "brent", "DCOILWTICO": "wti", "DHHNGSP": "gas_natural", "ECBDFR": "tipo_bce",
               "DEXUSEU": "usd_por_eur", "DEXCHUS": "cny_por_usd", "VIXCLS": "vix"}
OTROS_YAHOO = {"HG=F": "cobre", "GC=F": "oro", "DX-Y.NYB": "indice_dolar"}


def descargar_fred(serie, inicio=INICIO, fin=None):
    """Una serie diaria de FRED, sin rellenar (los festivos quedan vacíos)."""
    fin = fin or datetime.now().strftime("%Y-%m-%d")
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}&cosd={inicio}&coed={fin}"
    return pd.read_csv(url, index_col=0, parse_dates=True, na_values=".").iloc[:, 0].rename(SERIES_FRED[serie])


def descargar_yahoo(inicio=INICIO, fin=None):
    """Futuros del Brent y del WTI (apertura, máximo, mínimo, cierre y volumen) y cierres del cobre,
    el oro y el índice del dólar, como en el script del curso."""
    import yfinance as yf
    fin = fin or datetime.now().strftime("%Y-%m-%d")

    def ohlcv(ticker, prefijo):
        df = yf.download(ticker, start=inicio, end=fin, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open", "High", "Low", "Close", "Volume"]].add_prefix(f"{prefijo}_")

    cierres = yf.download(list(OTROS_YAHOO), start=inicio, end=fin, auto_adjust=False, progress=False)["Close"]
    return ohlcv("BZ=F", "brent_fut").join(ohlcv("CL=F", "wti_fut"), how="outer").join(
        cierres.rename(columns=OTROS_YAHOO), how="outer")


def combinar(fred, yahoo, inicio=INICIO):
    """Unión diaria como en el script del curso: festivos rellenados con el último valor, solo días
    con Brent y laborables."""
    tabla = fred.copy() if yahoo is None else fred.join(yahoo, how="outer")
    tabla = tabla.sort_index().ffill().dropna(subset=["brent"])
    tabla = tabla[tabla.index.dayofweek < 5].loc[inicio:]
    tabla.index.name = "Date"
    return tabla


def actualizar(directorio=DIR_ACTUAL, registrar=print):
    """Descarga todo desde 2000 hasta hoy y lo guarda en `directorio` (petroleo_dataset.csv y
    dias_brent.csv). Si Yahoo falla, avisa: sin cobre, oro e índice del dólar no se puede prever."""
    fred_crudo = {s: descargar_fred(s) for s in SERIES_FRED}
    try:
        yahoo = descargar_yahoo()
    except Exception as error:                     # como el script del curso: se sigue sin Yahoo
        registrar(f"Aviso: no se pudo descargar Yahoo Finance ({error})")
        yahoo = None
    tabla = combinar(pd.concat(fred_crudo.values(), axis=1), yahoo)
    dias = fred_crudo["DCOILBRENTEU"].dropna().index
    directorio.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(directorio / "petroleo_dataset.csv")
    pd.DataFrame({"Date": dias.strftime("%Y-%m-%d")}).to_csv(directorio / "dias_brent.csv", index=False)
    registrar(f"Datos hasta el {dias[-1].date()} (último Brent) guardados en {directorio}")
    return tabla, dias


def cargar(directorio=DIR_ACTUAL):
    """Tabla limpia de los datos descargados, hasta el último día con Brent (mismas reglas que la foto)."""
    tabla = datos.cargar_dataset(directorio / "petroleo_dataset.csv")
    dias = datos.cargar_dias_brent(directorio / "dias_brent.csv")
    return datos.limpiar(tabla, dias, corte=dias[-1])
