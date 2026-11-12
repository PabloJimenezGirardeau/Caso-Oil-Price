"""Pruebas de la combinación de red y lineal (D28). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import combinacion as co, estabilidad as es

SEMILLAS = list(range(42, 52))


def _fichas(n=150, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"horizonte": "medio", "pliegue": np.repeat([2018, 2019], [n // 2, n - n // 2]),
                         "fecha": pd.date_range("2018-01-01", periods=n, freq="B"),
                         "variación real": rng.normal(0, 0.08, n), "precio origen": rng.uniform(40, 90, n)})


def _redes(fichas, seed=1):
    """Previsiones de dos redes con 10 semillas, con el formato de `leer_previsiones`."""
    rng = np.random.default_rng(seed)
    return pd.concat([fichas.assign(modelo=m, intento=1, semilla=s,
                                    **{"variación prevista": rng.normal(0, 0.05, len(fichas))})
                      for m in ("RNN", "GRU") for s in SEMILLAS], ignore_index=True)


def _lineal(fichas, seed=2):
    rng = np.random.default_rng(seed)
    return fichas.assign(modelo="Lineal", intento=0, semilla=np.nan,
                         **{"variación prevista": rng.normal(0, 0.05, len(fichas))})


def test_peso_1_es_la_red_y_peso_0_el_lineal():
    fichas = _fichas()
    red = es.promedio(_redes(fichas), SEMILLAS[:5])
    lineal = _lineal(fichas)
    np.testing.assert_allclose(co.combinar(red, lineal, 1.0)["variación prevista"], red["variación prevista"],
                               rtol=0, atol=1e-12)
    solo_lineal = co.combinar(red, lineal, 0.0).merge(lineal[co.CLAVE_FICHA + ["variación prevista"]],
                                                      on=co.CLAVE_FICHA, suffixes=("", " lineal"))
    np.testing.assert_allclose(solo_lineal["variación prevista"], solo_lineal["variación prevista lineal"],
                               rtol=0, atol=1e-12)


def test_combinar_dos_previsiones_iguales_no_cambia_nada():
    fichas = _fichas()
    red = es.promedio(_redes(fichas), SEMILLAS[:5])
    lineal = red[red["modelo"] == "RNN"].assign(modelo="Lineal")
    rnn = co.combinar(red, lineal)
    rnn = rnn[rnn["modelo"] == "RNN"]
    np.testing.assert_allclose(rnn["variación prevista"], red[red["modelo"] == "RNN"]["variación prevista"],
                               rtol=0, atol=1e-12)


def test_la_combinacion_nunca_tiene_mas_error_que_la_media_de_las_dos():
    """Se promedian precios y el error absoluto es convexo: la mezcla no empeora la media."""
    for seed in range(5):
        fichas = _fichas(seed=seed)
        red = es.promedio(_redes(fichas, seed=seed + 10), SEMILLAS[:5])
        lineal = _lineal(fichas, seed=seed + 20)
        real = fichas["precio origen"] * np.exp(fichas["variación real"])

        def mae(prev):
            p = prev.merge(fichas[co.CLAVE_FICHA], on=co.CLAVE_FICHA)
            return (p["precio origen"] * np.exp(p["variación prevista"])
                    - p["precio origen"] * np.exp(p["variación real"])).abs().mean()

        rnn = red[red["modelo"] == "RNN"]
        assert real.notna().all()
        assert mae(co.combinar(rnn, lineal)) <= (mae(rnn) + mae(lineal)) / 2 + 1e-12


def test_falla_si_falta_la_prevision_del_lineal():
    fichas = _fichas()
    red = es.promedio(_redes(fichas), SEMILLAS[:5])
    with pytest.raises(ValueError):
        co.combinar(red, _lineal(fichas).iloc[:-3])


def test_curva_de_pesos():
    fichas = _fichas()
    previsiones, lineal = _redes(fichas), _lineal(fichas)
    curva = co.curva_pesos(previsiones, lineal, pesos=[0.0, 0.5, 1.0], semillas=SEMILLAS)
    assert list(curva.columns) == [0.0, 0.5, 1.0]
    # Peso 0: el lineal solo, igual para todas las redes
    np.testing.assert_allclose(curva[0.0], es.nota(lineal).iloc[0], rtol=1e-12)
    # Peso 1: la red sola, media de los dos grupos de 5 semillas
    for red in ("RNN", "GRU"):
        q = previsiones[previsiones["modelo"] == red]
        esperada = np.mean([es.nota(es.promedio(q, g)).iloc[0] for g in es.grupos(SEMILLAS, 5)])
        assert curva.loc[("medio", red), 1.0] == pytest.approx(esperada, rel=1e-12)


def test_regla_de_decision():
    indice = pd.MultiIndex.from_product([["corto", "medio", "largo"], ["RNN", "LSTM", "GRU"]],
                                        names=["horizonte", "modelo"])
    curva = pd.DataFrame({0.0: [0.99] * 3 + [0.97] * 3 + [0.82] * 3,
                          0.5: [0.99] * 3 + [0.92] * 3 + [0.84] * 3,
                          1.0: [0.99] * 3 + [0.94] * 3 + [0.91] * 3}, index=indice)
    t = co.decidir(curva, {"corto": 0.003, "medio": 0.008, "largo": 0.02})
    assert t.loc["medio", "se adopta"] and t.loc["medio", "se queda"] == "combinación"   # mejora 0,02 > 0,008
    assert not t.loc["largo", "se adopta"] and t.loc["largo", "se queda"] == "lineal"    # el lineal es mejor
    assert not t.loc["corto", "se adopta"] and t.loc["corto", "se queda"] == "red sola"  # empate: lo sencillo
