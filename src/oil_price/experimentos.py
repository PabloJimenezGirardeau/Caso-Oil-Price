"""Experimentos de búsqueda: fase A (estudio de los datos, D6, D9, D16).

Fase A: para cada horizonte, cada combinación de ventana × recorte × indicador de nivel se
entrena con la estructura base en las tres redes y en todos los pliegues de validación.
También se ajusta el modelo lineal (D17) con cada fuerza de regularización.

Cada resultado se guarda en cuanto termina. Si el proceso se interrumpe, al relanzarlo
continúa donde se quedó.
"""
import itertools
import time
from datetime import datetime

import numpy as np
import pandas as pd
import torch

from . import config, datos, entrenamiento as ent, evaluacion as ev, preprocesado as pp
from .modelos import ModeloLineal

CLAVE = ["horizonte", "ventana", "recorte", "nivel", "modelo", "alfa", "pliegue"]

# Formato fijo del archivo de resultados: todas las filas (redes y lineal) con las mismas columnas
COLUMNAS = ["horizonte", "sesiones", "ventana", "recorte", "nivel", "modelo", "alfa", "pliegue",
            "fichas train", "fichas evaluación", "MAE", "MSE", "MAE ingenuo", "MSE ingenuo",
            "MAE / ingenuo", "acierto dirección (%)", "parametros", "épocas", "mejor época",
            "segundos", "dispositivo", "semilla", "momento"]


def nombre_recorte(recorte):
    return "ninguno" if recorte is None else f"{recorte[0]:g}-{recorte[1]:g}"


def combinaciones_fase_a():
    """Todas las combinaciones de datos de la fase A, en el orden en que se ejecutan."""
    return [dict(horizonte=h, ventana=v, recorte=r, nivel=n)
            for h, v, r, n in itertools.product(config.HORIZONTES, config.VENTANAS,
                                                config.RECORTES, (True, False))]


def _fila(combinacion, modelo, alfa, pliegue, evaluado, prediccion, n_train, **extra):
    comparacion = ev.comparar_con_ingenuo(ev.errores(evaluado, prediccion), ev.errores(evaluado))
    c = comparacion.iloc[0]
    direccion = float(np.mean(np.sign(prediccion[:, 0]) == np.sign(evaluado.Y[:, 0])) * 100)
    return {"horizonte": combinacion["horizonte"], "sesiones": config.HORIZONTES[combinacion["horizonte"]],
            "ventana": combinacion["ventana"], "recorte": nombre_recorte(combinacion["recorte"]),
            "nivel": combinacion["nivel"], "modelo": modelo, "alfa": alfa, "pliegue": pliegue,
            "fichas train": n_train, "fichas evaluación": int(c["muestras"]),
            "MAE": c["MAE"], "MSE": c["RMSE"] ** 2,
            "MAE ingenuo": c["MAE ingenuo"], "MSE ingenuo": c["RMSE ingenuo"] ** 2,
            "MAE / ingenuo": c["MAE / ingenuo"], "acierto dirección (%)": direccion,
            **extra, "momento": datetime.now().isoformat(timespec="seconds")}


def _texto(valor):
    """Texto comparable para la clave: los vacíos (NaN) se convierten siempre en ''."""
    return "" if pd.isna(valor) else str(valor)


def _clave(fila):
    return tuple(_texto(fila[k]) for k in CLAVE)


def _ya_hechas(ruta):
    """Claves de los entrenamientos ya guardados, para no repetirlos al reanudar."""
    if not ruta.exists():
        return set()
    hechas = pd.read_csv(ruta)
    return {_clave(fila) for fila in hechas[CLAVE].to_dict("records")}


def _anadir(ruta, filas, columnas=None):
    """Añade filas al final del archivo. Con `columnas`, todas las filas llevan ese formato fijo."""
    tabla = pd.DataFrame(filas)
    if columnas is not None:
        tabla = tabla.reindex(columns=columnas)
    tabla.to_csv(ruta, mode="a", header=not ruta.exists(), index=False)


