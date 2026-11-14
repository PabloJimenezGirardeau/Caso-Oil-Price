"""Exporta a web/data/ los datos que lee la web del proyecto (GitHub Pages).

La web no calcula nada: solo lee estos JSON. Todas las cifras salen de aquí, con las mismas
funciones que usa el notebook 03 (validación hacia atrás, rango del 80 % y control con precios),
a partir de `data/` y `resultados/`. No entrena nada y tarda menos de un minuto.

Archivos:
- historico.json      precio diario del Brent (días reales de cotización, 2000-2026);
- cotizaciones.json   último valor del CSV y su variación diaria (cinta de la web);
- validacion.json     nota de cada modelo en 2010-2021 (MAE / ingenuo), por años y con todos juntos;
- rango.json          cobertura, anchura y nota del rango del 80 %, y su serie diaria de 2019-2021;
- espejismo.json      control con precios (D15): serie de 2018-2019 y medidas;
- prevision.json      precio de hoy y rango del 80 % de cada plazo (ver «Lo pendiente»);
- test.json           examen final (D33);
- en_vivo.json        previsión del 10/11/2026 (D34).

Lo pendiente. El examen final (D33) y la previsión del 10/11 (D34) no están hechos: `test.json` y
`en_vivo.json` se crean con `"estado": "pendiente"` y este script **no los pisa** si ya tienen otro
estado (los rellena quien ejecute D33 y D34; el formato está en web/README.md). En `prevision.json`,
la previsión de cada red queda en `null` hasta que existan las redes finales, y el rango es
**provisional**: el elegido en cada plazo (D30), centrado en el precio de hoy (D32), con el ancho
ajustado solo con lo conocido antes del 1/1/2022, para no usar ninguna respuesta del periodo de test.

Uso:
    python scripts/exportar_web.py
"""
import json

import numpy as np
import pandas as pd

from oil_price import comprobaciones as cp
from oil_price import config
from oil_price import control_precios as cpr
from oil_price import datos
from oil_price import entreno_completo as ec
from oil_price import estabilidad as es
from oil_price import experimentos as ex
from oil_price import hacia_atras as ha
from oil_price import incertidumbre as inc

DIR_WEB = config.RAIZ / "web" / "data"

HORIZONTES = ["corto", "medio", "largo"]
MODELOS = [*config.CELDAS, "Lineal"]
# Rango elegido en cada plazo (D30) y red de la aplicación (D33): fijados en el diario, no aquí
RANGO_ELEGIDO = {"corto": "memoria", "medio": "centrado", "largo": "centrado"}
RED_ELEGIDA = {"corto": "LSTM", "medio": "RNN", "largo": "RNN"}
# A 1 año el rango no cumple la regla de D30 (cubre menos del 75 %): se presenta como orientativo
ORIENTATIVO = {"corto": False, "medio": False, "largo": True}
FIN_AJUSTE_PROVISIONAL = 2022   # el rango de hoy se ajusta con lo conocido antes del 1/1 de este año
COTIZACIONES = {"brent": "Brent", "wti": "WTI", "gas_natural": "Gas natural", "oro": "Oro",
                "cobre": "Cobre", "vix": "VIX"}
SERIE_RANGO = ("2019-01-01", "2021-12-31")        # sección «Calma y tormenta»
SERIE_ESPEJISMO = ("2018-07-01", "2019-12-31")    # sección «El espejismo»
VENTANA_ESPEJISMO = ("2018-10-01", "2019-02-28")  # tramo que la web enseña al abrir (el desplome de finales de 2018)


def _fecha(valor):
    return pd.Timestamp(valor).strftime("%Y-%m-%d")


def _num(valor, decimales=4):
    return None if valor is None or pd.isna(valor) else round(float(valor), decimales)


def _lista(valores, decimales=2):
    return [_num(v, decimales) for v in valores]


def guardar(nombre, contenido):
    DIR_WEB.mkdir(parents=True, exist_ok=True)
    ruta = DIR_WEB / nombre
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {nombre:<20} {ruta.stat().st_size / 1024:7.1f} KB")


