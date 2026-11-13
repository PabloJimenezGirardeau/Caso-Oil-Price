"""Estabilidad (D27): promediar las previsiones de varias semillas.

Una red entrenada con otra semilla da otro resultado (a 1 año, hasta 0,04 de «MAE / ingenuo»), y
la época en que para es medio azar. Promediar las previsiones de varias semillas compensa ese azar.

Para cada horizonte y red se toma la configuración elegida en la fase B, sin volver a elegir
nada, y se entrena con `config.SEMILLAS_ESTABILIDAD` (10 semillas) en todos los pliegues de
validación, guardando la previsión de cada ficha. Con ellas se mide:
- el error de una red suelta frente al promedio de 2, 3, 5 y 10 semillas;
- la estabilidad: cuánto cambian la nota y las previsiones entre grupos de semillas distintos
  (por ejemplo, 42-46 frente a 47-51), frente a lo que cambian entre dos semillas sueltas.

Regla fijada de antemano: se adopta el promedio de `config.N_SEMILLAS_PROMEDIO` (5) semillas. El
promedio es la media de los precios que prevé cada semilla, así que su error (MAE) nunca supera
la media de los errores de sus semillas.

Las semillas 42, 43 y 44 ya se entrenaron en la fase B: deben reproducir exactamente sus
resultados (`comprobar_fase_b`). Cada entrenamiento se guarda en cuanto termina; si el proceso
se interrumpe, al relanzarlo continúa donde se quedó.
"""
import time

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, config, entrenamiento as ent, experimentos as ex

CLAVE_E = ["horizonte", "modelo", "intento", "pliegue", "semilla"]
COLUMNAS_PREVISIONES = ["horizonte", "modelo", "intento", "pliegue", "semilla", "fecha", "variación prevista"]
COLUMNAS_FICHAS = ["horizonte", "pliegue", "fecha", "variación real", "precio origen"]
ARCHIVOS = {"entrenos": "estabilidad.csv", "previsiones": "estabilidad_previsiones.csv",
            "fichas": "estabilidad_fichas.csv"}
# Por defecto, de lo más rápido a lo más lento: los primeros resultados llegan pronto
ORDEN = ["largo", "medio", "corto"]


# --- Qué se entrena ------------------------------------------------------------------------

def elegidas(dir_salida=config.DIR_RESULTADOS):
    """Configuración elegida en la fase B de cada horizonte y red: {(horizonte, red): (intento, valores)}."""
    _, cerrados, _ = bu.leer_resultados(dir_salida)
    salida = {}
    for (h, celda), (tabla, _) in bu.eleccion(dir_salida).items():
        intento = int(tabla.index[tabla["elegida"].to_numpy()][0])
        fila = bu._de(cerrados, h, celda)
        salida[(h, celda)] = (intento, bu._leer_params(fila[fila["intento"] == intento].iloc[0]))
    return salida


def _previsto(dir_salida, eleg):
    """Segundos por pliegue de cada red elegida: la media de lo que tardaron sus semillas en la fase B."""
    entrenos, _, confirmados = bu.leer_resultados(dir_salida)
    todas = pd.concat([t for t in (entrenos, confirmados) if not t.empty] or [entrenos], ignore_index=True)
    salida = {}
    for (h, celda), (intento, _) in eleg.items():
        filas = bu._de(todas, h, celda)
        filas = filas[filas["intento"] == intento]
        salida[(h, celda)] = filas.groupby("pliegue")["segundos"].mean().to_dict()
    return salida


# --- Entrenamiento y archivos ----------------------------------------------------------------

def _entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo):
    """Entrena como en la fase B. Devuelve la fila de resultados y la previsión de cada ficha."""
    fila, _, prediccion = bu._entrenar_y_prever(comb, celda, intento, params, año, train, evaluado,
                                                semilla, dispositivo)
    previsiones = pd.DataFrame({"horizonte": comb["horizonte"], "modelo": celda, "intento": intento,
                                "pliegue": año, "semilla": semilla, "fecha": evaluado.fechas,
                                "variación prevista": prediccion[:, 0]})
    return fila, previsiones


def _anadir_compacto(ruta, tabla, columnas):
    """Añade filas con 8 cifras significativas: sobra para variaciones y precios, y ocupa la mitad."""
    tabla.reindex(columns=columnas).to_csv(ruta, mode="a", header=not ruta.exists(), index=False,
                                           float_format="%.8g", date_format="%Y-%m-%d")


def _guardar_fichas(ruta, horizonte, pliegues):
    """Lo que pasó en cada ficha evaluada (variación real y precio de partida), una sola vez."""
    hechas = set()
    if ruta.exists():
        guardadas = pd.read_csv(ruta)
        hechas = set(map(tuple, guardadas[["horizonte", "pliegue"]].astype(str).to_numpy()))
    for año, _, evaluado in pliegues:
        if (horizonte, str(año)) in hechas:
            continue
        _anadir_compacto(ruta, pd.DataFrame({"horizonte": horizonte, "pliegue": año, "fecha": evaluado.fechas,
                                             "variación real": evaluado.Y[:, 0],
                                             "precio origen": evaluado.precio_origen}), COLUMNAS_FICHAS)


