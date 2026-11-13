"""Rango de incertidumbre (D30): cuánto puede moverse el precio.

Para cada previsión, un rango del 80 % (por defecto): «el precio estará entre X e Y $ con un
80 % de probabilidad». Se comparan tres rangos, ajustados **solo con lo ya conocido al empezar
cada año** (errores de fichas cuya respuesta llegó antes del 1 de enero):

- `ingenuo` (la referencia): centrado en el precio de hoy, con los percentiles de las variaciones
  a h sesiones de todos los años anteriores. Igual de ancho en calma y en tormenta.
- `fijo`: centrado en la previsión del modelo, con los percentiles de sus errores pasados.
- `volatilidad` (A, D8): centrado en la previsión, con los percentiles de los errores pasados
  divididos por la volatilidad de ese momento (la de 21 días, llevada al horizonte con la raíz del
  tiempo) y multiplicados por la volatilidad de hoy.
- `memoria` (A2): como A, pero el ancho crece con la volatilidad solo lo que dura de verdad el
  nerviosismo. La «memoria» m (entre 0 y 1) se aprende cada año de las variaciones ya conocidas
  desde 2001: es la pendiente de log|variación| sobre log(volatilidad / normal). El ancho se
  multiplica por (volatilidad de hoy / normal)^m. Con m = 0 es un rango fijo; con m = 1, como A.
  Se ajusta con las variaciones pasadas (los errores del ingenuo) porque los errores de las redes
  solo existen desde 2010 y no conocen la caída de 2008; la red está casi en el precio de hoy.
- `centrado` (A3): como A2, con tres cambios fijados antes de calcular. Ancho simétrico y sin
  tendencia (± el percentil 1 − α de |variación escalada − su mediana|); suelo en calma (la escala
  es (máximo(volatilidad de hoy, normal) / normal)^m: los datos hasta 2009 muestran que la calma no
  anticipa movimientos más pequeños); y la memoria m estimada con el método robusto
  (`comprobaciones.memoria_robusta`) solo con los días de volatilidad por encima de la normal.

Medidas: cobertura (cuántas veces el precio real quedó dentro), anchura (en % del precio de hoy)
y la puntuación de intervalos (anchura más un castigo de 2/α veces lo que el precio se sale; la
habitual para juzgar intervalos, Gneiting y Raftery, 2007), también en % del precio.
"""
import numpy as np
import pandas as pd

from . import config, experimentos as ex

METODOS = ["ingenuo", "fijo", "volatilidad", "memoria", "centrado"]
ALFA = 0.20          # rango del 80 %
ALFAS_INFO = [0.50, 0.05]   # 50 % y 95 %, solo como información
COBERTURA_MIN, COBERTURA_MAX, COBERTURA_TERCIO_MIN = 0.75, 0.85, 0.70
MEJORA_CENTRO = 0.01   # D32: mejora mínima de la nota para centrar el rango en la previsión de las redes
TERCIOS = ["calma", "normal", "tormenta"]


def contexto(bases=None):
    """Para cada día de origen: volatilidad anualizada de 21 días (con las variaciones reales) y,
    por horizonte, la fecha en que se conoce la respuesta y la variación real (para el rango
    ingenuo, con todos los años)."""
    bases = bases if bases is not None else ex._bases()
    base = bases[False]
    ctx = pd.DataFrame({"volatilidad": np.exp(base.entradas["log_vol_brent"])})
    for h in config.HORIZONTES:
        ctx[f"fin {h}"] = base.fechas_objetivo[h]
        ctx[f"variación {h}"] = base.objetivos[h]
    return ctx


def preparar(previsiones, ctx):
    """Añade a cada ficha su fecha de respuesta, la volatilidad de su origen y la escala del horizonte."""
    salida = []
    for h, p in previsiones.groupby("horizonte", sort=False):
        c = ctx[["volatilidad", f"fin {h}"]].rename(columns={f"fin {h}": "fecha fin"})
        p = p.merge(c, left_on="fecha", right_index=True, how="left", validate="many_to_one")
        p["escala"] = p["volatilidad"] * np.sqrt(config.HORIZONTES[h] / 252)
        salida.append(p)
    p = pd.concat(salida, ignore_index=True)
    if p[["volatilidad", "fecha fin"]].isna().any().any():
        raise ValueError("Fichas sin volatilidad o sin fecha de respuesta")
    return p


def _cuantiles(valores, alfa):
    return np.quantile(np.asarray(valores, np.float64), [alfa / 2, 1 - alfa / 2])


