---
title: Previsión del Brent
colorFrom: yellow
colorTo: gray
sdk: gradio
sdk_version: 6.32.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Previsión del Brent con RNN, LSTM y GRU y su rango del 80 %
---

# Previsión del Brent

Aplicación del proyecto académico de previsión del precio del Brent con redes recurrentes (RNN, LSTM y GRU), a 1 semana, 3 meses y 1 año.

- Elige el plazo y mira el precio previsto, su variación, el **rango del 80 %** y una explicación en lenguaje sencillo, con la fiabilidad que dio el examen final.
- Marca en el histórico los grandes picos y caídas del precio y explica el ciclo económico.
- **Actualizar datos** descarga los más recientes de FRED y Yahoo Finance; **Reentrenar** vuelve a entrenar las redes con ellos.
- Los modelos están en [PabloJimenezGirardeau/brent-rnn-lstm-gru](https://huggingface.co/PabloJimenezGirardeau/brent-rnn-lstm-gru) y el código, en [GitHub](https://github.com/PabloJimenezGirardeau/Caso-Oil-Price).

**Ninguna red mejora de forma fiable al modelo ingenuo** («el precio futuro será el de hoy»). Lo que sí funciona es el rango, que dice cuánto puede moverse el precio.

Proyecto académico. No es asesoramiento financiero ni una recomendación de inversión.
