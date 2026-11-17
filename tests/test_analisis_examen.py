"""Pruebas del análisis del examen (R², real frente a previsto, cuándo acierta y cuándo falla).
Ejecutar con: python -m pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price.evaluation import analisis_examen as ae
from oil_price.evaluation import examen_final as exa
from oil_price.utils import config


def test_r2_casos_conocidos():
    real = np.array([1.0, 2.0, 3.0, 4.0])
    assert ae.r2(real, real) == pytest.approx(1.0)                      # acierta todo
    assert ae.r2(real, np.full(4, real.mean())) == pytest.approx(0.0)   # prevé siempre la media
    assert ae.r2(real, real[::-1]) == pytest.approx(-3.0)               # 1 − 20/5
    assert np.isnan(ae.r2([2.0, 2.0], [1.0, 3.0]))                     # sin variabilidad, no se define


def _previsiones(n=60, semilla=0):
    """Fichas inventadas de un horizonte: un modelo perfecto y otro que prevé siempre subir un 1 %."""
    rng = np.random.default_rng(semilla)
    fechas = pd.bdate_range("2023-01-02", periods=n)
    real = rng.normal(0, 0.03, n)
    base = pd.DataFrame({"horizonte": "corto", "fecha": fechas, "variación real": real,
                         "precio origen": 80 + rng.normal(0, 5, n), "pliegue": fechas.year})
    return pd.concat([base.assign(modelo="perfecto", **{"variación prevista": real}),
                      base.assign(modelo="optimista", **{"variación prevista": 0.01})], ignore_index=True)


def _rangos(previsiones):
    """Rangos inventados con el formato de `examen_final.rangos_examen` (método elegido a 1 semana)."""
    f = previsiones.drop_duplicates("fecha")
    tercio = pd.Categorical(np.resize(["calma", "normal", "tormenta"], len(f)), categories=["calma", "normal", "tormenta"])
    return pd.DataFrame({"horizonte": "corto", "fecha": f["fecha"].values,
                         "fecha fin": f["fecha"].values + pd.Timedelta(days=7), "metodo": exa.METODO_RANGO["corto"],
                         "bajo": -0.05, "alto": 0.05, "dentro": np.abs(f["variación real"].values) <= 0.05,
                         "tercio": tercio})


def test_tabla_r2_con_el_ingenuo():
    p = _previsiones()
    t = ae.tabla_r2(p)
    assert t.loc[("corto", "perfecto"), "R² variación"] == pytest.approx(1.0)
    assert t.loc[("corto", "perfecto"), "R² precio"] == pytest.approx(1.0)
    real = p.loc[p["modelo"] == "perfecto", "variación real"]
    assert t.loc[("corto", ae.INGENUO), "R² variación"] == pytest.approx(ae.r2(real, np.zeros(len(real))))
    assert t.loc[("corto", ae.INGENUO), "R² variación"] <= 0                # prever 0 nunca supera a la media
    assert t.loc[("corto", "perfecto"), "R² frente al ingenuo"] == pytest.approx(1.0)   # quita todo su error
    assert t.loc[("corto", ae.INGENUO), "R² frente al ingenuo"] == 0.0
    o = ae.con_precios(p[p["modelo"] == "optimista"])
    esperado = 1 - (o["error ($)"] ** 2).sum() / (o["error del ingenuo ($)"] ** 2).sum()
    assert t.loc[("corto", "optimista"), "R² frente al ingenuo"] == pytest.approx(esperado)


def test_serie_real_frente_a_previsto():
    p = _previsiones()
    s = ae.serie(p, _rangos(p), "corto", modelo="perfecto")
    assert len(s) == 60 and s.index.is_monotonic_increasing and s.index.name == "fecha objetivo"
    assert np.allclose(s["precio previsto"], s["precio real"])               # el modelo perfecto acierta
    assert (s["rango bajo"] < s["precio hoy"]).all() and (s["precio hoy"] < s["rango alto"]).all()


def test_por_grupos_y_episodios():
    p = _previsiones()
    g = ae.por_grupos(p, _rangos(p))
    perfecto = g[g["modelo"] == "perfecto"]
    assert set(g["criterio"]) == {"mercado ese día", "movimiento después"}
    assert (perfecto["MAE ($)"] == 0).all() and (perfecto["MAE / ingenuo"] == 0).all()
    assert set(g.loc[g["criterio"] == "movimiento después", "grupo"]) == set(ae.TAMAÑO_MOVIMIENTO)
    s = ae.serie(p, _rangos(p), "corto", modelo="optimista")
    for criterio in ("fallos", "aciertos"):
        e = ae.episodios(s, criterio, n=3, separacion=5)
        posiciones = [s.index.get_loc(f) for f in e.index]
        assert len(e) == 3 and all(abs(a - b) > 5 for k, a in enumerate(posiciones) for b in posiciones[k + 1:])
    fallos = ae.episodios(s, "fallos", n=1, separacion=5)
    assert fallos["error de la red ($)"].abs().iloc[0] == pytest.approx((s["precio previsto"] - s["precio real"]).abs().max())
    with pytest.raises(ValueError):
        ae.episodios(s, "otro")


@pytest.mark.skipif(not (config.DIR_RESULTADOS / "examen_previsiones.csv").exists(), reason="falta el examen")
def test_coincide_con_la_tabla_oficial_del_examen():
    """Lo nuevo no cambia nada: los errores y la cobertura salen iguales que en la tabla del examen."""
    from oil_price.evaluation import incertidumbre as inc
    prev = exa.previsiones_examen()
    rangos = exa.rangos_examen(prev, inc.contexto())
    tabla = exa.tabla_comparativa(prev, exa.leer_entrenos())
    oficial = exa.resumen_rangos(rangos)
    for h, red in exa.ELEGIDA.items():
        s = ae.serie(prev, rangos, h)
        assert (s["precio previsto"] - s["precio real"]).abs().mean() == pytest.approx(tabla.loc[(h, red), "MAE ($)"])
        assert s["dentro del rango"].mean() == pytest.approx(oficial.loc[(h, exa.METODO_RANGO[h]), "cobertura"])
        assert s.notna().all().all()
    r2 = ae.tabla_r2(prev)                   # R² frente al ingenuo = 1 − (RMSE / RMSE del ingenuo)²
    assert np.allclose(r2["R² frente al ingenuo"], 1 - tabla.loc[r2.index, "RMSE / ingenuo"].astype(float) ** 2)
