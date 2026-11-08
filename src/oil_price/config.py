"""Parámetros del proyecto, en un único sitio.

Los usan los notebooks, las pruebas y la aplicación. Cada parámetro indica la
decisión del diario de ruta (docs/diario_de_ruta.md) que lo justifica.
"""
from pathlib import Path

import pandas as pd

# --- Rutas -------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]
DIR_DATOS = RAIZ / "data"
RUTA_DATASET = DIR_DATOS / "petroleo_dataset.csv"  # foto oficial de los datos (D12), solo lectura
RUTA_DIAS_BRENT = DIR_DATOS / "dias_brent.csv"     # días reales de cotización del Brent (D13)

# --- Periodo de estudio --------------------------------------------------------
FECHA_INICIO = pd.Timestamp("2000-08-30")  # primer día con oro y cobre (D5)
FECHA_CORTE = pd.Timestamp("2026-11-03")   # último Brent real de la foto de datos (D3, D12)

# --- Variables (D5) --------------------------------------------------------------
OBJETIVO = "brent"
VARIABLES = ["brent", "wti", "cobre", "oro", "indice_dolar", "vix"]
DIAS_VOLATILIDAD = 21   # volatilidad reciente del Brent (D5, D8)
DIAS_MEDIA = 252        # precio frente a su media del último año (D5)

# --- Horizontes de predicción (sesiones del Brent) ---------------------------------
HORIZONTES = {"corto": 5, "medio": 63, "largo": 252}

# --- Estudios de sensibilidad (se eligen en validación) ----------------------------------
VENTANAS = [20, 60, 120]                     # longitud de la ventana de entrada (D6)
RECORTES = [None, (0.5, 99.5), (1.0, 99.0)]  # percentiles de recorte de las entradas (D9)

# --- Partición E (D7) y prueba de robustez con la A (D10) --------------------------------
PARTICION = {
    "fin_train": pd.Timestamp("2017-12-31"),
    "fin_validacion": pd.Timestamp("2021-12-31"),
}
PARTICION_ROBUSTEZ = {
    "fin_train": pd.Timestamp("2018-12-31"),
    "fin_validacion": pd.Timestamp("2022-12-31"),
}

SEMILLA = 42
