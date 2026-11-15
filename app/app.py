"""Aplicación de previsión del Brent (Gradio): elige el plazo y mira el precio previsto, su variación, el rango
del 80 %, una explicación en lenguaje sencillo y el ciclo económico. Descarga datos nuevos y reentrena.

Uso local:    python app/app.py
Enlace público temporal (para enseñarla; dura unos días y solo mientras el programa siga abierto):
              python app/app.py --compartir
"""
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))                    # funciona sin instalar el paquete

import gradio as gr

from oil_price.inference import aplicacion as ap

ESTUDIO = RAIZ / "web" / "data"                          # resultados del estudio (los lee también la web)
WEB = "https://pablojimenezgirardeau.github.io/Caso-Oil-Price/"
GITHUB = "https://github.com/PabloJimenezGirardeau/Caso-Oil-Price"
MODELO = f"https://huggingface.co/{ap.REPO_MODELO}"

CSS = """
.gradio-container { max-width: 1180px !important; margin: auto; }
.cab h1 { font-weight: 300; font-size: 2.1rem; letter-spacing: -0.02em; margin: 0 0 4px; color: #f4efe6; }
.cab h1 em { font-family: 'Instrument Serif', Georgia, serif; font-style: italic; font-weight: 400; color: #e6dfd2; font-size: 1.15em; }
.cab p { color: #a39c90; margin: 0; }
.estado { color: #8a8378; font-family: ui-monospace, Consolas, monospace; font-size: 0.78rem; letter-spacing: 0.02em; }
.estado b { color: #f2921d; font-weight: 500; }
.aviso { border: 1px solid rgba(242,146,29,0.45); background: rgba(242,146,29,0.07); color: #e6dfd2; border-radius: 12px;
         padding: 10px 14px; font-size: 0.86rem; }
.cifras { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.cifra { border: 1px solid rgba(255,244,230,0.09); background: rgba(20,17,14,0.9); border-radius: 16px; padding: 16px 18px; }
.cifra .t { font-family: ui-monospace, Consolas, monospace; font-size: 0.68rem; letter-spacing: 0.07em; text-transform: uppercase; color: #8a8378; }
.cifra .n { font-family: ui-monospace, Consolas, monospace; font-size: 1.55rem; font-weight: 300; color: #f4efe6; margin-top: 6px; letter-spacing: -0.03em; }
.cifra .n.ambar { color: #f2921d; }
.cifra .s { color: #a39c90; font-size: 0.8rem; margin-top: 4px; }
.fiab { margin-top: 12px; color: #a39c90; font-size: 0.86rem; }
.chip { display: inline-block; border: 1px solid rgba(242,146,29,0.45); color: #f2921d; border-radius: 999px; padding: 1px 9px;
        font-family: ui-monospace, Consolas, monospace; font-size: 0.66rem; letter-spacing: 0.06em; text-transform: uppercase; margin-left: 6px; }
table, th, td { border-color: rgba(255,244,230,0.13) !important; }
.pie { color: #8a8378; font-size: 0.82rem; text-align: center; }
.pie a { color: #f4efe6; }
@media (max-width: 800px) { .cifras { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
"""

TEMA = gr.themes.Base(primary_hue="orange", neutral_hue="stone", font=[gr.themes.GoogleFont("Geist"), "system-ui", "sans-serif"],
                      font_mono=["ui-monospace", "Consolas", "monospace"]).set(
    body_background_fill="#000000", body_background_fill_dark="#000000",
    body_text_color="#f4efe6", body_text_color_dark="#f4efe6",
    block_background_fill="#0a0908", block_background_fill_dark="#0a0908",
    block_border_color="rgba(255,244,230,0.09)", block_border_color_dark="rgba(255,244,230,0.09)",
    input_background_fill="#14110e", input_background_fill_dark="#14110e",
    button_primary_background_fill="#f2921d", button_primary_background_fill_dark="#f2921d",
    button_primary_text_color="#000000", button_primary_text_color_dark="#000000",
    button_secondary_background_fill="#14110e", button_secondary_background_fill_dark="#14110e",
    button_secondary_text_color="#f4efe6", button_secondary_text_color_dark="#f4efe6")

