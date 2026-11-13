"""Validación hacia atrás (D29): las configuraciones elegidas, evaluadas en 2010-2017.

La validación (2018-2021) tiene pocos años, se ha usado muchas veces para elegir y puede ser un
periodo favorable a la señal de los modelos. Para saber si la ventaja de las redes es real sin
tocar el test, las mismas configuraciones (las elegidas en la fase B, sin volver a elegir nada)
se evalúan en años que nunca se usaron para elegir: cada año de 2010 a 2017 se prevé entrenando
solo con lo anterior, como en la validación. No se usa nada posterior al 31/12/2017: las fichas
cuya respuesta cae después se descartan, así que a 1 año el último año evaluado es 2016.

Se usan las semillas 42-46 (el promedio de 5 adoptado en D27) y el lineal de referencia, con su
misma regularización. Cada entrenamiento se guarda en cuanto termina; si el proceso se
interrumpe, al relanzarlo continúa donde se quedó.

Criterio, fijado antes de calcular (D29): la ventaja a 3 meses es real si la media de las tres
redes gana al ingenuo en al menos 9 de los 12 años (2010-2021) y queda por debajo de 1 con los
años juntos; dudosa con 7 u 8 años; no se sostiene con 6 o menos. A 1 año, 8 de 10.
"""
import time
from math import comb

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, combinacion as co, config, entrenamiento as ent, estabilidad as es
from . import experimentos as ex

AÑOS = list(range(2010, 2018))
LIMITE = pd.Timestamp("2017-12-31")
HORIZONTES = ["medio", "largo"]   # 1 semana se lanza aparte (--horizontes corto): con la ventana de 252 días tarda más
ARCHIVOS = {"entrenos": "hacia_atras.csv", "previsiones": "hacia_atras_previsiones.csv",
            "fichas": "hacia_atras_fichas.csv"}
CRITERIO = {"corto": {"real": 9, "dudosa": 7}, "medio": {"real": 9, "dudosa": 7}, "largo": {"real": 8, "dudosa": 6}}


# --- Qué se evalúa -------------------------------------------------------------------------------

def pliegues_hacia_atras(años=AÑOS, limite=LIMITE):
    """Un pliegue por año: entrena con todo lo anterior y prevé ese año, sin respuestas después de `limite`."""
    return [dict(nombre=f"hacia atrás (valida {año})", fin_train=pd.Timestamp(año - 1, 12, 31),
                 desde=pd.Timestamp(año, 1, 1), hasta=pd.Timestamp(año, 12, 31), limite_objetivo=limite)
            for año in años]


def pliegues(bases, comb_datos, años=AÑOS):
    """(año, train, evaluado) de cada año que tiene fichas evaluables en ese horizonte (como `busqueda._pliegues`)."""
    salida = []
    for pliegue in pliegues_hacia_atras(años):
        train, evaluado = ex._particion(bases, comb_datos, pliegue)
        if len(evaluado) >= config.MIN_FICHAS_EVALUACION:
            salida.append((pliegue["hasta"].year, train, evaluado))
    return salida


def previsiones_lineal(horizontes=None, bases=None):
    """Previsión del lineal de referencia en cada ficha de 2010-2017."""
    return co.previsiones_lineal(horizontes or HORIZONTES, bases=bases, pliegues=pliegues)


# --- Ejecución -------------------------------------------------------------------------------------

