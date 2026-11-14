"""Pruebas de la descarga de datos nuevos (sin conexión: solo la unión). Ejecutar con:
poetry run python -m pytest"""
import numpy as np
import pandas as pd

from oil_price import descarga


def test_combinar_como_el_script_del_curso():
    dias = pd.date_range("2024-01-01", "2024-01-10")          # incluye un fin de semana
    fred = pd.DataFrame({"brent": [80, np.nan, 81, 82, 83, 84, 85, 86, np.nan, 88.0],
                         "wti": [75, 76, np.nan, 77, 78, 79, 80, 81, 82, 83.0]}, index=dias)
    yahoo = pd.DataFrame({"oro": [2000.0, 2010.0]}, index=pd.DatetimeIndex(["2024-01-02", "2024-01-08"]))
    t = descarga.combinar(fred, yahoo)
    assert (t.index.dayofweek < 5).all()                       # sin sábados ni domingos
    assert t.loc["2024-01-02", "brent"] == 80                  # festivo del Brent: último valor
    assert t.loc["2024-01-03", "wti"] == 76                    # hueco del WTI: último valor
    assert t.loc["2024-01-05", "oro"] == 2000.0                # el oro del día 2 se arrastra hasta el 8
    assert t.index.name == "Date"


def test_tabla_de_la_api_de_graficos_de_yahoo():
    """Fechas en la zona del mercado: el cierre de Nueva York de las 18:00 cae en su día, no en el siguiente (UTC)."""
    respuesta = {"chart": {"result": [{
        "meta": {"exchangeTimezoneName": "America/New_York"},
        "timestamp": [1762898400, 1762984800, 1762984800],          # 11/11 y 12/11/2025 a las 17:00 de NY, uno repetido
        "indicators": {"quote": [{"open": [1, 2, 2.5], "high": [1, 2, 2.5], "low": [1, 2, 2.5],
                                  "close": [10.0, 20.0, 21.0], "volume": [5, 6, 7]}]}}]}}
    t = descarga.tabla_grafico(respuesta)
    assert list(t.index.strftime("%Y-%m-%d")) == ["2025-11-11", "2025-11-12"]
    assert t["Close"].tolist() == [10.0, 21.0]                     # del día repetido, el último
    assert list(t.columns) == ["Open", "High", "Low", "Close", "Volume"]