def memoria(variaciones, volatilidad):
    """Cuánto anticipa la volatilidad de hoy el tamaño del movimiento siguiente: la pendiente de
    log|variación| sobre log(volatilidad / normal), limitada entre 0 y 1. Devuelve (m, normal)."""
    normal = float(np.median(volatilidad))
    x = np.log(np.asarray(volatilidad, np.float64) / normal)
    y = np.log(np.abs(np.asarray(variaciones, np.float64)) + 1e-8)
    m = float(np.polyfit(x, y, 1)[0])
    return min(max(m, 0.0), 1.0), normal


def rangos(p, ctx, metodo, alfa=ALFA, años=None):
    """Rango de cada ficha de un horizonte y un modelo, año a año, ajustado solo con lo conocido
    antes de empezar ese año. Devuelve las fichas evaluadas con `bajo` y `alto` (variación
    logarítmica respecto al precio de hoy). Sin datos con los que ajustar, el año no se evalúa."""
    h = p["horizonte"].iloc[0]
    años = años if años is not None else sorted(p["pliegue"].unique())
    salida = []
    for año in años:
        inicio = pd.Timestamp(año, 1, 1)
        hoy = p[p["pliegue"] == año]
        conocido = p[p["fecha fin"] < inicio]
        extra = {}
        if metodo == "ingenuo":
            pasado = ctx.loc[ctx[f"fin {h}"] < inicio, f"variación {h}"].dropna()
            if len(pasado) == 0:
                continue
            q = _cuantiles(pasado, alfa)
            bajo, alto = np.full(len(hoy), q[0]), np.full(len(hoy), q[1])
        elif metodo == "memoria":
            pasado = ctx.loc[ctx[f"fin {h}"] < inicio, [f"variación {h}", "volatilidad"]].dropna()
            if len(pasado) == 0:
                continue
            m, normal = memoria(pasado[f"variación {h}"], pasado["volatilidad"])
            q = _cuantiles(pasado[f"variación {h}"] / (pasado["volatilidad"] / normal) ** m, alfa)
            escala_hoy = (hoy["volatilidad"] / normal) ** m
            bajo = hoy["variación prevista"] + escala_hoy * q[0]
            alto = hoy["variación prevista"] + escala_hoy * q[1]
            extra = {"memoria": m}
        elif metodo == "centrado":
            from .comprobaciones import memoria_robusta
            pasado = ctx.loc[ctx[f"fin {h}"] < inicio, [f"variación {h}", "volatilidad"]].dropna()
            if len(pasado) == 0:
                continue
            normal = float(np.median(pasado["volatilidad"]))
            nervioso = pasado[pasado["volatilidad"] >= normal]
            m = memoria_robusta(nervioso[f"variación {h}"], nervioso["volatilidad"])
            z = pasado[f"variación {h}"] / (np.maximum(pasado["volatilidad"], normal) / normal) ** m
            q = float(np.quantile(np.abs(z - np.median(z)), 1 - alfa))
            escala_hoy = (np.maximum(hoy["volatilidad"], normal) / normal) ** m
            bajo = hoy["variación prevista"] - escala_hoy * q
            alto = hoy["variación prevista"] + escala_hoy * q
            extra = {"memoria": m}
        else:
            if len(conocido) == 0:
                continue
            error = conocido["variación real"] - conocido["variación prevista"]
            if metodo == "fijo":
                q = _cuantiles(error, alfa)
                bajo, alto = hoy["variación prevista"] + q[0], hoy["variación prevista"] + q[1]
            elif metodo == "volatilidad":
                q = _cuantiles(error / conocido["escala"], alfa)
                bajo = hoy["variación prevista"] + hoy["escala"] * q[0]
                alto = hoy["variación prevista"] + hoy["escala"] * q[1]
            else:
                raise ValueError(f"Método desconocido: {metodo}")
        salida.append(hoy.assign(metodo=metodo, alfa=alfa, bajo=np.asarray(bajo), alto=np.asarray(alto), **extra))
    return pd.concat(salida, ignore_index=True) if salida else pd.DataFrame()


def medir(r, alfa=ALFA):
    """Añade a cada ficha si el precio quedó dentro, la anchura y la puntuación de intervalos (en %
    del precio de hoy)."""
    precio_bajo, precio_alto, real = np.exp(r["bajo"]), np.exp(r["alto"]), np.exp(r["variación real"])
    castigo = (2 / alfa) * ((precio_bajo - real).clip(lower=0) + (real - precio_alto).clip(lower=0))
    return r.assign(dentro=(real >= precio_bajo) & (real <= precio_alto),
                    anchura=100 * (precio_alto - precio_bajo),
                    nota=100 * (precio_alto - precio_bajo + castigo))


