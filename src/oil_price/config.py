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
DIR_RESULTADOS = RAIZ / "resultados"               # resultados de los experimentos (fases A y B)

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
VENTANAS = [10, 20, 40, 60, 120, 252]        # longitud de la ventana de entrada, en días (D6)
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

# --- Modelado (D11, D16, D17) ------------------------------------------------------------
CELDAS = ["RNN", "LSTM", "GRU"]

# Estructura base para la fase A (estudio de los datos); en la fase B cada red busca la suya
HIPERPARAMETROS_BASE = {"unidades": 64, "capas": 1, "dropout": 0.2, "lr": 1e-3, "l2": 0.0, "lote": 64}

# Igual para las tres redes
ENTRENAMIENTO = {
    "max_epocas": 100,
    "paciencia": 10,            # épocas sin mejorar antes de parar
    "paciencia_lr": 4,          # épocas sin mejorar antes de reducir la velocidad de aprendizaje
    "factor_lr": 0.5,           # la velocidad se multiplica por este factor al reducirse
    "recorte_gradiente": 1.0,   # norma máxima del gradiente
    "fraccion_parada": 0.15,    # último trozo del train usado para la parada temprana
    "delta_huber": 1.0,         # en desviaciones típicas del objetivo
    "sin_tendencia": True,      # D20, D22: quita la subida media del train y supone tendencia cero.
                                # La fase A original (con tendencia) lo desactiva de forma explícita
}

# Modelo lineal de referencia (Ridge): fuerza de la regularización a probar en validación
ALFAS_LINEAL = [1.0, 10.0, 100.0, 1e3, 1e4, 1e5]

# Un pliegue solo se evalúa si tiene al menos estas respuestas (a 252 sesiones, el de 2021 tiene 1)
MIN_FICHAS_EVALUACION = 20

# Confirmación de la fase A (D16, D19): las mejores combinaciones de cada horizonte se repiten
# con más semillas para medir el ruido del entrenamiento (la semilla 42 ya está en la fase A)
N_FINALISTAS = 3
SEMILLAS_EXTRA = [43, 44]

# --- Fase B: búsqueda de la configuración de cada red con Optuna (D16, D22) ---------------
# Datos elegidos en la fase A para cada horizonte (D19; a 1 año, D21). Todo sin tendencia (D20)
DATOS_FASE_B = {
    "corto": {"ventana": 252, "recorte": None, "nivel": False},
    "medio": {"ventana": 20, "recorte": None, "nivel": False},
    "largo": {"ventana": 20, "recorte": (0.5, 99.5), "nivel": False},
}

# Intentos por red en cada horizonte; el primero es la estructura base, como referencia. A 1 semana,
# 20 (D24): con la ventana de 252 días cada intento es lento, y a 3 meses la búsqueda no mejoró la base
INTENTOS_FASE_B = {"corto": 20, "medio": 40, "largo": 40}

# Semillas con las que se mide cada intento: a 1 año, tres, porque el azar es grande (0,06);
# a 1 semana y a 3 meses, una, y las finalistas (las 3 mejores y la base, D23) se confirman
# después con las demás
SEMILLAS_FASE_B = {"corto": [SEMILLA], "medio": [SEMILLA], "largo": [SEMILLA, *SEMILLAS_EXTRA]}

# Espacio de búsqueda, igual para las tres redes y los tres horizontes (D22). Incluye redes
# pequeñas y muy reguladas, para comprobar H8
ESPACIO_FASE_B = {
    "unidades": (8, 128),     # neuronas por capa (escala logarítmica)
    "capas": (1, 2),
    "dropout": (0.0, 0.5),
    "lr": (1e-4, 3e-3),       # velocidad de aprendizaje (escala logarítmica)
    "l2": (1e-6, 1e-2),       # fuerza de la regularización L2, si se usa (escala logarítmica)
    "lote": [32, 64, 128],
}

# Poda: un intento que va peor que la mediana de los anteriores en el mismo pliegue se abandona.
# Nunca en los primeros intentos ni tras el primer pliegue, que solo es un año
PODA_FASE_B = {"intentos_sin_poda": 10, "pliegues_sin_poda": 1}

# Núcleos de CPU para entrenar (de 8): deja margen para que el portátil vaya más fresco
HILOS_CPU = 6
