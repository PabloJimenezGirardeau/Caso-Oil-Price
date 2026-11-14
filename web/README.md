# Web del proyecto

Web estática que presenta el proyecto: «No sabemos adónde irá el Brent. Sabemos cuánto puede moverse.» Se publica en GitHub Pages desde esta carpeta.

No calcula nada: lee los JSON de `data/`, que genera `scripts/exportar_web.py` a partir de `resultados/`. Todas las cifras que se ven salen de ahí.

## Verla en local

Hace falta un servidor (la web lee los datos con `fetch`, y eso no funciona abriendo el archivo con doble clic). Desde la raíz del repositorio:

```
python -m http.server 8000 --directory web
```

y abrir <http://localhost:8000>. Para pararlo, `Ctrl + C`.

## Actualizar los datos

```
poetry run python scripts/exportar_web.py
```

Tarda menos de un minuto y no entrena nada. Escribe en `web/data/`:

| Archivo | Contenido |
|---|---|
| `historico.json` | Precio diario del Brent, solo días reales de cotización |
| `cotizaciones.json` | Último valor del CSV y variación diaria (la cinta del hero) |
| `validacion.json` | Nota de cada modelo en 2010-2021, por años y con todos juntos, y veredicto de la regla |
| `rango.json` | Cobertura, anchura y nota del rango del 80 %, y su serie diaria de 2019-2021 |
| `espejismo.json` | Control con precios (D15): serie de 2018-2019 y medidas |
| `prevision.json` | Precio de hoy y rango del 80 % de cada plazo |
| `test.json` | Examen final (D33) |
| `en_vivo.json` | Previsión del 10/11/2026 (D34) |

### Lo que está pendiente

La web enseña como «pendiente» lo que aún no existe; nunca un número inventado.

- **`prevision.json`**. La previsión de cada red (`prevision_red`) está en `null` hasta que existan las redes finales. El rango es **provisional** (`"estado": "provisional"`): el elegido en cada plazo, centrado en el precio de hoy, con la anchura ajustada solo con lo conocido antes del 1/1/2022, para no usar ninguna respuesta del periodo de test. Cuando se haga D34 hay que ampliar la función `prevision()` del exportador para que lea las previsiones finales y el rango definitivo, y poner otro estado (por ejemplo, `"definitiva"`): la web quita entonces el rótulo «provisional».
- **`test.json`**. Mientras diga `{"estado": "pendiente"}`, la columna «Examen final» de la tabla queda pendiente. El exportador no lo pisa si tiene otro estado. Formato que espera la web:

  ```json
  {"estado": "hecho", "periodo": "2022-2026",
   "plazos": {"corto": {"modelos": {"RNN": {"nota": 1.0}, "LSTM": {"nota": 1.0}, "GRU": {"nota": 1.0}, "Lineal": {"nota": 1.0}}},
              "medio": {"modelos": {}}, "largo": {"modelos": {}}}}
  ```

- **`en_vivo.json`**. Tampoco se pisa si ya no está pendiente. Al guardar la previsión: `"estado": "guardada"`, con `guardada` (fecha, `AAAA-MM-DD`), `commit` (el hash del commit que la guardó; la web lo enlaza), `prevision_red`, `bajo` y `alto`. Al comprobarla: `"estado": "comprobada"` y `precio_real`. El distintivo del hero y la tarjeta «Previsión en vivo» cambian solos.

Si un JSON lleva `"ejemplo": true`, la web lo avisa en una esquina («Datos de ejemplo»).

## Estructura

```
web/
├── index.html
├── favicon.svg
├── data/                 Los JSON (los genera scripts/exportar_web.py)
└── assets/
    ├── css/
    │   ├── fuente.css    Estilos: tema de Tailwind y componentes. Es lo que se edita
    │   └── estilos.css   Compilado y minificado. Es lo que carga la web; no se edita a mano
    ├── js/
    │   ├── principal.js  Arranque: carga los datos y lanza cada parte
    │   ├── datos.js      Lectura de los JSON
    │   ├── formato.js    Cifras y fechas en formato español
    │   ├── graficos.js   Utilidades para los gráficos en SVG (escalas, trazos, ejes)
    │   ├── crudo.js      El fondo de crudo: shader en WebGL
    │   ├── hero.js       La línea del Brent y el abanico del 80 %
    │   ├── cinta.js      Cinta de cotizaciones
    │   ├── prevision.js  Panel de la previsión y previsión en vivo
    │   ├── calma.js      «Calma y tormenta»
    │   ├── espejismo.js  «El espejismo»
    │   ├── secciones.js  Hallazgos, eje del tiempo del método y tabla comparativa
    │   ├── relieve.js    Curvas de nivel de fondo
    │   └── movimiento.js Scroll suave, entradas y contadores
    ├── fonts/            Geist, Geist Mono e Instrument Serif (woff2)
    ├── img/              Imagen fija del crudo (sin WebGL) e imagen para compartir
    └── vendor/           Librerías de terceros
```

## Recompilar los estilos

Solo hace falta si se cambia `assets/css/fuente.css` o las clases de `index.html`. No se necesita Node: se usa el ejecutable independiente de Tailwind CSS (v4.3.5).

1. Descargar `tailwindcss-windows-x64.exe` de <https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.5> y guardarlo como `herramientas/tailwindcss.exe` (la carpeta `herramientas/` no se sube al repositorio).
2. Desde la raíz del repositorio:

   ```
   herramientas\tailwindcss.exe -i web/assets/css/fuente.css -o web/assets/css/estilos.css --minify
   ```

   Con `--watch` al final, recompila solo cada vez que se guarda un cambio.

## Publicar en GitHub Pages

La publica el flujo `.github/workflows/web.yml` cada vez que se sube a `main` un cambio dentro de `web/`. No construye nada: sube la carpeta tal cual.

La primera vez, en GitHub:

1. **Settings → Pages → Build and deployment → Source: «GitHub Actions».**
2. Subir los cambios a `main` (o lanzar el flujo a mano: pestaña **Actions → Publicar la web → Run workflow**).
3. La dirección aparece al terminar el flujo; será `https://pablojimenezgirardeau.github.io/Caso-Oil-Price/`.

GitHub Pages solo está disponible en repositorios públicos, salvo con cuenta de pago.

## Librerías

Todas con versión fija y guardadas en el repositorio (no se cargan de ninguna CDN):

| Librería | Versión | Para qué |
|---|---|---|
| GSAP, con ScrollTrigger y SplitText | 3.15.1 | Animaciones, scroll y títulos por líneas |
| Lenis | 1.3.27 | Scroll suave |
| Tailwind CSS (CLI) | 4.3.5 | Estilos, compilados |
| Geist y Geist Mono (Fontsource) | 5.3.0 | Texto y cifras |
| Instrument Serif (Fontsource) | 5.3.0 | Cursiva de los titulares |

Los gráficos son SVG propio y el fondo de crudo es WebGL directo: no usan librería.

## Antes de enseñarla

- En el pie de `index.html` quedan por rellenar `[Nombre del autor]` y `[Universidad]`.
- Las etiquetas `og:url` y `og:image` de `index.html` llevan la dirección de GitHub Pages: hay que cambiarlas si cambia el nombre del repositorio o del usuario.
- Con «reducir movimiento» activado en el sistema, la web se ve sin animaciones. Sin WebGL, el fondo es una imagen fija (`assets/img/crudo.jpg`).
- Es una web de escritorio: no tiene versión para móvil. Por debajo de 1.024 px de ancho no se recoloca; aparece una barra de desplazamiento horizontal.
- No se ha medido con Lighthouse.
