"""Previsiones en vivo (D34), automáticas: guardar una previsión nueva cuando FRED publica un día de Brent nuevo,
y comprobar las pendientes cuando ya se conoce su precio.

Lo usa la actualización diaria (`scripts/inference/actualizar_diario.py`), que lanza GitHub Actions cada mañana
hasta `config.ACTUALIZACION_HASTA`. Dos reglas:
- FRED publica por tandas, con alrededor de una semana de retraso. Con cada tanda se guarda una previsión desde
  **cada día nuevo** (posterior al último ya guardado) cuya fecha prevista a 1 semana **todavía no ha llegado**:
  nunca se guarda algo ya ocurrido. El commit que la guarda, con su fecha, lo demuestra después;
- el precio real con el que se comprueba es el del Brent **5 sesiones después** del día de origen, la misma
  definición que en el entrenamiento y en la comprobación hecha a mano del 10/11/2026.
"""
import pandas as pd

from oil_price.utils import config

VERSION_FINAL = "modelos finales (hasta el 3/11/2026)"
COLUMNAS_COMPROBACION = ["version", "horizonte", "red", "fecha origen", "fecha real", "precio hoy", "precio previsto",
                         "precio real", "error de la red ($)", "error del ingenuo ($)", "rango bajo", "rango alto",
                         "dentro del rango", "creada", "comprobada"]


def activa(hoy, hasta=config.ACTUALIZACION_HASTA):
    """¿Sigue en marcha la actualización automática? (hasta `hasta`, ese día incluido)."""
    return pd.Timestamp(hoy).normalize() <= pd.Timestamp(hasta).normalize()


def objetivo(origen, sesiones=config.HORIZONTES["corto"]):
    """Fecha prevista a 1 semana desde `origen`, como la estima modelo_final.prever (días laborables)."""
    return pd.Timestamp(origen) + pd.offsets.BDay(sesiones)


def origenes_nuevos(dias, previas, hoy):
    """(días de origen que guardar, motivo). Los días con Brent posteriores al último origen ya guardado de los
    modelos finales cuya fecha prevista a 1 semana es posterior a `hoy`. Los que ya han llegado se saltan."""
    guardados = pd.to_datetime(previas.loc[previas["version"] == VERSION_FINAL, "fecha origen"]) if len(previas) else []
    ultimo = max(guardados) if len(guardados) else None
    nuevos = [pd.Timestamp(d) for d in dias if ultimo is None or pd.Timestamp(d) > ultimo]
    if not nuevos:
        return [], "No hay días de Brent nuevos desde la última previsión guardada."
    hoy = pd.Timestamp(hoy).normalize()
    validos = [d for d in nuevos if objetivo(d).normalize() > hoy]
    saltados = [d for d in nuevos if d not in validos]
    motivo = (f"Días nuevos: {', '.join(str(d.date()) for d in nuevos)}. Se guardan: "
              f"{', '.join(str(d.date()) for d in validos) or 'ninguno'}"
              + (f" (los demás ya han llegado a su fecha prevista: {', '.join(str(d.date()) for d in saltados)})." if saltados else "."))
    return validos, motivo


def marcar(tabla, creada, ultimo_brent):
    """Las filas de una previsión (modelo_final.prever) tal como se guardan en en_vivo.csv."""
    return tabla.assign(version=VERSION_FINAL, creada=creada, **{"último Brent publicado": ultimo_brent})


def comprobar(previas, comprobadas, brent, comprobada, sesiones=config.HORIZONTES["corto"]):
    """Filas que añadir a en_vivo_comprobacion.csv: las previsiones a 1 semana todavía sin comprobar cuyo precio
    real ya se conoce. `brent`: el precio de los días reales de cotización (lo que publica FRED)."""
    hechas = set(zip(comprobadas["version"], comprobadas["fecha origen"].astype(str))) if len(comprobadas) else set()
    filas = []
    for _, f in previas[previas["horizonte"] == "corto"].iterrows():
        origen = pd.Timestamp(f["fecha origen"])
        clave = (f["version"], str(origen.date()))
        if clave in hechas or origen not in brent.index:
            continue
        posicion = brent.index.get_loc(origen)
        if posicion + sesiones >= len(brent):
            continue                                       # su precio aún no se ha publicado
        dia, real = brent.index[posicion + sesiones], float(brent.iloc[posicion + sesiones])
        filas.append({"version": f["version"], "horizonte": "corto", "red": f["red"], "fecha origen": clave[1],
                      "fecha real": str(dia.date()), "precio hoy": f["precio hoy"], "precio previsto": f["precio previsto"],
                      "precio real": real, "error de la red ($)": f["precio previsto"] - real,
                      "error del ingenuo ($)": f["precio hoy"] - real, "rango bajo": f["rango bajo"],
                      "rango alto": f["rango alto"], "dentro del rango": bool(f["rango bajo"] <= real <= f["rango alto"]),
                      "creada": f["creada"], "comprobada": comprobada})
        hechas.add(clave)
    return pd.DataFrame(filas, columns=COLUMNAS_COMPROBACION)
