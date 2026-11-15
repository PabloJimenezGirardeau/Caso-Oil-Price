"""Comprobaciones automáticas de los datos y de las fichas.

Un error de fuga de información no hace fallar el código: solo da resultados demasiado
buenos. Estas funciones lo detectan y lanzan un error si algo no cuadra. Devuelven una
tabla con cada comprobación para mostrarla en los notebooks.
"""
import numpy as np
import pandas as pd


class ErrorDeValidacion(Exception):
    pass


def _resultado(titulo, comprobaciones):
    tabla = pd.DataFrame(comprobaciones, columns=["comprobación", "ok"])
    fallos = tabla.loc[~tabla["ok"], "comprobación"].tolist()
    if fallos:
        raise ErrorDeValidacion(f"{titulo}: fallan {fallos}")
    return tabla.assign(conjunto=titulo)[["conjunto", "comprobación", "ok"]]


def comprobar_limpio(limpio, dias_brent):
    valores = limpio.to_numpy()
    return _resultado("datos limpios", [
        ("sin huecos", not limpio.isna().any().any()),
        ("sin infinitos", bool(np.isfinite(valores).all())),
        ("todos los precios > 0", bool((valores > 0).all())),
        ("fechas en orden y sin duplicados",
         limpio.index.is_monotonic_increasing and not limpio.index.has_duplicates),
        ("solo días reales del Brent", bool(limpio.index.isin(dias_brent).all())),
    ])


def comprobar_conjunto(c):
    fechas_obj = pd.DataFrame(c.fechas_objetivo, columns=c.horizontes)
    hay_objetivo = fechas_obj.notna()
    origen = pd.Series(c.fechas)
    posterior = fechas_obj.gt(origen, axis=0) | ~hay_objetivo
    dentro_limite = (fechas_obj <= c.limite_objetivo) | ~hay_objetivo
    return _resultado(c.nombre, [
        ("entradas sin huecos ni infinitos", bool(np.isfinite(c.X).all())),
        ("objetivos válidos finitos", bool(np.isfinite(c.Y[~np.isnan(c.Y)]).all())),
        ("objetivo NaN ⇔ fecha de objetivo vacía", bool((np.isnan(c.Y) == ~hay_objetivo.to_numpy()).all())),
        ("la ventana acaba en el origen", bool((c.fechas_inicio_ventana <= c.fechas).all())),
        ("cada objetivo es posterior a su ficha", bool(posterior.to_numpy().all())),
        ("ningún objetivo pasa del límite del bloque", bool(dentro_limite.to_numpy().all())),
    ])


def comprobar_sin_fuga(train, evaluacion, preparador):
    objetivos_train = pd.DataFrame(train.fechas_objetivo).stack()
    ultimo_objetivo_train = objetivos_train.max() if len(objetivos_train) else pd.Timestamp.min
    return _resultado(f"{train.nombre} → {evaluacion.nombre}", [
        ("recorte y escalado ajustados solo con train", preparador.fecha_max_ <= train.limite_objetivo),
        ("las fichas de train son anteriores a las de evaluación", train.fechas.max() < evaluacion.fechas.min()),
        ("ninguna respuesta de train cae en el periodo de evaluación",
         ultimo_objetivo_train < evaluacion.fechas.min()),
    ])
