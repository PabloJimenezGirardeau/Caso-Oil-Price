# Predicción del precio del Brent con RNN, LSTM y GRU

**Caso de uso III · Aprendizaje automático (UAX)** · Trabajo individual

Comparativa de tres redes neuronales recurrentes (RNN simple, LSTM y GRU) para predecir el precio del petróleo **Brent** a 1 semana, 3 meses y 1 año (5, 63 y 252 sesiones). La red elegida en cada plazo se integra en una aplicación que calcula la previsión, da un rango de incertidumbre del 80 % y la explica en lenguaje sencillo, como apoyo a decisiones de inversión, cobertura y compra de energía.

- **Web y aplicación:** <https://pablojimenezgirardeau.github.io/Caso-Oil-Price/>
- **Modelos entrenados:** <https://huggingface.co/PabloJimenezGirardeau/brent-rnn-lstm-gru>

## Resultados

Las redes se comparan con el **modelo ingenuo** («el precio futuro será el de hoy»), la referencia habitual en precios de mercado. La nota es el error medio en dólares de la red dividido por el del ingenuo: 1 es empatar y, por encima de 1, equivocarse más.

| Plazo | Red elegida | Nota 2010-2021 | Nota en el examen (2022-2026) | p (Diebold-Mariano) | R² de la variación | Rango del 80 % en el examen |
|---|---|---|---|---|---|---|
| 1 semana | LSTM | 0,997 | 1,005 | 0,56 | −0,019 | acierta el 79 % |
| 3 meses | RNN | 0,994 | 1,094 | 0,13 | −0,059 | acierta el 84 % |
| 1 año | RNN | 0,941 | 1,198 | 0,26 | −0,303 | acierta el 89 % |

- **Ninguna red mejora de forma fiable al ingenuo.** La conclusión, con reglas fijadas antes del examen, es «sin evidencia de ventaja» en los tres plazos: ninguna diferencia es significativa. El R² del precio a 1 semana es 0,87, pero el ingenuo obtiene lo mismo; el R² de la variación, que mide si se anticipa el movimiento, es nulo o negativo.
- **Cuándo acierta y cuándo falla.** A 3 meses y a 1 año, la red gana al ingenuo con el mercado en calma (notas 0,94 y 0,77) y pierde en tormenta (1,24 y 1,71): en esos momentos prevé subidas que en 2022-2026 no llegaron.
- **El rango del 80 % cumple.** Contiene el precio real tantas veces como promete, o algo más, en los tres plazos. Es la parte más útil de la previsión: dice cuánto puede moverse el precio.

El detalle, con métricas (MAE, MSE, RMSE y R²) y gráficos de valores reales frente a previstos, está en el [notebook 03](notebooks/03_modelado.ipynb) (sección 14) y en la web.

## Metodología

**Modelos.** Las tres redes comparten estructura y solo cambia la celda recurrente. Predicen la variación del precio en el plazo, no el precio, a partir de los días anteriores del Brent y de otras variables de mercado. Se entrenan con pérdida de Huber y parada temprana, y cada previsión es la media de 5 redes entrenadas con semillas distintas. Los datos de entrada y la configuración de cada red se eligieron en dos fases: primero los datos (fase A) y después la configuración, con Optuna (fase B).

**Evaluación.**

- **Selección (2000-2021):** datos y configuración elegidos con el entrenamiento de 2000-2017 y la validación de 2018-2021.
- **Validación año a año (2010-2021):** cada año se prevé con redes entrenadas solo con los años anteriores. De aquí salen la red elegida en cada plazo y la nota 2010-2021.
- **Examen final (2022 – 3/11/2026):** redes entrenadas con todo lo anterior a 2022 y evaluadas una sola vez, con la red y las reglas de la conclusión fijadas por escrito antes.
- **Previsiones en vivo (desde el 3/11/2026):** modelos finales, entrenados con todo hasta el 3/11/2026. Cada previsión se guarda con un commit antes de conocer su precio y se comprueba cuando FRED lo publica.

Ningún modelo ve datos posteriores al día desde el que prevé; lo vigilan comprobaciones automáticas de fugas de información.