def guardar_pendiente(nombre, contenido):
    """Crea el archivo como pendiente; si ya existe con otro estado (D33 o D34 hechos), no lo toca."""
    ruta = DIR_WEB / nombre
    if ruta.exists() and json.loads(ruta.read_text(encoding="utf-8")).get("estado") != "pendiente":
        print(f"  {nombre:<20} ya tiene resultado: no se toca")
        return
    guardar(nombre, contenido)


# --- Datos --------------------------------------------------------------------------------------

def brent_real():
    """Tabla del CSV solo en los días en que cotizó el Brent, hasta el último dato real."""
    tabla = datos.cargar_dataset()
    tabla = tabla.loc[tabla.index.isin(datos.cargar_dias_brent())]
    return tabla.loc[:config.FECHA_CORTE].dropna(subset=["brent"])


def historico(tabla):
    return {"fechas": [_fecha(f) for f in tabla.index], "precios": _lista(tabla["brent"])}


def cotizaciones(tabla):
    ultimo, anterior = tabla.iloc[-1], tabla.iloc[-2]
    return {"fecha": _fecha(tabla.index[-1]),
            "valores": [{"clave": c, "nombre": n, "valor": _num(ultimo[c], 2),
                         "variacion": _num(100 * (ultimo[c] / anterior[c] - 1), 2)}
                        for c, n in COTIZACIONES.items()]}


# --- Previsiones de 2010-2021 --------------------------------------------------------------------

def previsiones_finales(bases):
    """Previsión de cada ficha de 2010-2021 con la versión adoptada de cada modelo: a 1 semana y a
    3 meses, las redes de siempre (promedio de las semillas 42-46); a 1 año, las entrenadas con todo
    (D31). En los tres, además, el lineal de referencia y la media de las tres redes."""
    doce = pd.concat([ha.previsiones_doce_años(bases, horizontes=["corto"]), ha.previsiones_doce_años(bases)],
                     ignore_index=True)
    d31 = ec.promedio(ec.leer_previsiones())[ha.COLUMNAS]
    d31 = d31[d31["horizonte"] == "largo"]
    largo = pd.concat([d31, ha.media_de_las_redes(d31)[ha.COLUMNAS],
                       doce[(doce["horizonte"] == "largo") & (doce["modelo"] == "Lineal")]], ignore_index=True)
    return pd.concat([doce[doce["horizonte"] != "largo"], largo], ignore_index=True)


def validacion(finales):
    sumas = ha.sumas_por_año(finales)
    por_año, juntos = ha.notas_por_año(sumas), ha.nota_juntos(sumas)
    salida = {"periodo": "2010-2021", "plazos": {}}
    for h in HORIZONTES:
        notas = por_año.xs(h, level="horizonte").dropna(axis=1, how="all")
        dm = cp.diebold_mariano(finales, h).droplevel("horizonte")
        c = ha.criterio(sumas, h)
        modelos = {}
        for m in [*MODELOS, ha.MEDIA]:
            fila = notas.loc[m].dropna()
            modelos[m] = {"nota": _num(juntos[(h, m)]), "ganados": int((fila < 1).sum()), "años": int(len(fila)),
                          "p": _num(dm.loc[m, "p (dos colas)"], 3),
                          "por_año": {str(a): _num(v, 3) for a, v in fila.items()}}
        salida["plazos"][h] = {
            "sesiones": config.HORIZONTES[h], "red_elegida": RED_ELEGIDA[h], "modelos": modelos,
            "criterio": {"veredicto": c["veredicto"], "ganados": c["años que gana al ingenuo"], "años": c["años"],
                         "nota": _num(c["nota con los años juntos"]),
                         "intervalo": [_num(c["intervalo 90 % (bajo)"], 3), _num(c["intervalo 90 % (alto)"], 3)],
                         "prob_sin_ventaja": _num(c["probabilidad sin ventaja"], 3)}}
    return salida


# --- Rango del 80 % -----------------------------------------------------------------------------

