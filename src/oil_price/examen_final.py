"""Examen final en test (D33): una sola vez, con el protocolo fijado antes de tocarlo.

- Cada red (RNN, LSTM y GRU, con la configuración elegida en la fase B) se entrena **una vez** con
  todo lo anterior al 1/1/2022 (train y validación, con purga), con las semillas 42-46, y prevé
  todas las fichas desde el 1/1/2022 cuya respuesta se conoce (hasta el 3/11/2026, D7).
  1 semana y 3 meses: el entrenamiento de siempre (parada temprana); 1 año: con todo el
  entrenamiento y épocas fijas (D31).
- El lineal de referencia (su regularización, sin tendencia) y el ingenuo.
- Rangos del 80 %: A2 a 1 semana y A3 a 3 meses y a 1 año, centrados en el precio de hoy (D30,
  D32), ajustados cada año con lo conocido antes del 1 de enero.

Cada entrenamiento se guarda en cuanto termina; si se interrumpe, al relanzar continúa donde se
quedó, sin repetir nada (sigue siendo una sola ejecución). El análisis está en el notebook 03.
"""
import time

import numpy as np
import pandas as pd
import torch

from . import busqueda as bu, combinacion as co, comprobaciones as cp, config, entrenamiento as ent
from . import estabilidad as es, experimentos as ex, hacia_atras as ha, incertidumbre as inc, preprocesado as pp

HORIZONTES = ["largo", "medio", "corto"]          # 1 semana, la más lenta, al final
CON_TODO = {"largo"}                              # D31: con todo el entrenamiento y épocas fijas
ELEGIDA = {"corto": "LSTM", "medio": "RNN", "largo": "RNN"}            # D33, fijada antes del test
METODO_RANGO = {"corto": "memoria", "medio": "centrado", "largo": "centrado"}   # D30 y D32
ARCHIVOS = {"entrenos": "examen.csv", "previsiones": "examen_previsiones.csv", "fichas": "examen_fichas.csv"}
CLAVE = ["horizonte", "modelo", "intento", "semilla"]
COLUMNAS_ENTRENOS = [*CLAVE, "épocas", "mejor época", "parametros", "segundos", "fichas de train", "fichas evaluadas"]
COLUMNAS_PREVISIONES = [*CLAVE, "fecha", "variación prevista"]
LINEAL = "Lineal"
SIGNIFICACION = 0.05


# --- Ejecución ----------------------------------------------------------------------------------

def particion(bases, h):
    """(train, evaluado) del examen: train hasta el 31/12/2021 con purga; evaluado desde el 1/1/2022."""
    return ex._particion(bases, bu.combinacion(h), pp.evaluacion_final())


def _entrenar(h, celda, intento, params, train, evaluado, semilla, dispositivo):
    ajustes = {"sin_tendencia": True}
    if h in CON_TODO:
        ajustes["epocas_fijas"] = config.EPOCAS_FIJAS[h][celda]
    r = ent.entrenar_red(celda, train, bu.hiperparametros(params), semilla=semilla, dispositivo=dispositivo,
                         ajustes=ajustes)
    fila = {"horizonte": h, "modelo": celda, "intento": intento, "semilla": semilla, "épocas": len(r.historial),
            "mejor época": r.mejor_epoca, "parametros": r.parametros, "segundos": r.segundos,
            "fichas de train": len(train), "fichas evaluadas": len(evaluado)}
    previsiones = pd.DataFrame({"horizonte": h, "modelo": celda, "intento": intento, "semilla": semilla,
                                "fecha": evaluado.fechas, "variación prevista": ent.predecir(r, evaluado.X)[:, 0]})
    return fila, previsiones


def _guardar_fichas(ruta, h, evaluado):
    """Lo que pasó en cada ficha del examen (variación real y precio de partida), una sola vez."""
    if ruta.exists() and h in set(pd.read_csv(ruta, usecols=["horizonte"])["horizonte"]):
        return
    es._anadir_compacto(ruta, pd.DataFrame({"horizonte": h, "fecha": evaluado.fechas,
                                            "variación real": evaluado.Y[:, 0],
                                            "precio origen": evaluado.precio_origen}),
                        ["horizonte", "fecha", "variación real", "precio origen"])


