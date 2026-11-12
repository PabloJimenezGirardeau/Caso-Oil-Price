"""Combinación de red y lineal (D28).

A 1 año el lineal es mejor que las redes, y a 3 meses al revés, pero cada uno falla en años
distintos. La forma más sencilla de aprovechar los dos es combinar sus previsiones.

Regla fijada antes de calcular nada:
- la previsión combinada es la media, a partes iguales (`config.PESO_RED_COMBINACION`), del precio
  que prevé la red (el promedio de 5 semillas de D27) y del que prevé el lineal. No hay pesos que
  afinar con la validación;
- en cada horizonte, con la media de las tres redes, la combinación se adopta si mejora a la mejor
  de las dos opciones por separado (red sola o lineal) en más del azar que queda con 5 semillas
  (el de D27). Si empata, se queda la opción sola, por sencilla;
- la curva con otros pesos (`config.PESOS_CURVA_COMBINACION`) es solo descriptiva.

El lineal es el de referencia de la fase B: sin tendencia, con los datos de cada horizonte y su
mejor fuerza de regularización (la de `resultados/tendencia.csv`). Sus previsiones se recalculan
aquí, en segundos, con las mismas fichas que las redes; su nota debe coincidir con la guardada.
"""
import numpy as np
import pandas as pd

from . import busqueda as bu, config, estabilidad as es, experimentos as ex
from .modelos import ModeloLineal

CLAVE_FICHA = ["horizonte", "pliegue", "fecha"]


def alfa_lineal(horizonte, dir_salida=config.DIR_RESULTADOS):
    """Fuerza de regularización del lineal de referencia de un horizonte y su nota guardada:
    sin tendencia, con los datos de la fase B y la mejor de las probadas."""
    t = pd.read_csv(dir_salida / "tendencia.csv", on_bad_lines="skip").dropna(subset=["MAE"])
    d = config.DATOS_FASE_B[horizonte]
    sel = t[(t["modelo"] == "Lineal") & (t["horizonte"] == horizonte) & (t["ventana"] == d["ventana"])
            & (t["recorte"] == ex.nombre_recorte(d["recorte"])) & (t["nivel"] == d["nivel"])]
    notas = ex.resumir(sel).set_index("alfa")["MAE / ingenuo"]
    return float(notas.idxmin()), float(notas.min())


def previsiones_lineal(horizontes=None, dir_salida=config.DIR_RESULTADOS, bases=None, pliegues=bu._pliegues):
    """Previsión del lineal de referencia en cada ficha de validación, con el formato de
    `estabilidad.leer_previsiones` (modelo «Lineal», sin semilla). Con `pliegues`, en otros años
    (una función como `busqueda._pliegues`)."""
    horizontes = horizontes or list(config.HORIZONTES)
    bases = bases if bases is not None else ex._bases()
    tablas = []
    for h in horizontes:
        alfa, _ = alfa_lineal(h, dir_salida)
        for año, train, evaluado in pliegues(bases, bu.combinacion(h)):
            lineal = ModeloLineal(alfa, sin_tendencia=True).ajustar(train)
            tablas.append(pd.DataFrame({
                "horizonte": h, "modelo": "Lineal", "intento": 0, "pliegue": año, "semilla": np.nan,
                "fecha": pd.DatetimeIndex(evaluado.fechas), "variación prevista": lineal.predecir(evaluado.X)[:, 0],
                "variación real": evaluado.Y[:, 0], "precio origen": evaluado.precio_origen, "alfa": alfa}))
    return pd.concat(tablas, ignore_index=True)


def combinar(red, lineal, peso_red=config.PESO_RED_COMBINACION):
    """Previsión combinada de cada ficha: media ponderada de los precios que prevén la red y el
    lineal, expresada como variación logarítmica. `red` es una previsión por red y ficha (por
    ejemplo, un promedio de semillas); lo que pasó en cada ficha se toma de ella."""
    lineal = lineal.assign(fecha=lineal["fecha"].astype(red["fecha"].dtype))   # misma resolución de fecha
    m = red.merge(lineal[CLAVE_FICHA + ["variación prevista"]].rename(columns={"variación prevista": "lineal"}),
                  on=CLAVE_FICHA, how="left", validate="many_to_one")
    if m["lineal"].isna().any():
        raise ValueError(f"{int(m['lineal'].isna().sum())} fichas de la red no tienen previsión del lineal")
    factor = peso_red * np.exp(m["variación prevista"]) + (1 - peso_red) * np.exp(m["lineal"])
    return m.assign(**{"variación prevista": np.log(factor)}).drop(columns="lineal")


def curva_pesos(previsiones, lineal, pesos=None, semillas=None, n=config.N_SEMILLAS_PROMEDIO, por=()):
    """«MAE / ingenuo» de la combinación con cada peso de la red, por horizonte y red (y por las
    columnas de `por`): media de los grupos de n semillas, como la nota adoptada en D27.
    Peso 1 es la red sola y peso 0, el lineal solo."""
    pesos = pesos if pesos is not None else config.PESOS_CURVA_COMBINACION
    semillas = semillas or config.SEMILLAS_ESTABILIDAD
    notas = []
    for grupo in es.grupos(semillas, n):
        prom = es.promedio(previsiones, grupo)
        notas += [es.nota(combinar(prom, lineal, w), por=por).rename(w) for w in pesos]
    tabla = pd.concat(notas, axis=1)
    return tabla.T.groupby(level=0, sort=False).mean().T.rename_axis(columns="peso de la red")


def decidir(curva, ruido, peso=config.PESO_RED_COMBINACION):
    """Regla de D28 en cada horizonte, con la media de las tres redes.

    `curva`: salida de `curva_pesos` (por horizonte y red); `ruido`: azar que queda con 5 semillas
    en cada horizonte (media de las tres redes, de D27)."""
    media = curva.groupby(level="horizonte", sort=False).mean()
    t = pd.DataFrame({"red sola": media[1.0], "lineal": media[0.0], "combinación": media[peso],
                      "ruido": pd.Series(ruido)})
    t["mejor por separado"] = t[["red sola", "lineal"]].min(axis=1)
    t["mejora"] = t["mejor por separado"] - t["combinación"]
    t["se adopta"] = t["mejora"] > t["ruido"]
    t["se queda"] = np.where(t["se adopta"], "combinación",
                             np.where(t["red sola"] <= t["lineal"], "red sola", "lineal"))
    return t
