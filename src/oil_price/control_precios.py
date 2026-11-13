"""Experimento de control con precios (D15, H4): la RNN elegida, entrenada para prever el precio.

Todo igual que la red de siempre (configuración de la fase B, ventana, recorte, escalado ajustado
solo con el train, purga, pérdida, parada temprana, semillas 42-46 y validación 2018-2021), salvo que:
- las entradas son las mismas variables en nivel (el precio de cada una en lugar de su variación
  diaria; la volatilidad y el resto, igual);
- el objetivo es el precio del Brent en t + h, centrado y escalado con el train, como es habitual.

Comprueba H4: una red entrenada con precios tiende a copiar el precio de hoy, y parece que acierta
(el «espejismo») porque el precio de hoy se parece mucho al de dentro de unos días.
"""
import numpy as np
import pandas as pd

from . import busqueda as bu, config, datos, entrenamiento as ent, estabilidad as es, experimentos as ex
from . import hacia_atras as ha, preprocesado as pp

HORIZONTES = ["corto", "medio"]
RED = "RNN"
NOMBRE = "RNN con precios"
ARCHIVO = "control_precios.csv"
COLUMNAS = ["horizonte", "modelo", "pliegue", "semilla", "fecha", "fecha objetivo", "precio previsto",
            "variación real", "precio origen", "épocas", "segundos"]


def base_precio(limpio, con_nivel=False):
    """La base de siempre con las variables en nivel en lugar de su variación diaria, y como
    objetivo el precio del Brent en t + h (no su variación)."""
    base = pp.preparar_base(limpio, con_nivel=con_nivel)
    entradas = base.entradas.copy()
    variaciones = [c for c in entradas.columns if c.startswith("r_")]
    for c in variaciones:
        entradas[c] = limpio[c[2:]].loc[entradas.index]
    entradas = entradas.rename(columns={c: c[2:] for c in variaciones})
    precio = limpio[config.OBJETIVO]
    objetivos = pd.DataFrame({n: precio.shift(-h) for n, h in config.HORIZONTES.items()}).loc[entradas.index]
    return pp.Base(entradas, objetivos, base.fechas_objetivo, base.precio)


def pliegues(h, limpio=None):
    """(año, train, evaluado) de la validación 2018-2021, con las fichas de precios."""
    comb = bu.combinacion(h)
    limpio = limpio if limpio is not None else datos.cargar_datos_limpios()
    return bu._pliegues({comb["nivel"]: base_precio(limpio, comb["nivel"])}, comb)


def _hechos(ruta):
    if not ruta.exists():
        return set()
    t = pd.read_csv(ruta, usecols=["horizonte", "pliegue", "semilla"])
    return set(zip(t["horizonte"], t["pliegue"], t["semilla"]))


def ejecutar(dir_salida=config.DIR_RESULTADOS, horizontes=None, semillas=None, registrar=print):
    """Entrena y guarda la previsión de cada ficha, en cuanto termina cada entrenamiento (reanudable)."""
    horizontes = horizontes or HORIZONTES
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    ruta = dir_salida / ARCHIVO
    hechos, eleg, limpio = _hechos(ruta), es.elegidas(dir_salida), datos.cargar_datos_limpios()
    dispositivo = ent.dispositivo_disponible()
    for h in horizontes:
        intento, params = eleg[(h, RED)]
        for año, train, evaluado in pliegues(h, limpio):
            for semilla in semillas:
                if (h, año, semilla) in hechos:
                    continue
                r = ent.entrenar_red(RED, train, bu.hiperparametros(params), semilla=semilla,
                                     dispositivo=dispositivo, ajustes={"sin_tendencia": True})
                # La red prevé el precio centrado: se le vuelve a sumar la media del train
                previsto = ent.predecir(r, evaluado.X)[:, 0] + r.tendencia[0]
                tabla = pd.DataFrame({
                    "horizonte": h, "modelo": NOMBRE, "pliegue": año, "semilla": semilla,
                    "fecha": pd.DatetimeIndex(evaluado.fechas),
                    "fecha objetivo": pd.DatetimeIndex(evaluado.fechas_objetivo[:, 0]),
                    "precio previsto": previsto,
                    "variación real": np.log(evaluado.Y[:, 0] / evaluado.precio_origen),
                    "precio origen": evaluado.precio_origen, "épocas": len(r.historial), "segundos": r.segundos})
                es._anadir_compacto(ruta, tabla, COLUMNAS)
                registrar(f"[{h} {NOMBRE}] {año} semilla {semilla} · {len(r.historial)} épocas · {r.segundos:.0f} s")


def leer(dir_salida=config.DIR_RESULTADOS):
    """Previsiones guardadas, con el precio previsto promediado entre semillas y su variación prevista
    (formato de `hacia_atras.COLUMNAS`, más la fecha objetivo y el precio previsto)."""
    p = pd.read_csv(dir_salida / ARCHIVO, parse_dates=["fecha", "fecha objetivo"])
    claves = ["horizonte", "modelo", "pliegue", "fecha", "fecha objetivo"]
    m = p.groupby(claves, sort=False).agg(**{"precio previsto": ("precio previsto", "mean"),
                                             "variación real": ("variación real", "first"),
                                             "precio origen": ("precio origen", "first")}).reset_index()
    m["variación prevista"] = np.log(m["precio previsto"].clip(lower=0.01) / m["precio origen"])
    return m


def _correlacion(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else np.nan


def espejismo(previsiones):
    """Por horizonte y modelo: la nota, cuánto se parece la previsión al precio futuro (correlación
    de niveles), su error frente al precio futuro y frente al precio de hoy, y la correlación entre
    el cambio previsto y el real."""
    p = previsiones.assign(**{"precio previsto": previsiones["precio origen"] * np.exp(previsiones["variación prevista"]),
                              "precio real": previsiones["precio origen"] * np.exp(previsiones["variación real"])})
    filas = {}
    for (h, m), g in p.groupby(["horizonte", "modelo"], sort=False):
        nota = ha.nota_juntos(ha.sumas_por_año(g)).iloc[0]
        cambio_previsto, cambio_real = g["precio previsto"] - g["precio origen"], g["precio real"] - g["precio origen"]
        filas[(h, m)] = {
            "nota (MAE / ingenuo)": nota,
            "correlación de niveles": _correlacion(g["precio previsto"], g["precio real"]),
            "error frente al precio futuro ($)": (g["precio previsto"] - g["precio real"]).abs().mean(),
            "error frente al precio de hoy ($)": (g["precio previsto"] - g["precio origen"]).abs().mean(),
            "correlación de los cambios": _correlacion(cambio_previsto, cambio_real)}
    t = pd.DataFrame(filas).T
    t.index.names = ["horizonte", "modelo"]
    return t
