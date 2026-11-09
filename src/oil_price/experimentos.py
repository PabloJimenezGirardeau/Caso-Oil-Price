"""Experimentos de búsqueda: fase A (estudio de los datos, D6, D9, D16), su confirmación (D19)
y el experimento sin tendencia (D20).

Fase A: para cada horizonte, cada combinación de ventana × recorte × indicador de nivel se
entrena con la estructura base en las tres redes y en todos los pliegues de validación.
También se ajusta el modelo lineal (D17) con cada fuerza de regularización.

Confirmación: las mejores combinaciones de cada horizonte se repiten con otras semillas,
para medir el ruido del entrenamiento y saber qué diferencias son reales.

Sin tendencia: la combinación elegida de cada horizonte se repite con las tres semillas, pero
sin la subida media del train (tendencia cero, como el ingenuo); el lineal, con todas las
combinaciones y fuerzas de regularización.

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

CLAVE_DATOS = ["horizonte", "ventana", "recorte", "nivel"]
CLAVE = CLAVE_DATOS + ["modelo", "alfa", "pliegue"]
CLAVE_SEMILLAS = CLAVE + ["semilla"]

# Formato fijo del archivo de resultados: todas las filas (redes y lineal) con las mismas columnas
COLUMNAS = ["horizonte", "sesiones", "ventana", "recorte", "nivel", "modelo", "alfa", "pliegue",
            "fichas train", "fichas evaluación", "MAE", "MSE", "MAE ingenuo", "MSE ingenuo",
            "MAE / ingenuo", "acierto dirección (%)", "parametros", "épocas", "mejor época",
            "segundos", "dispositivo", "semilla", "momento"]


def nombre_recorte(recorte):
    return "ninguno" if recorte is None else f"{recorte[0]:g}-{recorte[1]:g}"


RECORTE_POR_NOMBRE = {nombre_recorte(r): r for r in config.RECORTES}


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
    """Texto comparable para la clave: los vacíos (NaN) se convierten siempre en '', y los
    números enteros guardados como decimales (43.0, si la columna tiene vacíos) se escriben
    como enteros (43)."""
    if pd.isna(valor):
        return ""
    if isinstance(valor, (float, np.floating)) and float(valor).is_integer():
        return str(int(valor))
    return str(valor)


def _clave(fila, clave=CLAVE):
    return tuple(_texto(fila[k]) for k in clave)


def _ya_hechas(ruta, clave=CLAVE):
    """Claves de los entrenamientos ya guardados, para no repetirlos al reanudar."""
    if not ruta.exists():
        return set()
    hechas = pd.read_csv(ruta)
    return {_clave(fila, clave) for fila in hechas[clave].to_dict("records")}


def _anadir(ruta, filas, columnas=None):
    """Añade filas al final del archivo. Con `columnas`, todas las filas llevan ese formato fijo."""
    tabla = pd.DataFrame(filas)
    if columnas is not None:
        tabla = tabla.reindex(columns=columnas)
    tabla.to_csv(ruta, mode="a", header=not ruta.exists(), index=False)


def _datos(comb):
    """Columnas que identifican una combinación de datos, tal como se guardan."""
    return {"horizonte": comb["horizonte"], "ventana": comb["ventana"],
            "recorte": nombre_recorte(comb["recorte"]), "nivel": comb["nivel"]}


def _describir(comb, celda, año, semilla=None):
    texto = (f"{comb['horizonte']:<5} v={comb['ventana']:<3} rec={nombre_recorte(comb['recorte']):<8} "
             f"nivel={'sí' if comb['nivel'] else 'no'} {celda:<4} {año}")
    return texto if semilla is None else f"{texto} semilla {semilla}"


def _medido(fila):
    return (f"MAE/ingenuo {fila['MAE / ingenuo']:.3f} · {fila['épocas']:>3} épocas · "
            f"{fila['segundos']:5.1f} s")


def _particion(bases, comb, pliegue):
    """Fichas de train y de evaluación de una combinación en un pliegue, solo de su horizonte."""
    train_3h, eval_3h, _ = pp.construir_particion(bases[comb["nivel"]], comb["ventana"], comb["recorte"],
                                                  **pliegue)
    return pp.por_horizonte(train_3h, comb["horizonte"]), pp.por_horizonte(eval_3h, comb["horizonte"])


def _bases():
    """Datos limpios preparados con y sin indicador de nivel."""
    limpio = datos.cargar_datos_limpios()
    return {nivel: pp.preparar_base(limpio, con_nivel=nivel) for nivel in (True, False)}


def _filas_lineal(comb, año, train, evaluado, hechas, clave=CLAVE, sin_tendencia=False):
    """Modelo lineal con cada fuerza de regularización que falte: una fila por cada una."""
    filas = []
    for alfa in config.ALFAS_LINEAL:
        fila_clave = {**_datos(comb), "modelo": "Lineal", "alfa": alfa, "pliegue": año, "semilla": np.nan}
        if _clave(fila_clave, clave) in hechas:
            continue
        lineal = ModeloLineal(alfa, sin_tendencia=sin_tendencia).ajustar(train)
        filas.append(_fila(comb, "Lineal", alfa, año, evaluado, lineal.predecir(evaluado.X),
                           len(train), parametros=lineal.n_parametros))
    return filas


def _entrenar_y_medir(comb, celda, año, train, evaluado, semilla, dispositivo, ajustes=None):
    """Entrena una red con la estructura base y devuelve su fila de resultados y sus curvas."""
    resultado = ent.entrenar_red(celda, train, semilla=semilla, dispositivo=dispositivo, ajustes=ajustes)
    prediccion = ent.predecir(resultado, evaluado.X)
    fila = _fila(comb, celda, np.nan, año, evaluado, prediccion, len(train),
                 parametros=resultado.parametros, épocas=len(resultado.historial),
                 **{"mejor época": resultado.mejor_epoca, "segundos": resultado.segundos,
                    "dispositivo": str(dispositivo), "semilla": semilla})
    curvas = resultado.historial.assign(**_datos(comb), modelo=celda, pliegue=año)
    return fila, curvas


def nombre_fase_a(sin_tendencia=False):
    """Nombre base de los archivos de la fase A: con tendencia (la original) o sin ella (D20, D21)."""
    return "fase_a_sin_tendencia" if sin_tendencia else "fase_a"


def _claves_fase_a(combinaciones, pliegues):
    """Claves de los entrenamientos de redes de la fase A para esas combinaciones. A 252 sesiones
    se descuenta el último pliegue, que se omite por no tener respuestas."""
    ultimo_año = pliegues[-1]["hasta"].year
    return [_clave({**_datos(c), "modelo": celda, "alfa": np.nan, "pliegue": p["hasta"].year})
            for c in combinaciones for p in pliegues for celda in config.CELDAS
            if not (c["horizonte"] == "largo" and p["hasta"].year == ultimo_año)]


def ejecutar_fase_a(dir_salida=config.DIR_RESULTADOS, hilos=config.HILOS_CPU, limite=None,
                    registrar=print, ventanas=None, horizontes=None, sin_tendencia=False):
    """Ejecuta (o continúa) la fase A.

    `ventanas` / `horizontes`: solo esas ventanas u horizontes (para repartir el trabajo).
    `limite`: número máximo de combinaciones (para pruebas). `sin_tendencia` (D21): las redes
    se entrenan sin la subida media del train y se guardan en `fase_a_sin_tendencia.csv`; el
    lineal no se repite, porque sin tendencia ya está completo en `tendencia.csv` (D20).
    """
    torch.set_num_threads(hilos)
    dir_salida.mkdir(parents=True, exist_ok=True)
    nombre = nombre_fase_a(sin_tendencia)
    ruta, ruta_curvas = dir_salida / f"{nombre}.csv", dir_salida / f"{nombre}_curvas.csv"
    hechas = _ya_hechas(ruta)
    dispositivo = ent.dispositivo_disponible()
    ajustes = {"sin_tendencia": True} if sin_tendencia else None

    bases = _bases()
    pliegues = pp.pliegues_walk_forward()
    combinaciones = [c for c in combinaciones_fase_a()
                     if (ventanas is None or c["ventana"] in ventanas)
                     and (horizontes is None or c["horizonte"] in horizontes)][:limite]

    # Entrenamientos de redes de ESTA ejecución (las combinaciones elegidas) y cuántos ya estaban hechos
    claves = _claves_fase_a(combinaciones, pliegues)
    total, ya_hechos = len(claves), sum(clave in hechas for clave in claves)

    # Tiempo previsto: si la fase A original ya tiene esos entrenamientos (p. ej., al repetirla sin
    # tendencia), lo que tardaron allí; si no, la media de lo que se lleva hecho
    original = dir_salida / "fase_a.csv"
    previsto = _previsto(pd.read_csv(original)) if sin_tendencia and original.exists() else {}
    pendientes_previstos = {c: previsto.get(c) for c in claves if c not in hechas}
    con_previsto = bool(pendientes_previstos) and all(v is not None for v in pendientes_previstos.values())
    previsto_total = sum(pendientes_previstos.values()) if con_previsto else 0.0
    registrar(f"Fase A{' sin tendencia' if sin_tendencia else ''}: {len(combinaciones)} combinaciones → "
              f"{total} entrenamientos de redes "
              f"(ya hechos: {ya_hechos}, pendientes: {total - ya_hechos})"
              + (f" · tiempo previsto ≈ {previsto_total / 3600:.1f} h" if con_previsto else "")
              + f". Dispositivo: {dispositivo}, {hilos} hilos.")

    hechos_ahora, hecho_previsto, hecho_real, inicio = 0, 0.0, 0.0, time.perf_counter()
    for i, comb in enumerate(combinaciones, start=1):
        for pliegue in pliegues:
            año = pliegue["hasta"].year
            train, evaluado = _particion(bases, comb, pliegue)
            if len(evaluado) < config.MIN_FICHAS_EVALUACION:
                continue   # p. ej., 2021 a 252 sesiones: sus respuestas caerían en el test

            # Modelo lineal: una fila por cada fuerza de regularización (segundos en total)
            filas = [] if sin_tendencia else _filas_lineal(comb, año, train, evaluado, hechas)
            if filas:
                _anadir(ruta, filas, COLUMNAS)

            # Las tres redes, con la estructura base y la misma semilla
            for celda in config.CELDAS:
                clave = _clave({**_datos(comb), "modelo": celda, "alfa": np.nan, "pliegue": año})
                if clave in hechas:
                    continue
                fila, curvas = _entrenar_y_medir(comb, celda, año, train, evaluado, config.SEMILLA, dispositivo,
                                                 ajustes)
                _anadir(ruta, [fila], COLUMNAS)
                _anadir(ruta_curvas, curvas.to_dict("records"))

                hechos_ahora += 1
                if con_previsto:   # lo previsto, corregido con el ritmo real de esta ejecución
                    hecho_previsto += pendientes_previstos[clave]
                    hecho_real += fila["segundos"]
                    restante = (previsto_total - hecho_previsto) * hecho_real / max(hecho_previsto, 1e-9)
                else:
                    pendientes = total - ya_hechos - hechos_ahora
                    restante = (time.perf_counter() - inicio) / hechos_ahora * max(pendientes, 0)
                registrar(f"[{i}/{len(combinaciones)}] {_describir(comb, celda, año)} → {_medido(fila)} · "
                          f"quedan ≈ {restante / 3600:.1f} h")
    registrar(f"Fase A{' sin tendencia' if sin_tendencia else ''} terminada: {hechos_ahora} entrenamientos nuevos en "
              f"{(time.perf_counter() - inicio) / 3600:.2f} h.")


def finalistas(resultados, n=config.N_FINALISTAS):
    """Las n mejores combinaciones de datos de cada horizonte, por la media de las tres redes (D16)."""
    redes = resumir(resultados[resultados["modelo"] != "Lineal"])
    media = redes.groupby(CLAVE_DATOS, sort=False)["MAE / ingenuo"].mean().reset_index()
    elegidas = []
    for h in config.HORIZONTES:
        mejores = media[media["horizonte"] == h].nsmallest(n, "MAE / ingenuo")
        elegidas += [{"horizonte": h, "ventana": int(f["ventana"]), "recorte": RECORTE_POR_NOMBRE[f["recorte"]],
                      "nivel": bool(f["nivel"]), "fase A": f["MAE / ingenuo"]}
                     for f in mejores.to_dict("records")]
    return elegidas


def ejecutar_confirmacion(dir_salida=config.DIR_RESULTADOS, semillas=config.SEMILLAS_EXTRA,
                          n=config.N_FINALISTAS, hilos=config.HILOS_CPU, registrar=print,
                          elegidas=None, solo_mostrar=False, horizontes=None, sin_tendencia=False):
    """Repite las finalistas de la fase A con otras semillas (o continúa la repetición).

    Las finalistas son las `n` mejores de cada horizonte en `dir_salida/fase_a.csv`, salvo que se
    pasen en `elegidas`. Con `solo_mostrar`, solo las lista con el tiempo previsto, sin entrenar.
    `horizontes`: solo esos. `sin_tendencia` (D21): usa la fase A sin tendencia y entrena igual.
    """
    torch.set_num_threads(hilos)
    nombre = nombre_fase_a(sin_tendencia)
    pliegues = pp.pliegues_walk_forward()
    if elegidas is None:
        # Las finalistas solo son fiables con la fase A completa en esos horizontes
        combinaciones = [c for c in combinaciones_fase_a() if horizontes is None or c["horizonte"] in horizontes]
        faltan = set(_claves_fase_a(combinaciones, pliegues)) - _ya_hechas(dir_salida / f"{nombre}.csv")
        if faltan:
            registrar(f"La fase A{' sin tendencia' if sin_tendencia else ''} no está completa (faltan {len(faltan)} "
                      f"entrenamientos de redes): termínala antes con scripts/fase_a.py. No se entrena nada.")
            return []
    resultados_a = pd.read_csv(dir_salida / f"{nombre}.csv")
    elegidas = finalistas(resultados_a, n) if elegidas is None else elegidas
    elegidas = [c for c in elegidas if horizontes is None or c["horizonte"] in horizontes]
    ruta, ruta_curvas = dir_salida / f"{nombre}_semillas.csv", dir_salida / f"{nombre}_semillas_curvas.csv"
    pendientes = _pendientes_redes(elegidas, semillas, _ya_hechas(ruta, CLAVE_SEMILLAS),
                                   _previsto(resultados_a), pliegues)

    registrar(f"Finalistas de la fase A{' sin tendencia' if sin_tendencia else ''} ({n} por horizonte), "
              f"con las semillas {semillas}:")
    for comb in elegidas:
        registrar(f"  {_combinacion(comb)} · fase A {comb.get('fase A', np.nan):.3f}")
    registrar(f"Entrenamientos pendientes: {len(pendientes)} · tiempo previsto ≈ "
              f"{sum(pendientes.values()) / 3600:.1f} h ({hilos} hilos).")
    if solo_mostrar or not pendientes:
        return elegidas

    inicio = time.perf_counter()
    hechos = _entrenar_redes(elegidas, semillas, pendientes, _bases(), pliegues, ruta, ruta_curvas, registrar,
                             ajustes={"sin_tendencia": True} if sin_tendencia else None)
    registrar(f"Confirmación terminada: {hechos} entrenamientos nuevos en "
              f"{(time.perf_counter() - inicio) / 3600:.2f} h.")
    return elegidas


def _combinacion(comb):
    return (f"{comb['horizonte']:<5} ventana {comb['ventana']:>3} · recorte {nombre_recorte(comb['recorte']):<8} · "
            f"{'con' if comb['nivel'] else 'sin'} nivel")


def _previsto(resultados_a):
    """Segundos que tardó cada entrenamiento de redes en la fase A, para prever los que faltan."""
    redes_a = resultados_a[resultados_a["modelo"] != "Lineal"]
    return {_clave(f): f["segundos"] for f in redes_a.to_dict("records")}


def _pendientes_redes(elegidas, semillas, hechas, previsto, pliegues):
    """Entrenamientos de redes que faltan (combinación × pliegue × semilla × red), con su tiempo
    previsto: lo que tardó el mismo con la semilla 42 en la fase A."""
    ultimo_año = pliegues[-1]["hasta"].year
    pendientes = {}
    for comb in elegidas:
        for p in pliegues:
            if comb["horizonte"] == "largo" and p["hasta"].year == ultimo_año:
                continue   # sus respuestas caerían en el test
            for semilla in semillas:
                for celda in config.CELDAS:
                    fila = {**_datos(comb), "modelo": celda, "alfa": np.nan, "pliegue": p["hasta"].year}
                    clave = _clave({**fila, "semilla": semilla}, CLAVE_SEMILLAS)
                    if clave not in hechas:
                        pendientes[clave] = previsto.get(_clave(fila), 0.0)
    return pendientes


def _entrenar_redes(elegidas, semillas, pendientes, bases, pliegues, ruta, ruta_curvas, registrar,
                    ajustes=None):
    """Entrena las redes pendientes y guarda cada resultado en cuanto termina. Devuelve cuántas entrenó."""
    dispositivo = ent.dispositivo_disponible()
    previsto_total = sum(pendientes.values())
    hechos, hecho_previsto, hecho_real = 0, 0.0, 0.0
    for i, comb in enumerate(elegidas, start=1):
        for pliegue in pliegues:
            año = pliegue["hasta"].year
            train, evaluado = _particion(bases, comb, pliegue)
            if len(evaluado) < config.MIN_FICHAS_EVALUACION:
                continue
            for semilla in semillas:
                for celda in config.CELDAS:
                    clave = _clave({**_datos(comb), "modelo": celda, "alfa": np.nan, "pliegue": año,
                                    "semilla": semilla}, CLAVE_SEMILLAS)
                    if clave not in pendientes:
                        continue
                    fila, curvas = _entrenar_y_medir(comb, celda, año, train, evaluado, semilla, dispositivo,
                                                     ajustes)
                    _anadir(ruta, [fila], COLUMNAS)
                    _anadir(ruta_curvas, curvas.assign(semilla=semilla).to_dict("records"))

                    # Tiempo restante: lo previsto, corregido con el ritmo real de esta ejecución
                    hechos += 1
                    hecho_previsto += pendientes[clave]
                    hecho_real += fila["segundos"]
                    ritmo = hecho_real / hecho_previsto if hecho_previsto > 0 else 1.0
                    restante = (previsto_total - hecho_previsto) * ritmo
                    registrar(f"[{i}/{len(elegidas)}] {_describir(comb, celda, año, semilla)} → {_medido(fila)} · "
                              f"quedan ≈ {restante / 3600:.1f} h")
    return hechos


def eleccion(resultados_a, confirmacion, horizontes=None):
    """Combinación de datos elegida en cada horizonte (D19): las finalistas de la fase A con todas
    sus semillas (la 42 de la fase A y las de la confirmación), decididas con `decidir`.
    `horizontes`: solo esos (p. ej., la fase A sin tendencia, que solo se repite a 1 año)."""
    fin = pd.DataFrame([_datos(f) for f in finalistas(resultados_a)])
    redes_a = resultados_a[resultados_a["modelo"] != "Lineal"].merge(fin, on=CLAVE_DATOS)
    todas = pd.concat([redes_a, confirmacion], ignore_index=True)
    media = (resumir(todas, por=["semilla"]).groupby(CLAVE_DATOS + ["semilla"])["MAE / ingenuo"].mean()
             .unstack("semilla"))
    elegidas = {}
    for h in horizontes or config.HORIZONTES:
        tabla, _ = decidir(media.loc[h])
        v, r, n = tabla.index[tabla["elegida"].to_numpy()][0]
        elegidas[h] = {"horizonte": h, "ventana": int(v), "recorte": RECORTE_POR_NOMBRE[r], "nivel": bool(n)}
    return elegidas


def ejecutar_tendencia(dir_salida=config.DIR_RESULTADOS, semillas=None, horizontes=None,
                       hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    """Experimento sin tendencia (D20), o su continuación.

    - Redes: la combinación elegida de cada horizonte (D19), con las tres semillas.
    - Lineal: todas las combinaciones y fuerzas de regularización de la fase A (tarda minutos).
    Todo sin la subida media del train. Se guarda en `dir_salida/tendencia.csv`; lo mismo con
    tendencia ya está en la fase A y en su confirmación.
    """
    semillas = semillas or [config.SEMILLA, *config.SEMILLAS_EXTRA]
    horizontes = horizontes or list(config.HORIZONTES)
    torch.set_num_threads(hilos)
    resultados_a = pd.read_csv(dir_salida / "fase_a.csv")
    elegidas = [c for h, c in eleccion(resultados_a, pd.read_csv(dir_salida / "fase_a_semillas.csv")).items()
                if h in horizontes]
    ruta, ruta_curvas = dir_salida / "tendencia.csv", dir_salida / "tendencia_curvas.csv"
    hechas = _ya_hechas(ruta, CLAVE_SEMILLAS)
    pliegues = pp.pliegues_walk_forward()
    ultimo_año = pliegues[-1]["hasta"].year
    pendientes = _pendientes_redes(elegidas, semillas, hechas, _previsto(resultados_a), pliegues)

    combinaciones = [c for c in combinaciones_fase_a() if c["horizonte"] in horizontes]
    lineal_pendiente = [(c, p) for c in combinaciones for p in pliegues
                        if not (c["horizonte"] == "largo" and p["hasta"].year == ultimo_año)
                        and any(_clave({**_datos(c), "modelo": "Lineal", "alfa": a, "pliegue": p["hasta"].year,
                                        "semilla": np.nan}, CLAVE_SEMILLAS) not in hechas
                                for a in config.ALFAS_LINEAL)]

    registrar(f"Sin tendencia (D20) · combinación elegida de cada horizonte, con las semillas {semillas}:")
    for comb in elegidas:
        registrar(f"  {_combinacion(comb)}")
    registrar(f"Lineal: {len(lineal_pendiente)} combinaciones × pliegues pendientes (unos minutos). "
              f"Redes: {len(pendientes)} entrenamientos pendientes · tiempo previsto ≈ "
              f"{sum(pendientes.values()) / 3600:.1f} h ({hilos} hilos).")
    if solo_mostrar or not (pendientes or lineal_pendiente):
        return elegidas

    inicio, bases = time.perf_counter(), _bases()
    for i, (comb, pliegue) in enumerate(lineal_pendiente, start=1):
        train, evaluado = _particion(bases, comb, pliegue)
        if len(evaluado) < config.MIN_FICHAS_EVALUACION:
            continue
        filas = _filas_lineal(comb, pliegue["hasta"].year, train, evaluado, hechas, CLAVE_SEMILLAS,
                              sin_tendencia=True)
        if filas:
            _anadir(ruta, filas, COLUMNAS)
        if i % 20 == 0 or i == len(lineal_pendiente):
            registrar(f"Lineal: {i}/{len(lineal_pendiente)} ({(time.perf_counter() - inicio) / 60:.1f} min)")

    hechos = _entrenar_redes(elegidas, semillas, pendientes, bases, pliegues, ruta, ruta_curvas, registrar,
                             ajustes={"sin_tendencia": True})
    registrar(f"Sin tendencia terminado: {hechos} entrenamientos de redes nuevos en "
              f"{(time.perf_counter() - inicio) / 3600:.2f} h.")
    return elegidas


def solo_la_media(elegidas, bases=None):
    """Referencia (D20): un «modelo» que prevé siempre la subida media del train, sin mirar la ficha.

    Es lo que proyecta una red que no aprende nada útil: la misma media que `sin_tendencia` le
    quita (la del train de ajuste, sin el trozo de parada). Una fila por combinación y pliegue.
    """
    bases = bases or _bases()
    filas = []
    for comb in elegidas:
        for pliegue in pp.pliegues_walk_forward():
            train, evaluado = _particion(bases, comb, pliegue)
            if len(evaluado) < config.MIN_FICHAS_EVALUACION:
                continue
            ajuste, _ = ent.dividir_parada_temprana(train)
            media = np.nanmean(ajuste.Y, axis=0)
            prediccion = np.tile(media, (len(evaluado), 1)).astype(np.float32)
            filas.append(_fila(comb, "Solo la media", np.nan, pliegue["hasta"].year, evaluado, prediccion,
                               len(train), **{"subida media del train (%)": float(media[0]) * 100,
                                              "variación real media (%)": float(np.nanmean(evaluado.Y)) * 100}))
    return filas


def adoptar_sin_tendencia(con, sin, ruido):
    """Regla D20: se adopta «sin tendencia» si no empeora más de un ruido frente a «con tendencia».

    `con` y `sin`: «MAE / ingenuo» de cada variante (media de las tres redes y las semillas). En
    caso de empate se prefiere «sin tendencia», por prudente: supone lo mismo que el ingenuo.
    """
    return bool(sin - con <= ruido)


ORDEN_RECORTE = {"ninguno": 0, "0.5-99.5": 1, "1-99": 2}


def decidir(por_semilla):
    """Regla de elección de la combinación de datos de un horizonte (D6, D19).

    `por_semilla`: una fila por finalista (índice: ventana, recorte, nivel) y una columna por
    semilla, con su «MAE / ingenuo» medio en las tres redes.

    - Ruido: lo que cambia una misma finalista de una semilla a otra (desviación típica entre
      semillas, media de las finalistas).
    - Empatan con la mejor las finalistas cuya media esté a menos de un ruido de la mejor media.
    - Entre las empatadas gana la ventana más corta; con la misma ventana, la más sencilla
      (menos recorte y sin indicador de nivel).

    Devuelve la tabla con media, desviación, empate y elegida, y el ruido.
    """
    tabla = por_semilla.copy()
    tabla["media"] = por_semilla.mean(axis=1)
    tabla["desviación"] = por_semilla.std(axis=1, ddof=1)
    ruido = tabla["desviación"].mean()
    if pd.isna(ruido):   # con una sola semilla no se puede medir: nada empata salvo la propia mejor
        ruido = 0.0
    tabla["empata con la mejor"] = tabla["media"] - tabla["media"].min() <= ruido
    empatadas = tabla[tabla["empata con la mejor"]].reset_index()
    empatadas["orden recorte"] = empatadas["recorte"].map(ORDEN_RECORTE)
    ganadora = empatadas.sort_values(["ventana", "orden recorte", "nivel"]).iloc[0]
    tabla["elegida"] = [i == (ganadora["ventana"], ganadora["recorte"], ganadora["nivel"]) for i in tabla.index]
    return tabla, ruido


def resumir(resultados, por=()):
    """Junta los pliegues de cada combinación (cada ficha pesa igual) y calcula «MAE / ingenuo».

    Devuelve una fila por horizonte × ventana × recorte × nivel × modelo (× alfa en el lineal).
    Con `por` (p. ej., ["semilla"]), separa además por esas columnas.
    """
    r = resultados.assign(
        suma_ae=resultados["MAE"] * resultados["fichas evaluación"],
        suma_ae_ing=resultados["MAE ingenuo"] * resultados["fichas evaluación"],
        suma_se=resultados["MSE"] * resultados["fichas evaluación"],
        suma_se_ing=resultados["MSE ingenuo"] * resultados["fichas evaluación"],
        alfa=resultados["alfa"].fillna(-1))
    grupos = r.groupby(["horizonte", "ventana", "recorte", "nivel", "modelo", "alfa", *por], sort=False)
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