# Siempre en oscuro, sea cual sea el tema del navegador
FORZAR_OSCURO = "() => { document.body.classList.add('dark'); }"

APP = ap.Aplicacion(ESTUDIO)
ARRANQUE = {"hecho": False}


def asegurar_datos():
    """La primera vez que se pide algo, descarga los datos más recientes y calcula las previsiones."""
    if not ARRANQUE["hecho"]:
        APP.cargar(descargar=True)
        ARRANQUE["hecho"] = True


def estado_html():
    entrenado = min(m.fin_train for m in APP.modelos.values())
    texto = (f"<p class='estado'>Datos hasta el <b>{ap.fecha(APP.ultimo_dia)}</b> · {APP.origen} · modelos entrenados hasta el "
             f"<b>{ap.fecha(entrenado)}</b></p>")
    for aviso in APP.avisos:
        texto += f"<div class='aviso' style='margin-top:8px'>{aviso}</div>"
    return texto


def cifras_html(h):
    f = APP.fila(h)
    est = ap.fiabilidad(APP.estudio, h, f["red"])
    cambio = 100 * (f["precio previsto"] / f["precio hoy"] - 1)
    orient = "<span class='chip'>Orientativo</span>" if h == "largo" else ""
    return (
        "<div class='cifras'>"
        f"<div class='cifra'><div class='t'>Brent · {ap.fecha(f['fecha origen'])}</div><div class='n'>{ap.dolares(f['precio hoy'])}</div>"
        f"<div class='s'>último precio</div></div>"
        f"<div class='cifra'><div class='t'>Previsión de la {f['red']}</div><div class='n'>{ap.dolares(f['precio previsto'])}</div>"
        f"<div class='s'>{ap.variacion(cambio)} · hacia el {ap.fecha(f['fecha objetivo (estimada)'])}</div></div>"
        f"<div class='cifra'><div class='t'>Rango del 80 %{orient}</div><div class='n ambar'>{ap.num(f['rango bajo'])} – {ap.num(f['rango alto'])} $</div>"
        f"<div class='s'>{ap.variacion(100 * (f['rango bajo'] / f['precio hoy'] - 1))} a {ap.variacion(100 * (f['rango alto'] / f['precio hoy'] - 1))}</div></div>"
        f"<div class='cifra'><div class='t'>Ingenuo</div><div class='n'>{ap.dolares(f['precio hoy'])}</div>"
        f"<div class='s'>el precio de hoy, sin cambios</div></div>"
        "</div>"
        f"<p class='fiab'>Examen final {est['periodo']}, frente al ingenuo: <b>{est['conclusion']}</b>; "
        f"el rango acertó el <b>{ap.num(100 * est['cobertura'], 0)} %</b> de las veces (promete el 80 %).</p>")


def vista(h):
    asegurar_datos()
    return estado_html(), cifras_html(h), APP.grafico_prevision(h), APP.explicacion(h)


def actualizar(h):
    """Descarga datos nuevos y recalcula."""
    APP.cargar(descargar=True)
    ARRANQUE["hecho"] = True
    return vista(h)


def reentrenar(n_semillas, h):
    """Reentrena con los datos de hoy (en segundo plano) y enseña el registro mientras tanto."""
    asegurar_datos()
    registro, fin = [], threading.Event()
    semillas = list(range(42, 42 + int(n_semillas)))

    def trabajo():
        try:
            APP.reentrenar(semillas, registrar=registro.append)
            registro.append("Listo: los modelos se han reentrenado con los datos hasta " + ap.fecha(APP.ultimo_dia) + ".")
        except Exception as error:
            registro.append(f"Error al reentrenar: {error}")
        finally:
            fin.set()

    hilo = threading.Thread(target=trabajo, daemon=True)
    hilo.start()
    inicio = time.time()
    while not fin.wait(2):
        yield "\n".join(registro) + f"\n… {time.time() - inicio:.0f} s", *(gr.update(),) * 4
    hilo.join()
    yield ("\n".join(registro), *vista(h))


def ciclo():
    asegurar_datos()
    lista = ap.episodios(APP.precios)
    texto = "\n\n".join(f"**{n + 1:02d} · {e['fecha'].year} · {'pico' if e['tipo'] == 'max' else 'caída'} · {e['titulo']}.** {e['texto']}"
                        for n, e in enumerate(lista))
    return APP.grafico_ciclo(), texto


