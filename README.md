# Predicción del precio del Brent con RNN, LSTM y GRU

**Caso de uso III · Aprendizaje automático (UAX)** · Trabajo individual

Comparativa de tres redes neuronales recurrentes (RNN simple, LSTM y GRU) para predecir el precio del petróleo **Brent** a corto (5 días hábiles), medio (63) y largo plazo (252). El mejor modelo se integra en una aplicación que calcula la predicción, cuantifica su incertidumbre y la explica en lenguaje sencillo, como apoyo a decisiones de inversión, cobertura y compra de energía.

## Estado

- [x] Entorno y descarga de datos
- [x] Análisis exploratorio (EDA)
- [x] Preprocesamiento
- [ ] Modelos (RNN, LSTM y GRU) y comparativa: *en curso* (fase A cerrada: datos elegidos para cada horizonte, sin tendencia; fase B cerrada en los tres horizontes; estabilidad cerrada: se promedian 5 semillas; la combinación de red y lineal no mejora; la validación hacia atrás (2010-2017) no confirma la ventaja de las redes en ningún horizonte; rango del 80 % elegido en los tres horizontes; redes de 1 año entrenadas con todo el entrenamiento)
- [ ] Aplicación
- [ ] Presentación (máximo 5 diapositivas)

## Estructura del repositorio

```
├── data/
│   ├── petroleo_dataset.csv     Foto de los datos usada en el proyecto (solo lectura)
│   └── dias_brent.csv           Días reales de cotización del Brent (desde FRED)
├── docs/
│   └── assignment/              Enunciado del caso
├── notebooks/
│   ├── 01_eda.ipynb             Análisis exploratorio
│   ├── 02_preprocesamiento.ipynb  Del CSV a las fichas de entrenamiento
│   └── 03_modelado.ipynb        Entrenamiento y comparación de RNN, LSTM y GRU
├── resultados/                  Resultados de los experimentos (CSV versionados; los lee el notebook 03)
├── src/oil_price/               Código reutilizable (notebooks, scripts y aplicación), por funcionalidad
│   ├── data/                    Datos
│   │   ├── datos.py             Carga y limpieza
│   │   ├── preprocesado.py      Entradas, objetivos, recorte y escalado, fichas, particiones
│   │   ├── validaciones.py      Comprobaciones automáticas (huecos, fugas de información)
│   │   └── descarga.py          Datos nuevos (FRED y Yahoo, como el script del curso) en data/actual/, sin tocar la foto
│   ├── training/                Modelos y entrenamiento
│   │   ├── modelos.py           Las tres redes (misma estructura, cambia la celda) y modelo lineal
│   │   ├── entrenamiento.py     Entrenamiento común: pérdida Huber, parada temprana, semillas
│   │   ├── experimentos.py      Fase A, su confirmación y experimento sin tendencia
│   │   ├── busqueda.py          Fase B con Optuna: búsqueda por red y horizonte, poda, confirmación y elección
│   │   ├── estabilidad.py       Promedio de semillas (D27)
│   │   ├── combinacion.py       Combinación de red y lineal (D28)
│   │   ├── cribado.py           Criba de información nueva solo con datos hasta 2017
│   │   └── entreno_completo.py  Redes entrenadas con todo el entrenamiento y épocas fijas (D31)
│   ├── evaluation/              Evaluación, rangos y controles
│   │   ├── evaluacion.py        Métricas, modelo ingenuo y comparación con él
│   │   ├── hacia_atras.py       Validación hacia atrás (D29): las redes elegidas, evaluadas en 2010-2017
│   │   ├── incertidumbre.py     Rango de incertidumbre del 80 % (D30): rangos, cobertura y regla
│   │   ├── rango_redes.py       Redes que dan el rango (percentiles 10, 50 y 90)
│   │   ├── explicacion.py       Qué ve cada modelo: aportación e importancia de cada variable
│   │   ├── comprobaciones.py    Robustez: bootstrap por bloques, otras métricas, Diebold-Mariano
│   │   ├── controles.py         Controles del procedimiento: sin señal y con una señal plantada
│   │   ├── control_precios.py   Experimento de control (D15): prever el precio en vez de la variación
│   │   ├── examen_final.py      Examen final en test (D33): entrenamiento, tabla comparativa y conclusiones
│   │   └── analisis_examen.py   Tras el examen: R², real frente a previsto, cuándo acierta y cuándo falla
│   ├── inference/               Modelos finales y aplicación
│   │   ├── modelo_final.py      Entrenar, reentrenar, guardar, cargar y prever con su rango del 80 % (D34)
│   │   ├── aplicacion.py        Lógica de la aplicación: datos, previsión (sin reentrenar) y explicación
│   │   └── datos_web.py         Los datos en el formato de la web: los usan el exportador y el botón de la aplicación
│   └── utils/
│       ├── config.py            Parámetros: fechas, variables, horizontes, partición…
│       └── graficos.py          Estilo de los gráficos
├── scripts/                     Programas que se lanzan desde la terminal, con la misma división
│   ├── data/                    download_data.py (datos del curso: FRED + Yahoo), generar_dias_brent.py
│   ├── training/                fase_a.py, fase_a_semillas.py, tendencia.py, fase_b.py, estabilidad.py, entreno_completo.py
│   ├── evaluation/              importancia.py, hacia_atras.py, rango_redes.py, controles.py, control_precios.py, examen_final.py
│   └── inference/               prevision_en_vivo.py, prever.py, exportar_web.py, subir_modelo_hf.py
├── app/                         La aplicación: sirve la web con Python y hace funcionar «Actualizar datos»
├── web/                         La web del proyecto (GitHub Pages y aplicación); ver web/README.md
├── tests/                       Pruebas automáticas (pytest)
├── pyproject.toml               Dependencias (Poetry)
├── poetry.lock                  Versiones exactas de las dependencias
└── poetry.toml                  Configuración local de Poetry (entorno en .venv)
```

