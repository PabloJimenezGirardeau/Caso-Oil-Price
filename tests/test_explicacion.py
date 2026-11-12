"""Pruebas de «qué ve cada modelo» (explicacion.py). Ejecutar con: poetry run pytest"""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from oil_price import estabilidad as es, explicacion as xp, preprocesado as pp
from oil_price.modelos import ModeloLineal

VARIABLES = ["r_brent", "r_wti", "r_cobre", "log_vol_brent"]


def _conjunto(n=300, ventana=20, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, ventana, len(VARIABLES))).astype(np.float32)
    # La respuesta depende sobre todo de la volatilidad (como en los datos reales)
    Y = (0.05 * X[:, :, 3].mean(axis=1) + rng.normal(0, 0.02, n)).astype(np.float32)[:, None]
    fechas = pd.date_range("2018-01-01", periods=n, freq="B")
    return pp.Conjunto(nombre="prueba", X=X, Y=Y, fechas=fechas, fechas_inicio_ventana=fechas,
                       fechas_objetivo=np.full((n, 1), np.datetime64("NaT", "D")),
                       precio_origen=rng.uniform(40, 90, n), horizontes=["largo"], variables=VARIABLES,
                       limite_objetivo=pd.Timestamp("2021-12-31"))


def test_las_aportaciones_suman_la_prevision_del_lineal():
    c = _conjunto()
    lineal = ModeloLineal(1.0, sin_tendencia=True).ajustar(c)
    a = xp.aportaciones(lineal, c.X)
    assert a.shape == (len(c), len(VARIABLES))
    np.testing.assert_allclose(a.sum(axis=1), lineal.predecir(c.X)[:, 0], rtol=0, atol=1e-5)
    # La variable que de verdad importa es la que más mueve la previsión
    assert np.argmax(a.std(axis=0)) == VARIABLES.index("log_vol_brent")


def test_desordenar_solo_cambia_de_ficha_esa_variable():
    c = _conjunto()
    d = xp.desordenar(c.X, 2, np.random.default_rng(0))
    otras = [0, 1, 3]
    np.testing.assert_array_equal(d[:, :, otras], c.X[:, :, otras])
    assert not np.array_equal(d[:, :, 2], c.X[:, :, 2])
    # Mismas ventanas, en otro orden
    assert sorted(map(tuple, d[:, :, 2])) == sorted(map(tuple, c.X[:, :, 2]))


def test_desplazar_solo_esas_columnas_y_esos_dias():
    c = _conjunto()
    d = xp.desplazar(c.X, {0: 1.0}, ultimos=5)
    np.testing.assert_allclose(d[:, -5:, 0], c.X[:, -5:, 0] + 1.0)
    np.testing.assert_array_equal(d[:, :-5, 0], c.X[:, :-5, 0])
    np.testing.assert_array_equal(d[:, :, 1:], c.X[:, :, 1:])


def test_escenarios_en_unidades_escaladas():
    preparador = SimpleNamespace(desviacion_=pd.Series({"r_brent": 0.02, "r_wti": 0.025, "r_cobre": 0.015,
                                                        "log_vol_brent": 0.4}))
    cambios, ultimos = xp.cambios_escenario("volatilidad ×2", VARIABLES, preparador, ventana=20)
    assert ultimos is None and cambios == {3: pytest.approx(np.log(2) / 0.4)}
    cambios, ultimos = xp.cambios_escenario("Brent y WTI −10 % en un mes", VARIABLES, preparador, ventana=252)
    assert ultimos == xp.DIAS_MES
    # Repartida en el último mes, la caída suma un 10 % (en variación logarítmica)
    assert cambios[0] * 0.02 * ultimos == pytest.approx(np.log(0.9))
    assert cambios[1] * 0.025 * ultimos == pytest.approx(np.log(0.9))


def test_en_el_lineal_el_efecto_de_un_escenario_es_exacto():
    c = _conjunto()
    lineal = ModeloLineal(1.0, sin_tendencia=True).ajustar(c)
    d = xp.desplazar(c.X, {3: 0.5})
    coef = lineal.coef_[0].reshape(c.X.shape[1], len(VARIABLES))
    esperado = 100 * np.expm1(0.5 * coef[:, 3].sum())
    p0, p1 = lineal.predecir(c.X)[:, 0], lineal.predecir(d)[:, 0]
    assert xp._efecto_medio(p0, p1) == pytest.approx(esperado, rel=1e-4)


def test_la_nota_conjunta_coincide_con_la_de_estabilidad():
    c = _conjunto()
    prevision = np.random.default_rng(1).normal(0, 0.05, len(c))
    tabla = pd.DataFrame({"horizonte": "largo", "modelo": "X", "variación prevista": prevision,
                          "variación real": c.Y[:, 0], "precio origen": c.precio_origen})
    assert xp.nota_conjunta([(prevision, c)]) == pytest.approx(es.nota(tabla).iloc[0], rel=1e-6)
