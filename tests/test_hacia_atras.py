"""Pruebas de la validación hacia atrás (D29). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import busqueda as bu, experimentos as ex, hacia_atras as ha


def test_pliegues_de_2010_a_2017_sin_nada_despues_de_2017():
    pl = ha.pliegues_hacia_atras()
    assert [p["hasta"].year for p in pl] == list(range(2010, 2018))
    for p in pl:
        assert p["fin_train"] == pd.Timestamp(p["hasta"].year - 1, 12, 31)
        assert p["limite_objetivo"] == pd.Timestamp("2017-12-31")


@pytest.fixture(scope="module")
def bases():
    return ex._bases()


@pytest.mark.parametrize("horizonte, ultimo", [("medio", 2017), ("largo", 2016)])
def test_ninguna_ficha_mira_despues_de_2017(bases, horizonte, ultimo):
    pl = ha.pliegues(bases, bu.combinacion(horizonte))
    assert [a for a, _, _ in pl][-1] == ultimo           # a 1 año, 2017 no tiene respuestas antes de 2018
    for año, train, evaluado in pl:
        # El train solo conoce respuestas anteriores al año que prevé (purga)
        assert pd.Series(train.fechas_objetivo[:, 0]).max() < pd.Timestamp(año, 1, 1)
        # Lo evaluado es de ese año y su respuesta llega como mucho al 31/12/2017
        assert evaluado.fechas.min().year == año and evaluado.fechas.max().year == año
        assert pd.Series(evaluado.fechas_objetivo[:, 0]).max() <= ha.LIMITE


def test_prob_moneda():
    assert ha.prob_moneda(12, 12) == pytest.approx(1 / 4096)
    assert ha.prob_moneda(9, 12) == pytest.approx(299 / 4096)   # ≈ 7 %
    assert ha.prob_moneda(0, 12) == pytest.approx(1.0)


def _sumas(notas_por_año, fichas=100):
    """Sumas por año con la nota dada (error del ingenuo = 1 por ficha)."""
    filas = [{"horizonte": "medio", "modelo": m, "pliegue": año, "error": n * fichas, "error_ingenuo": fichas,
              "fichas": fichas, "aciertos": 55, "suben": 50}
             for m, notas in notas_por_año.items() for año, n in notas.items()]
    return pd.DataFrame(filas).set_index(["horizonte", "modelo", "pliegue"])


def test_criterio():
    años = range(2010, 2022)
    real = _sumas({m: {a: 0.95 for a in años} for m in ("RNN", "LSTM", "GRU")})
    r = ha.criterio(real, "medio")
    assert r["años"] == 12 and r["años que gana al ingenuo"] == 12 and r["veredicto"] == "real"
    assert r["nota con los años juntos"] == pytest.approx(0.95)
    assert r["intervalo 90 % (bajo)"] == pytest.approx(0.95) and r["intervalo 90 % (alto)"] == pytest.approx(0.95)
    # Gana 7 de 12 años: dudosa
    mitad = _sumas({m: {a: (0.95 if a < 2017 else 1.05) for a in años} for m in ("RNN", "LSTM", "GRU")})
    assert ha.criterio(mitad, "medio")["veredicto"] == "dudosa"
    # Gana 6 de 12: no se sostiene
    peor = _sumas({m: {a: (0.95 if a < 2016 else 1.05) for a in años} for m in ("RNN", "LSTM", "GRU")})
    assert ha.criterio(peor, "medio")["veredicto"] == "no se sostiene"


def _previsiones_dos_redes(n=120):
    rng = np.random.default_rng(1)
    fichas = pd.DataFrame({"horizonte": "medio", "pliegue": np.repeat([2016, 2019], n // 2),
                           "fecha": pd.date_range("2016-01-01", periods=n, freq="B"),
                           "variación real": rng.normal(0, 0.1, n), "precio origen": rng.uniform(40, 90, n)})
    return pd.concat([fichas.assign(modelo=m, **{"variación prevista": rng.normal(0, 0.05, n)}) for m in ("RNN", "GRU")],
                     ignore_index=True)


def test_media_de_las_redes_es_la_media_de_los_precios():
    p = _previsiones_dos_redes()
    media = ha.media_de_las_redes(p)
    a = np.exp(p[p["modelo"] == "RNN"]["variación prevista"].to_numpy())
    b = np.exp(p[p["modelo"] == "GRU"]["variación prevista"].to_numpy())
    np.testing.assert_allclose(media["variación prevista"], np.log((a + b) / 2), rtol=1e-12)
    with pytest.raises(ValueError):                    # una ficha sin una de las redes
        ha.media_de_las_redes(p.iloc[:-1])


def test_prudente_con_factor_0_es_el_ingenuo_y_con_1_no_cambia():
    from oil_price import estabilidad as es
    p = _previsiones_dos_redes()
    años = [2016, 2019]
    np.testing.assert_allclose(ha.nota_prudente(p, 0.0, años), 1.0, rtol=1e-12)
    np.testing.assert_allclose(ha.nota_prudente(p, 1.0, años), es.nota(p), rtol=1e-12)


def test_prudente_cruzado_elige_en_un_periodo_y_comprueba_en_el_otro():
    filas = []
    for periodo, mejor in (("2010-2017", 0.0), ("2018-2021", 1.0), ("todos", 0.5)):
        for f in ha.FACTORES:
            filas.append({"horizonte": "medio", "modelo": "RNN", "periodo": periodo, "factor": f,
                          "MAE / ingenuo": 1 + abs(f - mejor) / 10})
    r = ha.prudente_cruzado(pd.DataFrame(filas)).loc[("medio", "RNN")]
    assert r["factor elegido con 2010-2017"] == 0.0 and r["factor elegido con 2018-2021"] == 1.0
    assert r["mejor factor con todos"] == 0.5
    assert not r["se adopta"]           # los dos periodos piden lo contrario: elegido en uno, empeora el otro


def test_sumas_y_notas_coinciden_con_estabilidad():
    from oil_price import estabilidad as es
    rng = np.random.default_rng(0)
    n = 200
    p = pd.DataFrame({"horizonte": "medio", "modelo": "GRU", "pliegue": np.repeat([2010, 2011], n // 2),
                      "variación prevista": rng.normal(0, 0.05, n), "variación real": rng.normal(0, 0.1, n),
                      "precio origen": rng.uniform(40, 90, n)})
    s = ha.sumas_por_año(p)
    assert ha.nota_juntos(s).iloc[0] == pytest.approx(es.nota(p).iloc[0], rel=1e-12)
    por_año = ha.notas_por_año(s)
    assert por_año.loc[("medio", "GRU"), 2010] == pytest.approx(es.nota(p[p["pliegue"] == 2010]).iloc[0], rel=1e-12)