def _guardar_lineal(ruta, h, bases, train, evaluado, dir_salida):
    """Previsión del lineal de referencia (determinista: se guarda una sola vez)."""
    if ruta.exists():
        hechas = pd.read_csv(ruta, usecols=["horizonte", "modelo"])
        if ((hechas["horizonte"] == h) & (hechas["modelo"] == LINEAL)).any():
            return
    p = co.previsiones_lineal([h], dir_salida, bases, pliegues=lambda b, comb: [(0, train, evaluado)])
    tabla = pd.DataFrame({"horizonte": h, "modelo": LINEAL, "intento": 0, "semilla": np.nan,
                          "fecha": p["fecha"], "variación prevista": p["variación prevista"]})
    es._anadir_compacto(ruta, tabla, COLUMNAS_PREVISIONES)


def tiempo_previsto(dir_salida=config.DIR_RESULTADOS):
    """Segundos por entrenamiento: lo que tardaron en su último pliegue de validación (el de más
    datos; a 1 año, las redes entrenadas con todo), un 10 % más por los datos de más."""
    def ultimo_pliegue(t):
        salida = {}
        for (h, celda), g in t.groupby(["horizonte", "modelo"]):
            salida[(h, celda)] = 1.1 * float(g.loc[g["pliegue"] == g["pliegue"].max(), "segundos"].mean())
        return salida

    salida = ultimo_pliegue(es.leer_entrenos(dir_salida))
    ruta = dir_salida / "completo.csv"
    if ruta.exists():
        c = pd.read_csv(ruta)
        salida |= ultimo_pliegue(c[(c["variante"].astype(str) == "mediana") & c["horizonte"].isin(CON_TODO)])
    return salida


def ejecutar(dir_salida=config.DIR_RESULTADOS, horizontes=None, modelos=None, semillas=None,
             hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    horizontes = horizontes or HORIZONTES
    modelos = modelos or list(config.CELDAS)
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    torch.set_num_threads(hilos)
    dispositivo = ent.dispositivo_disponible()
    rutas = {k: dir_salida / v for k, v in ARCHIVOS.items()}
    eleg = es.elegidas(dir_salida)
    hechas = ex._ya_hechas(rutas["entrenos"], CLAVE)
    clave = lambda h, celda, intento, semilla: ex._clave(
        {"horizonte": h, "modelo": celda, "intento": intento, "semilla": semilla}, CLAVE)

    bases = ex._bases()
    particiones = {h: particion(bases, h) for h in horizontes}
    previsto = tiempo_previsto(dir_salida)
    registrar(f"Examen final en test (D33) · {hilos} hilos · dispositivo {dispositivo} · "
              f"semillas {semillas[0]}-{semillas[-1]}")
    total, segundos = 0, 0.0
    for h in horizontes:
        train, evaluado = particiones[h]
        registrar(f"  {h}: train {len(train)} fichas (hasta {pd.Timestamp(train.fechas[-1]).date()}) · "
                  f"evaluadas {len(evaluado)} ({pd.Timestamp(evaluado.fechas[0]).date()} → "
                  f"{pd.Timestamp(evaluado.fechas[-1]).date()})" + (" · con todo, épocas fijas" if h in CON_TODO else ""))
        for celda in modelos:
            pendientes = sum(clave(h, celda, eleg[(h, celda)][0], s) not in hechas for s in semillas)
            total += pendientes
            segundos += pendientes * previsto.get((h, celda), np.nan)
            registrar(f"    {celda:<4} intento {eleg[(h, celda)][0]:>2} · pendientes {pendientes} de {len(semillas)}")
    registrar(f"Entrenamientos pendientes: {total} · tiempo previsto ≈ {segundos / 60:.0f} min.")
    if solo_mostrar:
        return

    inicio, hechos = time.perf_counter(), 0
    for h in horizontes:
        train, evaluado = particiones[h]
        _guardar_fichas(rutas["fichas"], h, evaluado)
        _guardar_lineal(rutas["previsiones"], h, bases, train, evaluado, dir_salida)
        for celda in modelos:
            intento, params = eleg[(h, celda)]
            for semilla in semillas:
                if clave(h, celda, intento, semilla) in hechas:
                    continue
                fila, prev = _entrenar(h, celda, intento, params, train, evaluado, semilla, dispositivo)
                # Primero las previsiones y después la fila: la fila marca el entrenamiento como hecho
                es._anadir_compacto(rutas["previsiones"], prev, COLUMNAS_PREVISIONES)
                ex._anadir(rutas["entrenos"], [fila], COLUMNAS_ENTRENOS)
                hechos += 1
                registrar(f"[{h} {celda}] semilla {semilla} · {fila['épocas']} épocas · {fila['segundos']:5.0f} s · "
                          f"{hechos}/{total} en {(time.perf_counter() - inicio) / 60:.1f} min")
    registrar(f"Examen terminado en {(time.perf_counter() - inicio) / 60:.1f} min.")


# --- Lectura -------------------------------------------------------------------------------------

def leer_entrenos(dir_salida=config.DIR_RESULTADOS):
    ruta = dir_salida / ARCHIVOS["entrenos"]
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=COLUMNAS_ENTRENOS)


