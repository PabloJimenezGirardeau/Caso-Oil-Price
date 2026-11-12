"""Fase B (D16, D22): búsqueda de la mejor configuración de cada red con Optuna.

Para cada horizonte y cada red (RNN, LSTM, GRU), con los datos elegidos en la fase A
(`config.DATOS_FASE_B`) y sin tendencia (D20):

- `config.INTENTOS_FASE_B` intentos (40; a 1 semana, 20) con el mismo espacio de búsqueda para las tres redes
  (`config.ESPACIO_FASE_B`). El primero es la estructura base de la fase A, como referencia; los
  siguientes son al azar e iguales para las tres redes, y después Optuna (TPE) propone
  configuraciones cerca de las que mejor van.
- Cada intento se entrena en todos los pliegues de validación y se puntúa con «MAE / ingenuo»
  juntando los pliegues. A 1 año, con la media de 3 semillas; a 1 semana y a 3 meses, con una
  (`config.SEMILLAS_FASE_B`).
- Poda (`config.PODA_FASE_B`): desde el segundo pliegue, un intento que va peor que la mediana
  de los anteriores en ese mismo punto se abandona.
- Finalistas (D23): las 3 mejores configuraciones de cada red y, siempre, la estructura base (el
  intento 1), para que la búsqueda no acabe peor que donde empezó solo por azar.
- Confirmación: a 1 semana y a 3 meses, las finalistas se repiten con las semillas 43 y 44. A 1 año
  no hace falta: cada intento ya lleva 3 semillas.
- Elección (`decidir_configuracion`): la mejor media de las 3 semillas; las que quedan a menos de
  un ruido de ella empatan, y entre ellas gana la de menos parámetros.

Cada entrenamiento se guarda en cuanto termina, y cada intento al cerrarse. Si el proceso se
interrumpe, al relanzarlo los intentos cerrados se cargan en Optuna y el que quedó a medias se
repite con los mismos valores, sin volver a entrenar lo ya guardado. Tras una interrupción, los
intentos siguientes no son los mismos que sin ella (el azar de Optuna vuelve a empezar), pero la
búsqueda es igual de válida.
"""
import time

import numpy as np
import optuna
import pandas as pd
import torch

from . import config, entrenamiento as ent, experimentos as ex, preprocesado as pp

# Valores que propone Optuna en cada intento. La L2 se decide en dos pasos: si se usa y con qué
# fuerza. La fuerza se propone siempre, para que todos los intentos tengan los mismos ajustes
# (lo prefiere el muestreador de Optuna), y solo cuenta si se usa
PARAMETROS = ["unidades", "capas", "dropout", "lr", "lote", "con l2", "fuerza l2"]

CLAVE_B = ["horizonte", "modelo", "intento", "pliegue", "semilla"]
COLUMNAS_B = ["horizonte", "sesiones", "ventana", "recorte", "nivel", "modelo", "intento", *PARAMETROS,
              "pliegue", "semilla", "fichas train", "fichas evaluación", "MAE", "MSE", "MAE ingenuo",
              "MSE ingenuo", "MAE / ingenuo", "acierto dirección (%)", "parametros", "épocas",
              "mejor época", "segundos", "dispositivo", "momento"]
COLUMNAS_INTENTOS = ["horizonte", "modelo", "intento", "estado", "MAE / ingenuo", "pliegues", *PARAMETROS,
                     "parametros", "segundos", "momento"]
ARCHIVOS = {"entrenos": "fase_b.csv", "curvas": "fase_b_curvas.csv", "intentos": "fase_b_intentos.csv",
            "semillas": "fase_b_semillas.csv", "semillas_curvas": "fase_b_semillas_curvas.csv"}


# --- Espacio de búsqueda ----------------------------------------------------------------------

def distribuciones():
    """Rango de cada valor que propone Optuna (el mismo para las tres redes y horizontes)."""
    e, d = config.ESPACIO_FASE_B, optuna.distributions
    return {"unidades": d.IntDistribution(*e["unidades"], log=True),
            "capas": d.IntDistribution(*e["capas"]),
            "dropout": d.FloatDistribution(*e["dropout"]),
            "lr": d.FloatDistribution(*e["lr"], log=True),
            "lote": d.CategoricalDistribution(e["lote"]),
            "con l2": d.CategoricalDistribution([False, True]),
            "fuerza l2": d.FloatDistribution(*e["l2"], log=True)}


