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


def errores(conjunto, prediccion=None):
    """Error en $/barril de cada ficha y horizonte, en formato largo (una fila por ficha y horizonte).

    Sirve para juntar varios pliegues antes de calcular las métricas: así cada ficha pesa
    lo mismo, en lugar de promediar métricas de pliegues de distinto tamaño.
    """
    if prediccion is None:
        prediccion = np.zeros_like(conjunto.Y)
    tablas = []
    for j, horizonte in enumerate(conjunto.horizontes):
        ok = ~np.isnan(conjunto.Y[:, j])
        precio = conjunto.precio_origen[ok]
        tablas.append(pd.DataFrame({
            "fecha": conjunto.fechas[ok], "horizonte": horizonte,
            "variación real": conjunto.Y[ok, j], "variación prevista": prediccion[ok, j],
            "precio real": precio * np.exp(conjunto.Y[ok, j]),
            "precio previsto": precio * np.exp(prediccion[ok, j]),
        }))
    tabla = pd.concat(tablas, ignore_index=True)
    tabla["error"] = tabla["precio previsto"] - tabla["precio real"]
    return tabla


def comparar_con_ingenuo(errores_modelo, errores_ingenuo):
    """MAE y RMSE del modelo y del ingenuo por horizonte, y su cociente (< 1 = mejora al ingenuo)."""
    def resumir(tabla):
        return tabla.groupby("horizonte", sort=False)["error"].agg(
            MAE=lambda e: e.abs().mean(), RMSE=lambda e: np.sqrt((e ** 2).mean()), muestras="size")
    modelo, ingenuo = resumir(errores_modelo), resumir(errores_ingenuo)
    return pd.DataFrame({
        "muestras": modelo["muestras"],
        "MAE": modelo["MAE"], "MAE ingenuo": ingenuo["MAE"],
        "RMSE": modelo["RMSE"], "RMSE ingenuo": ingenuo["RMSE"],
        "MAE / ingenuo": modelo["MAE"] / ingenuo["MAE"],
        "mejora frente al ingenuo (%)": (1 - modelo["MAE"] / ingenuo["MAE"]) * 100,
    })


def puntuacion(comparacion):
    """Criterio de selección (D16): media de «MAE / ingenuo» en los horizontes. Menor es mejor."""
    return float(comparacion["MAE / ingenuo"].mean())
