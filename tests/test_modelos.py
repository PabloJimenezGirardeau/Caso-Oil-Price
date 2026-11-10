"""Pruebas de los modelos y del entrenamiento. Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest
import torch

from oil_price import entrenamiento as ent, evaluacion
from oil_price.modelos import ModeloLineal, RedRecurrente
from oil_price.preprocesado import Conjunto


def conjunto_sintetico(n=400, ventana=10, variables=3, semilla=0):
    """Fichas artificiales donde la respuesta depende linealmente del último día."""
    rng = np.random.default_rng(semilla)
    X = rng.normal(size=(n, ventana, variables)).astype(np.float32)
    Y = np.column_stack([0.5 * X[:, -1, 0], -0.3 * X[:, -1, 1], 0.2 * X[:, -1, 2]]).astype(np.float32)
    fechas = pd.bdate_range("2010-01-01", periods=n)
    fechas_obj = np.column_stack([(fechas + pd.offsets.BDay(h)).to_numpy() for h in (1, 5, 20)])
    return Conjunto(nombre="sintético", X=X, Y=Y, fechas=fechas,
                    fechas_inicio_ventana=fechas - pd.offsets.BDay(ventana - 1),
                    fechas_objetivo=fechas_obj, precio_origen=np.full(n, 80.0),
                    horizontes=["corto", "medio", "largo"],
                    variables=[f"v{i}" for i in range(variables)], limite_objetivo=fechas_obj.max())


@pytest.mark.parametrize("celda", ["RNN", "LSTM", "GRU"])
def test_forma_de_la_salida(celda):
    red = RedRecurrente(celda, n_entradas=8, unidades=16, capas=2, dropout=0.2)
    assert red(torch.zeros(5, 60, 8)).shape == (5, 3)


def test_perdida_ignora_respuestas_purgadas():
    pred = torch.zeros(4, 3, requires_grad=True)
    obj = torch.tensor([[1.0, np.nan, 0.0]] * 4)
    perdida = ent.perdida_huber(pred, obj, delta=1.0)
    perdida.backward()
    assert torch.isfinite(perdida)
    assert torch.all(pred.grad[:, 1] == 0)   # el horizonte purgado no influye


def test_parada_temprana_sin_fuga():
    c = conjunto_sintetico()
    ajuste, parada = ent.dividir_parada_temprana(c, fraccion=0.2)
    assert ajuste.fechas.max() < parada.fechas.min()
    respuestas_ajuste = pd.DataFrame(ajuste.fechas_objetivo).stack()
    assert respuestas_ajuste.max() < parada.fechas.min()   # ninguna respuesta de ajuste cae en la parada
    assert len(ajuste) + len(parada) == len(c)


def test_entrenamiento_aprende_y_es_reproducible():
    c = conjunto_sintetico()
    hp = {"unidades": 16, "lote": 32, "lr": 3e-3, "dropout": 0.0}
    a = ent.entrenar_red("GRU", c, hp, semilla=1, dispositivo=torch.device("cpu"),
                         ajustes={"max_epocas": 15})
    b = ent.entrenar_red("GRU", c, hp, semilla=1, dispositivo=torch.device("cpu"),
                         ajustes={"max_epocas": 15})
    np.testing.assert_allclose(ent.predecir(a, c.X), ent.predecir(b, c.X), rtol=1e-5)
    historial = a.historial
    assert historial["pérdida train"].iloc[-1] < historial["pérdida train"].iloc[0]   # aprende
    comparacion = evaluacion.comparar_con_ingenuo(evaluacion.errores(c, ent.predecir(a, c.X)),
                                                  evaluacion.errores(c))
    assert evaluacion.puntuacion(comparacion) < 1   # mejora al ingenuo en un problema predecible


def test_modelo_lineal_recupera_relacion_conocida():
    c = conjunto_sintetico(n=600)
    lineal = ModeloLineal(alfa=1e-3).ajustar(c)
    np.testing.assert_allclose(lineal.predecir(c.X), c.Y, atol=1e-3)


def test_lineal_sin_tendencia_no_proyecta_la_media():
    """Sin tendencia, los pesos son los mismos y solo desaparece la subida media del train."""
    c = conjunto_sintetico(n=600)
    c.Y = c.Y + np.float32(0.5)   # el train «sube» de media
    con = ModeloLineal(alfa=1e-3).ajustar(c)
    sin = ModeloLineal(alfa=1e-3, sin_tendencia=True).ajustar(c)
    np.testing.assert_allclose(con.predecir(c.X) - sin.predecir(c.X), np.tile(c.Y.mean(axis=0), (len(c), 1)),
                               atol=1e-4)
    ficha_media = c.X.reshape(len(c), -1).mean(axis=0).reshape(1, *c.X.shape[1:])
    np.testing.assert_allclose(sin.predecir(ficha_media), 0.0, atol=1e-5)   # ficha «media» → sin cambio


def test_red_sin_tendencia_no_proyecta_la_media():
    c = conjunto_sintetico()
    c.Y = c.Y + np.float32(3.0)   # subida media muy grande frente a la señal
    hp = {"unidades": 16, "lote": 32, "lr": 3e-3, "dropout": 0.0}
    sin = ent.entrenar_red("GRU", c, hp, semilla=1, dispositivo=torch.device("cpu"),
                           ajustes={"max_epocas": 15, "sin_tendencia": True})
    ajuste, _ = ent.dividir_parada_temprana(c)
    np.testing.assert_allclose(sin.tendencia, np.nanmean(ajuste.Y, axis=0), rtol=1e-5)
    assert np.abs(ent.predecir(sin, c.X).mean(axis=0)).max() < 0.5   # prevé alrededor de 0, no de 3
    por_defecto = ent.entrenar_red("GRU", c, hp, semilla=1, dispositivo=torch.device("cpu"), ajustes={"max_epocas": 1})
    np.testing.assert_allclose(por_defecto.tendencia, sin.tendencia)   # por defecto, sin tendencia (D22)
    con = ent.entrenar_red("GRU", c, hp, semilla=1, dispositivo=torch.device("cpu"),
                           ajustes={"max_epocas": 1, "sin_tendencia": False})
    assert np.all(con.tendencia == 0)   # la fase A original la conserva de forma explícita