def leer_previsiones(dir_salida=config.DIR_RESULTADOS):
    """Cada previsión guardada, con lo que pasó y el año de la ficha (columna «pliegue»)."""
    p = pd.read_csv(dir_salida / ARCHIVOS["previsiones"], parse_dates=["fecha"], on_bad_lines="skip")
    p = p.drop_duplicates([*CLAVE, "fecha"], keep="last")
    fichas = pd.read_csv(dir_salida / ARCHIVOS["fichas"], parse_dates=["fecha"])
    p = p.merge(fichas, on=["horizonte", "fecha"], how="left", validate="many_to_one")
    return p.assign(pliegue=p["fecha"].dt.year)


def previsiones_examen(dir_salida=config.DIR_RESULTADOS, semillas=None):
    """Una previsión por modelo y ficha (formato de `hacia_atras.COLUMNAS`): cada red con el promedio
    de las semillas 42-46, la media de las tres redes y el lineal."""
    semillas = semillas or config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    p = leer_previsiones(dir_salida)
    redes = es.promedio(p[p["modelo"] != LINEAL], semillas)
    if (redes["semillas"] != len(semillas)).any():
        raise ValueError("Hay fichas sin todas las semillas: el examen no ha terminado")
    redes = redes[ha.COLUMNAS]
    lineal = p.loc[p["modelo"] == LINEAL, ha.COLUMNAS]
    return pd.concat([redes, ha.media_de_las_redes(redes)[ha.COLUMNAS], lineal], ignore_index=True)


# --- Medidas y conclusiones ------------------------------------------------------------------------

def tabla_comparativa(previsiones, entrenos):
    """La tabla que pide el enunciado, por horizonte y modelo: MAE, RMSE y MSE (en $), la mejora
    frente al ingenuo, la nota (MAE / ingenuo), el acierto de dirección, el número de parámetros y el
    tiempo de entrenamiento (media por semilla). El ingenuo, como una fila más."""
    p = previsiones
    real = p["precio origen"] * np.exp(p["variación real"])
    t = p.assign(error=p["precio origen"] * np.exp(p["variación prevista"]) - real,
                 error_ingenuo=p["precio origen"] - real,
                 acierto=np.sign(p["variación prevista"]) == np.sign(p["variación real"]))
    filas = {}
    for h, gh in t.groupby("horizonte", sort=False):
        for m, g in gh.groupby("modelo", sort=False):
            mae, mae_ing = g["error"].abs().mean(), g["error_ingenuo"].abs().mean()
            mse, mse_ing = (g["error"] ** 2).mean(), (g["error_ingenuo"] ** 2).mean()
            e = entrenos[(entrenos["horizonte"] == h) & (entrenos["modelo"] == m)]
            filas[(h, m)] = {"fichas": len(g), "MAE ($)": mae, "RMSE ($)": np.sqrt(mse), "MSE ($²)": mse,
                             "mejora frente al ingenuo (MAE)": 1 - mae / mae_ing, "MAE / ingenuo": mae / mae_ing,
                             "RMSE / ingenuo": np.sqrt(mse / mse_ing), "acierto de dirección": g["acierto"].mean(),
                             "parámetros": e["parametros"].iloc[0] if len(e) else np.nan,
                             "segundos por entrenamiento": e["segundos"].mean() if len(e) else np.nan}
        # El ingenuo: todas las previsiones de un horizonte son de las mismas fichas
        g = gh[gh["modelo"] == gh["modelo"].iloc[0]]
        mae_ing, mse_ing = g["error_ingenuo"].abs().mean(), (g["error_ingenuo"] ** 2).mean()
        filas[(h, "ingenuo")] = {"fichas": len(g), "MAE ($)": mae_ing, "RMSE ($)": np.sqrt(mse_ing),
                                 "MSE ($²)": mse_ing, "mejora frente al ingenuo (MAE)": 0.0, "MAE / ingenuo": 1.0,
                                 "RMSE / ingenuo": 1.0, "acierto de dirección": (g["variación real"] > 0).mean(),
                                 "parámetros": 0, "segundos por entrenamiento": 0.0}
    tabla = pd.DataFrame(filas).T
    tabla.index.names = ["horizonte", "modelo"]
    return tabla