def tercios(medidas):
    """Tercio de volatilidad de cada ficha (calma, normal o tormenta), con los mismos cortes para
    todos los métodos y modelos de un horizonte."""
    salida = []
    for _, m in medidas.groupby("horizonte", sort=False):
        fichas = m.drop_duplicates(["fecha"])
        cortes = np.quantile(fichas["volatilidad"], [1 / 3, 2 / 3])
        salida.append(m.assign(tercio=pd.cut(m["volatilidad"], [-np.inf, *cortes, np.inf], labels=TERCIOS)))
    return pd.concat(salida, ignore_index=True)


def todos_los_rangos(previsiones, ctx, modelos=None, metodos=None, alfas=None):
    """Rangos medidos de todos los horizontes, modelos, métodos y niveles, en los años en que
    todos los métodos se pueden ajustar (los mismos para compararlos)."""
    modelos = modelos or sorted(previsiones["modelo"].unique())
    metodos = metodos or METODOS
    alfas = alfas or [ALFA, *ALFAS_INFO]
    p = preparar(previsiones[previsiones["modelo"].isin(modelos)], ctx)
    salida = []
    for (h, m), pm in p.groupby(["horizonte", "modelo"], sort=False):
        por_metodo = {(me, a): rangos(pm, ctx, me, a) for me in metodos for a in alfas}
        comunes = set.intersection(*(set(r["pliegue"]) for r in por_metodo.values() if len(r)))
        for (me, a), r in por_metodo.items():
            salida.append(medir(r[r["pliegue"].isin(comunes)], a))
    return tercios(pd.concat(salida, ignore_index=True))


def resumen(medidas, por=()):
    """Cobertura, anchura y nota medias por horizonte, modelo, método y nivel (y por `por`)."""
    claves = ["horizonte", "modelo", "metodo", "alfa", *por]
    g = medidas.groupby(claves, sort=False, observed=True)
    return pd.DataFrame({"cobertura": g["dentro"].mean(), "anchura (%)": g["anchura"].mean(),
                         "nota (%)": g["nota"].mean(), "fichas": g.size()})


def rangos_redes(cuantiles, ctx, ajustado=False, alfa=ALFA, años=None):
    """Rango B: los percentiles 10 y 90 que dan las redes (media de semillas), alrededor de su
    percentil 50. Con `ajustado` (solo como información), se ensanchan o estrechan con sus errores
    pasados ya conocidos: la cantidad que habría dado el 80 % en ellos (calibración conforme de
    cuantiles). `años`: {horizonte: años a evaluar}."""
    p = preparar(cuantiles.assign(**{"variación prevista": cuantiles["q50"]}), ctx)
    salida = []
    for (h, m), pm in p.groupby(["horizonte", "modelo"], sort=False):
        lista = años[h] if años is not None else sorted(pm["pliegue"].unique())
        for año in lista:
            hoy = pm[pm["pliegue"] == año]
            if len(hoy) == 0:
                continue
            bajo, alto = hoy["q10"].to_numpy(), hoy["q90"].to_numpy()
            if ajustado:
                conocido = pm[pm["fecha fin"] < pd.Timestamp(año, 1, 1)]
                if len(conocido) == 0:
                    continue
                fuera = np.maximum(conocido["q10"] - conocido["variación real"],
                                   conocido["variación real"] - conocido["q90"]).to_numpy()
                k = min(len(fuera), int(np.ceil((len(fuera) + 1) * (1 - alfa))))
                correccion = np.sort(fuera)[k - 1]
                bajo = np.minimum(bajo - correccion, hoy["q50"].to_numpy())
                alto = np.maximum(alto + correccion, hoy["q50"].to_numpy())
            salida.append(hoy.assign(metodo="redes ajustadas" if ajustado else "redes", alfa=alfa, bajo=bajo, alto=alto))
    return pd.concat(salida, ignore_index=True) if salida else pd.DataFrame()


def con_redes(medidas, cuantiles, ctx):
    """Añade B (y B ajustado, como información) a las medidas, en los mismos años que los demás rangos."""
    años = {h: sorted(medidas.loc[medidas["horizonte"] == h, "pliegue"].unique())
            for h in medidas["horizonte"].unique()}
    b = [medir(rangos_redes(cuantiles, ctx, ajustado=a, años=años)) for a in (False, True)]
    return tercios(pd.concat([medidas.drop(columns="tercio"), *b], ignore_index=True))