def leer_entrenos(dir_salida=config.DIR_RESULTADOS, archivos=ARCHIVOS):
    ruta = dir_salida / archivos["entrenos"]
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=bu.COLUMNAS_B)


def leer_previsiones(dir_salida=config.DIR_RESULTADOS, archivos=ARCHIVOS):
    """Previsión de cada red, semilla y ficha, junto a lo que pasó (variación real y precio de partida).
    Con `archivos`, los de otra ejecución con el mismo formato (por ejemplo, la validación hacia atrás)."""
    # on_bad_lines: si otro proceso está escribiendo, la última línea puede estar a medias
    previsiones = pd.read_csv(dir_salida / archivos["previsiones"], parse_dates=["fecha"], on_bad_lines="skip")
    # Si el proceso se cortó entre guardar las previsiones y la fila de resultados, ese
    # entrenamiento se repitió: vale la última copia (es idéntica)
    previsiones = previsiones.drop_duplicates(["horizonte", "modelo", "intento", "semilla", "fecha"], keep="last")
    fichas = pd.read_csv(dir_salida / archivos["fichas"], parse_dates=["fecha"])
    return previsiones.merge(fichas, on=["horizonte", "pliegue", "fecha"], how="left", validate="many_to_one")


def comprobar_fase_b(dir_salida=config.DIR_RESULTADOS):
    """Entrenamientos repetidos con las semillas de la fase B, con su MAE aquí y allí. Deben coincidir."""
    entrenos, _, confirmados = bu.leer_resultados(dir_salida)
    fase_b = pd.concat([t for t in (entrenos, confirmados) if not t.empty] or [entrenos], ignore_index=True)
    ahora = leer_entrenos(dir_salida)
    if ahora.empty or fase_b.empty:
        return pd.DataFrame(columns=CLAVE_E + ["MAE ahora", "MAE fase B", "diferencia"])
    comun = ahora[CLAVE_E + ["MAE"]].merge(fase_b[CLAVE_E + ["MAE"]], on=CLAVE_E, suffixes=(" ahora", " fase B"))
    comun["diferencia"] = (comun["MAE ahora"] - comun["MAE fase B"]).abs()
    return comun


# --- Ejecución -------------------------------------------------------------------------------

