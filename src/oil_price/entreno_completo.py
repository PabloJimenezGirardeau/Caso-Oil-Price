"""Las redes, reentrenadas con todo el entrenamiento (D31).

Hasta ahora, cada red se entrena con el 85 % inicial del entrenamiento y usa el 15 % final solo
para decidir cuándo parar, sin reentrenar después con todo; con la purga, no aprende de los
últimos 3-4 años antes de prever (el lineal sí). Aquí se entrena con **todo** el entrenamiento,
sin trozo de parada, durante un número fijo de épocas (`config.EPOCAS_FIJAS`: la mediana de sus
mejores épocas en la estabilidad). Todo lo demás, igual: configuraciones de la fase B, sin
tendencia y semillas 42-46. Solo como información, la RNN con 3 y con 10 épocas fijas.

Se evalúa en 2010-2021 (validación hacia atrás y validación). El test no se toca. Cada
entrenamiento se guarda en cuanto termina; al relanzar, continúa donde se quedó.
"""
import time

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, config, entrenamiento as ent, estabilidad as es, experimentos as ex
from . import rango_redes as rr

HORIZONTES = ["medio", "largo"]
ARCHIVOS = {"entrenos": "completo.csv", "previsiones": "completo_previsiones.csv", "fichas": "completo_fichas.csv"}
CLAVE = ["horizonte", "modelo", "intento", "variante", "pliegue", "semilla"]
COLUMNAS_ENTRENOS = [*CLAVE, "épocas", "MAE", "MAE / ingenuo", "parametros", "segundos"]
COLUMNAS_PREVISIONES = [*CLAVE, "fecha", "variación prevista"]
PRINCIPAL = "mediana"


def variantes(h, celda):
    """{variante: épocas}: la principal (la mediana) y, con la RNN, las de información."""
    salida = {PRINCIPAL: config.EPOCAS_FIJAS[h][celda]}
    if celda == "RNN":
        salida |= {str(n): n for n in config.EPOCAS_INFORMACION}
    return salida


def _entrenar(comb, celda, intento, params, variante, epocas, año, train, evaluado, semilla, dispositivo):
    resultado = ent.entrenar_red(celda, train, bu.hiperparametros(params), semilla=semilla, dispositivo=dispositivo,
                                 ajustes={"sin_tendencia": True, "epocas_fijas": epocas})
    prevision = ent.predecir(resultado, evaluado.X)
    medida = ex._fila(comb, celda, np.nan, año, evaluado, prevision, len(train), parametros=resultado.parametros,
                      épocas=epocas, segundos=resultado.segundos)
    fila = {"horizonte": comb["horizonte"], "modelo": celda, "intento": intento, "variante": variante,
            "pliegue": año, "semilla": semilla, "épocas": epocas, "MAE": medida["MAE"],
            "MAE / ingenuo": medida["MAE / ingenuo"], "parametros": resultado.parametros,
            "segundos": resultado.segundos}
    previsiones = pd.DataFrame({"horizonte": comb["horizonte"], "modelo": celda, "intento": intento,
                                "variante": variante, "pliegue": año, "semilla": semilla, "fecha": evaluado.fechas,
                                "variación prevista": prevision[:, 0]})
    return fila, previsiones


def ejecutar(dir_salida=config.DIR_RESULTADOS, horizontes=None, modelos=None, semillas=None,
             hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    horizontes = horizontes or HORIZONTES
    modelos = modelos or list(config.CELDAS)
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    torch.set_num_threads(hilos)
    dir_salida.mkdir(parents=True, exist_ok=True)
    dispositivo = ent.dispositivo_disponible()
    rutas = {k: dir_salida / v for k, v in ARCHIVOS.items()}
    eleg = es.elegidas(dir_salida)
    hechas = ex._ya_hechas(rutas["entrenos"], CLAVE)

    def clave(h, celda, intento, variante, año, semilla):
        return ex._clave({"horizonte": h, "modelo": celda, "intento": intento, "variante": variante,
                          "pliegue": año, "semilla": semilla}, CLAVE)

    bases = ex._bases()
    años = {h: rr.pliegues(bases, bu.combinacion(h)) for h in horizontes}
    registrar(f"Redes con todo el entrenamiento (D31) · {hilos} hilos · dispositivo {dispositivo} · "
              f"semillas {semillas[0]}-{semillas[-1]}")
    total = 0
    for h in horizontes:
        lista = [a for a, _, _ in años[h]]
        registrar(f"  {h}: años {lista[0]}-{lista[-1]} ({len(lista)})")
        for celda in modelos:
            for variante, epocas in variantes(h, celda).items():
                pendientes = sum(clave(h, celda, eleg[(h, celda)][0], variante, a, s) not in hechas
                                 for a in lista for s in semillas)
                total += pendientes
                registrar(f"    {celda:<4} {variante:<8} ({epocas} épocas) · pendientes {pendientes}")
    registrar(f"Entrenamientos pendientes: {total}.")
    if solo_mostrar:
        return

    inicio, hechos = time.perf_counter(), 0
    for h in horizontes:
        comb = bu.combinacion(h)
        es._guardar_fichas(rutas["fichas"], h, años[h])
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            for variante, epocas in variantes(h, celda).items():
                for semilla in semillas:
                    for año, train, evaluado in años[h]:
                        if clave(h, celda, intento, variante, año, semilla) in hechas:
                            continue
                        fila, prev = _entrenar(comb, celda, intento, params, variante, epocas, año, train, evaluado,
                                               semilla, dispositivo)
                        es._anadir_compacto(rutas["previsiones"], prev, COLUMNAS_PREVISIONES)
                        ex._anadir(rutas["entrenos"], [fila], COLUMNAS_ENTRENOS)
                        hechos += 1
                        minutos = (time.perf_counter() - inicio) / 60
                        registrar(f"[{h} {celda} {variante}] {año} semilla {semilla} → MAE/ingenuo "
                                  f"{fila['MAE / ingenuo']:.3f} · {fila['segundos']:5.1f} s · "
                                  f"{hechos}/{total} en {minutos:.1f} min")
    registrar(f"Terminado en {(time.perf_counter() - inicio) / 60:.1f} min.")


def leer_previsiones(dir_salida=config.DIR_RESULTADOS):
    p = pd.read_csv(dir_salida / ARCHIVOS["previsiones"], parse_dates=["fecha"])
    p = p.drop_duplicates([*CLAVE, "fecha"], keep="last")
    fichas = pd.read_csv(dir_salida / ARCHIVOS["fichas"], parse_dates=["fecha"])
    return p.merge(fichas, on=["horizonte", "pliegue", "fecha"], how="left", validate="many_to_one")


def leer_entrenos(dir_salida=config.DIR_RESULTADOS):
    ruta = dir_salida / ARCHIVOS["entrenos"]
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=COLUMNAS_ENTRENOS)


def promedio(previsiones, variante=PRINCIPAL, semillas=None):
    """Promedio de semillas de una variante, con el formato de `estabilidad.promedio`."""
    p = previsiones[previsiones["variante"] == variante].drop(columns="variante")
    return es.promedio(p, semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO])
