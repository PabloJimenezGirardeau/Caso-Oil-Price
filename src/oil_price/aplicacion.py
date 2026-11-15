"""Lógica de la aplicación (la interfaz está en app/app.py): datos, previsión, explicación y gráficos.

- Carga los modelos finales (de la carpeta local `modelos/final` o, si no está, del repositorio de
  modelo en Hugging Face) y los datos más recientes (descargados de FRED y Yahoo Finance a una
  carpeta aparte; si la descarga falla, los últimos que haya o la foto del estudio, avisándolo).
- Prevé a 1 semana, 3 meses y 1 año desde el último día, con el rango del 80 % (D30, D32).
- Explica cada previsión en lenguaje sencillo, con la fiabilidad que dio el examen final.
- Marca en el histórico los grandes picos y caídas y explica el ciclo económico.
- Reentrena los modelos con los datos nuevos, con la misma configuración (la de su ficha).
"""
import json
import socket
import tempfile
import threading
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import config, datos, descarga, incertidumbre as inc, modelo_final as mf, preprocesado as pp

REPO_MODELO = "PabloJimenezGirardeau/brent-rnn-lstm-gru"
ORDEN = ["corto", "medio", "largo"]
NOMBRE = {"corto": "1 semana", "medio": "3 meses", "largo": "1 año"}
HISTORIA = {"corto": 45, "medio": 150, "largo": 380}      # sesiones de pasado que se enseñan en el gráfico
AMBAR, HUESO, GRIS, FONDO = "#f2921d", "#f4efe6", "#a39c90", "#0a0908"
DIR_TRABAJO = Path(tempfile.gettempdir()) / "brent_app"


# --- Formato -------------------------------------------------------------------------------------

