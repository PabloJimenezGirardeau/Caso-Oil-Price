"""Métricas de evaluación (requisito 4 del enunciado)."""
import numpy as np
import pandas as pd


def metricas(conjunto, prediccion=None):
    """MSE, MAE y RMSE en $/barril y % de acierto de la dirección, por horizonte.

    `prediccion`: variaciones logarítmicas previstas, con forma (muestras, horizontes).
    Si es None, se evalúa el modelo ingenuo («el precio futuro = el precio de hoy»),
    que equivale a predecir una variación de 0.
    """
    ingenuo = prediccion is None
    if ingenuo:
        prediccion = np.zeros_like(conjunto.Y)

    filas = {}
    for j, horizonte in enumerate(conjunto.horizontes):
        ok = ~np.isnan(conjunto.Y[:, j])
        precio = conjunto.precio_origen[ok]
        real = precio * np.exp(conjunto.Y[ok, j])
        previsto = precio * np.exp(prediccion[ok, j])
        error = previsto - real
        mse = float(np.mean(error ** 2)) if ok.any() else np.nan
        direccion = (np.nan if ingenuo or not ok.any()   # el ingenuo no predice dirección
                     else float(np.mean(np.sign(prediccion[ok, j]) == np.sign(conjunto.Y[ok, j])) * 100))
        filas[horizonte] = {"muestras": int(ok.sum()), "MSE": mse,
                            "MAE": float(np.mean(np.abs(error))) if ok.any() else np.nan,
                            "RMSE": float(np.sqrt(mse)), "acierto dirección (%)": direccion}
    return pd.DataFrame(filas).T
