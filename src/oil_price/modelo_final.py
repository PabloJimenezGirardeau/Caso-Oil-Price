"""Modelos finales y previsión desde el último dato (D34; base de la aplicación).

- `entrenar`: entrena las redes elegidas antes del test (D33: LSTM a 1 semana, RNN a 3 meses y a
  1 año), con sus configuraciones de la fase B y las semillas 42-46, con todo lo que tiene respuesta
  hasta `fin_train` (con purga). Igual que en el examen: 1 semana y 3 meses con parada temprana;
  1 año con todo el entrenamiento y épocas fijas (D31).
- `guardar` y `cargar`: los pesos de cada semilla, el escalado (ajustado solo con el train) y una
  ficha JSON con la configuración. Es lo que se sube a Hugging Face.
- `prever`: desde un día de origen (por defecto, el último), el precio previsto (media de los precios
  de las semillas), su variación y el rango del 80 % centrado en el precio de hoy (A2 a 1 semana, A3 a
  3 meses y a 1 año; D30 y D32), ajustado con todo lo conocido hasta ese día.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, comprobaciones as cp, config, entrenamiento as ent, estabilidad as es
from . import examen_final as exa, incertidumbre as inc, preprocesado as pp
from .modelos import RedRecurrente

ELEGIDA = exa.ELEGIDA
METODO_RANGO = exa.METODO_RANGO
DIR_MODELOS = config.RAIZ / "modelos"


@dataclass
class ModeloHorizonte:
    """Lo necesario para prever un horizonte: una red por semilla, el escalado y la configuración."""
    horizonte: str
    celda: str
    intento: int
    hiperparametros: dict
    ventana: int
    recorte: tuple | None
    nivel: bool
    variables: list
    preparador: pp.Preparador
    redes: dict            # {semilla: ent.Resultado}
    fin_train: pd.Timestamp


# --- Entrenamiento ---------------------------------------------------------------------------------

def _particion(base, comb, fin_train):
    """Fichas de train (con purga) hasta `fin_train` y el escalado ajustado con ellas."""
    train, _, preparador = pp.construir_particion(base, comb["ventana"], comb["recorte"], fin_train=fin_train,
                                                  desde=fin_train, hasta=fin_train, limite_objetivo=fin_train)
    return pp.por_horizonte(train, comb["horizonte"]), preparador


def entrenar(fin_train, bases, horizontes=None, semillas=None, dir_salida=config.DIR_RESULTADOS,
             hilos=config.HILOS_CPU, registrar=print):
    """{horizonte: ModeloHorizonte} entrenados con todo lo que tiene respuesta hasta `fin_train`."""
    horizontes = horizontes or list(config.HORIZONTES)
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    torch.set_num_threads(hilos)
    dispositivo = ent.dispositivo_disponible()
    eleg = es.elegidas(dir_salida)
    salida = {}
    for h in horizontes:
        comb, celda = bu.combinacion(h), ELEGIDA[h]
        intento, params = eleg[(h, celda)]
        train, preparador = _particion(bases[comb["nivel"]], comb, pd.Timestamp(fin_train))
        ajustes = {"sin_tendencia": True}
        if h in exa.CON_TODO:
            ajustes["epocas_fijas"] = config.EPOCAS_FIJAS[h][celda]
        redes = {}
        for semilla in semillas:
            redes[semilla] = ent.entrenar_red(celda, train, bu.hiperparametros(params), semilla=semilla,
                                              dispositivo=dispositivo, ajustes=ajustes)
            registrar(f"[{h} {celda}] hasta {pd.Timestamp(fin_train).date()} · semilla {semilla} · "
                      f"{len(redes[semilla].historial)} épocas · {redes[semilla].segundos:.0f} s")
        salida[h] = ModeloHorizonte(h, celda, intento, bu.hiperparametros(params), comb["ventana"], comb["recorte"],
                                    comb["nivel"], list(train.variables), preparador, redes, pd.Timestamp(fin_train))
    return salida


# --- Guardar y cargar ------------------------------------------------------------------------------

def guardar(modelos, directorio):
    """Una carpeta por horizonte: `ficha.json`, `escalado.json` y `semilla_<n>.pt`."""
    directorio = Path(directorio)
    for h, m in modelos.items():
        d = directorio / h
        d.mkdir(parents=True, exist_ok=True)
        r0 = next(iter(m.redes.values()))
        ficha = {"horizonte": h, "sesiones": config.HORIZONTES[h], "celda": m.celda, "intento": m.intento,
                 "hiperparametros": m.hiperparametros, "ventana": m.ventana,
                 "recorte": list(m.recorte) if m.recorte else None, "nivel": m.nivel, "variables": m.variables,
                 "fin_train": str(m.fin_train.date()), "semillas": sorted(m.redes),
                 "escala_objetivo": {str(s): float(r.escala_objetivo[0]) for s, r in m.redes.items()},
                 "parametros": int(r0.parametros), "metodo_rango": METODO_RANGO[h]}
        (d / "ficha.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
        p = m.preparador
        escalado = {"recorte": list(p.recorte) if p.recorte else None, "columnas_recorte": p.columnas_recorte_,
                    "inferior": None if p.inferior_ is None else p.inferior_.to_dict(),
                    "superior": None if p.superior_ is None else p.superior_.to_dict(),
                    "media": p.media_.to_dict(), "desviacion": p.desviacion_.to_dict(),
                    "fecha_max": str(p.fecha_max_.date())}
        (d / "escalado.json").write_text(json.dumps(escalado, ensure_ascii=False, indent=2), encoding="utf-8")
        for s, r in m.redes.items():
            torch.save(r.modelo.state_dict(), d / f"semilla_{s}.pt")


def cargar(directorio):
    """{horizonte: ModeloHorizonte} desde una carpeta guardada con `guardar`."""
    salida = {}
    for d in sorted(Path(directorio).iterdir()):
        if not (d / "ficha.json").exists():
            continue
        f = json.loads((d / "ficha.json").read_text(encoding="utf-8"))
        e = json.loads((d / "escalado.json").read_text(encoding="utf-8"))
        prep = pp.Preparador(tuple(e["recorte"]) if e["recorte"] else None)
        prep.columnas_recorte_ = e["columnas_recorte"]
        prep.inferior_ = None if e["inferior"] is None else pd.Series(e["inferior"])
        prep.superior_ = None if e["superior"] is None else pd.Series(e["superior"])
        prep.media_, prep.desviacion_ = pd.Series(e["media"]), pd.Series(e["desviacion"])
        prep.fecha_max_ = pd.Timestamp(e["fecha_max"])
        hp = f["hiperparametros"]
        redes = {}
        for s in f["semillas"]:
            red = RedRecurrente(f["celda"], len(f["variables"]), hp["unidades"], hp["capas"], hp["dropout"], 1)
            red.load_state_dict(torch.load(d / f"semilla_{s}.pt", map_location="cpu"))
            red.eval()
            redes[s] = ent.Resultado(modelo=red, escala_objetivo=np.array([f["escala_objetivo"][str(s)]], np.float32),
                                     tendencia=np.zeros(1, np.float32), historial=pd.DataFrame(), mejor_epoca=0,
                                     segundos=0.0, parametros=f["parametros"], hiperparametros=hp)
        salida[f["horizonte"]] = ModeloHorizonte(f["horizonte"], f["celda"], f["intento"], hp, f["ventana"],
                                                 tuple(f["recorte"]) if f["recorte"] else None, f["nivel"],
                                                 f["variables"], prep, redes, pd.Timestamp(f["fin_train"]))
    return salida


# --- Previsión -------------------------------------------------------------------------------------

def ventana_hasta(m, base, fecha):
    """La ficha (1, ventana, variables) que acaba en `fecha`, escalada con el escalado del modelo."""
    escaladas = m.preparador.transformar(base.entradas[m.variables])
    pos = escaladas.index.get_loc(pd.Timestamp(fecha))
    if pos < m.ventana - 1:
        raise ValueError("No hay días suficientes antes de esa fecha para la ventana")
    return escaladas.iloc[pos - m.ventana + 1:pos + 1].to_numpy(np.float32)[None]


def rango_desde(ctx, h, metodo, fecha, alfa=inc.ALFA):
    """Límites del rango (variación logarítmica respecto al precio de `fecha`) centrado en el precio de
    hoy, ajustado con las respuestas conocidas hasta `fecha`. Misma cuenta que `incertidumbre.rangos`."""
    fecha = pd.Timestamp(fecha)
    pasado = ctx.loc[ctx[f"fin {h}"] <= fecha, [f"variación {h}", "volatilidad"]].dropna()
    var, vol = pasado[f"variación {h}"], pasado["volatilidad"]
    vol_hoy = float(ctx.loc[fecha, "volatilidad"])
    if metodo == "memoria":
        m, normal = inc.memoria(var, vol)
        q = inc._cuantiles(var / (vol / normal) ** m, alfa)
        escala = (vol_hoy / normal) ** m
        return float(escala * q[0]), float(escala * q[1]), m
    if metodo == "centrado":
        normal = float(np.median(vol))
        nervioso = pasado[vol >= normal]
        m = cp.memoria_robusta(nervioso[f"variación {h}"], nervioso["volatilidad"])
        z = var / (np.maximum(vol, normal) / normal) ** m
        q = float(np.quantile(np.abs(z - np.median(z)), 1 - alfa))
        escala = (max(vol_hoy, normal) / normal) ** m
        return float(-escala * q), float(escala * q), m
    raise ValueError(f"Método desconocido: {metodo}")


def prever(modelos, bases, ctx, fecha=None, alfa=inc.ALFA):
    """Una fila por horizonte: precio de hoy, previsión de cada semilla y su media (en precio), variación
    prevista y rango del 80 % (en $ y en variación), desde `fecha` (por defecto, el último día)."""
    filas = []
    for h, m in modelos.items():
        base = bases[m.nivel]
        dia = pd.Timestamp(fecha) if fecha is not None else base.entradas.index[-1]
        X = ventana_hasta(m, base, dia)
        precio_hoy = float(base.precio.loc[dia])
        por_semilla = {s: float(ent.predecir(r, X)[0, 0]) for s, r in m.redes.items()}
        precio = float(np.mean([precio_hoy * np.exp(v) for v in por_semilla.values()]))
        bajo, alto, memoria = rango_desde(ctx, h, METODO_RANGO[h], dia, alfa)
        filas.append({"horizonte": h, "sesiones": config.HORIZONTES[h], "red": m.celda,
                      "entrenada hasta": m.fin_train.date(), "fecha origen": dia.date(),
                      "fecha objetivo (estimada)": (dia + pd.offsets.BDay(config.HORIZONTES[h])).date(),
                      "precio hoy": precio_hoy, "precio previsto": precio,
                      "variación prevista": np.log(precio / precio_hoy),
                      "rango bajo": precio_hoy * np.exp(bajo), "rango alto": precio_hoy * np.exp(alto),
                      "rango": f"{METODO_RANGO[h]} (centrado en el precio de hoy)", "memoria del rango": memoria,
                      **{f"semilla {s}": precio_hoy * np.exp(v) for s, v in por_semilla.items()}})
    return pd.DataFrame(filas)