def estudio_md():
    t = APP.estudio["test"]
    partes = ["La comparativa del **examen final** (" + t["periodo"] + "), hecho una sola vez con todo decidido de antemano. "
              "Cada red es el promedio de cinco entrenamientos; en negrita, la elegida para cada plazo.\n"]
    for h in ap.ORDEN:
        p = t["plazos"][h]
        partes.append(f"### {ap.NOMBRE[h]}\n\n{ap.tabla_comparativa(APP.estudio, h)}\n\n"
                      f"Conclusión fijada antes de calcular: *{p['conclusion']}*. El rango del 80 % acertó el "
                      f"{ap.num(100 * p['rango']['cobertura'], 0)} % (±{ap.num(100 * p['rango']['margen'], 0)} puntos).")
    partes.append("**Ninguna red mejora de forma fiable al ingenuo** (suponer que el precio no cambia), ni en 12 años de pruebas "
                  "año a año ni en el examen final. Lo que sí funciona es el rango: dice cuánto puede moverse el precio.")
    return "\n\n".join(partes)


def construir():
    with gr.Blocks(title="Previsión del Brent") as demo:
        gr.HTML("<div class='cab'><h1>No sabemos adónde irá el Brent. <em>Sabemos cuánto puede moverse.</em></h1>"
                "<p>Previsión del precio del Brent a 1 semana, 3 meses y 1 año con redes neuronales (RNN, LSTM y GRU), "
                "siempre con su rango del 80 % y su fiabilidad.</p></div>")
        estado = gr.HTML()
        with gr.Tab("La previsión"):
            with gr.Row():
                plazo = gr.Radio([("1 semana", "corto"), ("3 meses", "medio"), ("1 año", "largo")], value="corto", label="Plazo",
                                 scale=3)
                boton = gr.Button("Actualizar datos", variant="secondary", scale=1)
            cifras = gr.HTML()
            grafico = gr.Plot(show_label=False)
            explicacion = gr.Markdown()
        with gr.Tab("El ciclo del petróleo"):
            gr.Markdown("Los grandes picos y caídas del Brent y lo que los provocó. El petróleo sigue al ciclo económico "
                        "mundial, pero sus movimientos más bruscos los desatan las sorpresas.")
            g_ciclo = gr.Plot(show_label=False)
            t_ciclo = gr.Markdown()
        with gr.Tab("Reentrenar"):
            gr.Markdown("Reentrena las tres redes con los datos hasta hoy, con la misma configuración elegida en el estudio. "
                        "**Tarda varios minutos** (a 1 semana, una red por semilla): en un servidor gratuito, más. "
                        "Con menos semillas es más rápido, pero la previsión varía algo más de una vez a otra. "
                        "Los modelos reentrenados duran mientras el servidor esté encendido.")
            semillas = gr.Slider(1, 5, value=2, step=1, label="Semillas (cuántas veces se entrena cada red; el resultado es la media)")
            entrenar = gr.Button("Reentrenar con los datos de hoy", variant="primary")
            registro = gr.Textbox(label="Registro", lines=8, interactive=False)
        with gr.Tab("El estudio"):
            gr.Markdown(estudio_md)
        gr.HTML(f"<p class='pie'>Proyecto académico. No es asesoramiento financiero ni una recomendación de inversión. · "
                f"<a href='{WEB}' target='_blank'>La web del proyecto</a> · <a href='{GITHUB}' target='_blank'>Código</a> · "
                f"<a href='{MODELO}' target='_blank'>Modelos</a></p>")

        salidas = [estado, cifras, grafico, explicacion]
        demo.load(vista, plazo, salidas)
        plazo.change(vista, plazo, salidas)
        boton.click(actualizar, plazo, salidas)
        entrenar.click(reentrenar, [semillas, plazo], [registro, *salidas])
        demo.load(ciclo, None, [g_ciclo, t_ciclo])
    return demo


if __name__ == "__main__":
    construir().launch(theme=TEMA, css=CSS, js=FORZAR_OSCURO, share="--compartir" in sys.argv)
