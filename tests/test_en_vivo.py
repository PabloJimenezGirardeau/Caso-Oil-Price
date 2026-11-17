"""Pruebas de las previsiones en vivo automáticas: cuándo se guarda una previsión y cómo se comprueba.
Ejecutar con: python -m pytest"""
import pandas as pd
import pytest

from oil_price.inference import en_vivo as ev
from oil_price.utils import config


def test_activa_hasta_el_ultimo_dia_incluido():
    assert ev.activa("2026-11-30 23:00") and not ev.activa("2026-12-01 00:01")
    assert config.ACTUALIZACION_HASTA == pd.Timestamp("2026-11-30")


def test_se_guarda_cada_dia_nuevo_de_la_tanda_si_su_fecha_no_ha_llegado():
    previas = pd.DataFrame([{"version": ev.VERSION_FINAL, "fecha origen": "2026-11-11"},
                            {"version": "modelos del test (hasta 2021)", "fecha origen": "2026-11-13"}])
    dias = pd.to_datetime(["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-16"])
    # La tanda del 12 al 16/11 llega el miércoles 18: las tres fechas previstas (19, 20 y 23/11) son futuras
    origenes, motivo = ev.origenes_nuevos(dias, previas, "2026-11-18 08:15")
    assert origenes == list(pd.to_datetime(["2026-11-12", "2026-11-13", "2026-11-16"])) and "Se guardan" in motivo
    assert ev.objetivo("2026-11-12") == pd.Timestamp("2026-11-19") and ev.objetivo("2026-11-16") == pd.Timestamp("2026-11-23")
    # Si llega el viernes 20: el 12/11 (para el 19) y el 13/11 (para el 20) ya han llegado; solo el 16/11
    origenes, motivo = ev.origenes_nuevos(dias, previas, "2026-11-20")
    assert origenes == [pd.Timestamp("2026-11-16")] and "ya han llegado" in motivo


def test_sin_dias_nuevos_no_se_guarda_nada():
    previas = pd.DataFrame([{"version": ev.VERSION_FINAL, "fecha origen": "2026-11-11"}])
    origenes, motivo = ev.origenes_nuevos(pd.to_datetime(["2026-11-10", "2026-11-11"]), previas, "2026-11-12")
    assert origenes == [] and "No hay días" in motivo


def test_marcar_como_se_guarda():
    tabla = pd.DataFrame({"horizonte": ["corto"], "fecha origen": ["2026-11-16"]})
    filas = ev.marcar(tabla, "2026-11-18T08:15:00", "2026-11-16")
    assert filas.loc[0, "version"] == ev.VERSION_FINAL and filas.loc[0, "creada"] == "2026-11-18T08:15:00"
    assert filas.loc[0, "último Brent publicado"] == "2026-11-16"


def test_comprobar_con_el_precio_cinco_sesiones_despues():
    dias = pd.to_datetime(["2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09", "2026-11-10",
                           "2026-11-11", "2026-11-12"])
    brent = pd.Series([107.03, 91.84, 97.96, 97.83, 91.03, 90.16, 92.14, 93.0], index=dias)
    previas = pd.DataFrame([
        {"version": ev.VERSION_FINAL, "horizonte": "corto", "red": "LSTM", "fecha origen": "2026-11-03",
         "precio hoy": 107.03, "precio previsto": 107.13, "rango bajo": 96.90, "rango alto": 117.75, "creada": "c1"},
        {"version": ev.VERSION_FINAL, "horizonte": "medio", "red": "RNN", "fecha origen": "2026-11-03",
         "precio hoy": 107.03, "precio previsto": 118.0, "rango bajo": 75.0, "rango alto": 151.0, "creada": "c1"},
        {"version": ev.VERSION_FINAL, "horizonte": "corto", "red": "LSTM", "fecha origen": "2026-11-06",
         "precio hoy": 97.83, "precio previsto": 97.74, "rango bajo": 86.31, "rango alto": 110.30, "creada": "c2"},
    ])
    nuevas = ev.comprobar(previas, pd.DataFrame(columns=ev.COLUMNAS_COMPROBACION), brent, "ahora")
    assert len(nuevas) == 1                                       # la del 6/11 aún no tiene su quinta sesión
    c = nuevas.iloc[0]
    assert c["fecha real"] == "2026-11-10" and c["precio real"] == pytest.approx(90.16)
    assert c["error de la red ($)"] == pytest.approx(107.13 - 90.16) and c["error del ingenuo ($)"] == pytest.approx(107.03 - 90.16)
    assert not c["dentro del rango"] and list(nuevas.columns) == ev.COLUMNAS_COMPROBACION
    # Lo ya comprobado no se repite
    assert ev.comprobar(previas, nuevas, brent, "ahora").empty


def test_la_comprobacion_coincide_con_la_hecha_a_mano():
    """La comprobación automática del 3/11 da lo mismo que la hecha a mano el 14/11 (resultados/en_vivo_comprobacion.csv)."""
    from oil_price.inference import datos_web as dw
    a_mano = pd.read_csv(config.DIR_RESULTADOS / "en_vivo_comprobacion.csv")
    previas = pd.read_csv(config.DIR_RESULTADOS / "en_vivo.csv")
    previas = previas[previas["fecha origen"] == "2026-11-03"]
    brent = dw.brent_real()["brent"]
    if brent.index[-1] < pd.Timestamp("2026-11-10"):
        pytest.skip("sin datos descargados hasta el 10/11 (data/actual)")
    auto = ev.comprobar(previas, pd.DataFrame(columns=ev.COLUMNAS_COMPROBACION), brent, "ahora")
    columnas = ["version", "fecha origen", "fecha real", "precio real", "dentro del rango"]
    a_mano = a_mano[columnas].sort_values("version").reset_index(drop=True)
    auto = auto[columnas].sort_values("version").reset_index(drop=True)
    pd.testing.assert_frame_equal(a_mano.astype(str), auto.astype(str))
