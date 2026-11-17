"""La aplicación de previsión del Brent: la web del proyecto, servida por Python para que funcione el botón
«Actualizar datos».

Al pulsarlo, descarga los datos más recientes de FRED y Yahoo Finance y los pasa por los modelos finales,
ya entrenados (no se reentrena nada). La web se actualiza en su sitio: precio de hoy, previsión de la red a
1 semana, 3 meses y 1 año, rango del 80 %, gráfico y explicación en lenguaje sencillo.

Es la misma web que se publica en GitHub Pages. Allí, sin Python detrás, enseña la previsión publicada.

Uso:
    python app/app.py                      # abre http://127.0.0.1:8765 en el navegador
    python app/app.py --puerto 8000 --sin-navegador
"""
import argparse
import json
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))                    # funciona sin instalar el paquete
WEB = RAIZ / "web"

from oil_price.inference import aplicacion as ap        # noqa: E402
from oil_price.inference import datos_web as dw         # noqa: E402

PUERTO = 8765


class Servicio:
    """Lo que hay detrás de la web: los modelos se cargan una vez al arrancar; los datos, al pulsar el botón."""

    def __init__(self, web=WEB, descargar=True, **opciones):
        self.web = Path(web)
        self.descargar = descargar
        self.app = ap.Aplicacion(self.web / "data", **opciones)
        self.cerrojo = threading.Lock()

    def estado(self):
        return {"servidor": True, "modelos_hasta": dw.fecha_iso(self.app.modelos_hasta)}

    def actualizar(self):
        """Descarga los datos (si se puede), los pasa por los modelos y lo devuelve en el formato de la web."""
        with self.cerrojo:
            self.app.cargar(descargar=self.descargar)
            publicada = json.loads((self.web / "data" / "prevision.json").read_text(encoding="utf-8"))
            return dw.actualizacion(self.app, publicada)


class Manejador(SimpleHTTPRequestHandler):
    """Sirve la carpeta web/ tal cual y responde a las dos rutas de la API."""

    protocol_version = "HTTP/1.1"   # conexiones reutilizables: la web pide unos treinta archivos al abrirse

    # Tipos fijos: en Windows, el registro puede dar otro tipo a .js y el navegador no cargaría los módulos
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".mjs": "text/javascript",
                      ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".woff2": "font/woff2",
                      ".png": "image/png", ".jpg": "image/jpeg", ".html": "text/html"}

    def __init__(self, *args, servicio=None, **kwargs):
        self.servicio = servicio
        super().__init__(*args, directory=str(servicio.web), **kwargs)

    def _ruta(self):
        return self.path.split("?")[0].split("#")[0]

    def _json(self, codigo, contenido):
        cuerpo = json.dumps(contenido, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def end_headers(self):
        if not self._ruta().startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")   # la web siempre la última versión de sus archivos
        super().end_headers()

    def do_GET(self):
        if self._ruta() == "/api/estado":
            self._json(200, self.servicio.estado())
        else:
            super().do_GET()

    def do_POST(self):
        if self._ruta() != "/api/actualizar":
            self._json(404, {"error": "no existe"})
            return
        try:
            self._json(200, self.servicio.actualizar())
        except Exception as error:                        # la web lo enseña como aviso, sin romperse
            self._json(500, {"error": str(error)})

    def log_message(self, formato, *args):
        if self._ruta().startswith("/api/"):
            sys.stderr.write(f"  {self.command} {self._ruta()} → {args[1] if len(args) > 1 else ''}\n")


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64         # la cola por defecto (5) se llena al abrir la web y el navegador ve fallos

    def handle_error(self, request, client_address):
        # Si el navegador se cierra o recarga a mitad de una respuesta, no es un error de la aplicación
        if isinstance(sys.exc_info()[1], (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def crear_servidor(servicio, puerto=PUERTO, anfitrion="127.0.0.1"):
    return Servidor((anfitrion, puerto), partial(Manejador, servicio=servicio))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--puerto", type=int, default=PUERTO)
    parser.add_argument("--sin-navegador", action="store_true", help="no abre el navegador")
    args = parser.parse_args()

    print("Cargando los modelos finales…")
    servicio = Servicio()
    servidor = crear_servidor(servicio, args.puerto)
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Modelos entrenados hasta el {ap.fecha(servicio.app.modelos_hasta)}.")
    print(f"La aplicación está en {url}  (Ctrl + C para cerrarla)")
    if not args.sin_navegador:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrada.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
