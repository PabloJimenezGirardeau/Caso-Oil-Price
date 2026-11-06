# Predicción del precio del Brent con RNN, LSTM y GRU

**Caso de uso III · Aprendizaje automático (UAX)** · Trabajo individual

Comparativa de tres redes neuronales recurrentes (RNN simple, LSTM y GRU) para predecir el precio del petróleo **Brent** a corto (5 días hábiles), medio (63) y largo plazo (252). El mejor modelo se integra en una aplicación que calcula la predicción, cuantifica su incertidumbre y la explica en lenguaje sencillo, como apoyo a decisiones de inversión, cobertura y compra de energía.

## Estado

- [x] Entorno y descarga de datos
- [x] Análisis exploratorio (EDA)
- [ ] Preprocesamiento
- [ ] Modelos (RNN, LSTM y GRU) y comparativa
- [ ] Aplicación
- [ ] Presentación (máximo 5 diapositivas)

El detalle del trabajo (decisiones, problemas, hipótesis y soluciones) está en el [diario de ruta](docs/diario_de_ruta.md).

## Estructura del repositorio

```
├── data/                     Datos descargados (se generan con scripts/download_data.py)
├── docs/
│   ├── assignment/           Enunciado del caso
│   └── diario_de_ruta.md     Registro de decisiones, problemas e hipótesis
├── notebooks/
│   └── 01_eda.ipynb          Análisis exploratorio
├── scripts/
│   └── download_data.py      Descarga de datos (FRED + Yahoo Finance)
├── pyproject.toml            Dependencias (Poetry)
├── poetry.lock               Versiones exactas de las dependencias
└── poetry.toml               Configuración local de Poetry (entorno en .venv)
```

A medida que avance el proyecto se añadirán:

| Carpeta | Contenido |
|---|---|
| `src/` | Código reutilizable (preparación de datos, modelos, evaluación), compartido por notebooks y aplicación |
| `app/` | Aplicación de predicción |
| `models/` | Modelos entrenados |
| `reports/figures/` | Figuras para la presentación |

**Convenciones**
- Los notebooks se numeran por orden de ejecución (`01_`, `02_`…) y se guardan **ejecutados**, para que los resultados se lean directamente en GitHub.
- El código que se use en más de un sitio se mueve a `src/` en lugar de copiarse entre notebooks.

## Puesta en marcha

**Requisitos:** Python 3.12 o superior, [Poetry](https://python-poetry.org/) y Git.

```bash
git clone https://github.com/PabloJimenezGirardeau/Caso-Oil-Price.git
cd Caso-Oil-Price
poetry install                                 # crea .venv e instala las dependencias
poetry run python scripts/download_data.py     # descarga los datos en data/
```

Para trabajar con los notebooks, selecciona el kernel del entorno `.venv` en VS Code o Jupyter.

> **Windows:** si `poetry` no está en el PATH, se puede invocar con su ruta completa: `& "$env:APPDATA\Python\Scripts\poetry.exe" install`. Para activar el entorno en PowerShell: `.\.venv\Scripts\Activate.ps1`.

## Datos

Datos diarios desde el 1 de enero de 2000, descargados de fuentes gratuitas:

| Fuente | Series |
|---|---|
| FRED (EIA, BCE, Fed, Cboe) | Brent spot (**variable objetivo**), WTI spot, gas natural Henry Hub, tipo de depósito del BCE, USD/EUR, CNY/USD, VIX |
| Yahoo Finance | Futuros del Brent y del WTI (OHLC y volumen), cobre, oro, índice del dólar |

## Documentación

- [Enunciado del caso](docs/assignment/ENUNCIADO.pdf)
- [Diario de ruta](docs/diario_de_ruta.md)
