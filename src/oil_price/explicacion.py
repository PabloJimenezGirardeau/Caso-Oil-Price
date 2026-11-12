"""Qué ve cada modelo: qué variables y qué situaciones mueven su previsión.

Solo análisis, en validación: no elige nada.

- **Lineal:** su previsión es una suma de aportaciones, una por variable y día de la ventana, así
  que se reparte exactamente entre las variables (`aportaciones_lineal`). Además se reajusta sin
  cada variable y con solo ella (`quitar_variables_lineal`).
- **Redes** (promedio de 5 semillas, como en D27): no se pueden repartir así. Se mide cuánto
  empeoran si se desordena una variable entre fichas (`importancia_y_efectos`): si la red no la
  usa, desordenarla no cambia nada. Hay que reentrenarlas (unos minutos), así que lo hace
  `scripts/importancia.py`, que guarda en `resultados/importancia.csv` y `resultados/efectos.csv`.
- **Situaciones típicas** (los dos modelos): cuánto cambia la previsión, de media, si la
  volatilidad del Brent fuese el doble o la mitad, o si el Brent y el WTI estuvieran un 10 % más
  abajo que hace un mes.
"""
import dataclasses
import time

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, combinacion as co, config, entrenamiento as ent, estabilidad as es
from . import experimentos as ex, preprocesado as pp
from .modelos import ModeloLineal

NOMBRES = {"r_brent": "Brent", "r_wti": "WTI", "r_cobre": "cobre", "r_oro": "oro", "r_indice_dolar": "dólar",
           "r_vix": "VIX", "log_vol_brent": "volatilidad Brent", "nivel_brent": "nivel Brent"}
DIAS_MES = 20
ESCENARIOS = {"volatilidad ×2": ("log_vol_brent", np.log(2.0)),
              "volatilidad ×0,5": ("log_vol_brent", np.log(0.5)),
              "Brent y WTI −10 % en un mes": (("r_brent", "r_wti"), np.log(0.9))}
ARCHIVOS = {"importancia": "importancia.csv", "efectos": "efectos.csv"}


# --- Piezas comunes ------------------------------------------------------------------------

def nota_conjunta(trozos):
    """«MAE / ingenuo» juntando las fichas de todos los años. `trozos`: [(previsión, evaluado)]."""
    error, ingenuo = [], []
    for prevision, evaluado in trozos:
        real = evaluado.precio_origen * np.exp(evaluado.Y[:, 0])
        error.append(np.abs(evaluado.precio_origen * np.exp(prevision) - real))
        ingenuo.append(np.abs(evaluado.precio_origen - real))
    return float(np.concatenate(error).mean() / np.concatenate(ingenuo).mean())


def _pliegues(horizonte, bases):
    """(año, train, evaluado, preparador) de cada año de validación, como en la fase B."""
    comb = bu.combinacion(horizonte)
    salida = []
    for año, train, evaluado in bu._pliegues(bases, comb):
        fin_train = pd.Timestamp(año - 1, 12, 31)
        preparador = pp.Preparador(comb["recorte"]).ajustar(bases[comb["nivel"]].entradas.loc[:fin_train])
        salida.append((año, train, evaluado, preparador))
    return salida


def _solo(conjunto, columnas):
    return dataclasses.replace(conjunto, X=conjunto.X[:, :, columnas])


def desordenar(X, columna, rng):
    """Copia de X con una variable (toda su ventana) cambiada de ficha al azar; el resto, igual."""
    salida = X.copy()
    salida[:, :, columna] = X[rng.permutation(len(X)), :, columna]
    return salida


def desplazar(X, cambios, ultimos=None):
    """Copia de X con cambios en unidades escaladas: {columna: cantidad por día}. Con `ultimos`,
    solo en los últimos días de la ventana."""
    salida = X.copy()
    desde = 0 if ultimos is None else max(X.shape[1] - ultimos, 0)
    for columna, cantidad in cambios.items():
        salida[:, desde:, columna] += cantidad
    return salida


