"""Comprobaciones de robustez de las conclusiones (12/11): sin entrenar, con las previsiones guardadas.

- `bootstrap_bloques`: intervalo de la nota remuestreando bloques de años contiguos (los años
  vecinos comparten respuestas solapadas, así que remuestrear años sueltos da intervalos demasiado
  estrechos).
- `notas_alternativas`: la nota con otras medidas: RMSE en $, error en variación logarítmica (que
  no da más peso a los años de precio alto) y la mediana de las notas de cada año.
- `diebold_mariano`: contraste de si el modelo y el ingenuo tienen el mismo error medio (absoluto,
  en $), con la varianza corregida por el solapamiento de las fichas (Newey-West con h − 1 retardos).
- `por_parejas`: cuántos años gana cada red a otra y la diferencia media de sus notas.
- `margen_cobertura`: el error típico de una cobertura, contando solo las fichas independientes
  (una de cada h sesiones).
- `memoria_robusta`: la memoria de A2 estimada con las medianas del tamaño del movimiento por
  deciles de volatilidad, menos sensible a los movimientos casi nulos que la regresión directa.
"""
from math import erf, sqrt

import numpy as np
import pandas as pd

from . import config, hacia_atras as ha


def bootstrap_bloques(sumas, modelos, bloque=2, repeticiones=10_000, nivel=0.90, semilla=0):
    """Intervalo de la nota media de esos modelos (años juntos), remuestreando bloques de `bloque`
    años contiguos con reemplazo. `sumas`: las de un horizonte (`hacia_atras.sumas_por_año`)."""
    rng = np.random.default_rng(semilla)
    años = sorted(set(sumas.index.get_level_values("pliegue")))
    tablas = [sumas.xs(m, level="modelo").droplevel("horizonte").reindex(años) for m in modelos]
    inicios = list(range(len(años) - bloque + 1))
    n_bloques = int(np.ceil(len(años) / bloque))
    notas = []
    for _ in range(repeticiones):
        elegidos = np.concatenate([np.arange(i, i + bloque) for i in rng.choice(inicios, n_bloques)])[:len(años)]
        notas.append(np.mean([t["error"].to_numpy()[elegidos].sum() / t["error_ingenuo"].to_numpy()[elegidos].sum()
                              for t in tablas]))
    cola = (1 - nivel) / 2
    return float(np.quantile(notas, cola)), float(np.quantile(notas, 1 - cola))


def notas_alternativas(previsiones):
    """Por horizonte y modelo: la nota de siempre (MAE en $), RMSE en $, MAE en variación
    logarítmica y la mediana de las notas de cada año, todas frente al ingenuo."""
    p = previsiones
    real = p["precio origen"] * np.exp(p["variación real"])
    t = p.assign(e=p["precio origen"] * np.exp(p["variación prevista"]) - real, e0=p["precio origen"] - real,
                 l=(p["variación prevista"] - p["variación real"]).abs(), l0=p["variación real"].abs())
    g = t.groupby(["horizonte", "modelo"], sort=False)
    por_año = t.groupby(["horizonte", "modelo", "pliegue"], sort=False).apply(
        lambda d: d["e"].abs().mean() / d["e0"].abs().mean(), include_groups=False)
    return pd.DataFrame({
        "MAE en $ (la de siempre)": g.apply(lambda d: d["e"].abs().sum() / d["e0"].abs().sum(), include_groups=False),
        "RMSE en $": g.apply(lambda d: np.sqrt((d["e"] ** 2).mean() / (d["e0"] ** 2).mean()), include_groups=False),
        "MAE en variación (%)": g["l"].sum() / g["l0"].sum(),
        "mediana de los años": por_año.groupby(level=["horizonte", "modelo"], sort=False).median(),
    })


def _normal_dos_colas(z):
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))


def diebold_mariano(previsiones, horizonte):
    """Contraste de Diebold y Mariano (1995) del error absoluto en $ de cada modelo frente al
    ingenuo, con varianza de Newey-West de h − 1 retardos (las fichas se solapan h − 1 sesiones).
    Diferencia media negativa: el modelo se equivoca menos. Devuelve una fila por modelo."""
    h = config.HORIZONTES[horizonte]
    filas = []
    for m, p in previsiones[previsiones["horizonte"] == horizonte].groupby("modelo", sort=False):
        p = p.sort_values("fecha")
        real = p["precio origen"] * np.exp(p["variación real"])
        d = ((p["precio origen"] * np.exp(p["variación prevista"]) - real).abs() - (p["precio origen"] - real).abs()).to_numpy()
        n, media = len(d), d.mean()
        c = d - media
        varianza = c @ c / n
        for k in range(1, min(h, n)):
            varianza += 2 * (1 - k / h) * (c[k:] @ c[:-k]) / n
        z = media / np.sqrt(max(varianza, 1e-12) / n)
        filas.append({"horizonte": horizonte, "modelo": m, "fichas": n, "fichas independientes": n // h,
                      "diferencia media ($)": media, "estadístico": z, "p (dos colas)": _normal_dos_colas(z)})
    return pd.DataFrame(filas).set_index(["horizonte", "modelo"])


def por_parejas(sumas, horizonte, modelos=None):
    """Para cada pareja de redes: años en que gana la primera, años en total y diferencia media de
    las notas por año (primera − segunda; negativa, mejor la primera)."""
    modelos = modelos or list(config.CELDAS)
    notas = ha.notas_por_año(sumas).xs(horizonte, level="horizonte")
    filas = []
    for i, a in enumerate(modelos):
        for b in modelos[i + 1:]:
            dif = (notas.loc[a] - notas.loc[b]).dropna()
            filas.append({"pareja": f"{a} frente a {b}", "años que gana la primera": int((dif < 0).sum()),
                          "años": len(dif), "diferencia media": dif.mean()})
    return pd.DataFrame(filas).set_index("pareja")


def margen_cobertura(cobertura, fichas, horizonte):
    """Error típico de una cobertura contando solo las fichas independientes (una de cada h)."""
    n = max(fichas // config.HORIZONTES[horizonte], 1)
    return float(np.sqrt(cobertura * (1 - cobertura) / n))


def memoria_robusta(variaciones, volatilidad, grupos=10):
    """Memoria de A2 con medianas: pendiente de log(mediana de |variación|) sobre log(mediana de la
    volatilidad) por deciles de volatilidad, limitada entre 0 y 1."""
    t = pd.DataFrame({"v": np.abs(np.asarray(variaciones, np.float64)), "s": np.asarray(volatilidad, np.float64)})
    t["grupo"] = pd.qcut(t["s"], grupos, labels=False, duplicates="drop")
    m = t.groupby("grupo").median()
    pendiente = float(np.polyfit(np.log(m["s"]), np.log(m["v"]), 1)[0])
    return min(max(pendiente, 0.0), 1.0)
