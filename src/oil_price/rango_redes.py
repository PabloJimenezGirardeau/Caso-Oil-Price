"""Redes que dan el rango (D30, candidato B).

En lugar de un número, cada red da tres: los percentiles 10, 50 y 90 de la variación a h sesiones.
El 50 es la previsión central y el 10 y el 90, el rango del 80 %. Se entrenan con la pérdida por
cuantiles («pinball»). Todo lo demás es como siempre: las configuraciones elegidas en la fase B
(sin volver a buscar), los mismos datos, sin tendencia, la misma parada temprana (con la pérdida
por cuantiles) y las semillas 42-46; el rango de las cinco semillas es la media de sus percentiles.

Se entrena en los años de la validación hacia atrás (2010-2017, sin nada posterior a 2017) y de
la validación (2018-2021), a 3 meses y a 1 año. El test no se toca. Cada entrenamiento se guarda
en cuanto termina; si el proceso se interrumpe, al relanzarlo continúa donde se quedó.
"""
import time

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, config, entrenamiento as ent, estabilidad as es, experimentos as ex
from . import hacia_atras as ha

CUANTILES = [0.1, 0.5, 0.9]
HORIZONTES = ["medio", "largo"]
ARCHIVOS = {"entrenos": "rango_redes.csv", "previsiones": "rango_redes_previsiones.csv",
            "fichas": "rango_redes_fichas.csv"}
COLUMNAS_ENTRENOS = ["horizonte", "modelo", "intento", "pliegue", "semilla", "épocas", "mejor época",
                     "pérdida parada", "parametros", "segundos"]
COLUMNAS_PREVISIONES = ["horizonte", "modelo", "intento", "pliegue", "semilla", "fecha", "q10", "q50", "q90"]


def pliegues(bases, comb):
    """(año, train, evaluado): 2010-2017 hacia atrás y 2018-2021 de la validación."""
    return ha.pliegues(bases, comb) + bu._pliegues(bases, comb)


def _entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo):
    resultado = ent.entrenar_red(celda, train, bu.hiperparametros(params), semilla=semilla, dispositivo=dispositivo,
                                 ajustes={"sin_tendencia": True, "cuantiles": CUANTILES})
    q = ent.predecir(resultado, evaluado.X)
    fila = {"horizonte": comb["horizonte"], "modelo": celda, "intento": intento, "pliegue": año, "semilla": semilla,
            "épocas": len(resultado.historial), "mejor época": resultado.mejor_epoca,
            "pérdida parada": float(resultado.historial["pérdida parada"].min()),
            "parametros": resultado.parametros, "segundos": resultado.segundos}
    previsiones = pd.DataFrame({"horizonte": comb["horizonte"], "modelo": celda, "intento": intento, "pliegue": año,
                                "semilla": semilla, "fecha": evaluado.fechas,
                                "q10": q[:, 0], "q50": q[:, 1], "q90": q[:, 2]})
    return fila, previsiones


def ejecutar(dir_salida=config.DIR_RESULTADOS, horizontes=None, modelos=None, semillas=None,
             hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    """Entrena (o continúa) las redes que dan el rango y guarda sus percentiles."""
    horizontes = horizontes or HORIZONTES
    modelos = modelos or list(config.CELDAS)
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    torch.set_num_threads(hilos)
    dir_salida.mkdir(parents=True, exist_ok=True)
    dispositivo = ent.dispositivo_disponible()
    rutas = {k: dir_salida / v for k, v in ARCHIVOS.items()}
    eleg = es.elegidas(dir_salida)
    previsto = {k: float(np.mean(list(v.values()))) for k, v in es._previsto(dir_salida, eleg).items()}
    hechas = ex._ya_hechas(rutas["entrenos"], es.CLAVE_E)

    def clave(h, celda, intento, año, semilla):
        return ex._clave({"horizonte": h, "modelo": celda, "intento": intento, "pliegue": año, "semilla": semilla},
                         es.CLAVE_E)

    bases = ex._bases()
    años = {h: pliegues(bases, bu.combinacion(h)) for h in horizontes}
    registrar(f"Redes que dan el rango (D30, B) · cuantiles {CUANTILES} · {hilos} hilos · dispositivo {dispositivo} · "
              f"semillas {semillas[0]}-{semillas[-1]}")
    total = 0.0
    for h in horizontes:
        lista = [a for a, _, _ in años[h]]
        registrar(f"  {h}: años {', '.join(map(str, lista))}")
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            pendientes = [(a, s) for a in lista for s in semillas if clave(h, celda, intento, a, s) not in hechas]
            total += previsto[(h, celda)] * len(pendientes)
            registrar(f"    {celda:<4} intento {intento:>2} · {bu.describir(params)} · "
                      f"pendientes {len(pendientes)} de {len(lista) * len(semillas)}")
    registrar(f"Tiempo previsto ≈ {total / 60:.0f} min.")
    if solo_mostrar:
        return

    reloj, inicio = bu._Reloj(total), time.perf_counter()
    for h in horizontes:
        comb = bu.combinacion(h)
        es._guardar_fichas(rutas["fichas"], h, años[h])
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            for semilla in semillas:
                for año, train, evaluado in años[h]:
                    if clave(h, celda, intento, año, semilla) in hechas:
                        continue
                    fila, prev = _entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo)
                    # Primero las previsiones y después la fila: la fila marca el entrenamiento como hecho
                    es._anadir_compacto(rutas["previsiones"], prev, COLUMNAS_PREVISIONES)
                    ex._anadir(rutas["entrenos"], [fila], COLUMNAS_ENTRENOS)
                    reloj.avanzar(previsto[(h, celda)], fila["segundos"])
                    registrar(f"[{h} {celda} · intento {intento}] {año} semilla {semilla} → "
                              f"{fila['épocas']:>3} épocas (mejor {fila['mejor época']}) · {fila['segundos']:5.1f} s"
                              f" · quedan ≈ {reloj.restante() / 60:.0f} min")
    registrar(f"Redes que dan el rango: terminado en {(time.perf_counter() - inicio) / 60:.1f} min.")


def leer_entrenos(dir_salida=config.DIR_RESULTADOS):
    ruta = dir_salida / ARCHIVOS["entrenos"]
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=COLUMNAS_ENTRENOS)


def leer_previsiones(dir_salida=config.DIR_RESULTADOS):
    """Percentiles de cada red, semilla y ficha, junto a lo que pasó (variación real y precio de partida)."""
    p = pd.read_csv(dir_salida / ARCHIVOS["previsiones"], parse_dates=["fecha"])
    p = p.drop_duplicates(["horizonte", "modelo", "intento", "semilla", "fecha"], keep="last")
    fichas = pd.read_csv(dir_salida / ARCHIVOS["fichas"], parse_dates=["fecha"])
    return p.merge(fichas, on=["horizonte", "pliegue", "fecha"], how="left", validate="many_to_one")


def promedio(previsiones, semillas=None):
    """Media de los percentiles de varias semillas en cada ficha (en variación logarítmica)."""
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    sel = previsiones[previsiones["semilla"].isin(list(semillas))]
    claves = ["horizonte", "modelo", "intento", "pliegue", "fecha"]
    return sel.groupby(claves, as_index=False, sort=False).agg(
        q10=("q10", "mean"), q50=("q50", "mean"), q90=("q90", "mean"), semillas=("semilla", "nunique"),
        **{"variación real": ("variación real", "first"), "precio origen": ("precio origen", "first")})