def num(valor, decimales=2):
    """107.03 → «107,03»; 6501 → «6.501»."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    entero, _, fraccion = f"{abs(valor):.{decimales}f}".partition(".")
    miles = f"{int(entero):,}".replace(",", ".")
    return ("−" if valor < 0 else "") + miles + ("," + fraccion if fraccion else "")


def dolares(valor, decimales=2):
    return f"{num(valor, decimales)} $"


def variacion(porcentaje, decimales=1):
    """3.54 → «+3,5 %»."""
    return ("+" if porcentaje > 0 else "") + num(porcentaje, decimales) + " %"


def fecha(valor):
    """2026-11-03 → «3/11/2026»."""
    t = pd.Timestamp(valor)
    return f"{t.day}/{t.month}/{t.year}"


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def mes_año(valor):
    t = pd.Timestamp(valor)
    return f"{MESES[t.month - 1]} de {t.year}"


# --- Datos y modelos -------------------------------------------------------------------------------

def cargar_modelos(directorio=None):
    """Los modelos finales: de `directorio`, de modelos/final si existe o de Hugging Face."""
    for candidato in (directorio, mf.DIR_MODELOS / "final"):
        if candidato and Path(candidato).exists() and any(Path(candidato).glob("*/ficha.json")):
            return mf.cargar(candidato)
    from huggingface_hub import snapshot_download
    return mf.cargar(snapshot_download(REPO_MODELO))


def cargar_estudio(directorio):
    """Resultados del estudio que usa la explicación: el examen final y la validación 2010-2021."""
    directorio = Path(directorio)
    return {n: json.loads((directorio / f"{n}.json").read_text(encoding="utf-8")) for n in ("test", "validacion")}


def cargar_datos(directorio=descarga.DIR_ACTUAL, descargar=True):
    """(tabla limpia, avisos, de dónde vienen). Con `descargar`, intenta bajar los datos más recientes; si no
    puede, usa los últimos descargados y, si no hay, la foto del estudio, y lo avisa."""
    directorio = Path(directorio)
    avisos = []
    if descargar:
        try:
            socket.setdefaulttimeout(30)
            descarga.actualizar(directorio, registrar=lambda m: avisos.append(m) if m.startswith("Aviso") else None)
        except Exception as error:
            avisos.append(f"No se han podido descargar datos nuevos: {error}")
    try:
        if (directorio / "petroleo_dataset.csv").exists():
            return descarga.cargar(directorio), avisos, "descargados de FRED y Yahoo Finance"
    except Exception as error:
        avisos.append(f"Los datos descargados no sirven ({error})")
    return datos.cargar_datos_limpios(), avisos, f"la foto del estudio (hasta el {fecha(config.FECHA_CORTE)})"


def preparar(limpio):
    """Entradas y objetivos de los modelos, y el contexto para el rango (volatilidad y variaciones pasadas)."""
    bases = {nivel: pp.preparar_base(limpio, con_nivel=nivel) for nivel in (True, False)}
    return bases, inc.contexto(bases)


# --- Ciclo económico -------------------------------------------------------------------------------

def _caida(antes, despues):
    return f"{num(100 * (1 - despues['precio'] / antes['precio']), 0)} %"


def _mayor_caida_diaria(precios, desde):
    c = 100 * (1 - precios / precios.shift(1))
    c = c.iloc[desde + 1:]
    return (float(c.max()), c.idxmax()) if len(c) and c.max() > 0 else None


# tipo: el máximo o el mínimo del tramo. «referencia»: solo sirve para el texto del siguiente episodio.
_EPISODIOS = [
    dict(tipo="max", desde="2008-01-01", hasta="2008-12-31", titulo="Máximo histórico",
         texto=lambda e, a, s: f"El {fecha(e['fecha'])}, {dolares(e['precio'])}. La demanda de China y otros emergentes, "
                               "un dólar débil y la entrada de dinero financiero en las materias primas empujaron el Brent "
                               "a su récord, justo antes de la crisis."),
    dict(tipo="min", desde="2008-07-01", hasta="2009-06-30", titulo="Crisis financiera",
         texto=lambda e, a, s: f"Tras la quiebra de Lehman Brothers, la recesión mundial hundió la demanda: {dolares(e['precio'])} "
                               f"en {mes_año(e['fecha'])}, un {_caida(a, e)} menos que en el máximo, en medio año."),
    dict(tipo="max", desde="2014-01-01", hasta="2014-08-31", referencia=True),
    dict(tipo="min", desde="2015-06-01", hasta="2016-06-30", titulo="Exceso de oferta",
         texto=lambda e, a, s: "El petróleo de esquisto de EE. UU. inundó el mercado y la OPEP decidió no recortar su "
                               f"producción para defender su cuota. De {dolares(a['precio'])} en {mes_año(a['fecha'])} a "
                               f"{dolares(e['precio'])} en {mes_año(e['fecha'])}: un {_caida(a, e)} menos."),
    dict(tipo="min", desde="2020-01-01", hasta="2020-12-31", titulo="Pandemia",
         texto=lambda e, a, s: "Los confinamientos paralizaron el transporte y la industria, el consumo se desplomó y los "
                               f"almacenes se llenaron. El {fecha(e['fecha'])}, {dolares(e['precio'])}"
                               + (f": el precio más bajo de toda la serie desde {s.index[0].year}." if e["precio"] <= s.min() else ".")),
    dict(tipo="max", desde="2022-01-01", hasta="2022-12-31", titulo="Invasión de Ucrania",
         texto=lambda e, a, s: "La invasión rusa de Ucrania y las sanciones a Rusia, uno de los mayores exportadores de crudo, "
                               f"dispararon el miedo a quedarse sin suministro: {dolares(e['precio'])} en {mes_año(e['fecha'])}."),
    dict(tipo="max", desde="2026-01-01", hasta="2099-12-31", titulo="Lo más reciente",
         texto=lambda e, a, s: (f"En 2026 el Brent volvió a dispararse, hasta {dolares(e['precio'])} el {fecha(e['fecha'])}, y "
                                "después cayó con la misma brusquedad"
                                + (lambda g: f": un {num(g[0], 1)} % en un solo día, el {fecha(g[1])}." if g else ".")(
                                    _mayor_caida_diaria(s, e["posicion"]))
                                + " Movimientos así no se pueden anticipar con datos de mercado: es justo cuando el rango se ensancha.")),
]


def episodios(precios):
    """Los grandes picos y caídas del Brent: la fecha y el precio se buscan en los datos (el máximo o el
    mínimo de cada tramo); solo la explicación es texto. `precios`: serie diaria con fechas como índice."""
    salida, anterior = [], None
    for e in _EPISODIOS:
        tramo = precios.loc[e["desde"]:e["hasta"]]
        if tramo.empty:
            continue
        dia = tramo.idxmax() if e["tipo"] == "max" else tramo.idxmin()
        actual = {"fecha": dia, "precio": float(tramo.loc[dia]), "posicion": int(precios.index.get_loc(dia))}
        if not e.get("referencia"):
            salida.append({**actual, "tipo": e["tipo"], "titulo": e["titulo"], "texto": e["texto"](actual, anterior, precios)})
        anterior = actual
    return salida


# --- Previsión y explicación -----------------------------------------------------------------------

def _limite(nudos, precio_hoy, s, lado):
    """Límite del abanico en la sesión s: pasa por los rangos calculados y, entre ellos, se interpola con la
    raíz del tiempo. Devuelve log(límite / precio de hoy)."""
    anterior = (0.0, 0.0)
    for sesiones, valor in nudos:
        v = np.log(valor[lado] / precio_hoy)
        if s <= sesiones:
            return anterior[1] + (v - anterior[1]) * (np.sqrt(s) - np.sqrt(anterior[0])) / (np.sqrt(sesiones) - np.sqrt(anterior[0]))
        anterior = (sesiones, v)
    return anterior[1]


def fiabilidad(estudio, h, red):
    """Lo que dijeron los estudios de esta red a este plazo, con las cifras de los datos."""
    t = estudio["test"]["plazos"][h]
    v = estudio["validacion"]["plazos"][h]
    return {"nota_examen": t["modelos"][red]["nota"], "conclusion": t["conclusion"], "cobertura": t["rango"]["cobertura"],
            "margen": t["rango"]["margen"], "periodo": estudio["test"]["periodo"], "nota_pruebas": v["modelos"][red]["nota"],
            "periodo_pruebas": estudio["validacion"]["periodo"], "mejora_rango": t["rango"]["mejora_pct"]}


def explicar(fila, estudio, precios):
    """Texto breve para un usuario no técnico: qué significa la previsión, qué fiabilidad tiene en ese plazo
    (según la comparativa) y qué factores pueden invalidarla."""
    h, red = fila["horizonte"], fila["red"]
    f = fiabilidad(estudio, h, red)
    cambio = 100 * (fila["precio previsto"] / fila["precio hoy"] - 1)
    ancho = (100 * (fila["rango bajo"] / fila["precio hoy"] - 1), 100 * (fila["rango alto"] / fila["precio hoy"] - 1))
    dif = 100 * (f["nota_examen"] - 1)
    quien = "quien supone que el precio no cambia"
    cuanto = (f"prácticamente lo mismo que {quien} (un {num(abs(dif), 1)} % {'más' if dif > 0 else 'menos'})" if abs(dif) < 2
              else f"un {num(abs(dif), 0)} % {'más' if dif > 0 else 'menos'} que {quien}")
    reciente = precios.pct_change().iloc[-30:] * 100
    peor = reciente.abs().idxmax()
    orientativo = " Es orientativo: hay muy pocos movimientos anuales independientes para comprobarlo." if h == "largo" else ""
    return (
        f"**Qué significa.** La red {red} prevé que dentro de {fila['sesiones']} sesiones (hacia el {fecha(fila['fecha objetivo (estimada)'])}) "
        f"el Brent estará en {dolares(fila['precio previsto'])}, un {variacion(cambio)} sobre el precio de hoy ({dolares(fila['precio hoy'])}). "
        f"Lo más útil es el rango del 80 %: de {dolares(fila['rango bajo'])} a {dolares(fila['rango alto'])} "
        f"({variacion(ancho[0])} a {variacion(ancho[1])}). Ocho de cada diez veces, el precio real debería quedar dentro.\n\n"
        f"**Qué fiabilidad tiene.** En el examen final ({f['periodo']}), esta red a {NOMBRE[h]} se equivocó {cuanto}: "
        f"*{f['conclusion']}*. Por eso la previsión de la red es orientativa. El rango, en cambio, acertó el "
        f"{num(100 * f['cobertura'], 0)} % de las veces (margen de ±{num(100 * f['margen'], 0)} puntos).{orientativo}\n\n"
        f"**Qué puede invalidarla.** Los choques que ningún dato de mercado anticipa: una guerra, una decisión de la OPEP+, una crisis "
        f"financiera o una pandemia. El rango se ensancha cuando el mercado está nervioso, pero no puede ver venir una sorpresa. "
        f"En los últimos 30 días, la mayor variación en un día fue de {variacion(float(reciente.loc[peor]))} (el {fecha(peor)})."
    )


def tabla_comparativa(estudio, h):
    """La comparativa del examen final de un plazo, en Markdown: error medio, RMSE, frente al ingenuo, parámetros
    y tiempo de entrenamiento de cada red, el lineal y el ingenuo."""
    t = estudio["test"]["plazos"][h]
    filas = ["| Modelo | Error medio (MAE) | RMSE | Frente al ingenuo | Parámetros | Entrenamiento |", "|---|---:|---:|---:|---:|---:|"]
    for modelo, nombre in [("RNN", "RNN"), ("LSTM", "LSTM"), ("GRU", "GRU"), ("Lineal", "Lineal (referencia)"), ("ingenuo", "Ingenuo (precio de hoy)")]:
        m = t["modelos"][modelo]
        elegido = "**" if modelo == t["red_elegida"] else ""
        frente = "—" if modelo == "ingenuo" else f"{num(abs(100 * m['mejora']), 1)} % {'menos' if m['mejora'] > 0 else 'más'} de error"
        parametros = "—" if not m["parametros"] else num(m["parametros"], 0)
        seg = "—" if modelo in ("Lineal", "ingenuo") else f"{num(m['segundos'], 1)} s"
        filas.append(f"| {elegido}{nombre}{elegido} | {num(m['mae'])} $ | {num(m['rmse'])} $ | {frente} | {parametros} | {seg} |")
    return "\n".join(filas)


class Aplicacion:
    """Estado de la aplicación: modelos, datos y previsiones. Un solo usuario a la vez (es una demostración)."""

    def __init__(self, directorio_estudio, directorio_modelos=None, directorio_datos=descarga.DIR_ACTUAL):
        self.estudio = cargar_estudio(directorio_estudio)
        self.directorio_datos = Path(directorio_datos)
        self.modelos = cargar_modelos(directorio_modelos)
        self.cerrojo = threading.Lock()
        self.avisos, self.origen = [], ""
        self.limpio = self.bases = self.ctx = self.tabla = None

    def cargar(self, descargar=True):
        """Descarga (o lee) los datos y recalcula las previsiones."""
        with self.cerrojo:
            self.limpio, self.avisos, self.origen = cargar_datos(self.directorio_datos, descargar)
            self.bases, self.ctx = preparar(self.limpio)
            self.tabla = mf.prever(self.modelos, self.bases, self.ctx).set_index("horizonte")
        return self

    @property
    def precios(self):
        return self.limpio["brent"]

    @property
    def ultimo_dia(self):
        return self.limpio.index[-1]

    def fila(self, h):
        return {**self.tabla.loc[h].to_dict(), "horizonte": h}

    def explicacion(self, h):
        return explicar(self.fila(h), self.estudio, self.precios)

    def reentrenar(self, semillas=None, registrar=print):
        """Reentrena los tres modelos con los datos hasta el último día, con la misma configuración, y recalcula."""
        with self.cerrojo:
            nuevos = mf.reentrenar(self.modelos, self.bases, self.ultimo_dia, semillas=semillas, registrar=registrar)
            self.modelos = nuevos
            mf.guardar(nuevos, DIR_TRABAJO / "modelos")
            self.tabla = mf.prever(self.modelos, self.bases, self.ctx).set_index("horizonte")
        return self

    # --- Gráficos ---
    def grafico_prevision(self, h):
        return grafico_prevision(self.bases[False].precio, self.tabla, h)

    def grafico_ciclo(self):
        return grafico_ciclo(self.precios, episodios(self.precios))


# --- Gráficos (plotly) --------------------------------------------------------------------------------

def _estilo(fig, alto):
    fig.update_layout(height=alto, margin=dict(l=8, r=8, t=44, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=GRIS, size=12), showlegend=True, legend=dict(orientation="h", y=1.08, x=0),
                      hovermode="x unified")
    fig.update_xaxes(gridcolor="rgba(255,244,230,0.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,244,230,0.08)", zeroline=False, ticksuffix=" $")
    return fig


def grafico_prevision(precios, tabla, h):
    """El precio reciente y, hacia el futuro, el abanico del rango del 80 % hasta el plazo elegido, con la
    previsión de la red y el ingenuo (el precio de hoy, sin cambios)."""
    fila = tabla.loc[h]
    hoy, origen = float(fila["precio hoy"]), pd.Timestamp(fila["fecha origen"])
    nudos = [(int(tabla.loc[c, "sesiones"]), {"bajo": float(tabla.loc[c, "rango bajo"]), "alto": float(tabla.loc[c, "rango alto"])})
             for c in ORDEN[:ORDEN.index(h) + 1]]
    sesiones = int(fila["sesiones"])
    pasos = np.arange(sesiones + 1) if sesiones <= 70 else np.unique(np.round(np.linspace(0, sesiones, 70)))
    fechas = [origen + pd.offsets.BDay(int(round(s))) for s in pasos]
    altos = [hoy * np.exp(_limite(nudos, hoy, s, "alto")) for s in pasos]
    bajos = [hoy * np.exp(_limite(nudos, hoy, s, "bajo")) for s in pasos]
    pasado = precios.iloc[-HISTORIA[h]:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pasado.index, y=pasado.values, name="Brent", line=dict(color=HUESO, width=1.6)))
    fig.add_trace(go.Scatter(x=fechas, y=altos, line=dict(color=AMBAR, width=1.2), name="Rango del 80 %", legendgroup="r"))
    fig.add_trace(go.Scatter(x=fechas, y=bajos, line=dict(color=AMBAR, width=1.2), fill="tonexty",
                             fillcolor="rgba(242,146,29,0.22)", showlegend=False, legendgroup="r"))
    fig.add_trace(go.Scatter(x=[origen, fechas[-1]], y=[hoy, hoy], name="Ingenuo (precio de hoy)",
                             line=dict(color=GRIS, width=1.2, dash="dot")))
    fig.add_trace(go.Scatter(x=[fechas[-1]], y=[float(fila["precio previsto"])], name=f"Previsión de la {fila['red']}", mode="markers",
                             marker=dict(color="#000000", size=11, line=dict(color=HUESO, width=2))))
    fig.add_vline(x=origen, line=dict(color="rgba(244,239,230,0.25)", dash="dot"))
    return _estilo(fig, 400)


def grafico_ciclo(precios, lista):
    """Todo el histórico con los grandes episodios numerados."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=precios.index, y=precios.values, name="Brent", line=dict(color=HUESO, width=1.1), opacity=0.8))
    fig.add_trace(go.Scatter(
        x=[e["fecha"] for e in lista], y=[e["precio"] for e in lista], mode="markers+text", name="Grandes episodios",
        text=[f"{n + 1:02d}" for n in range(len(lista))], textposition=["top center" if e["tipo"] == "max" else "bottom center" for e in lista],
        textfont=dict(color=AMBAR, size=12), marker=dict(color=AMBAR, size=9, line=dict(color="#000000", width=1.5)),
        customdata=[[e["titulo"]] for e in lista], hovertemplate="%{customdata[0]}<br>%{x|%d/%m/%Y} · %{y:.2f} $<extra></extra>"))
    return _estilo(fig, 430)
