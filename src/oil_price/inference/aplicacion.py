"""Lógica de la aplicación: datos, previsión y explicación. La interfaz es la web del proyecto (web/), que
sirve app/app.py; el formato de los datos para la web está en `datos_web.py`.

- Carga los modelos finales (de la carpeta local `modelos/final` o, si no está, del repositorio de
  modelo en Hugging Face) y los datos más recientes (descargados de FRED y Yahoo Finance a una
  carpeta aparte; si la descarga falla, los últimos que haya o la foto del estudio, avisándolo).
- Pasa los datos por los modelos ya entrenados, sin reentrenar: prevé a 1 semana, 3 meses y 1 año
  desde el último día, con el rango del 80 % (D30, D32).
- Explica cada previsión en lenguaje sencillo, con la fiabilidad que dio el examen final.
"""
import json
import socket
import threading
from pathlib import Path

import numpy as np
import pandas as pd

from oil_price.utils import config
from oil_price.data import datos, descarga, preprocesado as pp
from oil_price.evaluation import incertidumbre as inc
from oil_price.inference import modelo_final as mf

REPO_MODELO = "PabloJimenezGirardeau/brent-rnn-lstm-gru"
ORDEN = ["corto", "medio", "largo"]
NOMBRE = {"corto": "1 semana", "medio": "3 meses", "largo": "1 año"}


# --- Formato -------------------------------------------------------------------------------------

def num(valor, decimales=2):
    """107.03 → «107,03»; 6501 → «6.501»."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    entero, _, fraccion = f"{abs(valor):.{decimales}f}".partition(".")
    miles = f"{int(entero):,}".replace(",", ".")
    return ("−" if valor < 0 else "") + miles + ("," + fraccion if fraccion else "")


NBSP = "\u00a0"   # espacio que no se separa: «92,47 $» y «80 %» nunca se parten entre dos líneas


def dolares(valor, decimales=2):
    return f"{num(valor, decimales)}{NBSP}$"


def variacion(porcentaje, decimales=1):
    """3.54 → «+3,5 %»."""
    return ("+" if porcentaje > 0 else "") + num(porcentaje, decimales) + f"{NBSP}%"


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


# --- Explicación ------------------------------------------------------------------------------------

def fiabilidad(estudio, h, red):
    """Lo que dijeron los estudios de esta red a este plazo, con las cifras de los datos."""
    t = estudio["test"]["plazos"][h]
    v = estudio["validacion"]["plazos"][h]
    return {"nota_examen": t["modelos"][red]["nota"], "conclusion": t["conclusion"], "cobertura": t["rango"]["cobertura"],
            "margen": t["rango"]["margen"], "periodo": estudio["test"]["periodo"], "nota_pruebas": v["modelos"][red]["nota"],
            "periodo_pruebas": estudio["validacion"]["periodo"], "mejora_rango": t["rango"]["mejora_pct"]}


def explicar(fila, estudio, precios):
    """Texto breve para un usuario no técnico, en tres apartados: qué significa la previsión, qué fiabilidad
    tiene en ese plazo (según el examen final) y qué factores pueden invalidarla. Lista de {titulo, texto}."""
    h, red = fila["horizonte"], fila["red"]
    f = fiabilidad(estudio, h, red)
    cambio = 100 * (fila["precio previsto"] / fila["precio hoy"] - 1)
    ancho = (100 * (fila["rango bajo"] / fila["precio hoy"] - 1), 100 * (fila["rango alto"] / fila["precio hoy"] - 1))
    dif = 100 * (f["nota_examen"] - 1)
    quien = "quien supone que el precio no cambia"
    cuanto = (f"prácticamente lo mismo que {quien} (un {num(abs(dif), 1)}{NBSP}% {'más' if dif > 0 else 'menos'})" if abs(dif) < 2
              else f"un {num(abs(dif), 0)}{NBSP}% {'más' if dif > 0 else 'menos'} que {quien}")
    reciente = (precios.pct_change().iloc[-30:] * 100).dropna()
    peor = reciente.abs().idxmax()
    orientativo = " Es orientativo: hay muy pocos movimientos anuales independientes para comprobarlo." if h == "largo" else ""
    return [
        {"titulo": "Qué significa",
         "texto": f"La red {red} prevé que dentro de {fila['sesiones']} sesiones (hacia el "
                  f"{fecha(fila['fecha objetivo (estimada)'])}) el Brent estará en {dolares(fila['precio previsto'])}, "
                  f"un {variacion(cambio)} sobre el precio de hoy ({dolares(fila['precio hoy'])}). Lo más útil es el rango "
                  f"del 80{NBSP}%: de {dolares(fila['rango bajo'])} a {dolares(fila['rango alto'])} ({variacion(ancho[0])} a "
                  f"{variacion(ancho[1])}). Ocho de cada diez veces, el precio real debería quedar dentro."},
        {"titulo": "Qué fiabilidad tiene",
         "texto": f"En el examen final ({f['periodo']}), esta red a {NOMBRE[h]} se equivocó {cuanto}: «{f['conclusion']}». "
                  f"Por eso su previsión es orientativa. El rango, en cambio, acertó el {num(100 * f['cobertura'], 0)}{NBSP}% "
                  f"de las veces (margen de ±{num(100 * f['margen'], 0)} puntos).{orientativo}"},
        {"titulo": "Qué puede invalidarla",
         "texto": "Los choques que ningún dato de mercado anticipa: una guerra, una decisión de la OPEP+, una crisis "
                  "financiera o una pandemia. El rango se ensancha cuando el mercado está nervioso, pero no puede ver "
                  f"venir una sorpresa. En los últimos 30 días, la mayor variación en un día fue de "
                  f"{variacion(float(reciente.loc[peor]))} (el {fecha(peor)})."},
    ]


# --- La aplicación ---------------------------------------------------------------------------------

class Aplicacion:
    """Estado de la aplicación: modelos, datos y previsiones. Los modelos se cargan una vez; los datos, cada
    vez que se pide (`cargar`), y solo pasan por los modelos: no se reentrena nada."""

    def __init__(self, directorio_estudio, directorio_modelos=None, directorio_datos=descarga.DIR_ACTUAL):
        self.estudio = cargar_estudio(directorio_estudio)
        self.directorio_datos = Path(directorio_datos)
        self.modelos = cargar_modelos(directorio_modelos)
        self.cerrojo = threading.Lock()
        self.avisos, self.origen = [], ""
        self.limpio = self.bases = self.ctx = self.tabla = None

    def cargar(self, descargar=True):
        """Descarga (o lee) los datos y los pasa por los modelos."""
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

    @property
    def modelos_hasta(self):
        """Último día con el que se entrenaron los modelos (todos los días con respuesta conocida hasta entonces)."""
        return min(m.fin_train for m in self.modelos.values())

    def fila(self, h):
        return {**self.tabla.loc[h].to_dict(), "horizonte": h}

    def explicacion(self, h):
        return explicar(self.fila(h), self.estudio, self.precios)
