"""Pruebas del lanzador de experimentos. Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import experimentos as ex


def test_reanudar_reconoce_lo_ya_guardado(tmp_path):
    """Una fila guardada (red con alfa vacío, o lineal con alfa) se reconoce al releer el archivo."""
    ruta = tmp_path / "fase_a.csv"
    filas = [
        {"horizonte": "corto", "ventana": 10, "recorte": "ninguno", "nivel": True,
         "modelo": "RNN", "alfa": np.nan, "pliegue": 2018},
        {"horizonte": "largo", "ventana": 252, "recorte": "0.5-99.5", "nivel": False,
         "modelo": "Lineal", "alfa": 1e4, "pliegue": 2020},
    ]
    ex._anadir(ruta, filas, ex.COLUMNAS)
    hechas = ex._ya_hechas(ruta)
    for fila in filas:
        assert ex._clave(fila) in hechas
    otra = {**filas[0], "pliegue": 2019}
    assert ex._clave(otra) not in hechas


def test_reanudar_reconoce_la_semilla_aunque_se_lea_como_decimal(tmp_path):
    """Si la columna de semillas tiene vacíos, pandas la lee como decimal (43.0): debe reconocerse igual."""
    ruta = tmp_path / "fase_a_semillas.csv"
    base = {"horizonte": "medio", "ventana": 20, "recorte": "ninguno", "nivel": False,
            "modelo": "GRU", "alfa": np.nan, "pliegue": 2019}
    ex._anadir(ruta, [{**base, "semilla": 43}, {**base, "pliegue": 2020, "semilla": np.nan}], ex.COLUMNAS)
    hechas = ex._ya_hechas(ruta, ex.CLAVE_SEMILLAS)
    assert ex._clave({**base, "semilla": 43}, ex.CLAVE_SEMILLAS) in hechas
    assert ex._clave({**base, "semilla": 44}, ex.CLAVE_SEMILLAS) not in hechas


def test_formato_fijo_aunque_cambien_las_columnas(tmp_path):
    ruta = tmp_path / "fase_a.csv"
    ex._anadir(ruta, [{"horizonte": "corto", "MAE": 1.0}], ex.COLUMNAS)
    ex._anadir(ruta, [{"horizonte": "medio", "MAE": 2.0, "segundos": 3.0}], ex.COLUMNAS)
    tabla = pd.read_csv(ruta)
    assert list(tabla.columns) == ex.COLUMNAS and len(tabla) == 2


def test_resumir_junta_pliegues_ponderando_por_fichas():
    base = {"horizonte": "corto", "ventana": 10, "recorte": "ninguno", "nivel": True,
            "modelo": "GRU", "alfa": np.nan}
    resultados = pd.DataFrame([
        {**base, "pliegue": 2018, "fichas evaluación": 100, "MAE": 2.0, "MSE": 4.0,
         "MAE ingenuo": 2.0, "MSE ingenuo": 4.0},
        {**base, "pliegue": 2019, "fichas evaluación": 300, "MAE": 1.0, "MSE": 1.0,
         "MAE ingenuo": 2.0, "MSE ingenuo": 4.0},
    ])
    fila = ex.resumir(resultados).iloc[0]
    assert fila["MAE"] == pytest.approx((2 * 100 + 1 * 300) / 400)
    assert fila["MAE / ingenuo"] == pytest.approx(1.25 / 2.0)
    assert fila["pliegues"] == 2


def _resultado(horizonte, ventana, recorte, nivel, modelo, ratio, alfa=np.nan):
    return {"horizonte": horizonte, "ventana": ventana, "recorte": recorte, "nivel": nivel,
            "modelo": modelo, "alfa": alfa, "pliegue": 2018, "fichas evaluación": 100,
            "MAE": ratio, "MSE": ratio ** 2, "MAE ingenuo": 1.0, "MSE ingenuo": 1.0}


def test_finalistas_por_la_media_de_las_tres_redes():
    """Gana la media de las tres redes, no la mejor red suelta; el lineal no cuenta."""
    filas = []
    for celda, r60, r20, r10 in [("RNN", 1.10, 0.93, 0.97), ("LSTM", 0.85, 0.93, 0.97), ("GRU", 1.10, 0.93, 0.97)]:
        filas += [_resultado("medio", 60, "ninguno", False, celda, r60),
                  _resultado("medio", 20, "1-99", False, celda, r20),
                  _resultado("medio", 10, "ninguno", True, celda, r10)]
    filas.append(_resultado("medio", 60, "ninguno", False, "Lineal", 0.5, alfa=10.0))
    elegidas = ex.finalistas(pd.DataFrame(filas), n=2)
    assert [(e["ventana"], e["recorte"], e["nivel"]) for e in elegidas] == [(20, (1.0, 99.0), False),
                                                                            (10, None, True)]


def _por_semilla(filas):
    indice = pd.MultiIndex.from_tuples([f[0] for f in filas], names=["ventana", "recorte", "nivel"])
    return pd.DataFrame([f[1] for f in filas], index=indice, columns=[42, 43, 44])


def test_decidir_gana_la_mejor_si_la_diferencia_supera_el_ruido():
    tabla, ruido = ex.decidir(_por_semilla([((60, "ninguno", False), [0.90, 0.91, 0.92]),
                                            ((20, "ninguno", False), [0.95, 0.96, 0.97])]))
    assert ruido == pytest.approx(0.01)
    assert tabla["elegida"].tolist() == [True, False]


def test_decidir_empate_dentro_del_ruido_gana_la_ventana_mas_corta():
    tabla, _ = ex.decidir(_por_semilla([((60, "ninguno", False), [0.90, 0.93, 0.96]),
                                        ((20, "1-99", False), [0.91, 0.94, 0.97])]))
    assert tabla["empata con la mejor"].all()
    assert tabla["elegida"].tolist() == [False, True]


def test_eleccion_junta_la_fase_a_y_la_confirmacion():
    """La semilla 42 sale de la fase A y las demás de la confirmación; la suerte de la fase A no basta."""
    # (ventana, recorte, nivel): MAE / ingenuo con las semillas 42, 43 y 44
    casos = {(60, "ninguno", False): [0.90, 1.00, 1.00],   # la mejor en la fase A, por suerte
             (20, "ninguno", False): [0.93, 0.93, 0.93],
             (40, "1-99", False): [0.95, 0.95, 0.95],
             (10, "ninguno", True): [0.99, 0.99, 0.99]}    # no es finalista
    fase_a, confirmacion = [], []
    for h in ["corto", "medio", "largo"]:
        for (v, r, n), valores in casos.items():
            for celda in ["RNN", "LSTM", "GRU"]:
                fase_a.append({**_resultado(h, v, r, n, celda, valores[0]), "semilla": 42})
                confirmacion += [{**_resultado(h, v, r, n, celda, x), "semilla": s}
                                 for s, x in zip([43, 44], valores[1:])]
        fase_a.append({**_resultado(h, 60, "ninguno", False, "Lineal", 0.5, alfa=10.0), "semilla": np.nan})
    elegidas = ex.eleccion(pd.DataFrame(fase_a), pd.DataFrame(confirmacion))
    assert elegidas["medio"] == {"horizonte": "medio", "ventana": 20, "recorte": None, "nivel": False}


def test_adoptar_sin_tendencia_si_no_empeora_mas_que_el_ruido():
    assert ex.adoptar_sin_tendencia(con=1.10, sin=1.00, ruido=0.03)        # mejora
    assert ex.adoptar_sin_tendencia(con=0.93, sin=0.95, ruido=0.03)        # empeora menos que el ruido: empate
    assert not ex.adoptar_sin_tendencia(con=0.93, sin=0.97, ruido=0.03)    # empeora más que el ruido


def test_decidir_misma_ventana_gana_la_mas_sencilla():
    """Con la misma ventana: antes sin recorte que con recorte, y antes sin nivel que con nivel."""
    tabla, _ = ex.decidir(_por_semilla([((20, "1-99", False), [0.93, 0.94, 0.95]),
                                        ((20, "ninguno", True), [0.93, 0.94, 0.95]),
                                        ((20, "ninguno", False), [0.935, 0.945, 0.955])]))
    assert tabla["elegida"].tolist() == [False, False, True]