def sugerir(trial):
    """Valores de un intento, propuestos por Optuna dentro de `distribuciones()`."""
    e = config.ESPACIO_FASE_B
    return {"unidades": trial.suggest_int("unidades", *e["unidades"], log=True),
            "capas": trial.suggest_int("capas", *e["capas"]),
            "dropout": trial.suggest_float("dropout", *e["dropout"]),
            "lr": trial.suggest_float("lr", *e["lr"], log=True),
            "lote": trial.suggest_categorical("lote", e["lote"]),
            "con l2": trial.suggest_categorical("con l2", [False, True]),
            "fuerza l2": trial.suggest_float("fuerza l2", *e["l2"], log=True)}


def hiperparametros(params):
    """Valores de un intento → hiperparámetros para `entrenamiento.entrenar_red`."""
    return {"unidades": int(params["unidades"]), "capas": int(params["capas"]),
            "dropout": float(params["dropout"]), "lr": float(params["lr"]), "lote": int(params["lote"]),
            "l2": float(params["fuerza l2"]) if _si(params["con l2"]) else 0.0}


def parametros_base():
    """La estructura base de la fase A, expresada como un intento (el primero de cada búsqueda)."""
    base, e = config.HIPERPARAMETROS_BASE, config.ESPACIO_FASE_B
    return {"unidades": base["unidades"], "capas": base["capas"], "dropout": base["dropout"],
            "lr": base["lr"], "lote": base["lote"], "con l2": base["l2"] > 0,
            "fuerza l2": base["l2"] if base["l2"] > 0 else float(np.sqrt(e["l2"][0] * e["l2"][1]))}


def describir(params):
    hp = hiperparametros(params)
    l2 = f"L2 {hp['l2']:.0e}" if hp["l2"] else "sin L2"
    return (f"{hp['unidades']} neuronas × {hp['capas']} capa{'s' if hp['capas'] > 1 else ''} · "
            f"dropout {hp['dropout']:.2f} · lr {hp['lr']:.5f} · {l2} · lote {hp['lote']}")


def _si(valor):
    """Booleano leído de un CSV (puede llegar como texto)."""
    return valor if isinstance(valor, (bool, np.bool_)) else str(valor) == "True"


def _leer_params(fila):
    """Valores de un intento tal como los guarda el CSV, con su tipo original."""
    return {"unidades": int(fila["unidades"]), "capas": int(fila["capas"]), "dropout": float(fila["dropout"]),
            "lr": float(fila["lr"]), "lote": int(fila["lote"]), "con l2": bool(_si(fila["con l2"])),
            "fuerza l2": float(fila["fuerza l2"])}


# --- Datos, entrenamiento y puntuación --------------------------------------------------------

def combinacion(horizonte):
    return {"horizonte": horizonte, **config.DATOS_FASE_B[horizonte]}


def _pliegues(bases, comb):
    """(año, train, evaluado) de cada pliegue de validación que se evalúa en ese horizonte."""
    salida = []
    for pliegue in pp.pliegues_walk_forward():
        train, evaluado = ex._particion(bases, comb, pliegue)
        if len(evaluado) >= config.MIN_FICHAS_EVALUACION:
            salida.append((pliegue["hasta"].year, train, evaluado))
    return salida


def _entrenar_y_prever(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo):
    """Entrena una red con los valores de un intento, sin tendencia. Devuelve su fila, sus curvas
    y su previsión de cada ficha evaluada (variaciones logarítmicas)."""
    resultado = ent.entrenar_red(celda, train, hiperparametros(params), semilla=semilla, dispositivo=dispositivo,
                                 ajustes={"sin_tendencia": True})
    prediccion = ent.predecir(resultado, evaluado.X)
    fila = ex._fila(comb, celda, np.nan, año, evaluado, prediccion, len(train), intento=intento, **params,
                    semilla=semilla, parametros=resultado.parametros, épocas=len(resultado.historial),
                    **{"mejor época": resultado.mejor_epoca, "segundos": resultado.segundos,
                       "dispositivo": str(dispositivo)})
    curvas = resultado.historial.assign(horizonte=comb["horizonte"], modelo=celda, intento=intento,
                                        pliegue=año, semilla=semilla)
    return fila, curvas, prediccion


def _entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo):
    """Como `_entrenar_y_prever`, sin la previsión: su fila y sus curvas."""
    fila, curvas, _ = _entrenar_y_prever(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo)
    return fila, curvas


