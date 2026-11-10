"""Pruebas de la fase B (búsqueda con Optuna). Ejecutar con: poetry run pytest"""
import numpy as np
import optuna
import pandas as pd
import pytest

from oil_price import busqueda as bq, config, experimentos as ex


def test_lo_que_propone_optuna_coincide_con_los_rangos_guardados():
    """Para reanudar, los intentos se recargan con `distribuciones()`: deben ser los de `sugerir`."""
    estudio = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    estudio.optimize(lambda t: hash(tuple(bq.sugerir(t).items())) % 7, n_trials=5)
    for t in estudio.trials:
        assert t.distributions == bq.distribuciones()
        assert set(t.params) == set(bq.PARAMETROS)


def test_la_l2_solo_cuenta_si_se_usa():
    params = {**bq.parametros_base(), "con l2": False, "fuerza l2": 1e-3}
    assert bq.hiperparametros(params)["l2"] == 0.0
    assert bq.hiperparametros({**params, "con l2": True})["l2"] == pytest.approx(1e-3)


def test_el_primer_intento_es_la_estructura_base():
    assert bq.hiperparametros(bq.parametros_base()) == config.HIPERPARAMETROS_BASE


def test_decidir_configuracion_empate_gana_la_de_menos_parametros():
    por_semilla = pd.DataFrame({42: [0.90, 0.91, 0.99], 43: [0.92, 0.90, 1.01], 44: [0.91, 0.92, 1.00]},
                               index=pd.Index([7, 3, 12], name="intento"))
    parametros = pd.Series({7: 19_000, 3: 600, 12: 300})
    tabla, ruido = bq.decidir_configuracion(por_semilla, parametros)
    assert ruido == pytest.approx(0.01)
    assert list(tabla["empata con la mejor"]) == [True, True, False]
    assert tabla.loc[3, "elegida"] and tabla["elegida"].sum() == 1   # empata y es más pequeña


def test_la_base_siempre_es_finalista():
    """D23: el intento 1 entra en la final aunque no esté entre los 3 mejores, y no se repite si lo está."""
    cerrados = pd.DataFrame({"intento": [1, 2, 3, 4, 5, 6], "estado": ["completo"] * 5 + ["podado"],
                             "MAE / ingenuo": [0.95, 0.90, 0.91, 0.92, 0.99, 0.80]})
    assert list(bq.finalistas_b(cerrados)["intento"]) == [2, 3, 4, 1]   # el podado no cuenta
    cerrados.loc[0, "MAE / ingenuo"] = 0.85
    assert list(bq.finalistas_b(cerrados)["intento"]) == [1, 2, 3]


class Corte(Exception):
    """Simula que el proceso se interrumpe a mitad."""


def _entrenar_falso(llamadas, cortar_en=None):
    """Entrenamiento instantáneo: el resultado depende del dropout, del año y de la semilla."""
    def entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo):
        llamadas.append((intento, año, semilla))
        if cortar_en is not None and len(llamadas) == cortar_en:
            raise Corte()
        ratio = 0.8 + params["dropout"] + 0.01 * (año - 2018) + 0.001 * (semilla - 42)
        fila = {**ex._datos(comb), "sesiones": config.HORIZONTES[comb["horizonte"]], "modelo": celda,
                "intento": intento, **params, "pliegue": año, "semilla": semilla, "fichas train": 100,
                "fichas evaluación": 50, "MAE": ratio, "MSE": ratio ** 2, "MAE ingenuo": 1.0, "MSE ingenuo": 1.0,
                "MAE / ingenuo": ratio, "parametros": params["unidades"] * 10, "épocas": 5, "mejor época": 2,
                "segundos": 0.01}
        curvas = pd.DataFrame([{"época": 1, "pérdida train": 1.0, "pérdida parada": 1.0, "lr": 1e-3}]).assign(
            horizonte=comb["horizonte"], modelo=celda, intento=intento, pliegue=año, semilla=semilla)
        return fila, curvas
    return entrenar


