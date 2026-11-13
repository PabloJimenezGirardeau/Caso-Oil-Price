"""Pruebas del rango de incertidumbre (D30). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest
import torch

from oil_price import entrenamiento as ent, incertidumbre as inc, preprocesado as pp

H = "medio"
AÑO = 2012


def _datos(seed=0):
    """Fichas diarias de 2008 a 2013 con su volatilidad, su respuesta (conocida 91 días después) y
    una previsión; y el contexto con todas las variaciones, como `incertidumbre.contexto`."""
    rng = np.random.default_rng(seed)
    fechas = pd.bdate_range("2008-01-01", "2013-12-31")
    n = len(fechas)
    vol = np.exp(rng.normal(np.log(0.3), 0.4, n))
    var = rng.normal(0, 1, n) * vol * 0.5
    fin = fechas + pd.Timedelta(days=91)
    ctx = pd.DataFrame({"volatilidad": vol, f"fin {H}": fin, f"variación {H}": var}, index=fechas)
    p = pd.DataFrame({"horizonte": H, "modelo": "RNN", "pliegue": fechas.year, "fecha": fechas,
                      "variación prevista": rng.normal(0, 0.05, n), "variación real": var, "precio origen": 60.0,
                      "volatilidad": vol, "fecha fin": fin, "escala": vol * np.sqrt(63 / 252)})
    return p, ctx


def _cambiar_el_futuro(p, ctx):
    """Copias en las que todo lo que se conoce a partir del 1 de enero de AÑO es distinto."""
    inicio = pd.Timestamp(AÑO, 1, 1)
    p2, ctx2 = p.copy(), ctx.copy()
    p2.loc[p2["fecha fin"] >= inicio, "variación real"] *= 10
    ctx2.loc[ctx2[f"fin {H}"] >= inicio, f"variación {H}"] *= 10
    return p2, ctx2


@pytest.mark.parametrize("metodo", inc.METODOS)
def test_cada_rango_solo_usa_lo_conocido_antes_del_año(metodo):
    p, ctx = _datos()
    r1 = inc.rangos(p, ctx, metodo, años=[AÑO])
    r2 = inc.rangos(*_cambiar_el_futuro(p, ctx), metodo, años=[AÑO])
    assert len(r1) == (p["pliegue"] == AÑO).sum()
    np.testing.assert_allclose(r1["bajo"], r2["bajo"])
    np.testing.assert_allclose(r1["alto"], r2["alto"])


def test_el_rango_de_redes_ajustado_solo_usa_lo_conocido():
    p, ctx = _datos()
    cuant = p.assign(q10=p["variación prevista"] - 0.05, q50=p["variación prevista"], q90=p["variación prevista"] + 0.05)
    cuant = cuant.drop(columns=["volatilidad", "fecha fin", "escala"])
    r1 = inc.rangos_redes(cuant, ctx, ajustado=True, años={H: [AÑO]})
    p2, ctx2 = _cambiar_el_futuro(p, ctx)
    cuant2 = cuant.assign(**{"variación real": p2["variación real"]})
    r2 = inc.rangos_redes(cuant2, ctx2, ajustado=True, años={H: [AÑO]})
    np.testing.assert_allclose(r1["bajo"], r2["bajo"])
    # El rango de las redes es muy estrecho (±5 %) para movimientos de ±15 %: el ajuste lo ensancha
    assert (r1["alto"] - r1["bajo"]).mean() > 0.1
    sin_ajustar = inc.rangos_redes(cuant, ctx, ajustado=False, años={H: [AÑO]})
    np.testing.assert_allclose(sin_ajustar["alto"] - sin_ajustar["bajo"], 0.1)


def test_memoria():
    rng = np.random.default_rng(1)
    vol = np.exp(rng.normal(np.log(0.3), 0.5, 20000))
    m, _ = inc.memoria(rng.normal(size=vol.size) * vol, vol)           # el movimiento crece con la volatilidad
    assert m == pytest.approx(1.0, abs=0.05)
    m, _ = inc.memoria(rng.normal(size=vol.size), vol)                  # no depende de ella
    assert m == pytest.approx(0.0, abs=0.05)
    m, _ = inc.memoria(rng.normal(size=vol.size) * vol ** 3, vol)       # se limita a [0, 1]
    assert m == 1.0


def test_medir_la_nota_de_un_rango():
    # Precio de hoy 100: rango 90-110 (en variación logarítmica)
    r = pd.DataFrame({"bajo": [np.log(0.9)] * 3, "alto": [np.log(1.1)] * 3,
                      "variación real": [np.log(1.0), np.log(1.2), np.log(0.85)]})
    m = inc.medir(r, alfa=0.2)
    assert list(m["dentro"]) == [True, False, False]
    np.testing.assert_allclose(m["anchura"], 20.0)
    # Nota: anchura + (2 / 0,2) × lo que se sale (10 puntos por arriba y 5 por abajo)
    np.testing.assert_allclose(m["nota"], [20.0, 20.0 + 10 * 10, 20.0 + 10 * 5])


def test_perdida_por_cuantiles():
    q = torch.tensor([0.1, 0.5, 0.9])
    pred = torch.zeros(2, 3)
    obj = torch.tensor([[1.0], [-1.0]])
    # error +1: 0,1 · 0,5 · 0,9; error −1: 0,9 · 0,5 · 0,1 → media (1,5 + 1,5) / 6 = 0,5
    assert ent.perdida_cuantiles(pred, obj, q).item() == pytest.approx(0.5)


def _conjunto(n=400, ventana=10, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, ventana, 3)).astype(np.float32)
    Y = (0.3 * X[:, -1, :1] + rng.normal(0, 1, (n, 1))).astype(np.float32)
    fechas = pd.bdate_range("2010-01-01", periods=n)
    return pp.Conjunto(nombre="prueba", X=X, Y=Y, fechas=fechas, fechas_inicio_ventana=fechas,
                       fechas_objetivo=fechas.to_numpy()[:, None], precio_origen=np.full(n, 60.0),
                       horizontes=["medio"], variables=["a", "b", "c"], limite_objetivo=fechas[-1])


def test_red_con_cuantiles_da_tres_valores_ordenados():
    c = _conjunto()
    r = ent.entrenar_red("GRU", c, {"unidades": 8}, semilla=0, dispositivo=torch.device("cpu"),
                         ajustes={"cuantiles": [0.1, 0.5, 0.9], "max_epocas": 3})
    q = ent.predecir(r, c.X)
    assert q.shape == (len(c), 3) and (np.diff(q, axis=1) >= 0).all()
    normal = ent.entrenar_red("GRU", c, {"unidades": 8}, semilla=0, dispositivo=torch.device("cpu"),
                              ajustes={"max_epocas": 3})
    assert ent.predecir(normal, c.X).shape == (len(c), 1)
