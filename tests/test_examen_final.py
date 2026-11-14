"""Pruebas del examen final (D33). Ejecutar con: poetry run python -m pytest

Ninguna entrena ni evalúa nada en el test: las medidas se prueban con datos inventados, y con los
datos reales solo se comprueban las fechas de la partición.
"""
import numpy as np
import pandas as pd
import pytest

from oil_price import config, examen_final as exa, experimentos as ex


def test_particion_del_examen_sin_mirar_el_futuro():
    bases = ex._bases()
    fin_train, inicio_test = pd.Timestamp("2021-12-31"), pd.Timestamp("2022-01-01")
    for h in config.HORIZONTES:
        train, evaluado = exa.particion(bases, h)
        validas = ~np.isnan(train.Y[:, 0])
        assert pd.DatetimeIndex(train.fechas).max() <= fin_train
        assert pd.DatetimeIndex(train.fechas_objetivo[validas, 0]).max() <= fin_train      # purga
        assert pd.DatetimeIndex(evaluado.fechas).min() >= inicio_test
        objetivos = pd.DatetimeIndex(evaluado.fechas_objetivo[:, 0])
        assert not objetivos.isna().any() and objetivos.max() <= config.FECHA_CORTE


def _previsiones(**prevista):
    real = np.log(np.tile([1.1, 0.9], 50))
    filas = [pd.DataFrame({"horizonte": "medio", "modelo": m, "pliegue": 2022,
                           "fecha": pd.bdate_range("2022-01-03", periods=len(real)), "precio origen": 100.0,
                           "variación real": real, "variación prevista": v(real)})
             for m, v in prevista.items()]
    return pd.concat(filas, ignore_index=True)


def test_tabla_comparativa():
    p = _previsiones(cero=lambda r: np.zeros_like(r), perfecta=lambda r: r)
    entrenos = pd.DataFrame({"horizonte": "medio", "modelo": ["cero", "perfecta"], "parametros": [10, 20],
                             "segundos": [1.0, 3.0]})
    t = exa.tabla_comparativa(p, entrenos).loc["medio"]
    assert t.loc["cero", "MAE / ingenuo"] == pytest.approx(1.0)
    assert t.loc["cero", "MAE ($)"] == pytest.approx(10.0)                  # se mueve 10 $ cada vez
    assert t.loc["perfecta", "mejora frente al ingenuo (MAE)"] == pytest.approx(1.0)
    assert t.loc["perfecta", "RMSE ($)"] == pytest.approx(0.0, abs=1e-9)
    assert t.loc["ingenuo", "MSE ($²)"] == pytest.approx(100.0)
    assert t.loc["perfecta", "parámetros"] == 20 and t.loc["cero", "segundos por entrenamiento"] == 1.0


def test_conclusiones_fijadas_en_el_protocolo():
    assert exa.conclusion_prevision(0.20, -0.5) == ("sin evidencia de ventaja", "sin evidencia de ventaja")
    assert exa.conclusion_prevision(0.01, -0.5) == ("mejor que el ingenuo en test", "ventaja posible, no confirmada")
    assert exa.conclusion_prevision(0.01, 0.5) == ("peor que el ingenuo en test", "peor que el ingenuo en test")


def test_el_rango_cumple_a_menos_de_dos_margenes():
    assert exa.cumple_rango(0.80, 0.02) == "cumple"
    assert exa.cumple_rango(0.70, 0.02) == "se queda corto"
    assert exa.cumple_rango(0.70, 0.06) == "cumple"
    assert exa.cumple_rango(0.95, 0.02) == "se pasa"


def test_previsiones_del_examen_promedian_semillas(tmp_path):
    fechas = pd.bdate_range("2022-01-03", periods=4)
    semillas = config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    filas = [{"horizonte": "corto", "modelo": m, "intento": 1, "semilla": s, "fecha": f,
              "variación prevista": 0.01 * (k + 1)}
             for m in config.CELDAS for k, s in enumerate(semillas) for f in fechas]
    filas += [{"horizonte": "corto", "modelo": exa.LINEAL, "intento": 0, "semilla": np.nan, "fecha": f,
               "variación prevista": 0.0} for f in fechas]
    pd.DataFrame(filas).to_csv(tmp_path / exa.ARCHIVOS["previsiones"], index=False)
    pd.DataFrame({"horizonte": "corto", "fecha": fechas, "variación real": 0.02, "precio origen": 80.0}).to_csv(
        tmp_path / exa.ARCHIVOS["fichas"], index=False)
    p = exa.previsiones_examen(tmp_path)
    assert set(p["modelo"]) == {*config.CELDAS, "media de las tres", exa.LINEAL}
    rnn = p[p["modelo"] == "RNN"]["variación prevista"]
    # Media de los precios de las 5 semillas, como variación logarítmica
    assert rnn.iloc[0] == pytest.approx(np.log(np.mean(np.exp(0.01 * np.arange(1, 6)))))
    assert (p["pliegue"] == 2022).all()
    # Sin todas las semillas, el examen no ha terminado
    pd.DataFrame(filas[1:]).to_csv(tmp_path / exa.ARCHIVOS["previsiones"], index=False)
    with pytest.raises(ValueError):
        exa.previsiones_examen(tmp_path)


def test_rango_del_examen_con_un_mercado_inventado():
    rng = np.random.default_rng(0)
    dias = pd.bdate_range("2012-01-02", "2023-12-29")
    h = config.HORIZONTES["medio"]
    vol = np.exp(rng.normal(np.log(0.3), 0.3, len(dias)))
    ctx = pd.DataFrame({"volatilidad": vol}, index=dias)
    ctx["fin medio"] = pd.Series(dias, index=dias).shift(-h)
    ctx["variación medio"] = rng.normal(0, 1, len(dias)) * vol * np.sqrt(h / 252)
    ctx = ctx.dropna()
    fichas = ctx.loc["2022":].index
    p = pd.DataFrame({"horizonte": "medio", "modelo": exa.LINEAL, "pliegue": fichas.year, "fecha": fichas,
                      "precio origen": 80.0, "variación real": ctx.loc[fichas, "variación medio"].to_numpy(),
                      "variación prevista": 0.0})
    r = exa.resumen_rangos(exa.rangos_examen(p, ctx))
    assert set(r.index.get_level_values("metodo")) == {"ingenuo", "centrado"}
    elegido = r.loc[("medio", "centrado")]
    assert elegido["elegido"] and 0.65 < elegido["cobertura"] < 0.95
    assert elegido["veredicto"] in {"cumple", "se queda corto", "se pasa"}
    assert r.loc[("medio", "ingenuo"), "nota / ingenuo"] == pytest.approx(1.0)
