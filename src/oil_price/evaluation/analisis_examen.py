"""Análisis del examen final, después de hacerlo (recomendación del profesor, 17/11/2026): R²,
valores reales frente a previstos y cuándo aciertan y cuándo fallan los modelos.

Solo usa las previsiones ya guardadas del examen (`resultados/examen_*.csv`): no entrena nada ni cambia
ninguna decisión. Describe mejor lo que ya pasó.

- **R² sobre el precio** compara el precio previsto con el real. Sale muy alto incluso para el ingenuo,
  porque el precio de dentro de unos días se parece mucho al de hoy: no sirve para saber si el modelo
  aporta algo (es el «espejismo» del experimento de control, D15).
- **R² sobre la variación** compara cuánto se prevé que se mueva el precio con cuánto se movió. Ese
  dice si el modelo anticipa el movimiento: 0 es no explicar nada; por debajo de 0, peor que prever
  siempre la variación media del periodo.
- **R² frente al ingenuo** (1 − error cuadrático del modelo / el del ingenuo, en $): cuánto reduce el
  modelo el error del ingenuo. 0 es empatar con él; negativo, equivocarse más.
"""
import numpy as np
import pandas as pd

from oil_price.evaluation import examen_final as exa

INGENUO = "ingenuo"
SEPARACION_MINIMA = 21          # sesiones entre dos episodios distintos (un mes de mercado)
TAMAÑO_MOVIMIENTO = ["bajada fuerte", "sin gran cambio", "subida fuerte"]


def r2(real, previsto):
    """Coeficiente de determinación: 1 − (error cuadrático del modelo) / (variabilidad de lo real)."""
    real, previsto = np.asarray(real, dtype=float), np.asarray(previsto, dtype=float)
    total = ((real - real.mean()) ** 2).sum()
    return float(1 - ((real - previsto) ** 2).sum() / total) if total > 0 else np.nan


def con_precios(previsiones):
    """Cada ficha con el precio real, el previsto por el modelo y el del ingenuo (el de hoy), y los errores en $."""
    p = previsiones
    real = p["precio origen"] * np.exp(p["variación real"])
    previsto = p["precio origen"] * np.exp(p["variación prevista"])
    return p.assign(**{"precio real": real, "precio previsto": previsto, "error ($)": previsto - real,
                       "error del ingenuo ($)": p["precio origen"] - real})


def r2_frente_al_ingenuo(error, error_ingenuo):
    """1 − (error cuadrático del modelo) / (error cuadrático del ingenuo): cuánto reduce el error del ingenuo."""
    return float(1 - (np.asarray(error) ** 2).sum() / (np.asarray(error_ingenuo) ** 2).sum())


def tabla_r2(previsiones):
    """R² sobre el precio, sobre la variación y frente al ingenuo, por horizonte y modelo, con el ingenuo
    como una fila más (prevé el precio de hoy, es decir, variación cero)."""
    p = con_precios(previsiones)
    filas = {}
    for h, gh in p.groupby("horizonte", sort=False):
        for m, g in gh.groupby("modelo", sort=False):
            filas[(h, m)] = {"R² precio": r2(g["precio real"], g["precio previsto"]),
                             "R² variación": r2(g["variación real"], g["variación prevista"]),
                             "R² frente al ingenuo": r2_frente_al_ingenuo(g["error ($)"], g["error del ingenuo ($)"])}
        g = gh[gh["modelo"] == gh["modelo"].iloc[0]]
        filas[(h, INGENUO)] = {"R² precio": r2(g["precio real"], g["precio origen"]),
                               "R² variación": r2(g["variación real"], np.zeros(len(g))),
                               "R² frente al ingenuo": 0.0}
    tabla = pd.DataFrame(filas).T
    tabla.index.names = ["horizonte", "modelo"]
    return tabla


def _rango_elegido(rangos):
    """Del resultado de `examen_final.rangos_examen`, el rango elegido de cada horizonte (D30, D32)."""
    elegido = rangos["metodo"] == rangos["horizonte"].map(exa.METODO_RANGO)
    return rangos.loc[elegido, ["horizonte", "fecha", "fecha fin", "bajo", "alto", "dentro", "tercio"]]