def ejecutar_fase_a(dir_salida=config.DIR_RESULTADOS, hilos=config.HILOS_CPU, limite=None,
                    registrar=print, ventanas=None):
    """Ejecuta (o continúa) la fase A.

    `ventanas`: solo esas ventanas (para repartir el trabajo, p. ej. las cortas en el portátil
    y las largas en la GPU). `limite`: número máximo de combinaciones (para pruebas).
    """
    torch.set_num_threads(hilos)
    dir_salida.mkdir(parents=True, exist_ok=True)
    ruta, ruta_curvas = dir_salida / "fase_a.csv", dir_salida / "fase_a_curvas.csv"
    hechas = _ya_hechas(ruta)
    dispositivo = ent.dispositivo_disponible()

    limpio = datos.cargar_datos_limpios()
    bases = {nivel: pp.preparar_base(limpio, con_nivel=nivel) for nivel in (True, False)}
    pliegues = pp.pliegues_walk_forward()
    combinaciones = [c for c in combinaciones_fase_a()
                     if ventanas is None or c["ventana"] in ventanas][:limite]

    # Entrenamientos de redes de ESTA ejecución (las combinaciones elegidas) y cuántos ya estaban hechos.
    # A 252 sesiones se descuenta el último pliegue, que se omite por no tener respuestas.
    ultimo_año = pliegues[-1]["hasta"].year
    claves = [_clave({"horizonte": c["horizonte"], "ventana": c["ventana"],
                      "recorte": nombre_recorte(c["recorte"]), "nivel": c["nivel"],
                      "modelo": celda, "alfa": np.nan, "pliegue": p["hasta"].year})
              for c in combinaciones for p in pliegues for celda in config.CELDAS
              if not (c["horizonte"] == "largo" and p["hasta"].year == ultimo_año)]
    total, ya_hechos = len(claves), sum(clave in hechas for clave in claves)
    registrar(f"Fase A: {len(combinaciones)} combinaciones → {total} entrenamientos de redes "
              f"(ya hechos: {ya_hechos}, pendientes: {total - ya_hechos}). "
              f"Dispositivo: {dispositivo}, {hilos} hilos.")

    hechos_ahora, segundos_redes, inicio = 0, [], time.perf_counter()
    for i, comb in enumerate(combinaciones, start=1):
        for pliegue in pliegues:
            año = pliegue["hasta"].year
            train_3h, eval_3h, _ = pp.construir_particion(
                bases[comb["nivel"]], comb["ventana"], comb["recorte"], **pliegue)
            train = pp.por_horizonte(train_3h, comb["horizonte"])
            evaluado = pp.por_horizonte(eval_3h, comb["horizonte"])
            if len(evaluado) < config.MIN_FICHAS_EVALUACION:
                continue   # p. ej., 2021 a 252 sesiones: sus respuestas caerían en el test

            # Modelo lineal: una fila por cada fuerza de regularización (segundos en total)
            filas = []
            for alfa in config.ALFAS_LINEAL:
                fila = {"horizonte": comb["horizonte"], "ventana": comb["ventana"],
                        "recorte": nombre_recorte(comb["recorte"]), "nivel": comb["nivel"],
                        "modelo": "Lineal", "alfa": alfa, "pliegue": año}
                if _clave(fila) in hechas:
                    continue
                lineal = ModeloLineal(alfa).ajustar(train)
                filas.append(_fila(comb, "Lineal", alfa, año, evaluado, lineal.predecir(evaluado.X),
                                   len(train), parametros=lineal.n_parametros))
            if filas:
                _anadir(ruta, filas, COLUMNAS)

            # Las tres redes, con la estructura base y la misma semilla
            for celda in config.CELDAS:
                fila = {"horizonte": comb["horizonte"], "ventana": comb["ventana"],
                        "recorte": nombre_recorte(comb["recorte"]), "nivel": comb["nivel"],
                        "modelo": celda, "alfa": np.nan, "pliegue": año}
                if _clave(fila) in hechas:
                    continue
                resultado = ent.entrenar_red(celda, train, dispositivo=dispositivo)
                prediccion = ent.predecir(resultado, evaluado.X)
                _anadir(ruta, [_fila(comb, celda, np.nan, año, evaluado, prediccion, len(train),
                                     parametros=resultado.parametros, épocas=len(resultado.historial),
                                     **{"mejor época": resultado.mejor_epoca, "segundos": resultado.segundos,
                                        "dispositivo": str(dispositivo), "semilla": config.SEMILLA})],
                        COLUMNAS)
                curvas = resultado.historial.assign(
                    horizonte=comb["horizonte"], ventana=comb["ventana"],
                    recorte=nombre_recorte(comb["recorte"]), nivel=comb["nivel"], modelo=celda, pliegue=año)
                _anadir(ruta_curvas, curvas.to_dict("records"))

                hechos_ahora += 1
                segundos_redes.append(resultado.segundos)
                transcurrido = time.perf_counter() - inicio
                pendientes = total - ya_hechos - hechos_ahora
                restante = transcurrido / hechos_ahora * max(pendientes, 0)
                ratio = ev.comparar_con_ingenuo(ev.errores(evaluado, prediccion),
                                                ev.errores(evaluado))["MAE / ingenuo"].iloc[0]
                registrar(f"[{i}/{len(combinaciones)}] {comb['horizonte']:<5} v={comb['ventana']:<3} "
                          f"rec={nombre_recorte(comb['recorte']):<8} nivel={'sí' if comb['nivel'] else 'no'} "
                          f"{celda:<4} {año} → MAE/ingenuo {ratio:.3f} · {len(resultado.historial):>3} épocas · "
                          f"{resultado.segundos:5.1f} s · quedan ≈ {restante / 3600:.1f} h")
    registrar(f"Fase A terminada: {hechos_ahora} entrenamientos nuevos en "
              f"{(time.perf_counter() - inicio) / 3600:.2f} h.")


