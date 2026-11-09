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