def cambios_escenario(nombre, variables, preparador, ventana):
    """Cambios de un escenario en unidades escaladas, y desde qué días se aplican."""
    columnas, total = ESCENARIOS[nombre]
    if isinstance(columnas, str):   # un nivel: el mismo cambio todos los días de la ventana
        return {variables.index(columnas): total / preparador.desviacion_[columnas]}, None
    dias = min(DIAS_MES, ventana)   # variaciones diarias: la caída se reparte en el último mes
    return {variables.index(c): total / dias / preparador.desviacion_[c] for c in columnas}, dias


def _efecto_medio(prevision_base, prevision_escenario):
    """Cambio medio de la previsión, en % de variación del precio."""
    return float(100 * np.expm1(np.mean(prevision_escenario - prevision_base)))


# --- Lineal ----------------------------------------------------------------------------------

def _lineal(horizonte, train, columnas=None):
    alfa, _ = co.alfa_lineal(horizonte)
    return ModeloLineal(alfa, sin_tendencia=True).ajustar(train if columnas is None else _solo(train, columnas))


def aportaciones(lineal, X):
    """Aportación de cada variable (suma de sus días) a la previsión del lineal en cada ficha.
    Suman exactamente la previsión."""
    n, ventana, variables = X.shape
    coef = lineal.coef_[0].reshape(ventana, variables)
    media = lineal.media_x_[0].reshape(ventana, variables)
    return ((X.astype(np.float64) - media) * coef).sum(axis=1)


def aportaciones_lineal(horizonte, bases=None):
    """Aportación de cada variable a la previsión del lineal de referencia, ficha a ficha."""
    bases = bases if bases is not None else ex._bases()
    tablas = []
    for año, train, evaluado, _ in _pliegues(horizonte, bases):
        a = aportaciones(_lineal(horizonte, train), evaluado.X)
        t = pd.DataFrame(a, columns=[NOMBRES[v] for v in evaluado.variables])
        tablas.append(t.assign(horizonte=horizonte, pliegue=año, fecha=evaluado.fechas, previsión=a.sum(axis=1)))
    return pd.concat(tablas, ignore_index=True)


def peso_variables(aport):
    """Cuánto mueve cada variable la previsión (desviación típica de su aportación), en % del total,
    y su correlación con la previsión."""
    variables = [c for c in aport.columns if c in NOMBRES.values()]
    desv = aport[variables].std()
    return pd.DataFrame({"% de lo que mueve la previsión": 100 * desv / desv.sum(),
                         "correlación con la previsión": aport[variables].corrwith(aport["previsión"])}
                        ).sort_values("% de lo que mueve la previsión", ascending=False)


def nota_lineal(horizonte, variables=None, bases=None, pliegues=None):
    """Nota del lineal de referencia (misma regularización) con solo esas variables, por año y con
    los años juntos. Sin `variables`, con todas."""
    if pliegues is None:
        pliegues = _pliegues(horizonte, bases if bases is not None else ex._bases())
    trozos, por_año = [], {}
    for año, train, evaluado, _ in pliegues:
        columnas = None if variables is None else [evaluado.variables.index(v) for v in variables]
        lineal = _lineal(horizonte, train, columnas)
        prevision = lineal.predecir(evaluado.X if columnas is None else evaluado.X[:, :, columnas])[:, 0]
        trozos.append((prevision, evaluado))
        por_año[str(año)] = nota_conjunta([(prevision, evaluado)])
    return pd.Series({**por_año, "años juntos": nota_conjunta(trozos)})


def quitar_variables_lineal(horizonte, bases=None):
    """Nota del lineal (años juntos) con todas las variables, sin cada una y con solo ella."""
    pliegues = _pliegues(horizonte, bases if bases is not None else ex._bases())
    variables = pliegues[0][1].variables
    todas = nota_lineal(horizonte, pliegues=pliegues)["años juntos"]
    filas = {"todas": {"sin ella": todas, "solo ella": todas}}
    for v in variables:
        resto = [w for w in variables if w != v]
        filas[NOMBRES[v]] = {"sin ella": nota_lineal(horizonte, resto, pliegues=pliegues)["años juntos"],
                             "solo ella": nota_lineal(horizonte, [v], pliegues=pliegues)["años juntos"]}
    return pd.DataFrame(filas).T