def regla(medidas, modelos=None, alfa=ALFA, candidatos=None):
    """Regla de D30 en cada horizonte, con la media de las redes: el de mejor nota entre los que
    cubren entre el 75 % y el 85 % en total y al menos el 70 % en cada tercio de volatilidad.
    `candidatos`: los métodos que pueden elegirse (los demás se muestran solo como información)."""
    modelos = modelos or list(config.CELDAS)
    m = medidas[(medidas["alfa"] == alfa) & medidas["modelo"].isin(modelos)]
    total = resumen(m).groupby(level=["horizonte", "metodo"], sort=False).mean()
    por_tercio = (resumen(m, por=("tercio",))["cobertura"]
                  .groupby(level=["horizonte", "metodo", "tercio"], sort=False, observed=True).mean()
                  .unstack("tercio"))
    t = total.join(por_tercio)
    t["peor tercio"] = t[TERCIOS].min(axis=1)
    t["cumple"] = (t["cobertura"].between(COBERTURA_MIN, COBERTURA_MAX)
                   & (t["peor tercio"] >= COBERTURA_TERCIO_MIN))
    nota_ingenuo = t.xs("ingenuo", level="metodo")["nota (%)"]
    t["nota / ingenuo"] = t["nota (%)"] / nota_ingenuo.reindex(t.index.get_level_values("horizonte")).to_numpy()
    elegido = {}
    for h, g in t.groupby(level="horizonte", sort=False):
        if candidatos is not None:
            g = g[g.index.get_level_values("metodo").isin(candidatos)]
        posibles = g[g["cumple"]] if g["cumple"].any() else g
        elegido[h] = posibles["nota (%)"].idxmin()[1]
    t["elegido"] = [elegido[h] == me for h, me in t.index]
    return t


def centro_hoy(previsiones):
    """Las mismas previsiones con la variación prevista a cero: el rango queda centrado en el precio de hoy."""
    return previsiones.assign(**{"variación prevista": 0.0})


def regla_centro(med_redes, med_hoy, elegidos, modelos=None, alfa=ALFA, mejora_min=MEJORA_CENTRO):
    """Regla de D32 en cada horizonte, con el método elegido y la media de las redes: se mantiene el
    centro de las redes si mejora la nota del rango al menos `mejora_min` con los años juntos y en
    más de la mitad de los años; si no, el centro es el precio de hoy, salvo que así deje de cumplir
    la regla de D30 y con las redes la cumpla. `elegidos`: {horizonte: método}."""
    modelos = modelos or list(config.CELDAS)
    filas = {}
    for h, metodo in elegidos.items():
        datos = {}
        for centro, med in (("redes", med_redes), ("precio de hoy", med_hoy)):
            m = med[(med["horizonte"] == h) & (med["metodo"] == metodo) & (med["alfa"] == alfa)
                    & med["modelo"].isin(modelos)]
            total = resumen(m).mean()
            peor = (resumen(m, por=("tercio",))["cobertura"].groupby(level="tercio", observed=True).mean().min())
            r = {"cobertura": total["cobertura"], "nota (%)": total["nota (%)"], "peor tercio": peor,
                 "cumple": COBERTURA_MIN <= total["cobertura"] <= COBERTURA_MAX and peor >= COBERTURA_TERCIO_MIN}
            por_año = resumen(m, por=("pliegue",))["nota (%)"].groupby(level="pliegue").mean()
            datos[centro] = (r, por_año)
        (r_red, año_red), (r_hoy, año_hoy) = datos["redes"], datos["precio de hoy"]
        mejora = 1 - r_red["nota (%)"] / r_hoy["nota (%)"]
        ganados, años = int((año_red < año_hoy).sum()), len(año_red)
        redes = (mejora >= mejora_min and ganados > años / 2) or (r_red["cumple"] and not r_hoy["cumple"])
        filas[(h, metodo)] = {
            "cobertura (redes)": r_red["cobertura"], "cobertura (precio de hoy)": r_hoy["cobertura"],
            "peor tercio (redes)": r_red["peor tercio"], "peor tercio (precio de hoy)": r_hoy["peor tercio"],
            "nota (redes)": r_red["nota (%)"], "nota (precio de hoy)": r_hoy["nota (%)"],
            "mejora de las redes": mejora, "años que mejoran las redes": f"{ganados} de {años}",
            "centro elegido": "redes" if redes else "precio de hoy"}
    t = pd.DataFrame(filas).T
    t.index.names = ["horizonte", "metodo"]
    return t