def _medidas_rango(m, h):
    """Cobertura (total y por tercios de volatilidad), anchura, nota y fallos de un rango."""
    cobertura = float(m["dentro"].mean())
    return {"cobertura": _num(cobertura), "margen": _num(cp.margen_cobertura(cobertura, len(m), h)),
            "tercios": {t: _num(v) for t, v in m.groupby("tercio", observed=True)["dentro"].mean().items()},
            "anchura": _num(m["anchura"].mean(), 2), "nota": _num(m["nota"].mean(), 3),
            "falla_abajo": _num((m["variación real"] < m["bajo"]).mean()),
            "falla_arriba": _num((m["variación real"] > m["alto"]).mean()),
            "por_año": {str(a): _num(v, 3) for a, v in m.groupby("pliegue")["dentro"].mean().items()}}


def _serie_rango(elegido, fijo):
    """Serie diaria, en la fecha que se prevé: precio real, rango elegido, rango fijo y la
    volatilidad del día en que se hizo la previsión."""
    t = elegido.merge(fijo[["fecha", "bajo", "alto"]], on="fecha", suffixes=("", " fijo")).sort_values("fecha fin")
    t = t[t["fecha fin"].between(*SERIE_RANGO)]
    origen = t["precio origen"]
    return {"fechas": [_fecha(f) for f in t["fecha fin"]],
            "real": _lista(origen * np.exp(t["variación real"])),
            "bajo": _lista(origen * np.exp(t["bajo"])), "alto": _lista(origen * np.exp(t["alto"])),
            "bajo_fijo": _lista(origen * np.exp(t["bajo fijo"])), "alto_fijo": _lista(origen * np.exp(t["alto fijo"])),
            "volatilidad": _lista(t["volatilidad"], 3)}


def rango(finales, ctx):
    """Rango elegido en cada plazo, centrado en el precio de hoy (D32), frente al rango fijo (el
    «ingenuo» del estudio: percentiles 10-90 de las variaciones pasadas, igual de ancho siempre).
    Con el centro en el precio de hoy el rango es el mismo para las tres redes: se toma una."""
    redes = finales[finales["modelo"].isin(config.CELDAS)]
    medidas = inc.todos_los_rangos(inc.centro_hoy(redes), ctx, modelos=list(config.CELDAS), alfas=[inc.ALFA])
    medidas = medidas[medidas["modelo"] == config.CELDAS[0]]
    salida = {"nivel": 1 - inc.ALFA, "plazos": {}}
    for h in HORIZONTES:
        m = medidas[medidas["horizonte"] == h]
        elegido, fijo = m[m["metodo"] == RANGO_ELEGIDO[h]], m[m["metodo"] == "ingenuo"]
        años = sorted(int(a) for a in elegido["pliegue"].unique())
        salida["plazos"][h] = {
            "sesiones": config.HORIZONTES[h], "metodo": RANGO_ELEGIDO[h], "orientativo": ORIENTATIVO[h],
            "años": años, "fichas": int(len(elegido)),
            "elegido": _medidas_rango(elegido, h), "fijo": _medidas_rango(fijo, h),
            "mejora": _num(1 - elegido["nota"].mean() / fijo["nota"].mean()),
            "serie": _serie_rango(elegido, fijo) if h != "largo" else None}
    return salida


def rango_de_hoy(ctx, h, precio, volatilidad):
    """Rango provisional del último dato: el método elegido, centrado en el precio de hoy, con el
    ancho ajustado solo con las respuestas conocidas antes del 1/1/2022 (nada del test)."""
    # «fecha fin» vacía: la respuesta de esta ficha aún no se conoce (y el método elegido no la usa)
    ficha = pd.DataFrame({"horizonte": [h], "pliegue": [FIN_AJUSTE_PROVISIONAL], "fecha": [config.FECHA_CORTE],
                          "fecha fin": [pd.NaT], "variación prevista": [0.0], "volatilidad": [volatilidad]})
    r = inc.rangos(ficha, ctx, RANGO_ELEGIDO[h], años=[FIN_AJUSTE_PROVISIONAL]).iloc[0]
    return precio * float(np.exp(r["bajo"])), precio * float(np.exp(r["alto"]))


