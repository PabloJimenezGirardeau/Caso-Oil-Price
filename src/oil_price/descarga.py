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


def _yfinance(inicio, fin):
    """Futuros del Brent y del WTI (OHLCV) y cierres del cobre, el oro y el índice del dólar con
    yfinance, exactamente como en el script del curso."""
    import yfinance as yf

    def ohlcv(ticker, prefijo):
        df = yf.download(ticker, start=inicio, end=fin, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open", "High", "Low", "Close", "Volume"]].add_prefix(f"{prefijo}_")

    cierres = yf.download(list(OTROS_YAHOO), start=inicio, end=fin, auto_adjust=False, progress=False)["Close"]
    return ohlcv("BZ=F", "brent_fut").join(ohlcv("CL=F", "wti_fut"), how="outer").join(
        cierres.rename(columns=OTROS_YAHOO), how="outer")


def tabla_grafico(respuesta):
    """La respuesta de la API de gráficos de Yahoo Finance → OHLCV diario, con la fecha del día en la
    zona horaria del mercado (como hace yfinance) y el cierre sin ajustar."""
    r = respuesta["chart"]["result"][0]
    zona = r["meta"].get("exchangeTimezoneName", "UTC")
    fechas = (pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(zona).normalize().tz_localize(None))
    q = r["indicators"]["quote"][0]
    t = pd.DataFrame({"Open": q["open"], "High": q["high"], "Low": q["low"], "Close": q["close"],
                      "Volume": q["volume"]}, index=pd.DatetimeIndex(fechas, name="Date"), dtype=float)
    return t[~t.index.duplicated(keep="last")].dropna(subset=["Close"])


def _grafico(ticker, inicio, fin):
    """Una serie diaria pedida directamente a la API de gráficos de Yahoo Finance (la misma fuente que
    usa yfinance), solo con la biblioteca estándar."""
    import json
    import urllib.parse
    import urllib.request
    desde = int(pd.Timestamp(inicio).timestamp())
    hasta = int((pd.Timestamp(fin) + pd.Timedelta(days=1)).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}"
           f"?period1={desde}&period2={hasta}&interval=1d&events=history")
    peticion = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(peticion, timeout=30) as r:
        return tabla_grafico(json.load(r))


def _directo(inicio, fin):
    """Lo mismo que `_yfinance`, pidiendo cada serie directamente a Yahoo Finance."""
    tabla = _grafico("BZ=F", inicio, fin).add_prefix("brent_fut_").join(
        _grafico("CL=F", inicio, fin).add_prefix("wti_fut_"), how="outer")
    for ticker, nombre in OTROS_YAHOO.items():
        tabla = tabla.join(_grafico(ticker, inicio, fin)["Close"].rename(nombre), how="outer")
    return tabla


def _completa(tabla):
    return tabla is not None and all(v in tabla and not tabla[v].dropna().empty for v in OTROS_YAHOO.values())


def descargar_yahoo(inicio=INICIO, fin=None, registrar=print):
    """Datos de Yahoo Finance como en el script del curso. Primero con yfinance; si no devuelve datos
    (en algunos equipos su conexión falla), se piden directamente a la API de Yahoo Finance."""
    fin = fin or datetime.now().strftime("%Y-%m-%d")
    try:
        tabla = _yfinance(inicio, fin)
        if _completa(tabla):
            return tabla
        registrar("yfinance no ha devuelto datos: se piden directamente a Yahoo Finance")
    except Exception as error:
        registrar(f"yfinance ha fallado ({error}): se piden directamente a Yahoo Finance")
    return _directo(inicio, fin)


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
        yahoo = descargar_yahoo(registrar=registrar)
    except Exception as error:                     # como el script del curso: se sigue sin Yahoo
        registrar(f"Aviso: no se pudo descargar Yahoo Finance ({error})")
        yahoo = None
    faltan = [v for v in OTROS_YAHOO.values() if yahoo is None or v not in yahoo or yahoo[v].dropna().empty]
    if faltan:
        registrar(f"Aviso: Yahoo Finance no ha devuelto datos de {', '.join(faltan)}. Sin ellos no se puede "
                  "prever con estos datos; se puede volver a intentar más tarde")
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