def puntuar(filas):
    """«MAE / ingenuo» de un intento: juntando sus pliegues (D16) y, si tiene varias, media de sus semillas."""
    return float(ex.resumir(pd.DataFrame(filas), por=["semilla"])["MAE / ingenuo"].mean())


def _intermedios(filas):
    """Puntuación acumulada tras cada pliegue (la que ve la poda), de un intento ya guardado."""
    años = sorted(filas["pliegue"].unique())
    return {paso: puntuar(filas[filas["pliegue"] <= año]) for paso, año in enumerate(años)}


# --- Archivos ------------------------------------------------------------------------------

def _leer(ruta, columnas):
    if not ruta.exists():
        return pd.DataFrame(columns=columnas)
    return pd.read_csv(ruta)


def _de(tabla, horizonte, celda):
    return tabla[(tabla["horizonte"] == horizonte) & (tabla["modelo"] == celda)]


def leer_resultados(dir_salida=config.DIR_RESULTADOS):
    """Entrenamientos de la búsqueda, intentos cerrados y entrenamientos de la confirmación."""
    return (_leer(dir_salida / ARCHIVOS["entrenos"], COLUMNAS_B),
            _leer(dir_salida / ARCHIVOS["intentos"], COLUMNAS_INTENTOS),
            _leer(dir_salida / ARCHIVOS["semillas"], COLUMNAS_B))


# --- Búsqueda ------------------------------------------------------------------------------

def _estudio():
    """Estudio de Optuna con la misma semilla para las tres redes: sus primeros intentos al azar
    son los mismos."""
    poda = config.PODA_FASE_B
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    return optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=config.SEMILLA, n_startup_trials=10),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=poda["intentos_sin_poda"],
                                           n_warmup_steps=poda["pliegues_sin_poda"]))


def _cargar(estudio, intentos_red, entrenos_red):
    """Carga en Optuna los intentos ya cerrados y devuelve los valores del que quedó a medias
    (o None). Los intentos se numeran desde 1, en orden; en Optuna, desde 0."""
    numeros = sorted(intentos_red["intento"].astype(int))
    if numeros != list(range(1, len(numeros) + 1)):
        raise ValueError(f"Los intentos guardados no son consecutivos: {numeros}")
    dist, estados = distribuciones(), optuna.trial.TrialState
    cerrados = []
    for fila in intentos_red.sort_values("intento").to_dict("records"):
        completo = fila["estado"] == "completo"
        cerrados.append(optuna.trial.create_trial(
            state=estados.COMPLETE if completo else estados.PRUNED,
            value=float(fila["MAE / ingenuo"]) if completo else None,
            params=_leer_params(fila), distributions=dist,
            intermediate_values=_intermedios(entrenos_red[entrenos_red["intento"] == fila["intento"]])))
    estudio.add_trials(cerrados)

    sueltos = entrenos_red[~entrenos_red["intento"].isin(numeros)]
    if sueltos.empty:
        return None
    if set(sueltos["intento"].astype(int)) != {len(numeros) + 1}:
        raise ValueError(f"Hay entrenamientos de intentos no cerrados: {sorted(set(sueltos['intento']))}")
    return _leer_params(sueltos.iloc[0])


class _Reloj:
    """Tiempo restante: lo previsto (lo que tardó la estructura base en la fase A), corregido con
    el ritmo real de esta ejecución."""

    def __init__(self, previsto_total):
        self.total, self.hecho_previsto, self.hecho_real = previsto_total, 0.0, 0.0

    def avanzar(self, previsto, real):
        self.hecho_previsto += previsto
        self.hecho_real += real

    def descontar(self, previsto):
        self.total -= previsto   # entrenamientos que ya no se harán (intento podado)

    def restante(self):
        ritmo = self.hecho_real / self.hecho_previsto if self.hecho_previsto > 0 else 1.0
        return max(self.total - self.hecho_previsto, 0.0) * ritmo


def _previsto_base(dir_salida, comb, celda, años):
    """Segundos que tardó la estructura base con esos datos en la fase A, por pliegue (o una
    estimación si no está)."""
    ruta = dir_salida / "fase_a.csv"
    tabla = pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=ex.COLUMNAS)
    datos = ex._datos(comb)
    sel = tabla[(tabla["modelo"] == celda) & (tabla["horizonte"] == datos["horizonte"])
                & (tabla["ventana"] == datos["ventana"]) & (tabla["recorte"] == datos["recorte"])
                & (tabla["nivel"] == datos["nivel"])]
    por_año = sel.groupby("pliegue")["segundos"].mean().to_dict()
    respaldo = float(np.mean(list(por_año.values()))) if por_año else 10.0
    return {año: float(por_año.get(año, respaldo)) for año in años}


