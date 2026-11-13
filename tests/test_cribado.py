"""Pruebas de la criba de información nueva con el entrenamiento (cribado.py). Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import cribado as cr


@pytest.fixture(scope="module")
def datos_criba():
    return cr.medidas()


def test_la_puntuacion_z_no_mira_el_futuro():
    x = pd.Series(np.random.default_rng(0).normal(size=600))
    z = cr._z(x)
    cambiada = x.copy()
    cambiada.iloc[400:] += 50                    # cambiar el futuro...
    pd.testing.assert_series_equal(cr._z(cambiada).iloc[:400], z.iloc[:400])   # ...no cambia el pasado


@pytest.mark.parametrize("horizonte", ["medio", "largo"])
def test_nada_pasa_de_2017_y_se_aprende_solo_con_lo_anterior(datos_criba, horizonte):
    m, brent = datos_criba
    _, fecha_fin = cr._futuro(brent, horizonte)
    assert fecha_fin.loc[cr.origenes(m, brent, horizonte)].max() <= cr.FIN
    for año in (2006, 2010, 2016):
        aprender, prever = cr.division(m, brent, horizonte, año)
        assert len(aprender) and len(prever)
        assert fecha_fin.loc[aprender].max() < pd.Timestamp(año, 1, 1)     # respuestas conocidas antes del año
        assert prever.min().year == año and prever.max().year == año


def test_las_medidas_solo_usan_el_pasado(datos_criba, monkeypatch):
    """Las candidatas de un día no dependen de los días siguientes: calculadas solo con datos hasta
    2015 salen exactamente iguales."""
    from oil_price import datos
    m, _ = datos_criba
    corte = "2015-12-31"
    limpio, bruto = datos.cargar_datos_limpios(), datos.cargar_dataset().sort_index()
    monkeypatch.setattr(cr.datos, "cargar_datos_limpios", lambda: limpio.loc[:corte])
    monkeypatch.setattr(cr.datos, "cargar_dataset", lambda: bruto.loc[:corte])
    recortadas, _ = cr.medidas()
    pd.testing.assert_frame_equal(recortadas, m.loc[:corte])
    assert m.loc["2010":"2017"].notna().all().all()


def test_la_criba_marca_si_pasa(datos_criba):
    m, brent = datos_criba
    t = cr.validacion_en_train(m, brent, candidatas=["volatilidad 3 meses"])
    base = t.loc[("medio", "(ninguna: volatilidad 1 mes sola)")]
    fila = t.loc[("medio", "volatilidad 3 meses")]
    assert fila["mejora"] == pytest.approx(base["MAE / ingenuo"] - fila["MAE / ingenuo"])
    assert fila["pasa la criba"] == (fila["mejora"] >= cr.MEJORA_MINIMA and fila["años en que mejora"] > fila["años"] / 2)