def ejecutar_estabilidad(dir_salida=config.DIR_RESULTADOS, horizontes=None, modelos=None, semillas=None,
                         hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    """Entrena (o continúa) las redes elegidas con todas las semillas y guarda sus previsiones."""
    horizontes = horizontes or ORDEN
    modelos = modelos or list(config.CELDAS)
    semillas = semillas or config.SEMILLAS_ESTABILIDAD
    torch.set_num_threads(hilos)
    dir_salida.mkdir(parents=True, exist_ok=True)
    dispositivo = ent.dispositivo_disponible()
    rutas = {k: dir_salida / v for k, v in ARCHIVOS.items()}

    eleg = elegidas(dir_salida)
    faltan = [(h, c) for h in horizontes for c in modelos if (h, c) not in eleg]
    if faltan:
        raise ValueError(f"Falta la elección de la fase B de {faltan}")
    previsto = _previsto(dir_salida, eleg)
    hechas = ex._ya_hechas(rutas["entrenos"], CLAVE_E)

    def clave(h, celda, intento, año, semilla):
        return ex._clave({"horizonte": h, "modelo": celda, "intento": intento, "pliegue": año, "semilla": semilla},
                         CLAVE_E)

    registrar(f"Estabilidad (D27) · {hilos} hilos · dispositivo {dispositivo} · semillas {semillas[0]}-{semillas[-1]}")
    total = 0.0
    for h in horizontes:
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            años = previsto[(h, celda)]
            pendientes = [(a, s) for a in años for s in semillas if clave(h, celda, intento, a, s) not in hechas]
            segundos = sum(años[a] for a, _ in pendientes)
            total += segundos
            registrar(f"  {h:<5} {celda:<4} intento {intento:>2} · {bu.describir(params)} · "
                      f"pendientes {len(pendientes)} de {len(años) * len(semillas)} · previsto ≈ {segundos / 60:.0f} min")
    registrar(f"Tiempo previsto ≈ {total / 3600:.1f} h.")
    if solo_mostrar:
        return

    reloj, bases, inicio = bu._Reloj(total), ex._bases(), time.perf_counter()
    for h in horizontes:
        comb = bu.combinacion(h)
        pliegues = bu._pliegues(bases, comb)
        _guardar_fichas(rutas["fichas"], h, pliegues)
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            for semilla in semillas:
                for año, train, evaluado in pliegues:
                    if clave(h, celda, intento, año, semilla) in hechas:
                        continue
                    fila, previsiones = _entrenar(comb, celda, intento, params, año, train, evaluado,
                                                  semilla, dispositivo)
                    # Primero las previsiones y después la fila: la fila marca el entrenamiento como hecho
                    _anadir_compacto(rutas["previsiones"], previsiones, COLUMNAS_PREVISIONES)
                    ex._anadir(rutas["entrenos"], [fila], bu.COLUMNAS_B)
                    reloj.avanzar(previsto[(h, celda)][año], fila["segundos"])
                    registrar(f"[{h} {celda} · intento {intento}] {año} semilla {semilla} → {ex._medido(fila)}"
                              f" · quedan ≈ {reloj.restante() / 3600:.1f} h")
            comun = comprobar_fase_b(dir_salida)
            comun = comun[(comun["horizonte"] == h) & (comun["modelo"] == celda)]
            if len(comun):
                maxima = comun["diferencia"].max()
                relativa = (comun["diferencia"] / comun["MAE fase B"]).max()
                # Con otro número de hilos el orden de las sumas cambia: diferencias de redondeo
                registrar(f"Comprobación · {h} {celda}: {len(comun)} entrenamientos repetidos de la fase B · "
                          + ("reproducen exactamente sus resultados" if maxima < 1e-9
                             else f"coinciden salvo redondeo (diferencia máxima de MAE {maxima:.1e} $)" if relativa < 1e-5
                             else f"NO coinciden (diferencia máxima de MAE {maxima:.2e} $)"))
    registrar(f"Estabilidad terminada en {(time.perf_counter() - inicio) / 3600:.2f} h.")


# --- Análisis ----------------------------------------------------------------------------------

def promedio(previsiones, semillas):
    """Previsión del promedio de esas semillas: la media de los precios que prevé cada una,
    expresada como variación logarítmica. Una fila por red y ficha, con cuántas semillas entraron."""
    sel = previsiones[previsiones["semilla"].isin(list(semillas))]
    claves = ["horizonte", "modelo", "intento", "pliegue", "fecha"]
    g = sel.assign(factor=np.exp(sel["variación prevista"])).groupby(claves, as_index=False, sort=False)
    salida = g.agg(factor=("factor", "mean"), semillas=("semilla", "nunique"),
                   **{"variación real": ("variación real", "first"), "precio origen": ("precio origen", "first")})
    salida["variación prevista"] = np.log(salida["factor"])
    return salida.drop(columns="factor")


def nota(previsiones, por=()):
    """«MAE / ingenuo» juntando las fichas de todos los pliegues (como `experimentos.resumir`),
    por horizonte y red (y por las columnas de `por`)."""
    p = previsiones
    real = p["precio origen"] * np.exp(p["variación real"])
    tabla = p.assign(error=(p["precio origen"] * np.exp(p["variación prevista"]) - real).abs(),
                     error_ingenuo=(p["precio origen"] - real).abs())
    medias = tabla.groupby(["horizonte", "modelo", *por], sort=False)[["error", "error_ingenuo"]].mean()
    return (medias["error"] / medias["error_ingenuo"]).rename("MAE / ingenuo")


def grupos(semillas, n):
    """Grupos disjuntos de n semillas seguidas. Las que sobran no se usan."""
    semillas = list(semillas)
    return [semillas[i:i + n] for i in range(0, len(semillas) - n + 1, n)]


def cambio_prevision(a, b):
    """Cuánto cambia la previsión entre dos promedios (o dos semillas) de la misma red: diferencia
    media de los precios previstos, en % del precio de partida y frente al error del ingenuo."""
    claves = ["horizonte", "modelo", "fecha"]
    m = a.merge(b[claves + ["variación prevista"]], on=claves, suffixes=("", " b"))
    diferencia = (np.exp(m["variación prevista"]) - np.exp(m["variación prevista b"])).abs()
    error_ingenuo = (1 - np.exp(m["variación real"])).abs()
    t = m.assign(diferencia=diferencia, error_ingenuo=error_ingenuo).groupby(["horizonte", "modelo"], sort=False)
    medias = t[["diferencia", "error_ingenuo"]].mean()
    return pd.DataFrame({"cambio de la previsión (% del precio)": medias["diferencia"] * 100,
                         "cambio / error del ingenuo": medias["diferencia"] / medias["error_ingenuo"]})


def curva_semillas(previsiones, tamaños=(1, 2, 3, 5, 10), semillas=None):
    """Para cada número de semillas promediadas, con grupos disjuntos de semillas:
    - la nota media de los grupos y su desviación entre grupos (el azar que queda);
    - cuánto cambia la previsión entre dos grupos (media de los pares de grupos seguidos)."""
    semillas = sorted(semillas or previsiones["semilla"].unique())
    tablas = []
    for n in tamaños:
        gs = grupos(semillas, n)
        if not gs:
            continue
        proms = [promedio(previsiones, g) for g in gs]
        notas = pd.concat([nota(p) for p in proms], axis=1)
        t = pd.DataFrame({"semillas promediadas": n, "grupos": len(gs), "MAE / ingenuo": notas.mean(axis=1),
                          "azar entre grupos": notas.std(axis=1, ddof=1) if len(gs) > 1 else np.nan})
        pares = [cambio_prevision(proms[i], proms[i + 1]) for i in range(0, len(proms) - 1, 2)]
        if pares:
            t = t.join(sum(pares) / len(pares))
        tablas.append(t)
    return pd.concat(tablas).reset_index().set_index(["horizonte", "modelo", "semillas promediadas"]).sort_index()