def buscar(horizonte, celda, bases, dir_salida, intentos, reloj, previsto, registrar, dispositivo):
    """Búsqueda de una red en un horizonte (o su continuación). Devuelve el estudio de Optuna."""
    comb = combinacion(horizonte)
    semillas = config.SEMILLAS_FASE_B[horizonte]
    rutas = {k: dir_salida / v for k, v in ARCHIVOS.items()}
    entrenos, cerrados, _ = leer_resultados(dir_salida)
    entrenos, cerrados = _de(entrenos, horizonte, celda), _de(cerrados, horizonte, celda)

    estudio = _estudio()
    a_medias = _cargar(estudio, cerrados, entrenos)
    if a_medias is not None:
        estudio.enqueue_trial(a_medias)
    elif cerrados.empty:
        estudio.enqueue_trial(parametros_base())
    pendientes = intentos - len(cerrados)
    if pendientes <= 0:
        return estudio
    pliegues = _pliegues(bases, comb)
    etiqueta = f"{horizonte} {celda}"

    def objetivo(trial):
        params = sugerir(trial)
        intento = trial.number + 1
        previas = {(int(f["pliegue"]), int(f["semilla"])): f
                   for f in entrenos[entrenos["intento"] == intento].to_dict("records")}
        if any(_leer_params(f) != params for f in previas.values()):
            raise ValueError(f"{etiqueta} intento {intento}: lo guardado no coincide con los valores del intento")
        filas, inicio = [], time.perf_counter()
        for paso, (año, train, evaluado) in enumerate(pliegues):
            for semilla in semillas:
                fila = previas.get((año, semilla))
                if fila is None:
                    fila, curvas = _entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo)
                    ex._anadir(rutas["entrenos"], [fila], COLUMNAS_B)
                    ex._anadir(rutas["curvas"], curvas.to_dict("records"))
                    reloj.avanzar(previsto[celda][año], fila["segundos"])
                    registrar(f"[{etiqueta} · intento {intento}/{intentos}] {año}"
                              + (f" semilla {semilla}" if len(semillas) > 1 else "") + f" → {ex._medido(fila)}")
                else:
                    reloj.avanzar(previsto[celda][año], previsto[celda][año])
                filas.append(fila)
            valor = puntuar(filas)
            trial.report(valor, paso)
            podado = trial.should_prune()
            if podado or paso == len(pliegues) - 1:
                estado = "podado" if podado else "completo"
                faltan = [a for a, _, _ in pliegues[paso + 1:]]
                reloj.descontar(sum(previsto[celda][a] for a in faltan) * len(semillas))
                ex._anadir(rutas["intentos"], [{
                    "horizonte": horizonte, "modelo": celda, "intento": intento, "estado": estado,
                    "MAE / ingenuo": valor, "pliegues": paso + 1, **params,
                    "parametros": int(filas[0]["parametros"]),
                    "segundos": float(sum(f["segundos"] for f in filas)),
                    "momento": pd.Timestamp.now().isoformat(timespec="seconds")}], COLUMNAS_INTENTOS)
                mejor = min([t.value for t in estudio.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,))]
                            + ([valor] if not podado else []), default=np.nan)
                registrar(f"[{etiqueta} · intento {intento}/{intentos}] {estado.upper()} "
                          f"{'tras ' + str(paso + 1) + ' pliegues ' if podado else ''}· MAE/ingenuo {valor:.3f} · "
                          f"{describir(params)} · {int(filas[0]['parametros']):,} parámetros · "
                          f"{(time.perf_counter() - inicio) / 60:.1f} min · mejor hasta ahora {mejor:.3f} · "
                          f"quedan ≈ {reloj.restante() / 3600:.1f} h")
                if podado:
                    raise optuna.TrialPruned()
        return valor

    estudio.optimize(objetivo, n_trials=pendientes, catch=())
    return estudio


# --- Confirmación y elección ----------------------------------------------------------------

def finalistas_b(cerrados_red, n=config.N_FINALISTAS):
    """Las n mejores configuraciones (intentos completos) de una red en un horizonte y, si no está
    entre ellas, la estructura base (intento 1, D23): así compite con las mismas semillas."""
    completos = cerrados_red[cerrados_red["estado"] == "completo"]
    mejores = completos.nsmallest(n, "MAE / ingenuo")
    base = completos[(completos["intento"] == 1) & ~completos["intento"].isin(mejores["intento"])]
    return pd.concat([mejores, base])