def serie(previsiones, rangos, horizonte, modelo=None):
    """Real frente a previsto en cada ficha del examen, ordenado por la fecha a la que se refiere la
    previsión («fecha objetivo»): precio real, previsión del modelo, ingenuo y rango del 80 % en $."""
    modelo = modelo or exa.ELEGIDA[horizonte]
    p = con_precios(previsiones[(previsiones["horizonte"] == horizonte) & (previsiones["modelo"] == modelo)])
    r = _rango_elegido(rangos)
    p = p.merge(r[r["horizonte"] == horizonte].drop(columns="horizonte"), on="fecha", how="left", validate="one_to_one")
    return pd.DataFrame({"fecha origen": p["fecha"].values, "precio hoy": p["precio origen"].values,
                         "precio real": p["precio real"].values, "precio previsto": p["precio previsto"].values,
                         "rango bajo": (p["precio origen"] * np.exp(p["bajo"])).values,
                         "rango alto": (p["precio origen"] * np.exp(p["alto"])).values,
                         "dentro del rango": p["dentro"].values, "tercio": p["tercio"].values},
                        index=pd.DatetimeIndex(p["fecha fin"], name="fecha objetivo")).sort_index()


def _movimiento(variacion):
    """Tercio del movimiento real de cada ficha (bajada fuerte, sin gran cambio, subida fuerte)."""
    cortes = np.quantile(variacion, [1 / 3, 2 / 3])
    return pd.cut(variacion, [-np.inf, *cortes, np.inf], labels=TAMAÑO_MOVIMIENTO)


def por_grupos(previsiones, rangos):
    """Error de cada modelo frente al ingenuo según dos cosas:
    - el **mercado** el día de la previsión (calma, normal, tormenta: el tercio de volatilidad de los
      últimos 21 días, que se conoce ese día);
    - el **movimiento** que hubo después (bajada fuerte, sin gran cambio, subida fuerte: el tercio de
      la variación real, que solo se conoce al final). Dice en qué situaciones acierta y en cuáles no."""
    p = con_precios(previsiones)
    tercio = _rango_elegido(rangos)[["horizonte", "fecha", "tercio"]]
    p = p.merge(tercio, on=["horizonte", "fecha"], how="left", validate="many_to_one")
    salida = []
    for h, gh in p.groupby("horizonte", sort=False):
        gh = gh.assign(movimiento=_movimiento(gh["variación real"]))
        for criterio, columna in (("mercado ese día", "tercio"), ("movimiento después", "movimiento")):
            for (m, grupo), g in gh.groupby(["modelo", columna], sort=False, observed=True):
                mae, mae_ing = g["error ($)"].abs().mean(), g["error del ingenuo ($)"].abs().mean()
                salida.append({"horizonte": h, "criterio": criterio, "grupo": grupo, "modelo": m, "fichas": len(g),
                               "MAE ($)": mae, "MAE ingenuo ($)": mae_ing, "MAE / ingenuo": mae / mae_ing,
                               "acierto de dirección": (np.sign(g["variación prevista"]) == np.sign(g["variación real"])).mean(),
                               "variación prevista media": g["variación prevista"].mean(),
                               "variación real media": g["variación real"].mean()})
    return pd.DataFrame(salida)


def episodios(datos_serie, criterio, n=5, separacion=SEPARACION_MINIMA):
    """Los `n` momentos más extremos de una serie (de `serie`), sin repetir el mismo episodio: dos
    momentos deben estar a más de `separacion` sesiones (las fichas de días seguidos se solapan).
    - «fallos»: el mayor error de la red en $;
    - «aciertos»: donde la red más mejoró al ingenuo (error del ingenuo − error de la red)."""
    s = datos_serie.assign(**{"error de la red ($)": datos_serie["precio previsto"] - datos_serie["precio real"],
                              "error del ingenuo ($)": datos_serie["precio hoy"] - datos_serie["precio real"]})
    if criterio == "fallos":
        clave = s["error de la red ($)"].abs()
    elif criterio == "aciertos":
        clave = s["error del ingenuo ($)"].abs() - s["error de la red ($)"].abs()
    else:
        raise ValueError(f"criterio desconocido: {criterio}")
    posicion = pd.Series(np.arange(len(s)), index=s.index)
    elegidos = []
    for fecha in clave.sort_values(ascending=False).index:
        if all(abs(posicion[fecha] - posicion[e]) > separacion for e in elegidos):
            elegidos.append(fecha)
        if len(elegidos) == n:
            break
    columnas = ["fecha origen", "precio hoy", "precio previsto", "precio real", "error de la red ($)",
                "error del ingenuo ($)", "dentro del rango", "tercio"]
    return s.loc[elegidos, columnas]


def resumen(previsiones, rangos):
    """Para el texto: por horizonte, la red elegida y su nota frente al ingenuo en cada grupo."""
    g = por_grupos(previsiones, rangos)
    elegida = g["modelo"] == g["horizonte"].map(exa.ELEGIDA)
    return g[elegida].pivot_table(index=["horizonte", "criterio", "grupo"], values="MAE / ingenuo", sort=False)

