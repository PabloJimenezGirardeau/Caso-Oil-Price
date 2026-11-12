"""Pruebas de la estabilidad: promedio de semillas (D27). Ejecutar con: poetry run pytest"""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from oil_price import busqueda as bq, config, estabilidad as es, evaluacion as ev, experimentos as ex

AÑOS = (2018, 2019)
FICHAS = 30


def _previsiones_al_azar(semillas, n=200, seed=0):
    """Previsiones de una red (varias semillas) y lo que pasó, con el formato de `leer_previsiones`."""
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2018-01-01", periods=n, freq="B")
    real = rng.normal(0, 0.05, n)
    precio = rng.uniform(40, 90, n)
    return pd.concat([pd.DataFrame({"horizonte": "medio", "modelo": "GRU", "intento": 1, "pliegue": 2018,
                                    "semilla": s, "fecha": fechas, "variación prevista": rng.normal(0, 0.04, n),
                                    "variación real": real, "precio origen": precio}) for s in semillas],
                     ignore_index=True)


def test_el_promedio_de_semillas_iguales_es_la_misma_prevision():
    p = _previsiones_al_azar([42])
    copia = p.assign(semilla=43)
    prom = es.promedio(pd.concat([p, copia]), [42, 43])
    assert (prom["semillas"] == 2).all()
    np.testing.assert_allclose(prom["variación prevista"], p["variación prevista"], rtol=0, atol=1e-14)


def test_el_promedio_nunca_tiene_mas_error_que_la_media_de_sus_semillas():
    """Es la garantía de D27: se promedian los precios, y el error absoluto es convexo."""
    for seed in range(5):
        p = _previsiones_al_azar([42, 43, 44, 45, 46], seed=seed)
        sueltas = np.mean([es.nota(p[p["semilla"] == s]).iloc[0] for s in range(42, 47)])
        assert es.nota(es.promedio(p, range(42, 47))).iloc[0] <= sueltas + 1e-12


def test_la_nota_coincide_con_la_de_evaluacion():
    p = _previsiones_al_azar([42])
    conjunto = SimpleNamespace(Y=p[["variación real"]].to_numpy(), precio_origen=p["precio origen"].to_numpy(),
                               fechas=pd.DatetimeIndex(p["fecha"]), horizontes=["medio"])
    prevision = p[["variación prevista"]].to_numpy()
    esperada = ev.comparar_con_ingenuo(ev.errores(conjunto, prevision), ev.errores(conjunto))["MAE / ingenuo"].iloc[0]
    assert es.nota(p).iloc[0] == pytest.approx(esperada, rel=1e-12)


def test_grupos_disjuntos_de_semillas():
    semillas = config.SEMILLAS_ESTABILIDAD
    assert es.grupos(semillas, 5) == [list(range(42, 47)), list(range(47, 52))]
    assert es.grupos(semillas, 3) == [[42, 43, 44], [45, 46, 47], [48, 49, 50]]   # la 51 sobra
    assert es.grupos(semillas, 10) == [semillas]
    assert config.N_SEMILLAS_PROMEDIO * 2 <= len(semillas)   # dos grupos independientes del promedio adoptado


def test_la_prevision_no_cambia_respecto_a_si_misma():
    p = _previsiones_al_azar([42])
    cambio = es.cambio_prevision(p, p)
    assert (cambio == 0).all().all()


class Corte(Exception):
    """Simula que el proceso se interrumpe a mitad."""


def _entrenar_falso(llamadas, cortar_en=None):
    """Entrenamiento instantáneo: la previsión depende de la red, el año y la semilla."""
    def entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo):
        llamadas.append((comb["horizonte"], celda, año, semilla))
        if cortar_en is not None and len(llamadas) == cortar_en:
            raise Corte()
        fila = {"horizonte": comb["horizonte"], "modelo": celda, "intento": intento, "pliegue": año,
                "semilla": semilla, "MAE": 1.0 + 0.01 * semilla, "MAE / ingenuo": 0.9, "épocas": 5, "segundos": 0.1}
        previsiones = pd.DataFrame({"horizonte": comb["horizonte"], "modelo": celda, "intento": intento,
                                    "pliegue": año, "semilla": semilla, "fecha": evaluado.fechas,
                                    "variación prevista": 0.001 * (semilla - 40) + 0.0001 * (año - 2018)})
        return fila, previsiones
    return entrenar


def _pliegues_falsos(bases, comb):
    salida = []
    for i, año in enumerate(AÑOS):
        fechas = pd.date_range(f"{año}-01-02", periods=FICHAS, freq="B")
        evaluado = SimpleNamespace(fechas=fechas, Y=np.full((FICHAS, 1), 0.02 * (i + 1)),
                                   precio_origen=np.full(FICHAS, 60.0 + i))
        salida.append((año, None, evaluado))
    return salida


def test_la_ejecucion_se_reanuda_sin_repetir(tmp_path, monkeypatch):
    eleg = {(h, c): (3, bq.parametros_base()) for h in ("medio", "largo") for c in ("RNN", "GRU")}
    monkeypatch.setattr(es, "elegidas", lambda dir_salida: eleg)
    monkeypatch.setattr(es, "_previsto", lambda dir_salida, e: {k: {a: 1.0 for a in AÑOS} for k in e})
    monkeypatch.setattr(ex, "_bases", lambda: None)
    monkeypatch.setattr(bq, "_pliegues", _pliegues_falsos)
    opciones = dict(horizontes=["largo", "medio"], modelos=["RNN", "GRU"], semillas=[42, 43, 44],
                    registrar=lambda m: None)
    total = 2 * 2 * 3 * len(AÑOS)

    primera = []
    monkeypatch.setattr(es, "_entrenar", _entrenar_falso(primera, cortar_en=7))
    with pytest.raises(Corte):
        es.ejecutar_estabilidad(tmp_path, **opciones)
    assert len(es.leer_entrenos(tmp_path)) == 6

    segunda = []
    monkeypatch.setattr(es, "_entrenar", _entrenar_falso(segunda))
    es.ejecutar_estabilidad(tmp_path, **opciones)
    assert len(segunda) == total - 6                       # solo lo que faltaba (también el cortado)
    assert set(primera[:6]).isdisjoint(segunda)

    entrenos = es.leer_entrenos(tmp_path)
    assert len(entrenos) == total and not entrenos.duplicated(es.CLAVE_E).any()
    fichas = pd.read_csv(tmp_path / es.ARCHIVOS["fichas"])
    assert len(fichas) == 2 * len(AÑOS) * FICHAS             # una vez por horizonte y año, aunque se relance
    previsiones = es.leer_previsiones(tmp_path)
    assert len(previsiones) == total * FICHAS and previsiones["variación real"].notna().all()

    # Tercera vez: no queda nada por hacer
    tercera = []
    monkeypatch.setattr(es, "_entrenar", _entrenar_falso(tercera))
    es.ejecutar_estabilidad(tmp_path, **opciones)
    assert tercera == []

    curva = es.curva_semillas(previsiones, tamaños=(1, 3))
    assert set(curva.index.get_level_values("semillas promediadas")) == {1, 3}
    assert curva.loc[("largo", "RNN", 1), "grupos"] == 3
