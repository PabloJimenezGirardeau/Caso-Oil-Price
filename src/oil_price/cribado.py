"""Criba de información nueva solo con el entrenamiento (2000-2017).

Antes de gastar la validación en probar una variable nueva con las redes, se estudia **solo con
datos hasta el 31/12/2017**: ninguna respuesta, ni de lo que se usa para aprender ni de lo que se
evalúa, pasa de esa fecha. Así no se toca ni la validación (2018-2021) ni el test.

- `medidas`: las candidatas, calculadas cada día solo con información hasta ese día, a partir de
  los datos limpios y del CSV del proyecto (lo único permitido, junto con lo que indica el enunciado).
- `tormentas`: los episodios de volatilidad muy alta del train y qué pasó después.
- `relacion`: correlación de rangos de cada candidata con la variación posterior del Brent.
- `validacion_en_train`: el método del proyecto dentro del train. Cada año de 2006 a 2017 se prevé
  con un modelo lineal pequeño entrenado con lo anterior (solo respuestas conocidas antes de ese
  año). Se compara la volatilidad de un mes sola con la volatilidad más cada candidata.

Regla para pasar la criba (fijada antes de mirar, 12/11): mejorar a la volatilidad sola en al
menos 0,02 y en más de la mitad de los años. Solo una candidata que la pase merecería un
experimento con las redes.
"""
import numpy as np
import pandas as pd

from . import config, datos

FIN = pd.Timestamp("2017-12-31")
HORIZONTES = {"medio": 63, "largo": 252}
PRIMER_AÑO = 2006
BASE = "volatilidad 1 mes"
MEJORA_MINIMA = 0.02


def _z(x, dias=252):
    """Puntuación z de cada día frente a los `dias` anteriores (incluido ese día)."""
    return (x - x.rolling(dias).mean()) / x.rolling(dias).std()


def medidas():
    """Candidatas de cada día, con información hasta ese día, en el calendario del Brent.

    Devuelve (medidas, brent): la tabla de candidatas y el precio del Brent."""
    limpio = datos.cargar_datos_limpios()
    bruto = datos.cargar_dataset().sort_index()
    bruto = bruto.reindex(bruto.index.union(limpio.index)).ffill().reindex(limpio.index)   # solo valores pasados
    lp = np.log(limpio["brent"])
    r = lp.diff()
    anual = np.sqrt(252)
    # El WTI negativo del 20/04/2020 da logaritmos no válidos (NaN), pero queda fuera del train
    with np.errstate(invalid="ignore", divide="ignore"):
        parkinson = np.log(bruto["wti_fut_High"] / bruto["wti_fut_Low"]) ** 2 / (4 * np.log(2))
        wti_futuro = np.log(bruto["wti_fut_Close"] / bruto["wti"])
        brent_wti = np.log(bruto["brent"] / bruto["wti"])
    m = pd.DataFrame({
        "volatilidad 1 mes": np.log(r.rolling(21).std() * anual),
        "volatilidad 3 meses": np.log(r.rolling(63).std() * anual),
        "VIX en nivel": np.log(limpio["vix"]),
        "volatilidad de las caídas (1 mes)": np.log(np.sqrt((r.clip(upper=0) ** 2).rolling(21).mean() * 252)),
        "volatilidad de las subidas (1 mes)": np.log(np.sqrt((r.clip(lower=0) ** 2).rolling(21).mean() * 252)),
        "movimiento del último mes": lp.diff(21),
        "caída desde el máximo del año": lp - lp.rolling(252).max(),
        "precio frente a su media del año": lp - np.log(limpio["brent"].rolling(config.DIAS_MEDIA).mean()),
        "futuro WTI frente al contado": wti_futuro,
        "Brent frente al WTI": brent_wti,
        "dólar frente a su media del año": np.log(limpio["indice_dolar"] / limpio["indice_dolar"].rolling(252).mean()),
        "cobre frente a su media del año": np.log(limpio["cobre"] / limpio["cobre"].rolling(252).mean()),
        "gas frente al Brent": np.log(bruto["gas_natural"] / bruto["brent"]),
        "tipo del BCE (cambio en un año)": bruto["tipo_bce"].diff(252),
        "volatilidad intradía del futuro WTI (1 mes)": np.log(np.sqrt(parkinson.rolling(21).mean() * 252)),
        "ratio cobre/Brent (z a 252 días)": _z(np.log(limpio["cobre"] / limpio["brent"])),
        "ratio oro/Brent (z a 252 días)": _z(np.log(limpio["oro"] / limpio["brent"])),
    })
    return m.replace([np.inf, -np.inf], np.nan), limpio["brent"]


def _futuro(brent, horizonte):
    """Variación logarítmica a h sesiones y fecha en que se conoce, para cada día de origen."""
    n = HORIZONTES[horizonte]
    lp = np.log(brent)
    return lp.shift(-n) - lp, pd.Series(brent.index, index=brent.index).shift(-n)


def origenes(m, brent, horizonte):
    """Días de origen del train: con todas las candidatas y con la respuesta conocida antes de 2018."""
    variacion, fecha_fin = _futuro(brent, horizonte)
    ok = m.notna().all(axis=1) & variacion.notna() & (fecha_fin <= FIN)
    return m.index[ok]


def division(m, brent, horizonte, año):
    """(días para aprender, días a prever) de un año: se aprende solo con respuestas conocidas antes de ese año."""
    o = origenes(m, brent, horizonte)
    _, fecha_fin = _futuro(brent, horizonte)
    inicio = pd.Timestamp(año, 1, 1)
    return o[fecha_fin.loc[o] < inicio], o[(o >= inicio) & (o <= pd.Timestamp(año, 12, 31))]


