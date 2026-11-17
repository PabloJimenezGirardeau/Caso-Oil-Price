"""Pruebas de la aplicación: formato, descarga, previsión con la foto de los datos (sin descargar nada), datos en
el formato de la web y el servidor con su botón «Actualizar datos». Ejecutar con: python -m pytest"""
import importlib.util
import json
import threading
import urllib.error
import urllib.request

import pandas as pd
import pytest

from oil_price.inference import aplicacion as ap
from oil_price.inference import datos_web as dw
from oil_price.utils import config

WEB = config.RAIZ / "web"


def test_formato_espanol():
    assert ap.num(107.03) == "107,03" and ap.num(6501, 0) == "6.501" and ap.num(-0.5, 1) == "−0,5"
    assert ap.dolares(9.12) == "9,12\u00a0$" and ap.variacion(3.54) == "+3,5\u00a0%" and ap.variacion(-12.14) == "−12,1\u00a0%"
    assert ap.fecha("2026-11-03") == "3/11/2026" and ap.mes_año("2008-12-26") == "diciembre de 2008"


def test_la_descarga_incompleta_no_se_guarda(tmp_path, monkeypatch):
    """Si Yahoo no devuelve cobre, oro o dólar, la descarga avisa y no pisa los datos buenos."""
    from oil_price.data import descarga
    dias = pd.date_range("2024-01-01", periods=5)
    monkeypatch.setattr(descarga, "descargar_fred", lambda s, *a, **k: pd.Series(1.0, index=dias, name=descarga.SERIES_FRED[s]))
    monkeypatch.setattr(descarga, "descargar_yahoo", lambda *a, **k: None)
    avisos = []
    with pytest.raises(RuntimeError):
        descarga.actualizar(tmp_path, registrar=avisos.append)
    assert not list(tmp_path.iterdir()) and any("Yahoo" in a for a in avisos)


@pytest.fixture(scope="module")
def vacia(tmp_path_factory):
    return tmp_path_factory.mktemp("sin_datos")               # sin datos descargados: usa la foto del estudio


@pytest.fixture(scope="module")
def app(vacia):
    return ap.Aplicacion(WEB / "data", directorio_datos=vacia).cargar(descargar=False)


def test_aplicacion_completa_con_la_foto_del_estudio(app):
    assert app.origen.startswith("la foto del estudio") and app.ultimo_dia == config.FECHA_CORTE
    assert set(app.tabla.index) == set(ap.ORDEN) and app.modelos_hasta == config.FECHA_CORTE
    for h in ap.ORDEN:
        f = app.fila(h)
        assert f["rango bajo"] < f["precio hoy"] < f["rango alto"] and f["fecha origen"] == config.FECHA_CORTE.date()
        partes = app.explicacion(h)
        assert [p["titulo"] for p in partes] == ["Qué significa", "Qué fiabilidad tiene", "Qué puede invalidarla"]
        texto = " ".join(p["texto"] for p in partes)
        assert ap.dolares(f["precio previsto"]) in texto and ap.NOMBRE[h] in texto and "*" not in texto
    assert "orientativo" in app.explicacion("largo")[1]["texto"] and "orientativo." not in app.explicacion("corto")[1]["texto"]
    # Los datos solo pasan por los modelos: las previsiones son las congeladas en resultados/en_vivo.csv desde el 3/11/2026
    v = pd.read_csv(config.DIR_RESULTADOS / "en_vivo.csv")
    v = v[v["version"].str.startswith("modelos finales") & (v["fecha origen"] == "2026-11-03")].set_index("horizonte")
    for h in ap.ORDEN:
        assert app.fila(h)["precio previsto"] == pytest.approx(v.loc[h, "precio previsto"], abs=1e-3)


def test_actualizacion_en_el_formato_de_la_web(app):
    """Lo que devuelve el botón tiene la misma forma que los JSON publicados, y la web lo pinta igual."""
    publicada = json.loads((WEB / "data" / "prevision.json").read_text(encoding="utf-8"))
    a = dw.actualizacion(app, publicada)
    pv = a["prevision"]
    assert set(pv) == set(publicada) and pv["estado"] == "al momento" and pv["fecha"] == "2026-11-03"
    for h in ap.ORDEN:
        assert set(pv["plazos"][h]) == set(publicada["plazos"][h])
        assert pv["plazos"][h]["prevision_red"] == pytest.approx(app.fila(h)["precio previsto"], abs=0.006)
        assert pv["plazos"][h]["cobertura"] == publicada["plazos"][h]["cobertura"]      # lo que dijo el estudio
        assert [p["titulo"] for p in pv["explicaciones"][h]] == [p["titulo"] for p in publicada["explicaciones"][h]]
    assert a["historico"]["fechas"][-1] == pv["fecha"] and a["historico"]["precios"][-1] == pv["precio"]
    assert set(a["cotizaciones"]) == {"fecha", "valores"} and len(a["cotizaciones"]["valores"]) == len(dw.COTIZACIONES)
    assert a["estado"]["modelos_hasta"] == "2026-11-03" and a["estado"]["origen"].startswith("la foto")


# --- El servidor --------------------------------------------------------------------------------------

def _cargar_app_py():
    spec = importlib.util.spec_from_file_location("app_brent", config.RAIZ / "app" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def servidor(vacia):
    modulo = _cargar_app_py()
    srv = modulo.crear_servidor(modulo.Servicio(descargar=False, directorio_datos=vacia), puerto=0)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _pedir(url, metodo="GET"):
    with urllib.request.urlopen(urllib.request.Request(url, method=metodo, data=b"" if metodo == "POST" else None),
                                timeout=120) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


def test_el_servidor_sirve_la_web_tal_cual(servidor):
    estado, tipo, cuerpo = _pedir(servidor + "/")
    assert estado == 200 and "text/html" in tipo and cuerpo == (WEB / "index.html").read_bytes()
    estado, tipo, _ = _pedir(servidor + "/assets/js/principal.js")
    assert estado == 200 and tipo.startswith("text/javascript")          # si no, el navegador no carga los módulos
    estado, tipo, cuerpo = _pedir(servidor + "/api/estado")
    assert estado == 200 and json.loads(cuerpo) == {"servidor": True, "modelos_hasta": "2026-11-03"}


def test_el_boton_actualizar_datos(servidor):
    estado, tipo, cuerpo = _pedir(servidor + "/api/actualizar", "POST")
    datos = json.loads(cuerpo)
    assert estado == 200 and "application/json" in tipo
    assert set(datos) == {"prevision", "historico", "cotizaciones", "estado"} and datos["prevision"]["fecha"] == "2026-11-03"
    with pytest.raises(urllib.error.HTTPError) as error:
        _pedir(servidor + "/api/otra", "POST")
    assert error.value.code == 404