def ejecutar(dir_salida=config.DIR_RESULTADOS, horizontes=None, modelos=None, semillas=None,
             hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    """Entrena (o continúa) las redes elegidas en 2010-2017 y guarda sus previsiones."""
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
    registrar(f"Validación hacia atrás (D29) · {hilos} hilos · dispositivo {dispositivo} · "
              f"semillas {semillas[0]}-{semillas[-1]}")
    total = 0.0
    for h in horizontes:
        lista = [a for a, _, _ in años[h]]
        registrar(f"  {h}: años {lista[0]}-{lista[-1]} ({len(lista)})")
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            pendientes = [(a, s) for a in lista for s in semillas if clave(h, celda, intento, a, s) not in hechas]
            total += previsto[(h, celda)] * len(pendientes)
            registrar(f"    {celda:<4} intento {intento:>2} · {bu.describir(params)} · "
                      f"pendientes {len(pendientes)} de {len(lista) * len(semillas)}")
    registrar(f"Tiempo previsto ≈ {total / 60:.0f} min (algo menos: los primeros años entrenan con menos datos).")
    if solo_mostrar:
        return

    reloj, inicio = bu._Reloj(total), time.perf_counter()
    for h in horizontes:
        comb_datos = bu.combinacion(h)
        es._guardar_fichas(rutas["fichas"], h, años[h])
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            for semilla in semillas:
                for año, train, evaluado in años[h]:
                    if clave(h, celda, intento, año, semilla) in hechas:
                        continue
                    fila, prev = es._entrenar(comb_datos, celda, intento, params, año, train, evaluado,
                                              semilla, dispositivo)
                    # Primero las previsiones y después la fila: la fila marca el entrenamiento como hecho
                    es._anadir_compacto(rutas["previsiones"], prev, es.COLUMNAS_PREVISIONES)
                    ex._anadir(rutas["entrenos"], [fila], bu.COLUMNAS_B)
                    reloj.avanzar(previsto[(h, celda)], fila["segundos"])
                    registrar(f"[{h} {celda} · intento {intento}] {año} semilla {semilla} → {ex._medido(fila)}"
                              f" · quedan ≈ {reloj.restante() / 60:.0f} min")
    registrar(f"Validación hacia atrás terminada en {(time.perf_counter() - inicio) / 60:.1f} min.")


def leer_previsiones(dir_salida=config.DIR_RESULTADOS):
    return es.leer_previsiones(dir_salida, ARCHIVOS)


def leer_entrenos(dir_salida=config.DIR_RESULTADOS):
    return es.leer_entrenos(dir_salida, ARCHIVOS)


# --- Medidas ---------------------------------------------------------------------------------------

def sumas_por_año(previsiones):
    """Por horizonte, modelo y año: suma de errores del modelo y del ingenuo (en $), fichas, aciertos
    de dirección (sube o baja) y fichas en que el precio subió. Sumas, para poder juntar años."""
    p = previsiones
    real = p["precio origen"] * np.exp(p["variación real"])
    t = p.assign(error=(p["precio origen"] * np.exp(p["variación prevista"]) - real).abs(),
                 error_ingenuo=(p["precio origen"] - real).abs(),
                 acierto=np.sign(p["variación prevista"]) == np.sign(p["variación real"]),
                 sube=p["variación real"] > 0)
    return t.groupby(["horizonte", "modelo", "pliegue"], sort=False).agg(
        error=("error", "sum"), error_ingenuo=("error_ingenuo", "sum"), fichas=("error", "size"),
        aciertos=("acierto", "sum"), suben=("sube", "sum"))


def notas_por_año(sumas):
    """«MAE / ingenuo» de cada año (columnas) por horizonte y modelo."""
    return (sumas["error"] / sumas["error_ingenuo"]).unstack("pliegue")


def nota_juntos(sumas, por=("horizonte", "modelo")):
    g = sumas.groupby(level=list(por), sort=False)[["error", "error_ingenuo"]].sum()
    return g["error"] / g["error_ingenuo"]


def prob_moneda(ganados, años):
    """Probabilidad de ganar al ingenuo en `ganados` años o más de `años` sin ninguna ventaja
    (como sacar al menos tantas caras con una moneda)."""
    return sum(comb(años, k) for k in range(ganados, años + 1)) / 2 ** años


def intervalo(sumas, modelos, repeticiones=10_000, nivel=0.90, semilla=0):
    """Intervalo de la nota media de esos modelos con los años juntos, remuestreando años (con
    reemplazo): cuánto podría cambiar con otros años parecidos. `sumas`: las de un horizonte."""
    rng = np.random.default_rng(semilla)
    años = sorted(set(sumas.index.get_level_values("pliegue")))
    tablas = {m: sumas.xs(m, level="modelo").droplevel("horizonte").reindex(años) for m in modelos}
    elegidos = rng.integers(0, len(años), size=(repeticiones, len(años)))
    notas = np.mean([t["error"].to_numpy()[elegidos].sum(axis=1) / t["error_ingenuo"].to_numpy()[elegidos].sum(axis=1)
                     for t in tablas.values()], axis=0)
    cola = (1 - nivel) / 2
    return float(np.quantile(notas, cola)), float(np.quantile(notas, 1 - cola))


COLUMNAS = ["horizonte", "modelo", "pliegue", "fecha", "variación prevista", "variación real", "precio origen"]
MEDIA = "media de las tres"
FACTORES = np.round(np.arange(0, 1.01, 0.1), 1)
PERIODOS = {"2010-2017": list(range(2010, 2018)), "2018-2021": [2018, 2019, 2020, 2021]}


def media_de_las_redes(redes, nombre=MEDIA):
    """Media de los precios que prevén las redes en cada ficha, como variación logarítmica."""
    g = redes.assign(factor=np.exp(redes["variación prevista"])).groupby(
        ["horizonte", "pliegue", "fecha"], as_index=False, sort=False)
    t = g.agg(factor=("factor", "mean"), redes=("modelo", "nunique"),
              **{"variación real": ("variación real", "first"), "precio origen": ("precio origen", "first")})
    if (t["redes"] != t["redes"].max()).any():
        raise ValueError("Hay fichas sin la previsión de todas las redes")
    return t.assign(modelo=nombre, **{"variación prevista": np.log(t["factor"])}).drop(columns=["factor", "redes"])


def previsiones_doce_años(bases=None, dir_salida=config.DIR_RESULTADOS, horizontes=None):
    """Previsión de cada ficha de 2010-2021 (hacia atrás y validación), por defecto a 3 meses y a 1 año:
    cada red con el promedio de las semillas 42-46, el lineal de referencia y la media de las tres redes."""
    horizontes = horizontes or HORIZONTES
    semillas = config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    bases = bases if bases is not None else ex._bases()
    atras = es.promedio(leer_previsiones(dir_salida), semillas)
    atras = atras[atras["horizonte"].isin(horizontes)]
    validacion = es.promedio(es.leer_previsiones(dir_salida), semillas)
    validacion = validacion[validacion["horizonte"].isin(horizontes)]
    redes = pd.concat([atras[COLUMNAS], validacion[COLUMNAS]], ignore_index=True)
    lineal = pd.concat([previsiones_lineal(horizontes, bases=bases), co.previsiones_lineal(horizontes, dir_salida, bases)],
                       ignore_index=True)
    lineal["fecha"] = lineal["fecha"].astype(redes["fecha"].dtype)
    return pd.concat([redes, lineal[COLUMNAS], media_de_las_redes(redes)[COLUMNAS]], ignore_index=True)


def regla_media(sumas, horizonte, modelos=None, nombre=MEDIA):
    """Se adopta la media de las tres redes si, con todos los años juntos, mejora a cada red y gana
    al ingenuo en al menos tantos años como la mejor de ellas."""
    modelos = modelos or list(config.CELDAS)
    s = sumas.xs(horizonte, level="horizonte", drop_level=False)
    juntos = nota_juntos(s).xs(horizonte, level="horizonte")
    ganados = (notas_por_año(s).xs(horizonte, level="horizonte") < 1).sum(axis=1)
    adopta = bool((juntos[nombre] < juntos[modelos]).all() and ganados[nombre] >= ganados[modelos].max())
    return {"media de las tres": float(juntos[nombre]), "mejor red": juntos[modelos].idxmin(),
            "nota de la mejor red": float(juntos[modelos].min()), "años que gana la media": int(ganados[nombre]),
            "años que gana la mejor": int(ganados[modelos].max()), "se adopta": adopta}


def nota_prudente(previsiones, factor, años):
    """«MAE / ingenuo» por horizonte y modelo con la variación prevista multiplicada por `factor`
    (0 es el ingenuo; 1, la previsión sin ajustar), en esos años."""
    p = previsiones[previsiones["pliegue"].isin(años)]
    return es.nota(p.assign(**{"variación prevista": factor * p["variación prevista"]}))


def curvas_prudentes(previsiones, factores=FACTORES):
    """Nota con cada factor, por horizonte, modelo y periodo (2010-2017, 2018-2021 y todos)."""
    periodos = {**PERIODOS, "todos": PERIODOS["2010-2017"] + PERIODOS["2018-2021"]}
    filas = [nota_prudente(previsiones, f, años).rename("MAE / ingenuo").reset_index().assign(periodo=p, factor=f)
             for p, años in periodos.items() for f in factores]
    return pd.concat(filas, ignore_index=True)


def prudente_cruzado(curvas):
    """Regla de la previsión prudente: el factor se elige con un periodo y se comprueba en el otro, en
    los dos sentidos; se adopta si mejora a la previsión sin ajustar en los dos."""
    t = curvas.pivot_table(index=["horizonte", "modelo", "periodo"], columns="factor", values="MAE / ingenuo",
                           sort=False)
    filas = []
    for (h, m), g in t.groupby(level=["horizonte", "modelo"], sort=False):
        g = g.droplevel(["horizonte", "modelo"])
        fa, fb, ft = (float(g.loc[p].idxmin()) for p in ("2010-2017", "2018-2021", "todos"))
        filas.append({"horizonte": h, "modelo": m,
                      "factor elegido con 2010-2017": fa,
                      "2018-2021 sin ajustar": g.loc["2018-2021", 1.0], "2018-2021 prudente": g.loc["2018-2021", fa],
                      "factor elegido con 2018-2021": fb,
                      "2010-2017 sin ajustar": g.loc["2010-2017", 1.0], "2010-2017 prudente": g.loc["2010-2017", fb],
                      "mejor factor con todos": ft,
                      "todos sin ajustar": g.loc["todos", 1.0], "todos con el mejor factor": g.loc["todos", ft]})
    r = pd.DataFrame(filas).set_index(["horizonte", "modelo"])
    r["se adopta"] = ((r["2018-2021 prudente"] < r["2018-2021 sin ajustar"])
                      & (r["2010-2017 prudente"] < r["2010-2017 sin ajustar"]))
    return r


def criterio(sumas, horizonte, modelos=None):
    """Aplica el criterio de D29 a un horizonte con la media de las redes (todos los años que haya)."""
    modelos = modelos or list(config.CELDAS)
    s = sumas.xs(horizonte, level="horizonte", drop_level=False)
    por_año = notas_por_año(s).xs(horizonte, level="horizonte").loc[modelos].mean()
    ganados, años = int((por_año < 1).sum()), int(por_año.notna().sum())
    juntos = float(nota_juntos(s).xs(horizonte, level="horizonte").loc[modelos].mean())
    umbral = CRITERIO[horizonte]
    veredicto = ("real" if ganados >= umbral["real"] and juntos < 1
                 else "dudosa" if ganados >= umbral["dudosa"] else "no se sostiene")
    bajo, alto = intervalo(s, modelos)
    return {"años": años, "años que gana al ingenuo": ganados,
            "probabilidad sin ventaja": prob_moneda(ganados, años),
            "nota con los años juntos": juntos, "intervalo 90 % (bajo)": bajo, "intervalo 90 % (alto)": alto,
            "veredicto": veredicto}