**La web y la aplicación son la misma página.** Publicada en GitHub Pages (<https://pablojimenezgirardeau.github.io/Caso-Oil-Price/>), enseña el estudio y la previsión publicada. Servida por Python (`python app/app.py`), además funciona el botón **Actualizar datos**: descarga los datos de FRED y Yahoo Finance y los pasa por los modelos finales, ya entrenados (no se reentrena nada), y la página se actualiza en su sitio con la previsión de hoy, su rango del 80 % y su explicación.

Los pesos de los modelos entrenados (`modelos/`) no están en el repositorio: se publican en Hugging Face (<https://huggingface.co/PabloJimenezGirardeau/brent-rnn-lstm-gru>) y la aplicación los descarga sola si no los encuentra en local. En el código y los notebooks, `D27`, `D30`… son las decisiones numeradas del diario de trabajo, que no se sube.

**Convenciones**
- Los notebooks se numeran por orden de ejecución (`01_`, `02_`…) y se guardan **ejecutados**, para que los resultados se lean directamente en GitHub.
- El código que se usa en más de un sitio vive en `src/oil_price/`, no se copia entre notebooks.
- Todos los parámetros están en `src/oil_price/utils/config.py`.

## Puesta en marcha

**Requisitos:** Python 3.12 o superior, [Poetry](https://python-poetry.org/) y Git.

```bash
git clone https://github.com/PabloJimenezGirardeau/Caso-Oil-Price.git
cd Caso-Oil-Price
poetry install          # crea .venv, instala las dependencias y el paquete oil_price
poetry run pytest       # comprueba que todo funciona
```

Los datos con los que se obtuvieron los resultados ya están en `data/`, así que no hace falta descargarlos. Para descargar datos actualizados: `poetry run python scripts/data/download_data.py`. Esto cambia las cifras, porque el periodo llega hasta el día de la descarga.

**La aplicación** abre la web del proyecto con el botón **Actualizar datos** funcionando (los datos nuevos pasan por los modelos, sin reentrenar). Solo usa Python estándar más el entorno del proyecto:

```bash
pip install huggingface_hub     # dentro del entorno .venv; para descargar los modelos si no están en modelos/final
python app/app.py               # abre http://127.0.0.1:8765 en el navegador (Ctrl + C para cerrarla)
```

Si no encuentra los modelos en `modelos/final/`, los descarga de Hugging Face (<https://huggingface.co/PabloJimenezGirardeau/brent-rnn-lstm-gru>). Si la descarga de datos falla (sin conexión, o Yahoo bloquea), usa los últimos datos descargados o la foto del estudio, y lo dice. En un entorno nuevo, todo lo necesario está en `app/requirements.txt`.

Para trabajar con los notebooks, selecciona el kernel del entorno `.venv` en VS Code o Jupyter.

> **Windows:** si `poetry` no está en el PATH, o si Smart App Control bloquea `poetry.exe` («Una directiva de Control de aplicaciones bloqueó este archivo»), se puede invocar a través de su Python interno: `& "$env:APPDATA\pypoetry\venv\Scripts\python.exe" -m poetry install`. Para activar el entorno en PowerShell: `.\.venv\Scripts\Activate.ps1`.
>
> **PyTorch:** se instala la versión para CPU. Para usar una GPU NVIDIA hay que reinstalar PyTorch con soporte CUDA (ver https://pytorch.org/get-started/locally/).

## Experimentos

Los entrenamientos largos se lanzan con scripts, no desde los notebooks. Cada resultado se guarda en `resultados/` en cuanto termina; si el proceso se interrumpe, al volver a lanzarlo continúa donde se quedó.

```bash
python scripts/training/fase_a.py                        # fase A completa (6 núcleos de CPU)
python scripts/training/fase_a.py --ventanas 10 20 40 60 # solo algunas ventanas
python scripts/training/fase_a.py --help                 # todas las opciones

python scripts/training/fase_a_semillas.py --solo-mostrar # finalistas de la fase A y tiempo previsto
python scripts/training/fase_a_semillas.py                # las repite con las semillas 43 y 44

python scripts/training/tendencia.py --solo-mostrar       # qué se entrena sin tendencia y tiempo previsto
python scripts/training/tendencia.py                      # combinaciones elegidas sin la subida media del train

python scripts/training/fase_a.py --horizontes largo --sin-tendencia           # fase A de 1 año sin tendencia
python scripts/training/fase_a_semillas.py --horizontes largo --sin-tendencia  # y su confirmación con semillas

python scripts/training/fase_b.py --solo-mostrar                 # fase B: plan y tiempo previsto
python scripts/training/fase_b.py --horizontes largo medio       # 1 año y 3 meses, 40 intentos por red (unas 2,5 h)
python scripts/training/fase_b.py --horizontes corto             # 1 semana, 20 intentos por red (la más lenta, unas 12-15 h)

python scripts/training/estabilidad.py --solo-mostrar            # estabilidad (D27): plan y tiempo previsto
python scripts/training/estabilidad.py                           # las 9 redes elegidas con 10 semillas (unas 5 h)

python scripts/evaluation/importancia.py                           # qué variables usan las redes, a 3 meses y a 1 año (unos 10 min)
python scripts/evaluation/hacia_atras.py                           # validación hacia atrás, 2010-2017 (unos 12 min)
python scripts/evaluation/hacia_atras.py --horizontes corto       # lo mismo a 1 semana (unos 75 min)
python scripts/evaluation/rango_redes.py                           # redes que dan el rango, 2010-2021 (unos 55 min)
python scripts/training/entreno_completo.py                      # redes entrenadas con todo (D31), 3 meses y 1 año (unos 8 min)
python scripts/evaluation/controles.py                             # controles sin señal y con señal plantada, con el lineal (unos 6 min)
python scripts/evaluation/control_precios.py                       # la RNN entrenada con precios (D15), 1 semana y 3 meses (unos 50 min)
python scripts/evaluation/examen_final.py                          # plan del examen final en test (no entrena nada)
python scripts/evaluation/examen_final.py --ejecutar               # el examen final en test, una sola vez (unos 40-55 min)
python scripts/inference/prevision_en_vivo.py                     # modelos finales y previsión desde el 3/11/2026 (unos 12 min)
python -c "from oil_price.data import descarga; descarga.actualizar()"   # datos nuevos en data/actual/
python scripts/inference/prever.py --desde 2026-11-11             # previsión con los modelos guardados desde ese día
python scripts/inference/exportar_web.py                          # datos de la web (web/data/), sin entrenar nada
python app/app.py                                       # la aplicación: la web con «Actualizar datos», en http://127.0.0.1:8765
python scripts/inference/subir_modelo_hf.py                       # sube los modelos a Hugging Face (con la sesión iniciada o HF_TOKEN)
```

Los notebooks leen esos resultados y los analizan (`notebooks/03_modelado.ipynb`).

## Datos

Datos diarios desde el 1 de enero de 2000, descargados de fuentes gratuitas:

| Fuente | Series |
|---|---|
| FRED (EIA, BCE, Fed, Cboe) | Brent spot (**variable objetivo**), WTI spot, gas natural Henry Hub, tipo de depósito del BCE, USD/EUR, CNY/USD, VIX |
| Yahoo Finance | Futuros del Brent y del WTI (OHLC y volumen), cobre, oro, índice del dólar |

El proyecto usa la foto descargada el 05/11/2026 (último Brent real: 03/11/2026). El modelo trabaja con Brent, WTI, cobre, oro, índice del dólar y VIX desde el 30/08/2000; el porqué de cada elección está en los notebooks.

## Documentación

- [Enunciado del caso](docs/assignment/ENUNCIADO.pdf)
