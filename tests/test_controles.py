"""Pruebas de los controles del procedimiento (negativo y positivo). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import controles as ct, preprocesado as pp


def _conjunto(n, rng, inicio):
    X = rng.normal(size=(n, 5, 3)).astype(np.float32)
    Y = rng.normal(0, 0.1, (n, 1)).astype(np.float32)          # sin ninguna relación con X
    fechas = pd.bdate_range(inicio, periods=n)
    return pp.Conjunto(nombre="prueba", X=X, Y=Y, fechas=fechas, fechas_inicio_ventana=fechas,
                       fechas_objetivo=fechas.to_numpy()[:, None], precio_origen=np.full(n, 60.0),
                       horizontes=["medio"], variables=["a", "b", "c"], limite_objetivo=fechas[-1])


def _pliegues(años=4):
    rng = np.random.default_rng(0)
    return [(2010 + k, _conjunto(1500, rng, "2000-01-03"), _conjunto(250, rng, f"{2010 + k}-01-01"))
            for k in range(años)]


def test_el_ruido_da_la_mejora_prometida():
    rng = np.random.default_rng(1)
    for mejora in (0.04, 0.16):
        k = ct.ruido_para(mejora)
        y = rng.normal(size=400_000)
        chivato = y + k * rng.normal(size=y.size)
        prevision = chivato / (1 + k ** 2)                      # el mejor previsor lineal
        assert 1 - np.abs(y - prevision).mean() / np.abs(y).mean() == pytest.approx(mejora, abs=0.004)


def test_chivato_solo_en_el_ultimo_dia():
    c = _conjunto(10, np.random.default_rng(2), "2010-01-01")
    nuevo = ct.con_chivato(c, np.arange(10.0))
    assert nuevo.X.shape == (10, 5, 4) and nuevo.variables[-1] == "chivato"
    assert np.array_equal(nuevo.X[:, -1, 3], np.arange(10.0)) and not nuevo.X[:, :-1, 3].any()
    assert np.array_equal(nuevo.X[:, :, :3], c.X)


def test_desplazar_conserva_las_respuestas_y_los_huecos():
    Y = np.arange(100, dtype=np.float32)[:, None]
    Y[[3, 50]] = np.nan
    nuevo = ct.desplazar(Y, np.random.default_rng(3), minimo=20)
    assert np.isnan(nuevo[[3, 50], 0]).all()
    assert sorted(nuevo[~np.isnan(nuevo[:, 0]), 0]) == sorted(Y[~np.isnan(Y[:, 0]), 0])
    assert not np.array_equal(nuevo, Y, equal_nan=True)


def test_controles_sin_señal_y_con_señal():
    pliegues = _pliegues()
    sin = ct.medir(ct.negativo("medio", pliegues, alfa=100.0, repeticion=0), "medio")
    con = ct.medir(ct.positivo("medio", pliegues, alfa=100.0, mejora=0.16, repeticion=0), "medio")
    assert sin["nota"] == pytest.approx(1.0, abs=0.03)
    assert con["nota"] < 0.92 and con["años que gana"] == 4
