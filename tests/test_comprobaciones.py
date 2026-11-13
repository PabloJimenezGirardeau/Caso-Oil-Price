"""Pruebas de las comprobaciones de robustez y del entrenamiento con todo (D31). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest
import torch

from oil_price import comprobaciones as cp, config, entrenamiento as ent, entreno_completo as ec, preprocesado as pp


def _sumas(notas, fichas=100):
    filas = [{"horizonte": "medio", "modelo": m, "pliegue": a, "error": n * fichas, "error_ingenuo": fichas,
              "fichas": fichas, "aciertos": 50, "suben": 50} for m, por_año in notas.items() for a, n in por_año.items()]
    return pd.DataFrame(filas).set_index(["horizonte", "modelo", "pliegue"])


def test_bootstrap_por_bloques_con_años_iguales():
    s = _sumas({"RNN": {a: 0.9 for a in range(2010, 2022)}})
    assert cp.bootstrap_bloques(s, ["RNN"]) == pytest.approx((0.9, 0.9))


def test_por_parejas():
    s = _sumas({"RNN": {2010: 0.9, 2011: 1.1, 2012: 0.8}, "LSTM": {2010: 1.0, 2011: 1.0, 2012: 1.0},
                "GRU": {2010: 1.0, 2011: 1.0, 2012: 1.0}})
    t = cp.por_parejas(s, "medio")
    assert t.loc["RNN frente a LSTM", "años que gana la primera"] == 2
    assert t.loc["RNN frente a LSTM", "diferencia media"] == pytest.approx(-0.2 / 3)


def test_diebold_mariano_sin_diferencia_y_con_ventaja():
    rng = np.random.default_rng(0)
    n = 2000
    real = rng.normal(0, 0.05, n)
    p = pd.DataFrame({"horizonte": "corto", "fecha": pd.bdate_range("2010-01-01", periods=n), "precio origen": 60.0,
                      "variación real": real})
    igual = p.assign(modelo="igual", **{"variación prevista": 0.0})
    mejor = p.assign(modelo="mejor", **{"variación prevista": real * 0.5})
    t = cp.diebold_mariano(pd.concat([igual, mejor]), "corto")
    assert t.loc[("corto", "igual"), "diferencia media ($)"] == pytest.approx(0.0)
    assert t.loc[("corto", "mejor"), "p (dos colas)"] < 0.001


def test_memoria_robusta():
    rng = np.random.default_rng(1)
    vol = np.exp(rng.normal(np.log(0.3), 0.5, 20000))
    assert cp.memoria_robusta(rng.normal(size=vol.size) * vol, vol) == pytest.approx(1.0, abs=0.05)
    assert cp.memoria_robusta(rng.normal(size=vol.size), vol) == pytest.approx(0.0, abs=0.05)


def test_margen_de_cobertura_con_fichas_independientes():
    assert cp.margen_cobertura(0.8, 6300, "medio") == pytest.approx(np.sqrt(0.8 * 0.2 / 100))


def test_epocas_fijas_entrenan_con_todo_y_hasta_el_final():
    rng = np.random.default_rng(0)
    n = 300
    X = rng.normal(size=(n, 10, 3)).astype(np.float32)
    Y = (0.3 * X[:, -1, :1] + rng.normal(0, 1, (n, 1))).astype(np.float32)
    fechas = pd.bdate_range("2010-01-01", periods=n)
    c = pp.Conjunto(nombre="prueba", X=X, Y=Y, fechas=fechas, fechas_inicio_ventana=fechas,
                    fechas_objetivo=fechas.to_numpy()[:, None], precio_origen=np.full(n, 60.0),
                    horizontes=["medio"], variables=["a", "b", "c"], limite_objetivo=fechas[-1])
    r = ent.entrenar_red("RNN", c, {"unidades": 8}, semilla=0, dispositivo=torch.device("cpu"),
                         ajustes={"epocas_fijas": 4})
    assert len(r.historial) == 4 and r.mejor_epoca == 4
    assert r.historial["pérdida parada"].isna().all()       # no hay trozo de parada
    # La escala del objetivo sale de todas las fichas, no del 85 % inicial
    assert r.escala_objetivo[0] == pytest.approx(np.nanstd(Y), rel=1e-5)


def test_variantes_de_entreno_completo():
    assert ec.variantes("largo", "GRU") == {"mediana": config.EPOCAS_FIJAS["largo"]["GRU"]}
    assert set(ec.variantes("medio", "RNN")) == {"mediana", *map(str, config.EPOCAS_INFORMACION)}