def resumir(resultados):
    """Junta los pliegues de cada combinación (cada ficha pesa igual) y calcula «MAE / ingenuo».

    Devuelve una fila por horizonte × ventana × recorte × nivel × modelo (× alfa en el lineal).
    """
    r = resultados.assign(
        suma_ae=resultados["MAE"] * resultados["fichas evaluación"],
        suma_ae_ing=resultados["MAE ingenuo"] * resultados["fichas evaluación"],
        suma_se=resultados["MSE"] * resultados["fichas evaluación"],
        suma_se_ing=resultados["MSE ingenuo"] * resultados["fichas evaluación"],
        alfa=resultados["alfa"].fillna(-1))
    grupos = r.groupby(["horizonte", "ventana", "recorte", "nivel", "modelo", "alfa"], sort=False)
    resumen = grupos.agg(pliegues=("pliegue", "nunique"), fichas=("fichas evaluación", "sum"),
                         suma_ae=("suma_ae", "sum"), suma_ae_ing=("suma_ae_ing", "sum"),
                         suma_se=("suma_se", "sum"), suma_se_ing=("suma_se_ing", "sum"))
    resumen["MAE"] = resumen["suma_ae"] / resumen["fichas"]
    resumen["MAE ingenuo"] = resumen["suma_ae_ing"] / resumen["fichas"]
    resumen["RMSE"] = np.sqrt(resumen["suma_se"] / resumen["fichas"])
    resumen["RMSE ingenuo"] = np.sqrt(resumen["suma_se_ing"] / resumen["fichas"])
    resumen["MAE / ingenuo"] = resumen["MAE"] / resumen["MAE ingenuo"]
    resumen = resumen.drop(columns=[c for c in resumen.columns if c.startswith("suma_")]).reset_index()
    resumen["alfa"] = resumen["alfa"].replace(-1, np.nan)
    return resumen