def tormentas(m, brent, cuantil=0.90, separacion=21):
    """Episodios del train con la volatilidad de un mes en el 10 % más alto (días a menos de
    `separacion` sesiones forman un episodio), con el movimiento del mes anterior y la variación
    media posterior a 3 meses y a 1 año (solo respuestas conocidas antes de 2018)."""
    vol = np.exp(m[BASE])
    umbral = vol.loc[origenes(m, brent, "medio")].quantile(cuantil)
    idx = np.flatnonzero(((vol >= umbral) & (vol.index <= FIN)).to_numpy())
    grupos, actual = [], [idx[0]]
    for i in idx[1:]:
        if i - actual[-1] <= separacion:
            actual.append(i)
        else:
            grupos.append(actual)
            actual = [i]
    grupos.append(actual)
    futuros = {h: _futuro(brent, h) for h in HORIZONTES}
    filas = []
    for g in grupos:
        fechas = vol.index[g]
        inicio = fechas[0]
        mes = m["movimiento del último mes"].loc[inicio]
        fila = {"desde": inicio.date(), "hasta": fechas[-1].date(), "días": len(g),
                "volatilidad máx. (%)": round(100 * vol.loc[fechas].max()),
                "precio al empezar ($)": round(brent.loc[inicio], 1),
                "mes anterior (%)": round(100 * np.expm1(mes), 1),
                "tipo": "tras una caída" if mes < 0 else "tras una subida"}
        for h, (variacion, fecha_fin) in futuros.items():
            v = variacion.loc[fechas][fecha_fin.loc[fechas] <= FIN]
            fila[f"{config.HORIZONTES[h]} sesiones después (%)"] = round(100 * np.expm1(v.mean()), 1) if len(v) else np.nan
        filas.append(fila)
    return pd.DataFrame(filas), float(umbral)


def media_todos_los_dias(m, brent):
    """Variación media posterior (%) de todos los días del train, para comparar con las tormentas."""
    salida = {}
    for h in HORIZONTES:
        variacion, _ = _futuro(brent, h)
        salida[f"{config.HORIZONTES[h]} sesiones después (%)"] = float(
            100 * np.expm1(variacion.loc[origenes(m, brent, h)].mean()))
    return salida


def relacion(m, brent):
    """Correlación de rangos de cada candidata con la variación posterior (todos los días del train)."""
    salida = {}
    for h in HORIZONTES:
        o = origenes(m, brent, h)
        salida[h] = m.loc[o].corrwith(_futuro(brent, h)[0].loc[o], method="spearman")
    salida["correlación con la volatilidad 1 mes"] = m.loc[origenes(m, brent, "medio")].corr(method="spearman")[BASE]
    return pd.DataFrame(salida)


def _sumas(m, brent, horizonte, columnas, alfa=1e-3):
    """Por año a prever: suma de errores (en $) del modelo lineal pequeño y del ingenuo.

    El modelo es lineal, sin término fijo (sin tendencia), sobre las candidatas estandarizadas con
    lo que se usa para aprender."""
    variacion, _ = _futuro(brent, horizonte)
    filas = {}
    for año in range(PRIMER_AÑO, FIN.year + 1):
        aprender, prever = division(m, brent, horizonte, año)
        if len(prever) == 0:
            continue
        X, y = m.loc[aprender, columnas].to_numpy(), variacion.loc[aprender].to_numpy()
        media, desv = X.mean(axis=0), X.std(axis=0)
        Z = (X - media) / desv
        coef = np.linalg.solve(Z.T @ Z + alfa * len(Z) * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
        prevision = ((m.loc[prever, columnas].to_numpy() - media) / desv) @ coef
        precio = brent.loc[prever].to_numpy()
        real = precio * np.exp(variacion.loc[prever].to_numpy())
        filas[año] = {"error": np.abs(precio * np.exp(prevision) - real).sum(), "ingenuo": np.abs(precio - real).sum()}
    return pd.DataFrame(filas).T


def validacion_en_train(m, brent, candidatas=None):
    """Para cada horizonte: la volatilidad de un mes sola y con cada candidata añadida (MAE / ingenuo
    de 2006-2017 juntos), cuánto mejora, en cuántos años mejora y si pasa la criba."""
    candidatas = candidatas or [c for c in m.columns if c != BASE]
    filas = []
    for h in HORIZONTES:
        base = _sumas(m, brent, h, [BASE])
        nota_base = base["error"].sum() / base["ingenuo"].sum()
        filas.append({"horizonte": h, "candidata": "(ninguna: volatilidad 1 mes sola)", "MAE / ingenuo": nota_base,
                      "mejora": 0.0, "años en que mejora": np.nan, "años": len(base), "pasa la criba": False})
        for c in candidatas:
            t = _sumas(m, brent, h, [BASE, c])
            nota = t["error"].sum() / t["ingenuo"].sum()
            mejora_años = int((t["error"] < base["error"]).sum())
            filas.append({"horizonte": h, "candidata": c, "MAE / ingenuo": nota, "mejora": nota_base - nota,
                          "años en que mejora": mejora_años, "años": len(t),
                          "pasa la criba": bool(nota_base - nota >= MEJORA_MINIMA and mejora_años > len(t) / 2)})
    return pd.DataFrame(filas).set_index(["horizonte", "candidata"])
