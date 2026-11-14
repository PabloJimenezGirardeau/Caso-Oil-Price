"""Pruebas de los modelos finales y de la previsión desde el último dato (D34). Ejecutar con:
poetry run python -m pytest"""
import numpy as np
import pandas as pd
import pytest
import torch

from oil_price import entrenamiento as ent, incertidumbre as inc, modelo_final as mf, preprocesado as pp
from oil_price.modelos import RedRecurrente


def _ctx(h="medio", sesiones=63):
    rng = np.random.default_rng(0)
    dias = pd.bdate_range("2010-01-04", "2022-12-30")
    vol = np.exp(rng.normal(np.log(0.3), 0.3, len(dias)))
    ctx = pd.DataFrame({"volatilidad": vol}, index=dias)
    ctx[f"fin {h}"] = pd.Series(dias, index=dias).shift(-sesiones)
    ctx[f"variación {h}"] = rng.normal(0, 1, len(dias)) * vol * np.sqrt(sesiones / 252)
    return ctx


@pytest.mark.parametrize("metodo", ["memoria", "centrado"])
def test_rango_desde_coincide_con_el_de_la_validacion(metodo):
    """Ajustado con lo conocido hasta el 31/12, da lo mismo que `incertidumbre.rangos` para el año siguiente."""
    ctx = _ctx()
    dia = pd.Timestamp("2021-06-01")
    p = pd.DataFrame({"horizonte": ["medio"], "pliegue": [2021], "fecha": [dia], "variación prevista": [0.0],
                      "volatilidad": [ctx.loc[dia, "volatilidad"]], "fecha fin": [ctx.loc[dia, "fin medio"]]})
    esperado = inc.rangos(p, ctx, metodo).iloc[0]
    # Mismo ajuste (hasta el 31/12/2020), con la volatilidad de ese día
    ctx_hoy = ctx.copy()
    ctx_hoy.loc[pd.Timestamp("2020-12-31"), "volatilidad"] = ctx.loc[dia, "volatilidad"]
    bajo, alto, _ = mf.rango_desde(ctx_hoy, "medio", metodo, "2020-12-31")
    assert bajo == pytest.approx(esperado["bajo"]) and alto == pytest.approx(esperado["alto"])


def _modelo_y_base():
    rng = np.random.default_rng(1)
    dias = pd.bdate_range("2020-01-01", periods=80)
    entradas = pd.DataFrame({"r_brent": rng.normal(0, 0.02, 80), "log_vol_brent": rng.normal(-1.2, 0.1, 80)},
                            index=dias)
    base = pp.Base(entradas=entradas, objetivos=pd.DataFrame({"corto": np.zeros(80)}, index=dias),
                   fechas_objetivo=pd.DataFrame({"corto": dias}, index=dias),
                   precio=pd.Series(np.linspace(60, 70, 80), index=dias))
    preparador = pp.Preparador(None).ajustar(entradas.iloc[:60])
    torch.manual_seed(0)
    red = RedRecurrente("RNN", 2, 4, 1, 0.0, 1).eval()
    resultado = ent.Resultado(modelo=red, escala_objetivo=np.array([0.03], np.float32), tendencia=np.zeros(1, np.float32),
                              historial=pd.DataFrame(), mejor_epoca=1, segundos=0.0, parametros=10,
                              hiperparametros={"unidades": 4, "capas": 1, "dropout": 0.0})
    m = mf.ModeloHorizonte("corto", "RNN", 1, {"unidades": 4, "capas": 1, "dropout": 0.0}, 10, None, False,
                           ["r_brent", "log_vol_brent"], preparador, {42: resultado}, dias[59])
    return m, base


def test_guardar_y_cargar_dan_la_misma_prevision(tmp_path):
    m, base = _modelo_y_base()
    X = mf.ventana_hasta(m, base, base.entradas.index[-1])
    assert X.shape == (1, 10, 2)
    mf.guardar({"corto": m}, tmp_path)
    cargado = mf.cargar(tmp_path)["corto"]
    assert cargado.celda == "RNN" and cargado.ventana == 10 and cargado.fin_train == m.fin_train
    assert np.allclose(mf.ventana_hasta(cargado, base, base.entradas.index[-1]), X)
    assert ent.predecir(cargado.redes[42], X) == pytest.approx(ent.predecir(m.redes[42], X))


def test_prever_desde_el_ultimo_dia():
    m, base = _modelo_y_base()
    dias = base.entradas.index
    rng = np.random.default_rng(2)
    vol = np.exp(rng.normal(np.log(0.3), 0.3, len(dias)))
    ctx = pd.DataFrame({"volatilidad": vol, "fin corto": pd.Series(dias, index=dias).shift(-5),
                        "variación corto": rng.normal(0, 1, len(dias)) * vol * np.sqrt(5 / 252)}, index=dias)
    p = mf.prever({"corto": m}, {False: base}, ctx).iloc[0]
    assert p["fecha origen"] == dias[-1].date() and p["precio hoy"] == pytest.approx(70.0)
    assert p["precio previsto"] == pytest.approx(70.0 * np.exp(ent.predecir(m.redes[42], mf.ventana_hasta(m, base, dias[-1]))[0, 0]))
    assert p["rango bajo"] < 70.0 < p["rango alto"]
    assert p["fecha objetivo (estimada)"] == (dias[-1] + pd.offsets.BDay(5)).date()