def prevision(tabla, ctx, datos_rango):
    precio, fecha = float(tabla["brent"].iloc[-1]), tabla.index[-1]
    volatilidad = float(ctx.loc[fecha, "volatilidad"])
    plazos = {}
    for h in HORIZONTES:
        bajo, alto = rango_de_hoy(ctx, h, precio, volatilidad)
        medido = datos_rango["plazos"][h]["elegido"]
        plazos[h] = {"sesiones": config.HORIZONTES[h],
                     # días laborables: aproximada salvo a 1 semana (3/11 + 5 sesiones = 10/11, D34)
                     "fecha_objetivo": _fecha(fecha + pd.offsets.BDay(config.HORIZONTES[h])),
                     "fecha_aproximada": h != "corto",
                     "red": RED_ELEGIDA[h], "prevision_red": None, "ingenuo": _num(precio, 2),
                     "bajo": _num(bajo, 2), "alto": _num(alto, 2),
                     "cobertura": medido["cobertura"], "margen": medido["margen"],
                     "orientativo": ORIENTATIVO[h]}
    return {"estado": "provisional", "fecha": _fecha(fecha), "precio": _num(precio, 2),
            "volatilidad": _num(volatilidad, 3), "ajuste_hasta": f"{FIN_AJUSTE_PROVISIONAL - 1}-12-31",
            "plazos": plazos}


# --- El espejismo (D15) --------------------------------------------------------------------------

def espejismo():
    precios = cpr.leer()
    semillas = config.SEMILLAS_ESTABILIDAD[:config.N_SEMILLAS_PROMEDIO]
    prev = es.leer_previsiones()
    nuestra = es.promedio(prev[(prev["modelo"] == "RNN") & prev["horizonte"].isin(cpr.HORIZONTES)], semillas)
    nuestra = nuestra.merge(precios[["horizonte", "fecha", "fecha objetivo"]], on=["horizonte", "fecha"])
    comparar = pd.concat([precios[ha.COLUMNAS].assign(modelo="precios"),
                          nuestra[ha.COLUMNAS].assign(modelo="variaciones"),
                          precios.assign(modelo="ingenuo", **{"variación prevista": 0.0})[ha.COLUMNAS]],
                         ignore_index=True)
    t = cpr.espejismo(comparar).xs("corto", level="horizonte")
    medidas = {m: {"nota": _num(f["nota (MAE / ingenuo)"], 3), "correlacion": _num(f["correlación de niveles"], 3),
                   "error_futuro": _num(f["error frente al precio futuro ($)"], 2),
                   "error_hoy": _num(f["error frente al precio de hoy ($)"], 2)} for m, f in t.iterrows()}
    g = precios[(precios["horizonte"] == "corto") & precios["fecha objetivo"].between(*SERIE_ESPEJISMO)]
    g = g.sort_values("fecha objetivo")
    return {"sesiones": config.HORIZONTES["corto"], "periodo_medidas": "2018-2021", "medidas": medidas,
            "ventana": list(VENTANA_ESPEJISMO),
            "serie": {"fechas": [_fecha(f) for f in g["fecha objetivo"]],
                      "real": _lista(g["precio origen"] * np.exp(g["variación real"])),
                      "ingenuo": _lista(g["precio origen"]), "red_precios": _lista(g["precio previsto"])}}


def main():
    print("Exportando los datos de la web a web/data/ …")
    tabla = brent_real()
    bases = ex._bases()
    ctx = inc.contexto(bases)
    finales = previsiones_finales(bases)
    datos_rango = rango(finales, ctx)
    datos_prevision = prevision(tabla, ctx, datos_rango)

    guardar("historico.json", historico(tabla))
    guardar("cotizaciones.json", cotizaciones(tabla))
    guardar("validacion.json", validacion(finales))
    guardar("rango.json", datos_rango)
    guardar("espejismo.json", espejismo())
    guardar("prevision.json", datos_prevision)
    guardar_pendiente("test.json", {"estado": "pendiente"})
    guardar_pendiente("en_vivo.json", {
        "estado": "pendiente", "fecha_origen": datos_prevision["fecha"],
        "fecha_objetivo": datos_prevision["plazos"]["corto"]["fecha_objetivo"],
        "precio_origen": datos_prevision["precio"], "guardada": None, "commit": None,
        "red": RED_ELEGIDA["corto"], "prevision_red": None, "bajo": None, "alto": None, "precio_real": None})
    print("Hecho.")


if __name__ == "__main__":
    main()
