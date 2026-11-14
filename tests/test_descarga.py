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
