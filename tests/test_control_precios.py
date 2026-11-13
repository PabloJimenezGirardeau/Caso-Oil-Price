"""Pruebas del experimento de control con precios (D15). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import config, control_precios as cpr


def _limpio(n=600):
    rng = np.random.default_rng(0)
    fechas = pd.bdate_range("2005-01-03", periods=n)
    return pd.DataFrame({"brent": 60 * np.exp(np.cumsum(rng.normal(0, 0.02, n))),
                         "wti": 55 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))}, index=fechas)


def test_base_de_precios_con_niveles_y_precio_futuro():
    limpio = _limpio()
    base = cpr.base_precio(limpio)
    assert not any(c.startswith("r_") for c in base.entradas.columns)
    dias = base.entradas.index
    assert np.allclose(base.entradas["brent"], limpio.loc[dias, "brent"])
    assert np.allclose(base.entradas["wti"], limpio.loc[dias, "wti"])
    h = config.HORIZONTES["corto"]
    t = dias[10]
    futuro = limpio["brent"].iloc[limpio.index.get_loc(t) + h]
    assert base.objetivos.loc[t, "corto"] == pytest.approx(futuro)
    assert base.objetivos["largo"].iloc[-1:].isna().all()       # sin futuro, sin objetivo


def _previsiones(prevista, real):
    n = len(real)
    return pd.DataFrame({"horizonte": "corto", "modelo": "m", "pliegue": 2018,
                         "fecha": pd.bdate_range("2018-01-01", periods=n), "precio origen": 60.0,
                         "variación prevista": prevista, "variación real": real})


def test_espejismo_de_quien_copia_el_precio_de_hoy_y_de_quien_acierta():
    real = np.random.default_rng(1).normal(0, 0.05, 500)
    copia = cpr.espejismo(_previsiones(np.zeros(500), real)).iloc[0]
    assert copia["nota (MAE / ingenuo)"] == pytest.approx(1.0)
    assert copia["error frente al precio de hoy ($)"] == pytest.approx(0.0)
    assert np.isnan(copia["correlación de los cambios"])
    acierta = cpr.espejismo(_previsiones(real, real)).iloc[0]
    assert acierta["nota (MAE / ingenuo)"] == pytest.approx(0.0, abs=1e-9)
    assert acierta["correlación de los cambios"] == pytest.approx(1.0)