def necesita_confirmacion(horizonte):
    """A 1 semana y a 3 meses cada intento lleva una semilla: las finalistas se repiten con más."""
    return len(config.SEMILLAS_FASE_B[horizonte]) == 1


def confirmar(horizonte, celda, bases, dir_salida, intentos, reloj, previsto, registrar, dispositivo):
    """Repite las finalistas de una red (las 3 mejores y la base) con las semillas 43 y 44 (o continúa)."""
    if not necesita_confirmacion(horizonte):
        return
    comb = combinacion(horizonte)
    rutas = {k: dir_salida / v for k, v in ARCHIVOS.items()}
    _, cerrados, confirmados = leer_resultados(dir_salida)
    cerrados = _de(cerrados, horizonte, celda)
    if len(cerrados) < intentos:
        registrar(f"{horizonte} {celda}: la búsqueda no está completa ({len(cerrados)}/{intentos}); "
                  f"no se confirma todavía.")
        return
    hechas = {ex._clave(f, CLAVE_B) for f in confirmados.to_dict("records")}
    pliegues = _pliegues(bases, comb)
    for fin in finalistas_b(cerrados).to_dict("records"):
        params, intento = _leer_params(fin), int(fin["intento"])
        for año, train, evaluado in pliegues:
            for semilla in config.SEMILLAS_EXTRA:
                clave = ex._clave({"horizonte": horizonte, "modelo": celda, "intento": intento,
                                   "pliegue": año, "semilla": semilla}, CLAVE_B)
                if clave in hechas:
                    continue
                fila, curvas = _entrenar(comb, celda, intento, params, año, train, evaluado, semilla, dispositivo)
                ex._anadir(rutas["semillas"], [fila], COLUMNAS_B)
                ex._anadir(rutas["semillas_curvas"], curvas.to_dict("records"))
                reloj.avanzar(previsto[celda][año], fila["segundos"])
                registrar(f"[{horizonte} {celda} · confirmación intento {intento}] {año} semilla {semilla} → "
                          f"{ex._medido(fila)} · quedan ≈ {reloj.restante() / 3600:.1f} h")


def decidir_configuracion(por_semilla, parametros):
    """Regla de elección de la configuración de una red (D16, D22).

    `por_semilla`: una fila por finalista (índice: intento) y una columna por semilla, con su
    «MAE / ingenuo». `parametros`: número de parámetros de cada finalista.
    - Ruido: desviación típica entre semillas, media de las finalistas.
    - Empatan con la mejor las finalistas cuya media esté a menos de un ruido de la mejor media.
    - Entre las empatadas gana la de menos parámetros (la más sencilla).
    Devuelve la tabla con media, desviación, parámetros, empate y elegida, y el ruido.
    """
    tabla = por_semilla.copy()
    tabla["media"] = por_semilla.mean(axis=1)
    tabla["desviación"] = por_semilla.std(axis=1, ddof=1)
    ruido = tabla["desviación"].mean()
    if pd.isna(ruido):
        ruido = 0.0
    tabla["parámetros"] = parametros.reindex(tabla.index)
    tabla["empata con la mejor"] = tabla["media"] - tabla["media"].min() <= ruido
    ganadora = tabla[tabla["empata con la mejor"]].sort_values(["parámetros", "media"]).index[0]
    tabla["elegida"] = tabla.index == ganadora
    return tabla, ruido


def eleccion(dir_salida=config.DIR_RESULTADOS, intentos=None):
    """Configuración elegida de cada red y horizonte con la búsqueda (y la confirmación) completas.

    `intentos`: los de la búsqueda completa; por defecto, los de `config.INTENTOS_FASE_B` en cada
    horizonte. Devuelve {(horizonte, red): (tabla, ruido)}, con la tabla de `decidir_configuracion`.
    """
    entrenos, cerrados, confirmados = leer_resultados(dir_salida)
    # Solo las tablas con filas: una vacía convertiría las columnas numéricas en texto
    todas = pd.concat([t for t in (entrenos, confirmados) if not t.empty] or [entrenos], ignore_index=True)
    salida = {}
    for h in config.HORIZONTES:
        for celda in config.CELDAS:
            cerrados_red = _de(cerrados, h, celda)
            if len(cerrados_red) < (intentos or config.INTENTOS_FASE_B[h]):
                continue
            fin = finalistas_b(cerrados_red)
            filas = _de(todas, h, celda)
            filas = filas[filas["intento"].isin(fin["intento"])]
            semillas = [config.SEMILLA, *config.SEMILLAS_EXTRA]
            if len(filas.groupby(["intento", "semilla"])) < len(fin) * len(semillas):
                continue   # falta la confirmación
            por_semilla = (ex.resumir(filas, por=["intento", "semilla"])
                           .pivot_table(index="intento", columns="semilla", values="MAE / ingenuo")
                           .reindex(fin["intento"]))
            salida[(h, celda)] = decidir_configuracion(por_semilla, fin.set_index("intento")["parametros"])
    return salida


