"""Pruebas de la aplicación: formato, ciclo económico, abanico del rango y una ejecución completa con los modelos
locales y la foto de los datos (sin descargar nada). Ejecutar con: python -m pytest"""
import numpy as np
import pandas as pd
import pytest

from oil_price import aplicacion as ap, config, datos


def test_formato_espanol():
    assert ap.num(107.03) == "107,03" and ap.num(6501, 0) == "6.501" and ap.num(-0.5, 1) == "−0,5"
    assert ap.dolares(9.12) == "9,12 $" and ap.variacion(3.54) == "+3,5 %" and ap.variacion(-12.14) == "−12,1 %"
    assert ap.fecha("2026-11-03") == "3/11/2026" and ap.mes_año("2008-12-26") == "diciembre de 2008"


def test_episodios_del_ciclo_buscados_en_los_datos():
    precios = datos.cargar_datos_limpios()["brent"]
    lista = ap.episodios(precios)
    assert [e["titulo"] for e in lista] == ["Máximo histórico", "Crisis financiera", "Exceso de oferta", "Pandemia",
                                            "Invasión de Ucrania", "Lo más reciente"]
    assert [e["tipo"] for e in lista] == ["max", "min", "min", "min", "max", "max"]
    for e in lista:                                           # fecha y precio salen de la serie, no del texto
        assert precios.loc[e["fecha"]] == pytest.approx(e["precio"])
    assert lista[0]["fecha"] == pd.Timestamp("2008-07-03") and lista[3]["precio"] == pytest.approx(9.12)
    assert "9,12 $" in lista[3]["texto"] and "toda la serie" in lista[3]["texto"]
    assert lista[1]["precio"] < lista[0]["precio"] and "77 %" in lista[1]["texto"]


def test_limite_del_abanico_empieza_en_cero_y_pasa_por_los_rangos():
    nudos = [(5, {"bajo": 95.0, "alto": 105.0}), (63, {"bajo": 70.0, "alto": 140.0})]
    assert ap._limite(nudos, 100.0, 0, "alto") == 0
    assert 100 * np.exp(ap._limite(nudos, 100.0, 5, "alto")) == pytest.approx(105.0)
    assert 100 * np.exp(ap._limite(nudos, 100.0, 63, "bajo")) == pytest.approx(70.0)
    crece = [ap._limite(nudos, 100.0, s, "alto") for s in range(0, 64)]
    assert all(b >= a for a, b in zip(crece, crece[1:]))      # el abanico solo se abre


def test_la_descarga_incompleta_no_se_guarda(tmp_path, monkeypatch):
    """Si Yahoo no devuelve cobre, oro o dólar, la descarga avisa y no pisa los datos buenos."""
    from oil_price import descarga
    dias = pd.date_range("2024-01-01", periods=5)
    monkeypatch.setattr(descarga, "descargar_fred", lambda s, *a, **k: pd.Series(1.0, index=dias, name=descarga.SERIES_FRED[s]))
    monkeypatch.setattr(descarga, "descargar_yahoo", lambda *a, **k: None)
    avisos = []
    with pytest.raises(RuntimeError):
        descarga.actualizar(tmp_path, registrar=avisos.append)
    assert not list(tmp_path.iterdir()) and any("Yahoo" in a for a in avisos)


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    vacia = tmp_path_factory.mktemp("sin_datos")              # sin datos descargados: usa la foto del estudio
    return ap.Aplicacion(config.RAIZ / "web" / "data", directorio_datos=vacia).cargar(descargar=False)


def test_aplicacion_completa_con_la_foto_del_estudio(app):
    assert app.origen.startswith("la foto del estudio") and app.ultimo_dia == config.FECHA_CORTE
    assert list(app.tabla.index) == ["corto", "largo", "medio"] or set(app.tabla.index) == set(ap.ORDEN)
    for h in ap.ORDEN:
        f = app.fila(h)
        assert f["rango bajo"] < f["precio hoy"] < f["rango alto"] and f["fecha origen"] == config.FECHA_CORTE.date()
        texto = app.explicacion(h)
        assert all(k in texto for k in ("Qué significa", "Qué fiabilidad tiene", "Qué puede invalidarla"))
        assert ap.dolares(f["precio previsto"]) in texto and ap.NOMBRE[h] in texto
    assert "orientativo" in app.explicacion("largo").lower() and "orientativo" not in app.explicacion("corto").lower().split("rango")[0]
    # Las previsiones coinciden con las congeladas en resultados/en_vivo.csv desde el 3/11/2026
    v = pd.read_csv(config.DIR_RESULTADOS / "en_vivo.csv")
    v = v[v["version"].str.startswith("modelos finales") & (v["fecha origen"] == "2026-11-03")].set_index("horizonte")
    for h in ap.ORDEN:
        assert app.fila(h)["precio previsto"] == pytest.approx(v.loc[h, "precio previsto"], abs=1e-3)


def test_graficos_y_tabla_del_estudio(app):
    fig = app.grafico_prevision("medio")
    assert [t.name for t in fig.data][0] == "Brent" and any(t.name and t.name.startswith("Previsión") for t in fig.data)
    assert len(app.grafico_ciclo().data[1].x) == 6
    tabla = ap.tabla_comparativa(app.estudio, "corto")
    assert tabla.count("\n") == 6 and "**LSTM**" in tabla and "Ingenuo (precio de hoy)" in tabla