# --- Redes y lineal: desorden y escenarios ------------------------------------------------------

def importancia_y_efectos(horizontes=("medio", "largo"), semillas=None, repeticiones=5, hilos=config.HILOS_CPU,
                          registrar=print, bases=None):
    """Reentrena las redes elegidas (con las semillas dadas, por defecto 42-46) y mide, para su
    promedio y para el lineal:
    - cuánto empeora la nota al desordenar cada variable (media de `repeticiones` desórdenes);
    - cuánto cambia de media la previsión en cada escenario.
    Devuelve (importancia, efectos)."""
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    torch.set_num_threads(hilos)
    dispositivo = ent.dispositivo_disponible()
    bases = bases if bases is not None else ex._bases()
    eleg = es.elegidas()
    importancia, efectos = [], []
    inicio = time.perf_counter()
    for h in horizontes:
        pliegues = _pliegues(h, bases)
        variables = pliegues[0][1].variables
        modelos = [*config.CELDAS, "Lineal"]
        base = {m: [] for m in modelos}                                    # [(previsión, evaluado)]
        desorden = {(m, v, r): [] for m in modelos for v in variables for r in range(repeticiones)}
        escenario = {(m, e): [] for m in modelos for e in ESCENARIOS}
        for año, train, evaluado, preparador in pliegues:
            predictores = {"Lineal": [lambda X, lin=_lineal(h, train): lin.predecir(X)[:, 0]]}
            for celda in config.CELDAS:
                _, params = eleg[(h, celda)]
                predictores[celda] = []
                for s in semillas:
                    resultado = ent.entrenar_red(celda, train, bu.hiperparametros(params), semilla=s,
                                                 dispositivo=dispositivo, ajustes={"sin_tendencia": True})
                    predictores[celda].append(lambda X, r=resultado: ent.predecir(r, X)[:, 0])
                registrar(f"{h} {año} {celda}: {len(semillas)} semillas entrenadas "
                          f"({(time.perf_counter() - inicio) / 60:.1f} min)")

            def prever(modelo, X):   # promedio de semillas: media de los precios previstos
                return np.log(np.mean([np.exp(f(X)) for f in predictores[modelo]], axis=0))

            for m in modelos:
                p0 = prever(m, evaluado.X)
                base[m].append((p0, evaluado))
                for i, v in enumerate(variables):
                    rng = np.random.default_rng(1000 * año + i)   # el mismo desorden para todos los modelos
                    for r in range(repeticiones):
                        desorden[(m, v, r)].append((prever(m, desordenar(evaluado.X, i, rng)), evaluado))
                for e in ESCENARIOS:
                    cambios, ultimos = cambios_escenario(e, variables, preparador, evaluado.X.shape[1])
                    pe = prever(m, desplazar(evaluado.X, cambios, ultimos))
                    escenario[(m, e)].append((p0, pe))
        for m in modelos:
            nota_base = nota_conjunta(base[m])
            for v in variables:
                desordenada = np.mean([nota_conjunta(desorden[(m, v, r)]) for r in range(repeticiones)])
                importancia.append({"horizonte": h, "modelo": m, "variable": NOMBRES[v], "nota": nota_base,
                                    "nota desordenada": desordenada, "pérdida": desordenada - nota_base})
            for e in ESCENARIOS:
                p0 = np.concatenate([a for a, _ in escenario[(m, e)]])
                pe = np.concatenate([b for _, b in escenario[(m, e)]])
                efectos.append({"horizonte": h, "modelo": m, "escenario": e,
                                "cambio medio de la previsión (%)": _efecto_medio(p0, pe)})
        registrar(f"{h}: hecho ({(time.perf_counter() - inicio) / 60:.1f} min)")
    return pd.DataFrame(importancia), pd.DataFrame(efectos)


def leer(dir_salida=config.DIR_RESULTADOS):
    """(importancia, efectos) guardados por `scripts/importancia.py`."""
    return tuple(pd.read_csv(dir_salida / ARCHIVOS[k]) for k in ("importancia", "efectos"))
