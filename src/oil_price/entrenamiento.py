"""Entrenamiento de las redes, igual para las tres (D9, D16).

- Pérdida Huber sobre objetivos escalados por horizonte (para que el largo plazo, con
  variaciones mucho mayores, no acapare el aprendizaje). Las respuestas purgadas (NaN) se
  ignoran.
- Adam, recorte de gradientes y reducción automática de la velocidad de aprendizaje.
- Parada temprana con el último trozo del train (con purga), nunca con el periodo que se
  evalúa. Se guarda la mejor versión de la red, no la última.
- Tendencia (D20): por defecto, la red aprende también la subida media del periodo de
  entrenamiento y la proyecta al futuro. Con `sin_tendencia`, aprende solo la variación
  respecto a esa media y, para el futuro, supone tendencia cero, como el ingenuo.
"""
import copy
import dataclasses
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from torch import nn

from . import config
from .modelos import RedRecurrente, contar_parametros


def fijar_semilla(semilla):
    np.random.seed(semilla)
    torch.manual_seed(semilla)


def dispositivo_disponible():
    """GPU si la hay (por ejemplo, en la universidad); si no, CPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# --- División para la parada temprana ----------------------------------------------------

def subconjunto(conjunto, mascara, limite_objetivo=None):
    """Fichas seleccionadas por `mascara`. Con `limite_objetivo`, se purgan las respuestas posteriores."""
    Y = conjunto.Y[mascara].copy()
    fechas_obj = conjunto.fechas_objetivo[mascara].copy()
    limite = conjunto.limite_objetivo
    if limite_objetivo is not None:
        limite = pd.Timestamp(limite_objetivo)
        fuera = ~(fechas_obj <= np.datetime64(limite))   # NaT también cuenta como fuera
        Y[fuera] = np.nan
        fechas_obj[fuera] = np.array("NaT", dtype=fechas_obj.dtype)
    return dataclasses.replace(
        conjunto, X=conjunto.X[mascara], Y=Y, fechas=conjunto.fechas[mascara],
        fechas_inicio_ventana=conjunto.fechas_inicio_ventana[mascara], fechas_objetivo=fechas_obj,
        precio_origen=conjunto.precio_origen[mascara], limite_objetivo=limite)


def dividir_parada_temprana(train, fraccion=config.ENTRENAMIENTO["fraccion_parada"]):
    """Separa el último `fraccion` del train (por fechas) para decidir cuándo parar.

    Las fichas de ajuste cuyas respuestas caerían en el trozo de parada se purgan.
    """
    corte = train.fechas[int(len(train) * (1 - fraccion))]
    ajuste = subconjunto(train, train.fechas < corte, limite_objetivo=corte - pd.Timedelta(days=1))
    parada = subconjunto(train, train.fechas >= corte)
    return ajuste, parada


# --- Pérdida y entrenamiento --------------------------------------------------------------

def perdida_huber(prediccion, objetivo, delta):
    """Huber solo sobre las respuestas válidas (las purgadas son NaN)."""
    validas = ~torch.isnan(objetivo)
    return nn.functional.huber_loss(prediccion[validas], objetivo[validas], delta=delta)


def perdida_cuantiles(prediccion, objetivo, cuantiles):
    """Pérdida por cuantiles («pinball»), media de los cuantiles: para el cuantil q, q·e si el error
    e = objetivo − previsión es positivo y (q − 1)·e si es negativo. Su mínimo está en el cuantil q.
    `objetivo` tiene una columna (un horizonte); `prediccion`, una por cuantil. Sin las purgadas (NaN)."""
    validas = ~torch.isnan(objetivo[:, 0])
    e = objetivo[validas] - prediccion[validas]
    return torch.maximum(cuantiles * e, (cuantiles - 1) * e).mean()


@torch.no_grad()
def _perdida_media(modelo, X, Y, delta, lote=2048, perdida=None):
    """Pérdida media en modo evaluación. Por defecto Huber; con `perdida`, esa función (por filas válidas)."""
    modelo.eval()
    total, n = 0.0, 0
    for i in range(0, len(X), lote):
        if perdida is None:
            validas = int((~torch.isnan(Y[i:i + lote])).sum())
            if validas:
                total += perdida_huber(modelo(X[i:i + lote]), Y[i:i + lote], delta).item() * validas
                n += validas
        else:
            validas = int((~torch.isnan(Y[i:i + lote, 0])).sum())
            if validas:
                total += perdida(modelo(X[i:i + lote]), Y[i:i + lote]).item() * validas
                n += validas
    return total / max(n, 1)


@dataclass
class Resultado:
    modelo: RedRecurrente
    escala_objetivo: np.ndarray   # desviación típica de cada horizonte en el train de ajuste
    tendencia: np.ndarray         # subida media del train de ajuste que se ha quitado (0 si se conserva)
    historial: pd.DataFrame       # pérdidas por época (curvas de aprendizaje)
    mejor_epoca: int
    segundos: float
    parametros: int
    hiperparametros: dict
    cuantiles: list | None = None  # con cuantiles, una salida por cuantil (un solo horizonte)


def entrenar_red(celda, train, hiperparametros=None, semilla=config.SEMILLA, dispositivo=None,
                 ajustes=None):
    """Entrena una red con las fichas de `train` y devuelve su mejor versión.

    Con `ajustes={"cuantiles": [0.1, 0.5, 0.9]}` (un solo horizonte), la red da un valor por
    cuantil y se entrena con la pérdida por cuantiles en lugar de Huber (rango de incertidumbre, D30).
    Con `ajustes={"epocas_fijas": n}` (D31), se entrena con **todo** `train`, sin trozo de parada
    temprana, durante n épocas, y se devuelve la red de la última.
    Sin esos ajustes, el entrenamiento es exactamente el de siempre."""
    hp = {**config.HIPERPARAMETROS_BASE, **(hiperparametros or {})}
    ent = {**config.ENTRENAMIENTO, **(ajustes or {})}
    dispositivo = dispositivo or dispositivo_disponible()
    fijar_semilla(semilla)

    epocas_fijas = ent.get("epocas_fijas")
    if epocas_fijas:
        ajuste, parada = train, None
    else:
        ajuste, parada = dividir_parada_temprana(train, ent["fraccion_parada"])
    escala = np.nanstd(ajuste.Y, axis=0).astype(np.float32)
    n_horizontes = ajuste.Y.shape[1]
    tendencia = (np.nanmean(ajuste.Y, axis=0) if ent["sin_tendencia"] else np.zeros(n_horizontes)).astype(np.float32)
    tensor = lambda a: torch.tensor(a, dtype=torch.float32, device=dispositivo)
    Xa, Ya = tensor(ajuste.X), tensor((ajuste.Y - tendencia) / escala)
    if parada is not None:
        Xp, Yp = tensor(parada.X), tensor((parada.Y - tendencia) / escala)

    cuantiles = ent.get("cuantiles")
    if cuantiles and Ya.shape[1] != 1:
        raise ValueError("Con cuantiles, la red se entrena para un solo horizonte")
    q = tensor(np.asarray(cuantiles, np.float32)) if cuantiles else None

    def perdida_lote(prediccion, objetivo):
        if cuantiles:
            return perdida_cuantiles(prediccion, objetivo, q)
        return perdida_huber(prediccion, objetivo, ent["delta_huber"])

    modelo = RedRecurrente(celda, Xa.shape[2], hp["unidades"], hp["capas"], hp["dropout"],
                           len(cuantiles) if cuantiles else Ya.shape[1]).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=hp["lr"], weight_decay=hp["l2"])
    planificador = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizador, factor=ent["factor_lr"], patience=ent["paciencia_lr"])
    generador = torch.Generator().manual_seed(semilla)

    mejor, mejor_estado, mejor_epoca, sin_mejora, historial = np.inf, None, 0, 0, []
    inicio = time.perf_counter()
    for epoca in range(1, (epocas_fijas or ent["max_epocas"]) + 1):
        modelo.train()
        for idx in torch.randperm(len(Xa), generator=generador).split(hp["lote"]):
            idx = idx.to(dispositivo)
            optimizador.zero_grad()
            perdida = perdida_lote(modelo(Xa[idx]), Ya[idx])
            perdida.backward()
            nn.utils.clip_grad_norm_(modelo.parameters(), ent["recorte_gradiente"])
            optimizador.step()

        # Ambas pérdidas en modo evaluación (sin dropout), para que las curvas sean comparables
        medida = perdida_lote if cuantiles else None
        perdida_ajuste = _perdida_media(modelo, Xa, Ya, ent["delta_huber"], perdida=medida)
        if epocas_fijas:   # sin trozo de parada: se entrena hasta la última época
            historial.append({"época": epoca, "pérdida train": perdida_ajuste, "pérdida parada": np.nan,
                              "lr": optimizador.param_groups[0]["lr"]})
            mejor_epoca, mejor_estado = epoca, copy.deepcopy(modelo.state_dict())
            continue
        perdida_parada = _perdida_media(modelo, Xp, Yp, ent["delta_huber"], perdida=medida)
        planificador.step(perdida_parada)
        historial.append({"época": epoca, "pérdida train": perdida_ajuste,
                          "pérdida parada": perdida_parada, "lr": optimizador.param_groups[0]["lr"]})

        if perdida_parada < mejor - 1e-6:
            mejor, mejor_epoca, sin_mejora = perdida_parada, epoca, 0
            mejor_estado = copy.deepcopy(modelo.state_dict())
        else:
            sin_mejora += 1
            if sin_mejora >= ent["paciencia"]:
                break

    modelo.load_state_dict(mejor_estado)
    return Resultado(modelo=modelo, escala_objetivo=escala, tendencia=tendencia,
                     historial=pd.DataFrame(historial),
                     mejor_epoca=mejor_epoca, segundos=time.perf_counter() - inicio,
                     parametros=contar_parametros(modelo), hiperparametros=hp, cuantiles=cuantiles)


@torch.no_grad()
def predecir(resultado, X, lote=2048):
    """Variaciones logarítmicas previstas, en su escala original (muestras, horizontes).

    Si la red se entrenó sin tendencia, la subida media del train no se vuelve a sumar: se
    supone tendencia cero para el futuro. Con cuantiles, una columna por cuantil, ordenadas de menor
    a mayor (si la red los da cruzados, se reordenan).
    """
    modelo = resultado.modelo
    modelo.eval()
    dispositivo = next(modelo.parameters()).device
    salidas = [modelo(torch.tensor(X[i:i + lote], dtype=torch.float32, device=dispositivo)).cpu().numpy()
               for i in range(0, len(X), lote)]
    prevision = np.concatenate(salidas) * resultado.escala_objetivo
    if getattr(resultado, "cuantiles", None):
        prevision = np.sort(prevision, axis=1)
    return prevision
