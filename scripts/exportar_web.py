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
- prevision.json      la previsión publicada: la de los modelos finales desde el último día de origen
                      con los tres plazos (resultados/en_vivo.csv), con su rango del 80 % (D34);
- test.json           examen final (D33): nota de cada modelo, conclusiones y rango;
- en_vivo.json        historial de previsiones en vivo a 1 semana, cada una con el commit que la
                      guardó antes de conocer el precio, y su comprobación cuando existe (D34).

Precios recientes. Si hay datos descargados (data/actual/, con `descarga.actualizar`), el histórico
y las cotizaciones llegan hasta el último Brent publicado; si no, hasta el 3/11/2026 (la foto del
estudio, que no se toca). Las cifras del estudio (validación, rango, espejismo, test) salen siempre
de la foto.

Uso:
    python scripts/exportar_web.py
"""
import io
import json
import subprocess

import numpy as np
import pandas as pd

from oil_price import comprobaciones as cp
from oil_price import config
from oil_price import control_precios as cpr
from oil_price import datos
from oil_price import descarga
from oil_price import entreno_completo as ec
from oil_price import examen_final as exa
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
EN_VIVO = config.DIR_RESULTADOS / "en_vivo.csv"
COMPROBACION = config.DIR_RESULTADOS / "en_vivo_comprobacion.csv"
FINALES = "modelos finales"   # comienzo del nombre de la versión de los modelos finales en en_vivo.csv
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
    """Tabla del CSV solo en los días en que cotizó el Brent, hasta el último dato real. Con datos
    descargados (data/actual/), esos, hasta el último Brent publicado; si no, la foto del estudio."""
    if (descarga.DIR_ACTUAL / "petroleo_dataset.csv").exists():
        tabla = datos.cargar_dataset(descarga.DIR_ACTUAL / "petroleo_dataset.csv")
        dias = datos.cargar_dias_brent(descarga.DIR_ACTUAL / "dias_brent.csv")
        return tabla.loc[tabla.index.isin(dias)].dropna(subset=["brent"])
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


def prevision(datos_rango, tabla):
    """La previsión publicada (D34): la de los modelos finales desde el último día de origen que tiene
    los tres plazos en resultados/en_vivo.csv (guardada allí antes de conocer los precios), con su
    rango del 80 %, el elegido en cada plazo centrado en el precio de ese día (D30, D32)."""
    v = pd.read_csv(EN_VIVO, parse_dates=["fecha origen", "fecha objetivo (estimada)"])
    v = v[v["version"].str.startswith(FINALES)]
    completos = v.groupby("fecha origen")["horizonte"].nunique()
    dia = completos[completos == len(HORIZONTES)].index.max()
    filas = v[v["fecha origen"] == dia].drop_duplicates("horizonte", keep="last").set_index("horizonte")
    precio = float(filas["precio hoy"].iloc[0])
    r = np.log(tabla["brent"].loc[:dia]).diff().iloc[-config.DIAS_VOLATILIDAD:]
    plazos = {}
    for h in HORIZONTES:
        f, medido = filas.loc[h], datos_rango["plazos"][h]["elegido"]
        plazos[h] = {"sesiones": config.HORIZONTES[h], "fecha_objetivo": _fecha(f["fecha objetivo (estimada)"]),
                     # días laborables: exacta a 1 semana salvo festivo; aproximada a 3 meses y a 1 año
                     "fecha_aproximada": h != "corto", "red": RED_ELEGIDA[h],
                     "prevision_red": _num(f["precio previsto"], 2), "ingenuo": _num(precio, 2),
                     "bajo": _num(f["rango bajo"], 2), "alto": _num(f["rango alto"], 2),
                     "cobertura": medido["cobertura"], "margen": medido["margen"], "orientativo": ORIENTATIVO[h]}
    return {"estado": "definitiva", "fecha": _fecha(dia), "precio": _num(precio, 2),
            "volatilidad": _num(r.std() * np.sqrt(252), 3), "ajuste_hasta": _fecha(dia), "plazos": plazos}


def test(ctx):
    """El examen final (D33): nota, MAE, RMSE y p de cada modelo, la conclusión fijada para la red
    elegida y el rango elegido de cada plazo (cobertura, margen, mejora frente al rango fijo)."""
    p = exa.previsiones_examen()
    tabla = exa.tabla_comparativa(p, exa.leer_entrenos())
    concl = exa.conclusiones(p)
    rangos = exa.resumen_rangos(exa.rangos_examen(p, ctx))
    por_año = ha.notas_por_año(ha.sumas_por_año(p))
    plazos = {}
    for h in HORIZONTES:
        modelos = {}
        for m in [*MODELOS, ha.MEDIA, "ingenuo"]:
            f = tabla.loc[(h, m)]
            modelos[m] = {"nota": _num(f["MAE / ingenuo"]), "mae": _num(f["MAE ($)"], 2), "rmse": _num(f["RMSE ($)"], 2),
                          "mejora": _num(f["mejora frente al ingenuo (MAE)"]),
                          "parametros": None if pd.isna(f["parámetros"]) else int(f["parámetros"]),
                          "segundos": _num(f["segundos por entrenamiento"], 1)}
            if m != "ingenuo":
                modelos[m] |= {"p": _num(concl.loc[(h, m), "p (dos colas)"], 3), "conclusion": concl.loc[(h, m), "en el test"],
                               "por_año": {str(a): _num(v, 3) for a, v in por_año.loc[(h, m)].dropna().items()}}
        r = rangos.loc[(h, RANGO_ELEGIDO[h])]
        mejora = 1 - float(r["nota / ingenuo"])
        plazos[h] = {"sesiones": config.HORIZONTES[h], "red_elegida": RED_ELEGIDA[h],
                     "conclusion": concl.loc[(h, RED_ELEGIDA[h]), "conclusión final"], "modelos": modelos,
                     "rango": {"cobertura": _num(r["cobertura"]), "margen": _num(r["margen (±)"]),
                               "tercios": {t_: _num(r[t_]) for t_ in inc.TERCIOS}, "mejora": _num(mejora),
                               "mejora_pct": int(round(100 * mejora)), "veredicto": r["veredicto"]}}
    return {"estado": "hecho", "periodo": "2022-2026", "plazos": plazos}


def _commits(ruta):
    """{(versión, horizonte, origen, creada): commit que guardó esa fila por primera vez}, recorriendo la
    historia de git del archivo. Una previsión sin commit no se ha guardado todavía."""
    rel = ruta.relative_to(config.RAIZ).as_posix()
    git = lambda *a: subprocess.run(["git", *a], cwd=config.RAIZ, capture_output=True, check=True).stdout.decode("utf-8")
    primero = {}
    for sha in git("log", "--reverse", "--format=%H", "--", rel).split():
        t_ = pd.read_csv(io.StringIO(git("show", f"{sha}:{rel}")))
        for clave in zip(t_["version"], t_["horizonte"], t_["fecha origen"].astype(str), t_["creada"]):
            primero.setdefault(clave, sha)
    return primero


def en_vivo():
    """Historial de previsiones en vivo a 1 semana de los modelos finales (D34): todas, también las
    que fallaron, con el commit que las guardó y, cuando existe, el precio real."""
    v = pd.read_csv(EN_VIVO)
    c = pd.read_csv(COMPROBACION) if COMPROBACION.exists() else pd.DataFrame(columns=["version", "fecha origen"])
    commits = _commits(EN_VIVO)
    sel = v[v["version"].str.startswith(FINALES) & (v["horizonte"] == "corto")].sort_values("fecha origen")
    previsiones = []
    for _, f in sel.iterrows():
        comp = c[(c["version"] == f["version"]) & (c["fecha origen"].astype(str) == str(f["fecha origen"]))]
        real = float(comp["precio real"].iloc[0]) if len(comp) else None
        commit = commits.get((f["version"], f["horizonte"], str(f["fecha origen"]), f["creada"]))
        previsiones.append({
            "fecha_origen": _fecha(f["fecha origen"]), "fecha_objetivo": _fecha(f["fecha objetivo (estimada)"]),
            "guardada": str(f["creada"])[:10], "commit": commit, "red": f["red"],
            "prevision_red": _num(f["precio previsto"], 2), "precio_origen": _num(f["precio hoy"], 2),
            "bajo": _num(f["rango bajo"], 2), "alto": _num(f["rango alto"], 2), "precio_real": _num(real, 2),
            "dentro": None if real is None else bool(f["rango bajo"] <= real <= f["rango alto"]),
            "estado": "comprobada" if real is not None else "guardada" if commit else "sin guardar"})
    return {"estado": "historial", "red": RED_ELEGIDA["corto"], "sesiones": config.HORIZONTES["corto"],
            "fecha_objetivo": previsiones[-1]["fecha_objetivo"],
            "comprobadas": sum(x["estado"] == "comprobada" for x in previsiones),
            "previsiones": previsiones}


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
    datos_prevision = prevision(datos_rango, tabla)

    guardar("historico.json", historico(tabla))
    guardar("cotizaciones.json", cotizaciones(tabla))
    guardar("validacion.json", validacion(finales))
    guardar("rango.json", datos_rango)
    guardar("espejismo.json", espejismo())
    guardar("prevision.json", datos_prevision)
    guardar("test.json", test(ctx))
    guardar("en_vivo.json", en_vivo())
    print("Hecho.")


if __name__ == "__main__":
    main()