def conclusion_prevision(p_valor, diferencia, significacion=SIGNIFICACION):
    """Las conclusiones fijadas en D33: (en el test, final junto con los 12 años de 2010-2021).
    En los 12 años ninguna red se sostuvo («dudosa» como mucho, que no es evidencia de ventaja)."""
    if p_valor >= significacion:
        return "sin evidencia de ventaja", "sin evidencia de ventaja"
    if diferencia < 0:
        return "mejor que el ingenuo en test", "ventaja posible, no confirmada"
    return "peor que el ingenuo en test", "peor que el ingenuo en test"


def conclusiones(previsiones):
    """Diebold-Mariano de cada modelo frente al ingenuo y su conclusión, en cada horizonte; se marca
    la red elegida para la aplicación (D33)."""
    dm = pd.concat([cp.diebold_mariano(previsiones, h) for h in previsiones["horizonte"].unique()])
    textos = [conclusion_prevision(pv, d) for pv, d in zip(dm["p (dos colas)"], dm["diferencia media ($)"])]
    dm["en el test"] = [a for a, _ in textos]
    dm["conclusión final"] = [b for _, b in textos]
    dm["elegida"] = [ELEGIDA.get(h) == m for h, m in dm.index]
    return dm


def rangos_examen(previsiones, ctx, alfa=inc.ALFA):
    """Rango elegido de cada horizonte y el ingenuo, centrados en el precio de hoy (D32), en cada
    ficha del examen. Centrado en el precio de hoy, el rango no depende de la red: se calcula una vez."""
    fichas = previsiones[previsiones["modelo"] == LINEAL].assign(modelo="precio de hoy")
    salida = []
    for h, metodo in METODO_RANGO.items():
        f = fichas[fichas["horizonte"] == h]
        if len(f):
            salida.append(inc.todos_los_rangos(inc.centro_hoy(f), ctx, metodos=["ingenuo", metodo], alfas=[alfa]))
    return pd.concat(salida, ignore_index=True)


def cumple_rango(cobertura, margen, objetivo=1 - inc.ALFA):
    """D33: el rango cumple si su cobertura queda a menos de dos márgenes del 80 %."""
    if abs(cobertura - objetivo) <= 2 * margen:
        return "cumple"
    return "se queda corto" if cobertura < objetivo else "se pasa"


def resumen_rangos(medidas):
    """Por horizonte y método: cobertura, su margen, los tercios, anchura, nota frente al ingenuo,
    fallos por abajo y por arriba y si cumple (D33)."""
    filas = {}
    for (h, metodo), m in medidas.groupby(["horizonte", "metodo"], sort=False):
        cobertura = m["dentro"].mean()
        margen = cp.margen_cobertura(cobertura, len(m), h)
        tercios = m.groupby("tercio", observed=True)["dentro"].mean()
        nota_ing = medidas[(medidas["horizonte"] == h) & (medidas["metodo"] == "ingenuo")]["nota"].mean()
        filas[(h, metodo)] = {"fichas": len(m), "cobertura": cobertura, "margen (±)": margen,
                              **{t: tercios.get(t, np.nan) for t in inc.TERCIOS},
                              "anchura (%)": m["anchura"].mean(), "nota / ingenuo": m["nota"].mean() / nota_ing,
                              "falla por abajo": (m["variación real"] < m["bajo"]).mean(),
                              "falla por arriba": (m["variación real"] > m["alto"]).mean(),
                              "elegido": metodo == METODO_RANGO[h],
                              "veredicto": cumple_rango(cobertura, margen)}
    t = pd.DataFrame(filas).T
    t.index.names = ["horizonte", "metodo"]
    return t