# --- Ejecución -----------------------------------------------------------------------------

def ejecutar_fase_b(dir_salida=config.DIR_RESULTADOS, horizontes=None, modelos=None,
                    intentos=None, hilos=config.HILOS_CPU, registrar=print, solo_mostrar=False):
    """Ejecuta (o continúa) la fase B: búsqueda y confirmación de cada red, horizonte a horizonte,
    en el orden de `horizontes`. `intentos`, por defecto, los de `config.INTENTOS_FASE_B`."""
    horizontes = horizontes or list(config.HORIZONTES)
    modelos = modelos or list(config.CELDAS)
    n_intentos = {h: intentos or config.INTENTOS_FASE_B[h] for h in horizontes}
    torch.set_num_threads(hilos)
    dir_salida.mkdir(parents=True, exist_ok=True)
    dispositivo = ent.dispositivo_disponible()
    _, cerrados, confirmados = leer_resultados(dir_salida)

    # Plan y tiempo previsto (sin contar lo que ahorre la poda)
    previstos, total = {}, 0.0
    registrar(f"Fase B · {hilos} hilos · dispositivo {dispositivo}")
    for h in horizontes:
        comb, semillas, intentos = combinacion(h), config.SEMILLAS_FASE_B[h], n_intentos[h]
        años = [p["hasta"].year for p in pp.pliegues_walk_forward()]
        if h == "largo":
            años = años[:-1]   # el último pliegue no tiene respuestas a 1 año (caerían en el test)
        previstos[h] = {celda: _previsto_base(dir_salida, comb, celda, años) for celda in modelos}
        registrar(f"  {h} ({config.HORIZONTES[h]} sesiones) · {intentos} intentos por red · ventana {comb['ventana']} días · "
                  f"recorte {ex.nombre_recorte(comb['recorte'])} · {'con' if comb['nivel'] else 'sin'} nivel · "
                  f"semillas por intento: {semillas}")
        for celda in modelos:
            hechos = len(_de(cerrados, h, celda))
            por_intento = sum(previstos[h][celda].values()) * len(semillas)
            confirmacion = (sum(previstos[h][celda].values()) * (config.N_FINALISTAS + 1) * len(config.SEMILLAS_EXTRA)
                            if necesita_confirmacion(h) else 0.0)
            confirmacion -= len(_de(confirmados, h, celda)) * np.mean(list(previstos[h][celda].values()))
            pendiente = max(intentos - hechos, 0) * por_intento + max(confirmacion, 0.0)
            total += pendiente
            registrar(f"    {celda:<4} intentos hechos {hechos}/{intentos} · previsto ≈ {pendiente / 3600:.1f} h")
    registrar(f"Tiempo previsto ≈ {total / 3600:.1f} h sin contar la poda (con ella, bastante menos).")
    if solo_mostrar:
        return

    reloj, bases, inicio = _Reloj(total), ex._bases(), time.perf_counter()
    for h in horizontes:
        for celda in modelos:
            buscar(h, celda, bases, dir_salida, n_intentos[h], reloj, previstos[h], registrar, dispositivo)
        for celda in modelos:
            confirmar(h, celda, bases, dir_salida, n_intentos[h], reloj, previstos[h], registrar, dispositivo)
        for (hh, celda), (tabla, ruido) in eleccion(dir_salida, n_intentos[h]).items():
            if hh == h and celda in modelos:
                elegido = tabla.index[tabla["elegida"].to_numpy()][0]
                registrar(f"Elegida · {h} {celda}: intento {elegido} · MAE/ingenuo {tabla.loc[elegido, 'media']:.3f} "
                          f"(media de 3 semillas, ruido {ruido:.3f}) · {int(tabla.loc[elegido, 'parámetros']):,} parámetros")
    registrar(f"Fase B terminada en {(time.perf_counter() - inicio) / 3600:.2f} h.")