def test_la_busqueda_se_reanuda_sin_repetir_y_confirma(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "_bases", lambda: None)
    monkeypatch.setattr(bq, "_pliegues", lambda bases, comb: [(año, None, None) for año in (2018, 2019, 2020)])
    monkeypatch.setitem(config.PODA_FASE_B, "intentos_sin_poda", 2)   # para que haya poda con pocos intentos
    opciones = dict(horizontes=["medio"], modelos=["GRU"], intentos=8, registrar=lambda m: None)

    # Primera ejecución: se corta en el segundo pliegue del intento 3
    primera = []
    monkeypatch.setattr(bq, "_entrenar", _entrenar_falso(primera, cortar_en=8))
    with pytest.raises(Corte):
        bq.ejecutar_fase_b(tmp_path, **opciones)
    entrenos, cerrados, _ = bq.leer_resultados(tmp_path)
    assert list(cerrados["intento"]) == [1, 2] and len(entrenos) == 7

    # Segunda ejecución: repite el intento 3 con los mismos valores, sin volver a entrenar 2018
    segunda = []
    monkeypatch.setattr(bq, "_entrenar", _entrenar_falso(segunda))
    bq.ejecutar_fase_b(tmp_path, **opciones)
    assert segunda[0] == (3, 2019, 42)
    entrenos, cerrados, confirmados = bq.leer_resultados(tmp_path)

    assert list(cerrados["intento"]) == list(range(1, 9))
    assert not entrenos.duplicated(bq.CLAVE_B).any() and not confirmados.duplicated(bq.CLAVE_B).any()
    assert bq._leer_params(cerrados.iloc[0]) == bq.parametros_base()
    for fila in cerrados.to_dict("records"):   # cada intento tiene un entrenamiento por pliegue evaluado
        del_intento = entrenos[entrenos["intento"] == fila["intento"]]
        assert len(del_intento) == fila["pliegues"]
        assert (fila["estado"] == "completo") == (fila["pliegues"] == 3)
        assert all(bq._leer_params(f) == bq._leer_params(fila) for f in del_intento.to_dict("records"))
    assert (cerrados["estado"] == "podado").any()   # la poda ha actuado

    # Confirmación: las 3 mejores y la base, con las semillas 43 y 44 en los 3 pliegues; y elección
    finalistas = bq.finalistas_b(cerrados)
    assert 1 in set(finalistas["intento"])
    assert len(confirmados) == len(finalistas) * 3 * 2
    assert set(confirmados["intento"]) == set(finalistas["intento"])
    tabla, ruido = bq.eleccion(tmp_path, intentos=8)[("medio", "GRU")]
    assert tabla["elegida"].sum() == 1 and ruido >= 0

    # Una tercera ejecución no entrena nada
    tercera = []
    monkeypatch.setattr(bq, "_entrenar", _entrenar_falso(tercera))
    bq.ejecutar_fase_b(tmp_path, **opciones)
    assert tercera == []


def test_los_datos_de_la_fase_b_son_los_elegidos_en_la_fase_a():
    """`config.DATOS_FASE_B` debe coincidir con la regla D19 aplicada a los resultados (1 año: D21)."""
    r = config.DIR_RESULTADOS
    archivos = ["fase_a.csv", "fase_a_semillas.csv", "fase_a_sin_tendencia.csv", "fase_a_sin_tendencia_semillas.csv"]
    if not all((r / a).exists() for a in archivos):
        pytest.skip("faltan los resultados de la fase A")
    leer = lambda a: pd.read_csv(r / a)
    elegidas = {**ex.eleccion(leer(archivos[0]), leer(archivos[1]), horizontes=["corto", "medio"]),
                **ex.eleccion(leer(archivos[2]), leer(archivos[3]), horizontes=["largo"])}
    for h, datos in config.DATOS_FASE_B.items():
        assert {k: elegidas[h][k] for k in datos} == datos, h