## Aplicación y web

La web y la aplicación son la misma página. Muestra la previsión de cada plazo con su rango del 80 % y su explicación, el momento del ciclo del petróleo, la comparación entre lo previsto y lo real, y las previsiones en vivo ya comprobadas.

- **En GitHub Pages** (<https://pablojimenezgirardeau.github.io/Caso-Oil-Price/>) enseña el estudio y la última previsión publicada.
- **Servida con Python** (`python app/app.py`) funciona además el botón **Actualizar datos**: descarga los datos de FRED y Yahoo Finance, los pasa por los modelos finales ya entrenados (no se reentrena nada) y actualiza la página con la previsión de hoy.

**Actualización automática (hasta el 30/11/2026).** Cada mañana, GitHub Actions ([`actualizar.yml`](.github/workflows/actualizar.yml)) descarga los datos. Si FRED ha publicado días nuevos de Brent, prevé desde cada uno con los modelos finales, guarda las previsiones con un commit antes de que llegue su fecha, comprueba las pendientes y vuelve a publicar la web. También se puede lanzar a mano desde la pestaña **Actions** (*Run workflow*).

Los pesos de los modelos no están en el repositorio: se publican en [Hugging Face](https://huggingface.co/PabloJimenezGirardeau/brent-rnn-lstm-gru), y la aplicación los descarga si no los encuentra en local.

## Datos

Datos diarios desde el 1 de enero de 2000, de fuentes gratuitas:

| Fuente | Series |
|---|---|
| FRED (EIA, BCE, Fed, Cboe) | Brent spot (**variable objetivo**), WTI spot, gas natural Henry Hub, tipo de depósito del BCE, USD/EUR, CNY/USD, VIX |
| Yahoo Finance | Futuros del Brent y del WTI (OHLC y volumen), cobre, oro, índice del dólar |

El estudio usa la foto descargada el 05/11/2026 (último Brent: 03/11/2026), guardada en `data/petroleo_dataset.csv`. Los modelos trabajan con Brent, WTI, cobre, oro, índice del dólar y VIX desde el 30/08/2000; el porqué de cada elección está en los notebooks.

Las previsiones en vivo y la aplicación usan datos descargados después, en `data/actual/` (fuera del repositorio), sin tocar la foto. Se descargan con el botón de la aplicación o con `python -c "from oil_price.data import descarga; descarga.actualizar()"`. El script del curso, `scripts/data/download_data.py`, **sobrescribe la foto**: solo sirve para regenerarla.

## Estructura del repositorio

```
├── data/                    Foto de los datos del estudio y días reales de cotización del Brent
├── docs/assignment/         Enunciado del caso
├── notebooks/               01 EDA · 02 Preprocesamiento · 03 Modelado, examen final y previsiones en vivo
├── presentacion/            Presentación del caso (PDF y PowerPoint)
├── src/oil_price/           Código reutilizable, por funcionalidad
│   ├── data/                Carga, limpieza, preprocesado, validaciones y descarga de datos nuevos
│   ├── training/            Las tres redes, entrenamiento y búsqueda de datos y configuración
│   ├── evaluation/          Métricas, validación, rango del 80 %, controles y examen final
│   ├── inference/           Modelos finales, previsión, aplicación y previsiones en vivo
│   └── utils/               Parámetros (config.py) y estilo de los gráficos
├── scripts/                 Programas de terminal, con la misma división que src/
├── resultados/              Resultados de los experimentos (CSV; los lee el notebook 03)
├── app/                     Servidor de la aplicación
├── web/                     Web del proyecto (GitHub Pages y aplicación)
├── tests/                   Pruebas automáticas (pytest)
├── .github/workflows/       Publicación de la web y actualización diaria
└── pyproject.toml           Dependencias (Poetry, con poetry.lock y poetry.toml)
```

<details>
<summary>Módulos de <code>src/oil_price/</code></summary>

| Módulo | Qué hace |
|---|---|
| `data/datos.py` | Carga y limpieza |
| `data/preprocesado.py` | Entradas, objetivos, recorte y escalado, fichas y particiones |
| `data/validaciones.py` | Comprobaciones automáticas: huecos y fugas de información |
| `data/descarga.py` | Datos nuevos de FRED y Yahoo en `data/actual/`, sin tocar la foto |
| `training/modelos.py` | Las tres redes (misma estructura, cambia la celda) y el modelo lineal |
| `training/entrenamiento.py` | Entrenamiento común: pérdida de Huber, parada temprana y semillas |
| `training/experimentos.py` | Fase A, su confirmación y el experimento sin tendencia |
| `training/busqueda.py` | Fase B con Optuna: búsqueda por red y plazo, poda, confirmación y elección |
| `training/estabilidad.py` | Promedio de semillas |
| `training/combinacion.py` | Combinación de red y lineal |
| `training/cribado.py` | Criba de información nueva, solo con datos hasta 2017 |
| `training/entreno_completo.py` | Redes entrenadas con todo el entrenamiento y épocas fijas |
| `evaluation/evaluacion.py` | Métricas, modelo ingenuo y comparación con él |
| `evaluation/hacia_atras.py` | Validación hacia atrás: las redes elegidas, evaluadas en 2010-2017 |
| `evaluation/incertidumbre.py` | Rango de incertidumbre del 80 %: rangos, cobertura y regla |
| `evaluation/rango_redes.py` | Redes que dan el rango (percentiles 10, 50 y 90) |
| `evaluation/explicacion.py` | Qué ve cada modelo: aportación e importancia de cada variable |
| `evaluation/comprobaciones.py` | Robustez: bootstrap por bloques, otras métricas y Diebold-Mariano |
| `evaluation/controles.py` | Controles del procedimiento: sin señal y con una señal plantada |
| `evaluation/control_precios.py` | Control: prever el precio en vez de la variación |
| `evaluation/examen_final.py` | Examen final en test: entrenamiento, tabla comparativa y conclusiones |
| `evaluation/analisis_examen.py` | Tras el examen: R², real frente a previsto, cuándo acierta y cuándo falla |
| `inference/modelo_final.py` | Entrenar, guardar, cargar y prever con el rango del 80 % |
| `inference/aplicacion.py` | Lógica de la aplicación: datos, previsión sin reentrenar y explicación |
| `inference/datos_web.py` | Los datos en el formato de la web (exportador y botón de la aplicación) |
| `inference/en_vivo.py` | Previsiones en vivo: cuándo se guarda una nueva y cómo se comprueba |
| `utils/config.py` | Parámetros: fechas, variables, plazos, particiones… |
| `utils/graficos.py` | Estilo de los gráficos |

</details>

Los notebooks se guardan ejecutados, para leer los resultados directamente en GitHub. El código que se usa en más de un sitio vive en `src/oil_price/`, y todos los parámetros están en `src/oil_price/utils/config.py`. Las referencias `D15`, `D27`… del código y los notebooks son las decisiones numeradas del diario de trabajo, que no forma parte del repositorio.

## Instalación

**Requisitos:** Python 3.12 o superior, [Poetry](https://python-poetry.org/) y Git.

```bash
git clone https://github.com/PabloJimenezGirardeau/Caso-Oil-Price.git
cd Caso-Oil-Price
poetry install          # crea .venv e instala las dependencias y el paquete oil_price
poetry run pytest       # pruebas automáticas
```

Los comandos siguientes suponen el entorno activado (`.\.venv\Scripts\Activate.ps1` en PowerShell, `source .venv/bin/activate` en Linux y macOS). Para los notebooks, selecciona el kernel de `.venv` en VS Code o Jupyter.

**Aplicación.** Solo necesita, además, `huggingface_hub`, para descargar los modelos si no están en `modelos/final/`:

```bash
pip install huggingface_hub
python app/app.py       # abre http://127.0.0.1:8765 en el navegador (Ctrl + C para cerrarla)
```

Si la descarga de datos falla (sin conexión, o Yahoo la bloquea), usa los últimos datos descargados o la foto del estudio, y lo indica. Fuera del entorno del proyecto, las dependencias están en `app/requirements.txt`.

> **Windows:** si `poetry` no está en el PATH, o Smart App Control bloquea `poetry.exe`, se puede invocar con su Python interno: `& "$env:APPDATA\pypoetry\venv\Scripts\python.exe" -m poetry install`.
>
> **PyTorch:** se instala la versión para CPU. Para usar una GPU NVIDIA hay que reinstalarlo con soporte CUDA ([instrucciones](https://pytorch.org/get-started/locally/)).

## Reproducir los experimentos

Los entrenamientos largos se lanzan con scripts, no desde los notebooks. Cada resultado se guarda en `resultados/` en cuanto termina y, si el proceso se interrumpe, al relanzarlo continúa donde se quedó. Varios scripts admiten `--solo-mostrar` (plan y tiempo previsto, sin entrenar) y todos `--help`. Los tiempos son aproximados, en CPU.

```bash
# 1. Datos de entrada (fase A) y configuración (fase B, Optuna)
python scripts/training/fase_a.py                         # fase A (6 núcleos de CPU)
python scripts/training/fase_a_semillas.py                # confirmación de los finalistas con las semillas 43 y 44
python scripts/training/tendencia.py                      # combinaciones elegidas, sin la subida media del entrenamiento
python scripts/training/fase_a.py --horizontes largo --sin-tendencia           # fase A de 1 año sin tendencia
python scripts/training/fase_a_semillas.py --horizontes largo --sin-tendencia  # y su confirmación
python scripts/training/fase_b.py --horizontes largo medio  # 1 año y 3 meses, 40 intentos por red (unas 2,5 h)
python scripts/training/fase_b.py --horizontes corto        # 1 semana, 20 intentos por red (unas 12-15 h)

# 2. Estabilidad, validación, rango y controles
python scripts/training/estabilidad.py                    # las 9 redes elegidas con 10 semillas (unas 5 h)
python scripts/evaluation/importancia.py                  # qué variables usan las redes (unos 10 min)
python scripts/evaluation/hacia_atras.py                  # validación hacia atrás 2010-2017, 3 meses y 1 año (unos 12 min)
python scripts/evaluation/hacia_atras.py --horizontes corto  # lo mismo a 1 semana (unos 75 min)
python scripts/evaluation/rango_redes.py                  # redes que dan el rango, 2010-2021 (unos 55 min)
python scripts/training/entreno_completo.py               # redes entrenadas con todo el entrenamiento (unos 8 min)
python scripts/evaluation/controles.py                    # sin señal y con una señal plantada (unos 6 min)
python scripts/evaluation/control_precios.py              # la RNN entrenada con precios (unos 50 min)

# 3. Examen final en test (una sola vez)
python scripts/evaluation/examen_final.py                 # el plan, sin entrenar nada
python scripts/evaluation/examen_final.py --ejecutar      # el examen (unos 40-55 min)

# 4. Modelos finales, previsiones y web
python scripts/inference/prevision_en_vivo.py             # modelos finales y previsión desde el 3/11/2026 (unos 12 min)
python scripts/inference/prever.py --desde 2026-11-11     # previsión con los modelos guardados, desde un día dado
python scripts/inference/actualizar_diario.py             # lo que hace GitHub Actions cada mañana
python scripts/inference/exportar_web.py                  # datos de la web (web/data/), sin entrenar nada
python scripts/inference/subir_modelo_hf.py               # sube los modelos a Hugging Face (sesión iniciada o HF_TOKEN)
```

## Documentación

- [Enunciado del caso](docs/assignment/ENUNCIADO.pdf)
- [Presentación (PDF)](presentacion/Prevision_Brent_presentacion.pdf) y su [versión editable en PowerPoint](presentacion/Prevision_Brent_presentacion.pptx)
- Notebooks: [01 · EDA](notebooks/01_eda.ipynb), [02 · Preprocesamiento](notebooks/02_preprocesamiento.ipynb), [03 · Modelado, examen final y previsiones en vivo](notebooks/03_modelado.ipynb)
- [La web: cómo verla, actualizarla y publicarla](web/README.md)
- [Ficha de los modelos en Hugging Face](https://huggingface.co/PabloJimenezGirardeau/brent-rnn-lstm-gru)
