"""Controles del procedimiento: negativo (sin señal) y positivo (señal plantada), con el lineal.

Comprueban el procedimiento entero (fichas, purga, escalado, entrenamiento, evaluación y el
criterio de D29) con el lineal de referencia, que tarda segundos: los mismos años de la
validación hacia atrás y la validación (2010-2021), los mismos datos y la misma regularización.

- Negativo: las respuestas del entrenamiento se desplazan en círculo un número de fichas al azar.
  Conservan cómo se mueve el precio, pero ya no corresponden a sus entradas: no hay nada que
  aprender, y el criterio no debería ver ventaja.
- Positivo: se añade a las entradas un «chivato», la respuesta verdadera más ruido, solo en el
  último día de la ventana. El ruido se fija para que el mejor previsor posible mejore al ingenuo
  en una cantidad conocida. Dice desde qué mejora el criterio la detecta.
"""
from dataclasses import replace

import numpy as np
import pandas as pd

from . import busqueda as bu, combinacion as co, config, experimentos as ex, hacia_atras as ha
from .modelos import ModeloLineal

MEJORAS = [0.01, 0.02, 0.04, 0.08, 0.16]   # mejora del mejor previsor con el chivato
REPETICIONES_NEGATIVO = 20
REPETICIONES_POSITIVO = 10
NOMBRE = "control"


def ruido_para(mejora):
    """Ruido del chivato (en desviaciones de la respuesta) con el que el mejor previsor lineal
    mejora al ingenuo en `mejora`. Con respuestas normales el error medio es proporcional a la
    desviación: 1 − mejora = √(1 − R²), y con el chivato R² = 1 / (1 + ruido²)."""
    r2 = 1 - (1 - mejora) ** 2
    return float(np.sqrt(1 / r2 - 1))


def pliegues_doce(bases, h):
    """(año, train, evaluado) de 2010-2021: hacia atrás (sin nada posterior a 2017) y validación."""
    comb = bu.combinacion(h)
    return ha.pliegues(bases, comb) + bu._pliegues(bases, comb)


def con_chivato(conjunto, chivato):
    """El conjunto con una variable más que solo vale en el último día de la ventana (el resto, 0)."""
    extra = np.zeros((*conjunto.X.shape[:2], 1), dtype=conjunto.X.dtype)
    extra[:, -1, 0] = chivato
    return replace(conjunto, X=np.concatenate([conjunto.X, extra], axis=2),
                   variables=[*conjunto.variables, "chivato"])


def desplazar(Y, rng, minimo):
    """Las respuestas válidas desplazadas en círculo entre `minimo` y n − `minimo` fichas."""
    validas = ~np.isnan(Y[:, 0])
    y = Y[validas, 0]
    nuevo = Y.copy()
    nuevo[validas, 0] = np.roll(y, int(rng.integers(minimo, len(y) - minimo)))
    return nuevo


def _previsiones(h, año, evaluado, prevista):
    return pd.DataFrame({"horizonte": h, "modelo": NOMBRE, "pliegue": año,
                         "fecha": pd.DatetimeIndex(evaluado.fechas), "variación prevista": prevista,
                         "variación real": evaluado.Y[:, 0], "precio origen": evaluado.precio_origen})


def negativo(h, pliegues, alfa, repeticion):
    """Previsiones del lineal entrenado con las respuestas desplazadas (al menos un año más el horizonte)."""
    rng = np.random.default_rng(repeticion)
    minimo = 252 + config.HORIZONTES[h]
    tablas = []
    for año, train, evaluado in pliegues:
        modelo = ModeloLineal(alfa, sin_tendencia=True).ajustar(replace(train, Y=desplazar(train.Y, rng, minimo)))
        tablas.append(_previsiones(h, año, evaluado, modelo.predecir(evaluado.X)[:, 0]))
    return pd.concat(tablas, ignore_index=True)


def positivo(h, pliegues, alfa, mejora, repeticion):
    """Previsiones del lineal con el chivato: respuesta + ruido, en la escala de las respuestas del
    train y llevado a desviación 1, como las demás entradas."""
    rng = np.random.default_rng(repeticion)
    ruido = ruido_para(mejora)
    tablas = []
    for año, train, evaluado in pliegues:
        escala = float(np.nanstd(train.Y[:, 0]))

        def chivato(c):
            y = np.nan_to_num(c.Y[:, 0])
            return (y + rng.normal(0, ruido * escala, len(y))) / (escala * np.sqrt(1 + ruido ** 2))

        modelo = ModeloLineal(alfa, sin_tendencia=True).ajustar(con_chivato(train, chivato(train)))
        tablas.append(_previsiones(h, año, evaluado, modelo.predecir(con_chivato(evaluado, chivato(evaluado)).X)[:, 0]))
    return pd.concat(tablas, ignore_index=True)


def medir(previsiones, h):
    """Nota con los años juntos, años que gana y veredicto con el criterio de D29."""
    c = ha.criterio(ha.sumas_por_año(previsiones), h, [NOMBRE])
    return {"nota": c["nota con los años juntos"], "años que gana": c["años que gana al ingenuo"],
            "años": c["años"], "veredicto": c["veredicto"]}


def ejecutar(horizontes=None, mejoras=MEJORAS, rep_negativo=REPETICIONES_NEGATIVO,
             rep_positivo=REPETICIONES_POSITIVO, bases=None, registrar=print):
    """Una fila por horizonte, control, mejora plantada y repetición."""
    horizontes = horizontes or list(config.HORIZONTES)
    bases = bases if bases is not None else ex._bases()
    filas = []
    for h in horizontes:
        alfa, _ = co.alfa_lineal(h)
        pliegues = pliegues_doce(bases, h)
        for r in range(rep_negativo):
            filas.append({"horizonte": h, "control": "negativo", "mejora plantada": 0.0, "repetición": r,
                          **medir(negativo(h, pliegues, alfa, r), h)})
        registrar(f"{h}: control negativo hecho ({rep_negativo} repeticiones)")
        for mejora in mejoras:
            for r in range(rep_positivo):
                filas.append({"horizonte": h, "control": "positivo", "mejora plantada": mejora, "repetición": r,
                              **medir(positivo(h, pliegues, alfa, mejora, r), h)})
            registrar(f"{h}: control positivo con mejora del {100 * mejora:.0f} % hecho")
    return pd.DataFrame(filas)


def resumen(filas):
    """Por horizonte, control y mejora plantada: nota media y su rango, mejora medida y en qué
    parte de las repeticiones sale cada veredicto."""
    g = filas.groupby(["horizonte", "control", "mejora plantada"], sort=False)
    t = g["nota"].agg(["mean", "min", "max"]).rename(columns={"mean": "nota media", "min": "nota mínima",
                                                              "max": "nota máxima"})
    t["mejora medida"] = 1 - t["nota media"]
    t["años que gana (media)"] = g["años que gana"].mean()
    veredictos = (filas.groupby(["horizonte", "control", "mejora plantada", "veredicto"], sort=False).size()
                  .unstack("veredicto", fill_value=0))
    veredictos = veredictos.reindex(columns=["real", "dudosa", "no se sostiene"], fill_value=0)
    return t.join(veredictos.div(veredictos.sum(axis=1), axis=0))
