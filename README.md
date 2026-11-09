# Predicción del precio del Brent con RNN, LSTM y GRU

**Caso de uso III · Aprendizaje automático (UAX)** · Trabajo individual

Comparativa de tres redes neuronales recurrentes (RNN simple, LSTM y GRU) para predecir el precio del petróleo **Brent** a corto (5 días hábiles), medio (63) y largo plazo (252). El mejor modelo se integra en una aplicación que calcula la predicción, cuantifica su incertidumbre y la explica en lenguaje sencillo, como apoyo a decisiones de inversión, cobertura y compra de energía.

## Estado

- [x] Entorno y descarga de datos
- [x] Análisis exploratorio (EDA)
- [x] Preprocesamiento
- [ ] Modelos (RNN, LSTM y GRU) y comparativa: *en curso* (modelos y entrenamiento listos; pendientes la búsqueda de configuraciones y el examen final)
- [ ] Aplicación
- [ ] Presentación (máximo 5 diapositivas)

El detalle del trabajo (decisiones, problemas, hipótesis y soluciones) está en el [diario de ruta](docs/diario_de_ruta.md).

## Estructura del repositorio

```
├── data/
│   ├── petroleo_dataset.csv     Foto de los datos usada en el proyecto (solo lectura)
│   └── dias_brent.csv           Días reales de cotización del Brent (desde FRED)
├── docs/
│   ├── assignment/              Enunciado del caso
│   └── diario_de_ruta.md        Registro de decisiones, problemas e hipótesis
├── notebooks/
│   ├── 01_eda.ipynb             Análisis exploratorio
│   ├── 02_preprocesamiento.ipynb  Del CSV a las fichas de entrenamiento
│   └── 03_modelado.ipynb        Entrenamiento y comparación de RNN, LSTM y GRU
├── resultados/                  Resultados de los experimentos (CSV versionados; los lee el notebook 03)
├── scripts/
│   ├── download_data.py         Descarga de datos (FRED + Yahoo Finance), del curso
│   ├── generar_dias_brent.py    Genera data/dias_brent.csv
│   └── fase_a.py                Lanza la fase A del estudio (ventana × recorte × nivel)
├── src/oil_price/               Código reutilizable (notebooks y aplicación)
│   ├── config.py                Parámetros: fechas, variables, horizontes, partición…
│   ├── datos.py                 Carga y limpieza
│   ├── preprocesado.py          Entradas, objetivos, recorte y escalado, fichas, particiones
│   ├── validaciones.py          Comprobaciones automáticas (huecos, fugas de información)
│   ├── modelos.py               Las tres redes (misma estructura, cambia la celda) y modelo lineal
│   ├── entrenamiento.py         Entrenamiento común: pérdida Huber, parada temprana, semillas
│   ├── experimentos.py          Búsquedas (fase A): ejecución reanudable y resumen de resultados
│   ├── evaluacion.py            Métricas, modelo ingenuo y comparación con él
│   └── graficos.py              Estilo de los gráficos
├── tests/                       Pruebas automáticas (pytest)
├── pyproject.toml               Dependencias (Poetry)
├── poetry.lock                  Versiones exactas de las dependencias
└── poetry.toml                  Configuración local de Poetry (entorno en .venv)
```

A medida que avance el proyecto se añadirán:

| Carpeta | Contenido |
|---|---|
| `app/` | Aplicación de predicción |
| `models/` | Modelos entrenados |
| `reports/figures/` | Figuras para la presentación |

**Convenciones**
- Los notebooks se numeran por orden de ejecución (`01_`, `02_`…) y se guardan **ejecutados**, para que los resultados se lean directamente en GitHub.
- El código que se usa en más de un sitio vive en `src/oil_price/`, no se copia entre notebooks.
- Todos los parámetros están en `src/oil_price/config.py`.

## Puesta en marcha

**Requisitos:** Python 3.12 o superior, [Poetry](https://python-poetry.org/) y Git.

```bash
git clone https://github.com/PabloJimenezGirardeau/Caso-Oil-Price.git
cd Caso-Oil-Price
poetry install          # crea .venv, instala las dependencias y el paquete oil_price
poetry run pytest       # comprueba que todo funciona
```

Los datos con los que se obtuvieron los resultados ya están en `data/`, así que no hace falta descargarlos. Para descargar datos actualizados: `poetry run python scripts/download_data.py`. Esto cambia las cifras, porque el periodo llega hasta el día de la descarga.

Para trabajar con los notebooks, selecciona el kernel del entorno `.venv` en VS Code o Jupyter.

> **Windows:** si `poetry` no está en el PATH, o si Smart App Control bloquea `poetry.exe` («Una directiva de Control de aplicaciones bloqueó este archivo»), se puede invocar a través de su Python interno: `& "$env:APPDATA\pypoetry\venv\Scripts\python.exe" -m poetry install`. Para activar el entorno en PowerShell: `.\.venv\Scripts\Activate.ps1`.
>
> **PyTorch:** se instala la versión para CPU. Para usar una GPU NVIDIA hay que reinstalar PyTorch con soporte CUDA (ver https://pytorch.org/get-started/locally/).

## Experimentos

Los entrenamientos largos se lanzan con scripts, no desde los notebooks. Cada resultado se guarda en `resultados/` en cuanto termina; si el proceso se interrumpe, al volver a lanzarlo continúa donde se quedó.

```bash
python scripts/fase_a.py                        # fase A completa (6 núcleos de CPU)
python scripts/fase_a.py --ventanas 10 20 40 60 # solo algunas ventanas
python scripts/fase_a.py --help                 # todas las opciones
```

Los notebooks leen esos resultados y los analizan (`notebooks/03_modelado.ipynb`).

## Datos

Datos diarios desde el 1 de enero de 2000, descargados de fuentes gratuitas:

| Fuente | Series |
|---|---|
| FRED (EIA, BCE, Fed, Cboe) | Brent spot (**variable objetivo**), WTI spot, gas natural Henry Hub, tipo de depósito del BCE, USD/EUR, CNY/USD, VIX |
| Yahoo Finance | Futuros del Brent y del WTI (OHLC y volumen), cobre, oro, índice del dólar |

El proyecto usa la foto descargada el 05/11/2026 (último Brent real: 03/11/2026). El modelo trabaja con Brent, WTI, cobre, oro, índice del dólar y VIX desde el 30/08/2000; el porqué de cada elección está en el diario de ruta.

## Documentación

- [Enunciado del caso](docs/assignment/ENUNCIADO.pdf)
- [Diario de ruta](docs/diario_de_ruta.md)
