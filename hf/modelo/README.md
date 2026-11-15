---
license: mit
language:
- es
library_name: pytorch
pipeline_tag: time-series-forecasting
tags:
- time-series
- forecasting
- finance
- oil
- brent
- rnn
- lstm
- gru
---

# Brent: RNN, LSTM y GRU

Redes recurrentes para prever el precio del petróleo **Brent** a tres plazos: **1 semana** (5 sesiones), **3 meses** (63) y **1 año** (252). Proyecto académico de Aprendizaje Automático (Universidad Alfonso X el Sabio). Código, notebooks y diario completo en el repositorio de GitHub: <https://github.com/PabloJimenezGirardeau/Caso-Oil-Price>.

> **Proyecto académico. No es asesoramiento financiero ni una recomendación de inversión.**

## Lo importante, primero

**Ninguna red mejora de forma fiable al modelo ingenuo** («el precio futuro será el de hoy»), ni en 12 años de pruebas año a año (2010-2021) ni en un examen final (2022-2026) que se usó una sola vez. Lo que sí funciona es el **rango del 80 %**, que dice cuánto puede moverse el precio. Por eso la previsión de las redes debe leerse siempre junto a su rango y con esta advertencia.

## Qué contiene

Una carpeta por plazo, con la red elegida para ese plazo (elegida **antes** del examen, con los 12 años de validación):

| Carpeta | Plazo | Red | Parámetros | Ventana |
|---|---|---|---|---|
| `corto/` | 1 semana | LSTM | 2.968 | 252 días |
| `medio/` | 3 meses | RNN | 4.737 | 20 días |
| `largo/` | 1 año | RNN | 6.376 | 20 días |

En cada carpeta:
- `semilla_42.pt` … `semilla_46.pt`: los pesos de cinco entrenamientos con distinta semilla. La previsión final es la **media de los precios** que prevé cada semilla;
- `escalado.json`: el recorte y la estandarización de las entradas, ajustados **solo con datos de entrenamiento**;
- `ficha.json`: la configuración (neuronas, capas, *dropout*, ventana, variables, escala del objetivo, fecha hasta la que se entrenó).

Están entrenadas con todo lo que tiene respuesta hasta el **3/11/2026**. El plazo de 1 año se entrena con todo el entrenamiento y una época fija; los otros dos, con parada temprana.

## Qué prevén

La red prevé la **variación logarítmica** del precio entre hoy y dentro de 5, 63 o 252 sesiones, no el precio. (Probado: una red entrenada con precios parece acertar en un gráfico, pero se equivoca un 54 % más que el ingenuo a 1 semana.)

**Entradas** (siete series diarias, con la ventana indicada arriba): variación diaria del Brent, WTI, cobre, oro, índice del dólar y VIX, y el logaritmo de la volatilidad del Brent en los últimos 21 días.

## Resultados

Nota = error medio en dólares del modelo dividido por el del ingenuo (**1 es empatar; por encima de 1, se equivoca más**).

| Plazo | Red | Nota 2010-2021 (12 años) | Nota en el examen 2022-2026 | p (Diebold-Mariano) | Conclusión fijada antes |
|---|---|---|---|---|---|
| 1 semana | LSTM | 0,997 | 1,005 | 0,56 | sin evidencia de ventaja |
| 3 meses | RNN | 0,994 | 1,094 | 0,13 | sin evidencia de ventaja |
| 1 año | RNN | 0,941 | 1,198 | 0,26 | sin evidencia de ventaja |

**Rango del 80 %** (centrado en el precio de hoy; su anchura depende de la volatilidad reciente): en el examen final acertó el **79 %** a 1 semana, el **84 %** a 3 meses y el **89 %** a 1 año. A 1 semana es un 7 % más preciso que un rango fijo; a 3 meses y a 1 año, igual. A 1 año hay muy pocos movimientos independientes: es orientativo.

## Cómo usarlo

Los pesos solo sirven con el código del repositorio, que reconstruye las fichas de entrada igual que en el entrenamiento:

```python
from huggingface_hub import snapshot_download
from oil_price import modelo_final

carpeta = snapshot_download("PabloJimenezGirardeau/brent-rnn-lstm-gru")
modelos = modelo_final.cargar(carpeta)          # {"corto": …, "medio": …, "largo": …}
```

`modelo_final.prever(modelos, bases, ctx)` devuelve, para cada plazo, el precio previsto, la variación y el rango del 80 %. La aplicación del repositorio de GitHub (`python app/app.py`) lo hace con datos descargados al momento.

## Límites

- Con datos de mercado no se pueden anticipar choques: el 4/11/2026 el Brent cayó un 14 % en un día y ni las redes ni el ingenuo lo vieron.
- Las redes de 3 meses y de 1 año prevén hoy subidas grandes (efecto de lo aprendido tras caídas con el mercado nervioso). En el examen final esas mismas redes se equivocaron **más** que el ingenuo: úsese solo el rango como referencia.
- Datos: FRED (EIA, BCE, Fed, Cboe) y Yahoo Finance, de 2000 a noviembre de 2026. Este repositorio no incluye datos.
- Es un trabajo académico, no un producto financiero.
