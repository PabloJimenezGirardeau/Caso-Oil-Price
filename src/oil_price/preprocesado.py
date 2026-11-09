"""Del dato limpio a las fichas que entran en la red (decisiones D4 a D9 del diario).

Flujo:
    tabla limpia ──► preparar_base() ──► Base: entradas, objetivos y fechas de los objetivos
    Base ──► construir_particion() ──► fichas de train y de evaluación. El recorte y el
             escalado se ajustan SOLO con el train (sin fuga de información).

Una «ficha» es una ventana de N días de entradas que acaba en el día de origen t, con
su respuesta: la variación logarítmica del Brent entre t y t + h sesiones.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config


# --- Entradas y objetivos ---------------------------------------------------------

def calcular_entradas(limpio, dias_vol=config.DIAS_VOLATILIDAD, dias_media=config.DIAS_MEDIA):
    """Variables de entrada de cada día t, calculadas solo con información hasta t.

    - r_<variable>: variación logarítmica diaria de cada variable (D4, D5).
    - log_vol_brent: log de la volatilidad anualizada del Brent en los últimos `dias_vol` días,
      calculada con las variaciones reales, antes de cualquier recorte (D5, D8).
    - nivel_brent: log del precio frente a su media de los últimos `dias_media` días (D5).
    """
    entradas = np.log(limpio).diff().add_prefix("r_")
    volatilidad = entradas["r_brent"].rolling(dias_vol).std() * np.sqrt(252)
    entradas["log_vol_brent"] = np.log(volatilidad)
    entradas["nivel_brent"] = np.log(limpio["brent"] / limpio["brent"].rolling(dias_media).mean())
    return entradas


@dataclass
class Base:
    """Datos diarios ya transformados, alineados en las mismas fechas."""
    entradas: pd.DataFrame         # variables de entrada (sin recortar ni escalar)
    objetivos: pd.DataFrame        # variación log del Brent entre t y t + h (NaN si t + h no existe)
    fechas_objetivo: pd.DataFrame  # fecha t + h en la que se conoce cada objetivo
    precio: pd.Series              # precio del Brent en t ($/barril)


def preparar_base(limpio, horizontes=config.HORIZONTES, con_nivel=True):
    """Calcula entradas y objetivos.

    Los primeros `DIAS_MEDIA` días sirven solo para calentar los indicadores y se descartan,
    también cuando `con_nivel=False`, para que las dos variantes usen exactamente los
    mismos días.
    """
    entradas = calcular_entradas(limpio).dropna()
    if not con_nivel:
        entradas = entradas.drop(columns="nivel_brent")

    log_precio = np.log(limpio[config.OBJETIVO])
    calendario = pd.Series(limpio.index, index=limpio.index)
    objetivos = pd.DataFrame({n: log_precio.shift(-h) - log_precio for n, h in horizontes.items()})
    fechas_objetivo = pd.DataFrame({n: calendario.shift(-h) for n, h in horizontes.items()})

    dias = entradas.index
    return Base(entradas, objetivos.loc[dias], fechas_objetivo.loc[dias],
                limpio[config.OBJETIVO].loc[dias])


# --- Recorte y escalado (ajustados solo con train) --------------------------------------

class Preparador:
    """Recorta las entradas entre dos percentiles y las estandariza (media 0, desviación 1).

    Los percentiles, medias y desviaciones se calculan en `ajustar()` con las entradas de
    train y después se aplican tal cual a cualquier periodo (D9).

    Por defecto solo se recortan las variaciones diarias (columnas `r_*`), que tienen picos
    aislados. Los indicadores de volatilidad y nivel no se recortan: son suaves y son la
    «alarma de tormenta». Si se recortaran, en 2020 la volatilidad se quedaría fija en el
    máximo del train durante meses (ver notebook 02, sección 4).
    """

    def __init__(self, recorte=(1.0, 99.0), solo_variaciones=True):
        self.recorte = recorte
        self.solo_variaciones = solo_variaciones

    def ajustar(self, entradas_train):
        self.fecha_max_ = entradas_train.index.max()
        self.columnas_recorte_ = [c for c in entradas_train.columns
                                  if c.startswith("r_") or not self.solo_variaciones]
        if self.recorte is None:
            self.inferior_ = self.superior_ = None
        else:
            seleccion = entradas_train[self.columnas_recorte_]
            self.inferior_ = seleccion.quantile(self.recorte[0] / 100)
            self.superior_ = seleccion.quantile(self.recorte[1] / 100)
        recortadas = self.recortar(entradas_train)
        self.media_ = recortadas.mean()
        self.desviacion_ = recortadas.std()
        return self

    def recortar(self, entradas):
        if self.recorte is None:
            return entradas
        resultado = entradas.copy()
        resultado[self.columnas_recorte_] = entradas[self.columnas_recorte_].clip(
            lower=self.inferior_, upper=self.superior_, axis=1)
        return resultado

    def transformar(self, entradas):
        return (self.recortar(entradas) - self.media_) / self.desviacion_


# --- Fichas (ventanas) -------------------------------------------------------------------

@dataclass
class Conjunto:
    """Fichas listas para la red.

    X: (muestras, ventana, variables). Y: (muestras, horizontes), NaN si el objetivo cae
    después de `limite_objetivo` (purgado para no mirar el bloque siguiente).
    """
    nombre: str
    X: np.ndarray
    Y: np.ndarray
    fechas: pd.DatetimeIndex                 # día de origen t (último día de la ventana)
    fechas_inicio_ventana: pd.DatetimeIndex  # primer día de la ventana
    fechas_objetivo: np.ndarray              # (muestras, horizontes), NaT si está purgado
    precio_origen: np.ndarray                # precio del Brent en t, para volver a $/barril
    horizontes: list
    variables: list
    limite_objetivo: pd.Timestamp

    def __len__(self):
        return len(self.fechas)

    def resumen(self):
        validos = (~np.isnan(self.Y)).sum(axis=0)
        return {"fichas": len(self),
                "desde": self.fechas.min().date() if len(self) else None,
                "hasta": self.fechas.max().date() if len(self) else None,
                **{f"objetivos {h}": int(n) for h, n in zip(self.horizontes, validos)}}


def crear_conjunto(nombre, base, escaladas, ventana, desde, hasta, limite_objetivo):
    """Fichas con origen entre `desde` y `hasta`, usando los `ventana` días que acaban en el origen.

    La ventana puede incluir días anteriores a `desde` (es pasado). Los objetivos cuya fecha
    supera `limite_objetivo` se dejan como NaN (purga).
    """
    fechas = escaladas.index
    pos = np.flatnonzero((fechas >= desde) & (fechas <= hasta))
    pos = pos[pos >= ventana - 1]

    valores = escaladas.to_numpy(dtype=np.float32)
    vistas = np.lib.stride_tricks.sliding_window_view(valores, ventana, axis=0)
    X = np.ascontiguousarray(vistas[pos - ventana + 1].transpose(0, 2, 1))

    fechas_obj = base.fechas_objetivo.iloc[pos]
    validos = fechas_obj <= limite_objetivo
    Y = base.objetivos.iloc[pos].where(validos).to_numpy(dtype=np.float32)

    return Conjunto(nombre=nombre, X=X, Y=Y, fechas=fechas[pos],
                    fechas_inicio_ventana=fechas[pos - ventana + 1],
                    fechas_objetivo=fechas_obj.where(validos).to_numpy(),
                    precio_origen=base.precio.iloc[pos].to_numpy(),
                    horizontes=list(base.objetivos.columns), variables=list(escaladas.columns),
                    limite_objetivo=pd.Timestamp(limite_objetivo))


def por_horizonte(conjunto, horizonte):
    """Fichas de un solo horizonte, para una red por horizonte (D18).

    Se quedan solo las fichas con respuesta válida para ese horizonte: por ejemplo, a 252
    sesiones se descartan las del último año de cada bloque, que no tienen respuesta.
    """
    j = conjunto.horizontes.index(horizonte)
    validas = ~np.isnan(conjunto.Y[:, j])
    return Conjunto(nombre=f"{conjunto.nombre} · {horizonte}", X=conjunto.X[validas],
                    Y=conjunto.Y[validas, j:j + 1], fechas=conjunto.fechas[validas],
                    fechas_inicio_ventana=conjunto.fechas_inicio_ventana[validas],
                    fechas_objetivo=conjunto.fechas_objetivo[validas, j:j + 1],
                    precio_origen=conjunto.precio_origen[validas], horizontes=[horizonte],
                    variables=conjunto.variables, limite_objetivo=conjunto.limite_objetivo)


# --- Particiones -------------------------------------------------------------------------

def pliegues_walk_forward(particion=config.PARTICION):
    """Pliegues anuales dentro de la validación (D7).

    Cada pliegue entrena con todo lo anterior al año que valida. Los objetivos de validación
    pueden caer en años posteriores, pero nunca después del fin de la validación.
    """
    fin_train, fin_val = particion["fin_train"], particion["fin_validacion"]
    return [dict(nombre=f"pliegue {i} (valida {año})",
                 fin_train=pd.Timestamp(año - 1, 12, 31),
                 desde=pd.Timestamp(año, 1, 1), hasta=pd.Timestamp(año, 12, 31),
                 limite_objetivo=fin_val)
            for i, año in enumerate(range(fin_train.year + 1, fin_val.year + 1), start=1)]


def evaluacion_final(particion=config.PARTICION, corte=config.FECHA_CORTE):
    """Entrenamiento con train + validación y evaluación en test (D7)."""
    fin_val = particion["fin_validacion"]
    return dict(nombre="test", fin_train=fin_val, desde=fin_val + pd.Timedelta(days=1),
                hasta=corte, limite_objetivo=corte)


def construir_particion(base, ventana, recorte, fin_train, desde, hasta, limite_objetivo,
                        nombre="evaluación"):
    """Ajusta el preparador SOLO con el train y crea las fichas de train y de evaluación.

    El train son los orígenes hasta `fin_train` cuyos objetivos también acaban antes de
    `fin_train` (purga).
    """
    preparador = Preparador(recorte).ajustar(base.entradas.loc[:fin_train])
    escaladas = preparador.transformar(base.entradas)
    train = crear_conjunto("train", base, escaladas, ventana,
                           desde=base.entradas.index[0], hasta=fin_train, limite_objetivo=fin_train)
    evaluacion = crear_conjunto(nombre, base, escaladas, ventana, desde, hasta, limite_objetivo)
    return train, evaluacion, preparador
