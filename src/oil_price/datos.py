"""Carga y limpieza de los datos (decisiones D3, D5, D12 y D13 del diario).

El CSV original (data/petroleo_dataset.csv) es de solo lectura: aquí nunca se modifica.
"""
import pandas as pd

from . import config


def cargar_dataset(ruta=config.RUTA_DATASET):
    """CSV de datos tal como lo genera scripts/download_data.py."""
    return pd.read_csv(ruta, parse_dates=["Date"], index_col="Date")


def cargar_dias_brent(ruta=config.RUTA_DIAS_BRENT):
    """Días en que el Brent cotizó de verdad (generados con scripts/generar_dias_brent.py)."""
    return pd.DatetimeIndex(pd.read_csv(ruta, parse_dates=["Date"])["Date"])


def valores_no_positivos(datos, variables=config.VARIABLES):
    """Precios <= 0 (no admiten logaritmo). En la práctica, el WTI del 20/04/2020."""
    tabla = datos[variables]
    return tabla.where(tabla <= 0).stack().dropna()


def limpiar(datos, dias_brent, inicio=config.FECHA_INICIO, corte=config.FECHA_CORTE,
            variables=config.VARIABLES):
    """Tabla diaria limpia, lista para calcular variaciones.

    1. Solo los días en que cotizó el Brent: fuera los festivos rellenados por la descarga (D3).
    2. Solo el periodo de estudio [inicio, corte] y las variables elegidas (D5, D12).
    3. Los precios no positivos se sustituyen por el último valor válido (D5).
    """
    limpio = datos.loc[datos.index.isin(dias_brent), variables]
    limpio = limpio.loc[inicio:corte]
    return limpio.mask(limpio <= 0).ffill()


def cargar_datos_limpios():
    """Atajo: carga el CSV y el calendario del Brent y devuelve la tabla limpia."""
    return limpiar(cargar_dataset(), cargar_dias_brent())
