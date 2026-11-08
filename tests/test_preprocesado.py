"""Pruebas del preprocesamiento. Ejecutar con: poetry run pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import config, datos, preprocesado as pp, validaciones as v


@pytest.fixture(scope="module")
def limpio():
    return datos.cargar_datos_limpios()


@pytest.fixture(scope="module")
def base(limpio):
    return pp.preparar_base(limpio)


def test_limpieza(limpio):
    dias = datos.cargar_dias_brent()
    v.comprobar_limpio(limpio, dias)
    assert limpio.index.min() == config.FECHA_INICIO
    assert limpio.index.max() == config.FECHA_CORTE
    assert limpio.loc["2020-04-20", "wti"] > 0  # WTI negativo sustituido por el valor anterior


def test_entradas_solo_usan_el_pasado(limpio):
    """Cambiar el futuro no puede alterar las entradas de días anteriores."""
    corte = pd.Timestamp("2015-06-30")
    alterado = limpio.copy()
    alterado.loc[alterado.index > corte] *= 3.0
    originales = pp.calcular_entradas(limpio).loc[:corte]
    con_futuro_alterado = pp.calcular_entradas(alterado).loc[:corte]
    pd.testing.assert_frame_equal(originales, con_futuro_alterado)


def test_objetivos(limpio, base):
    """El objetivo a h sesiones es log(P[t+h] / P[t]) y su fecha es t+h."""
    precio = limpio["brent"]
    t = base.entradas.index[1000]
    pos = precio.index.get_loc(t)
    for nombre, h in config.HORIZONTES.items():
        esperado = np.log(precio.iloc[pos + h] / precio.iloc[pos])
        assert base.objetivos.loc[t, nombre] == pytest.approx(esperado)
        assert base.fechas_objetivo.loc[t, nombre] == precio.index[pos + h]


def test_preparador_ajustado_solo_con_train(base):
    """Alterar los datos posteriores al train no cambia el recorte ni el escalado."""
    fin_train = config.PARTICION["fin_train"]
    alteradas = base.entradas.copy()
    alteradas.loc[alteradas.index > fin_train] *= 10
    a = pp.Preparador((1, 99)).ajustar(base.entradas.loc[:fin_train])
    b = pp.Preparador((1, 99)).ajustar(alteradas.loc[:fin_train])
    pd.testing.assert_series_equal(a.media_, b.media_)
    pd.testing.assert_series_equal(a.superior_, b.superior_)


def test_indicadores_no_se_recortan(base):
    """La volatilidad y el nivel conservan su valor real (la alarma no se apaga)."""
    fin_train = config.PARTICION["fin_train"]
    preparador = pp.Preparador((1, 99)).ajustar(base.entradas.loc[:fin_train])
    recortadas = preparador.recortar(base.entradas)
    for columna in ["log_vol_brent", "nivel_brent"]:
        pd.testing.assert_series_equal(recortadas[columna], base.entradas[columna])
    assert recortadas["r_brent"].max() <= preparador.superior_["r_brent"]


@pytest.mark.parametrize("ventana", config.VENTANAS)
@pytest.mark.parametrize("recorte", config.RECORTES)
def test_particiones_sin_fuga(base, ventana, recorte):
    for p in pp.pliegues_walk_forward() + [pp.evaluacion_final()]:
        train, evaluacion, preparador = pp.construir_particion(
            base, ventana, recorte, p["fin_train"], p["desde"], p["hasta"], p["limite_objetivo"], p["nombre"])
        v.comprobar_conjunto(train)
        v.comprobar_conjunto(evaluacion)
        v.comprobar_sin_fuga(train, evaluacion, preparador)
        assert train.X.shape[1:] == (ventana, base.entradas.shape[1])


def test_ventana_contiene_los_dias_correctos(base):
    ventana = 60
    preparador = pp.Preparador(None).ajustar(base.entradas)
    escaladas = preparador.transformar(base.entradas)
    c = pp.crear_conjunto("prueba", base, escaladas, ventana, desde=pd.Timestamp("2010-01-01"),
                          hasta=pd.Timestamp("2010-12-31"), limite_objetivo=config.FECHA_CORTE)
    i = 37
    pos = escaladas.index.get_loc(c.fechas[i])
    np.testing.assert_allclose(c.X[i], escaladas.iloc[pos - ventana + 1: pos + 1].to_numpy(), rtol=1e-6)


def test_purga_quita_objetivos_que_cruzan_el_limite(base):
    preparador = pp.Preparador(None).ajustar(base.entradas)
    escaladas = preparador.transformar(base.entradas)
    limite = pd.Timestamp("2015-12-31")
    c = pp.crear_conjunto("prueba", base, escaladas, 60, desde=pd.Timestamp("2015-01-01"),
                          hasta=limite, limite_objetivo=limite)
    for j, nombre in enumerate(c.horizontes):
        fecha_objetivo = base.fechas_objetivo.loc[c.fechas, nombre]
        debe_conservarse = (fecha_objetivo <= limite).to_numpy()
        np.testing.assert_array_equal(~np.isnan(c.Y[:, j]), debe_conservarse)
    largo = c.horizontes.index("largo")
    assert np.isnan(c.Y[-50:, largo]).all()   # las fichas de final de año no tienen respuesta a 1 año
    assert not np.isnan(c.Y[:10, 0]).any()     # a 5 sesiones, las de enero sí
