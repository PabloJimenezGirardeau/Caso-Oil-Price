# Diario de ruta

Registro del proyecto: qué se hace, qué se deshace y por qué, los problemas que aparecen, las hipótesis que se plantean y cómo se resuelven.

- **Resumen vivo** (arriba): decisiones, hipótesis y limitaciones vigentes. Se actualiza en cada sesión.
- **Entradas** (abajo): una por sesión de trabajo, en orden cronológico, con los apartados *Hecho*, *Problemas y soluciones*, *Decisiones*, *Deshecho o descartado* y *Pendiente*.

Estados: ✅ vigente · 🟡 propuesta (pendiente de validar) · ❌ descartada.

---

## Resumen vivo

### Decisiones

| ID | Fecha | Decisión | Motivo | Estado | Referencia |
|---|---|---|---|---|---|
| D1 | 05/11/2026 | Entorno con Poetry en `.venv` dentro del repo, con Python 3.12 del sistema | Reproducible y fácil de detectar desde VS Code; evita usar el Python de otro proyecto | ✅ | `poetry.toml` |
| D2 | 06/11/2026 | Usar el `poetry.lock` oficial del curso (pandas 3.1.0) | pandas 3.1.1 queda bloqueado por Smart App Control | ✅ | `poetry.lock` |
| D3 | 06/11/2026 | Trabajar con el calendario real del Brent (6.501 días) y usar el último dato real como precio actual | 502 filas del CSV son festivos rellenados y las 2 últimas son copias (comprobado contra FRED) | ✅ | EDA §1 |
| D4 | 06/11/2026 | Objetivo: Brent spot (EIA); el modelo predice su variación logarítmica a 5, 63 y 252 sesiones y el precio se reconstruye a partir de ella | El precio no es estacionario y la variación sí; «predecir 0» equivale al modelo ingenuo | ✅ (vigilada con H4) | EDA §3-4 |
| D5 | 06/11/2026 | Variables de entrada: Brent, WTI, cobre, oro, índice del dólar y VIX (en variaciones), desde el 30/08/2000, **más 2 indicadores del Brent**: volatilidad de 21 días (siempre) y precio frente a su media anual (estudio con y sin) | Relación con el Brent y cobertura completa; el resto es redundante o no aporta. La volatilidad es predecible (EDA §5) y el nivel recupera la noción de «caro o barato» que se pierde al usar variaciones | ✅ (vigilada con H2 y H6) | EDA §6, Prep. §2 |
| D6 | 06/11/2026 (act. 08/11) | **Ventana de entrada, una por horizonte:** se prueban **10, 20, 40, 60, 120 y 252 días** (de lo inmediato al ciclo anual) en validación. En cada horizonte gana la ventana con menor error medio en las tres redes, y las tres usan esa misma ventana. Si dos empatan dentro del ruido, gana la más corta. Opcional: comprobar al final con las redes ya ajustadas. Se presenta como curva «error según la ventana» | Con una red por horizonte (D18), cada plazo puede necesitar una memoria distinta. Ventanas bien separadas, en lugar de un ajuste fino: entre ventanas cercanas la diferencia es menor que el ruido y ganaría la que tuviera suerte. El enunciado exige la misma ventana para las tres redes de cada comparación | ✅ | EDA §5, Diario 08/11 |
| D7 | 06/11/2026 | **Partición E:** train 2000-2017 · validación walk-forward 2018-2021 (4 pliegues anuales, con purga) · test 2022-hoy, usado una sola vez | Frente a la A, da un test más sólido en el horizonte más difícil (4 años independientes a 252 días frente a 3) e incluye las dos últimas crisis (2022 y 2026), sin perder variedad en train ni en validación | ✅ | EDA §8 |
| D8 | 06/11/2026 | Intervalo del 80 % con los cuantiles 10-90 de los errores de validación de cada horizonte, **relativos a la volatilidad reciente** (21 días); en la app se multiplican por la volatilidad del momento | Las colas gruesas impiden suponer normalidad, y la volatilidad es predecible: la horquilla debe ensancharse en las crisis y estrecharse en calma | ✅ (vigilada con H3) | EDA §7 |
| D9 | 06/11/2026 | **Recorte de las variaciones diarias** (no de los indicadores), con percentiles calculados solo con train. **Estudio:** sin recorte / 0,5-99,5 % / 1-99 %. Entrenamiento con **pérdida Huber**; evaluación sobre los datos reales, sin recortar | Los 8 mayores movimientos son de 2020 y dominarían el entrenamiento. Recortar los indicadores apagaría la «alarma de tormenta» (Prep. §4) | ✅ | EDA §4, Prep. §4 |
| D10 | 06/11/2026 | Al terminar, repetir la evaluación con la partición A (train 2000-2018 · val 2019-2022 · test 2023-hoy) como prueba de robustez | Si las conclusiones se mantienen con las dos particiones, son más creíbles. Solo sirve para comprobar, no para elegir | ✅ | EDA §8 |
| D11 | 06/11/2026 | Redes con **PyTorch** | La GPU de la universidad es Windows, y en Windows nativo solo PyTorch usa la GPU; también funciona en CPU en el portátil | ✅ | Diario 06/11 |
| D12 | 06/11/2026 | `data/petroleo_dataset.csv` **se mantiene versionado** como foto de los datos del proyecto. Los experimentos usarán una fecha de corte fija, y las descargas de la app se guardarán en otro archivo | Criterio: quitarlo solo si no causa fallos. Sí los causaría: si Yahoo falla, el script sigue sin cobre, oro e índice del dólar, y cada descarga nueva cambia el test y todas las cifras | ✅ | Diario 06/11 |
| D13 | 06/11/2026 | Calendario de días reales del Brent en `data/dias_brent.csv`, generado una vez desde FRED (`scripts/generar_dias_brent.py`) y versionado. El CSV original no se modifica nunca; el resto del preprocesamiento se hace en memoria | El preprocesamiento funciona sin conexión y siempre da el mismo resultado; las fichas se generan en menos de 1 s y no hace falta guardarlas | ✅ | Prep. §1 |
| D14 | 06/11/2026 | Código reutilizable en el paquete `src/oil_price/` (instalado con `poetry install`): configuración única (`config.py`), comprobaciones automáticas (`validaciones.py`) y pruebas con `pytest` (`tests/`) | Notebooks y aplicación usan la misma receta y los mismos parámetros; una fuga de información no da error visible, así que se comprueba automáticamente | ✅ | Prep. |
| D15 | 06/11/2026 | **Experimento de control para H4, al final:** la red ganadora, con su mejor configuración, entrenada también para predecir el **precio** en lugar de la variación. Se compara su error con el del ingenuo y el de nuestra red, se dibuja el «espejismo» (línea que sigue al precio con un día de retraso) y se comprueba si su predicción se parece más al precio real o al de ayer | Versión mínima: pocos entrenamientos, código reutilizado. Aporta evidencia para H4 y una figura muy clara para la presentación, sin multiplicar el estudio | ✅ | Diario 06/11 |
| D16 | 08/11/2026 | **Búsqueda de la mejor configuración de cada red en dos fases.** Fase A (común): las 18 combinaciones de ventana × recorte × nivel con una estructura base, en las 3 redes y los 4 pliegues; se elige la mejor de media. Fase B (por red): **Optuna** con el mismo espacio y **40 intentos por red** (neuronas, capas, dropout, velocidad de aprendizaje en rango continuo 0,0001-0,003, regularización L2, tamaño de lote). Fijo para las tres: Adam, Huber, parada temprana con un trozo final del train (guarda la mejor versión), reducción automática de la velocidad, recorte de gradientes. Criterio fijado de antemano: error / error del ingenuo, promediado en horizontes y pliegues; las 3 mejores configuraciones se confirman con 3 semillas; empate → la de menos parámetros. Curvas de aprendizaje de las ganadoras | El enunciado pide un presupuesto de ajuste similar, no la misma configuración: cada red compite con su mejor versión. Optuna explora mejor que una rejilla con el mismo número de intentos y dice qué parámetros importan | ✅ (la fase B se concreta en D22) | Diario 08/11 |
| D17 | 08/11/2026 | **Modelo lineal (Ridge) como referencia extra** en la comparativa, con las mismas fichas y el mismo criterio; su regularización se elige en los mismos pliegues de validación. Se prescinde de él si resultara costoso | Peldaño intermedio entre el ingenuo y las redes: responde a «¿hacía falta una red neuronal?». No lo pide el enunciado; suma credibilidad | ✅ | Diario 08/11 |
| D18 | 08/11/2026 | **Una red por horizonte**: cada tipo de red (RNN, LSTM, GRU) se entrena y se ajusta por separado para 5, 63 y 252 sesiones, es decir, 9 modelos. El presupuesto de ajuste de D16 (fase B) se aplica a cada par red-horizonte | El enunciado no lo impide. La prueba inicial mostró que el largo plazo se comporta muy distinto (memoriza y proyecta tendencias): separado, no contamina al corto y medio plazo, y cada horizonte puede tener su propia configuración | ✅ | Diario 08/11 |
| D19 | 09/11/2026 | **Elección de los datos de cada horizonte (cierre de la fase A).** Las 3 mejores combinaciones de cada horizonte (media de las 3 redes) se repiten con 2 semillas más (43 y 44; la 42 ya está en la fase A) y se toma la media de las 3 semillas. **Ruido:** desviación típica entre semillas (media de las finalistas del horizonte). Empatan con la mejor las finalistas a menos de un ruido de ella. Entre las empatadas gana la ventana más corta (D6) y, con la misma ventana, la más sencilla (menos recorte, sin nivel). El lineal no se repite porque no tiene azar | Con una sola semilla, muchas diferencias de la fase A son menores que el azar del propio entrenamiento. La regla se fija antes de ver los resultados para no elegir a conveniencia | ✅ | `experimentos.decidir`, Diario 09/11 |
| D20 | 09/11/2026 | **Experimento sin tendencia, antes de la fase B.** La combinación elegida de cada horizonte (D19) se repite con las 3 semillas **sin la subida media del train**: la red aprende la variación respecto a esa media y, para el futuro, supone tendencia cero, como el ingenuo. El lineal se repite igual (sin término fijo), con todas las combinaciones y fuerzas de regularización. **Regla, fijada antes de ver los resultados:** en cada horizonte se adopta «sin tendencia» si no empeora más de un ruido (el de D19: 0,002 / 0,011 / 0,033) frente a «con tendencia», comparando la media de las 3 redes y las 3 semillas; si empeora más, se mantiene la tendencia. El lineal sigue la misma regla con su mejor versión de cada variante. Si se adopta a 3 meses o a 1 año, se propone repetir la fase A de ese horizonte sin tendencia antes de la fase B | Un modelo que no aprende nada útil proyecta la subida media del train, y a 1 año eso solo ya cuesta 1,16 veces el error del ingenuo (las redes elegidas, 1,11). Con unos 14 años de datos esa media no es fiable (margen de unos ±9 puntos), y la fase B, al regular más las redes, las acercaría a ella. Tendencia cero es lo que supone el ingenuo y lo habitual con precios de mercado; en caso de empate se prefiere por prudente. **Resultado: se adopta sin tendencia en los tres horizontes** (a 1 año, de 1,114 a 1,044; empate a 1 semana y a 3 meses) | ✅ | Diario 09/11, `scripts/tendencia.py`, notebook 03 §4 |
| D21 | 09/11/2026 | **Fase A de 1 año, repetida sin tendencia.** Las 36 combinaciones de 1 año con las 3 redes y la semilla 42, sin tendencia; las 3 mejores se repiten con las semillas 43 y 44 y se elige con la regla D19. Sustituye a la elección de 1 año de D19. A 1 semana y a 3 meses se mantiene la elección de D19, porque sin tendencia el resultado no cambia. El lineal no se repite (sin tendencia ya está completo, D20) | Los datos de 1 año se eligieron con tendencia, y quitarla cambia el resultado en 0,07; el indicador de nivel, por ejemplo, podía estar compensando la tendencia. **Resultado: a 1 año, 20 días, recorte 0,5-99,5, sin nivel (1,027)**, en lugar de 120 días con nivel (1,044 sin tendencia). Rinden igual dentro del azar, pero la nueva es más sencilla, más rápida y más regular por años | ✅ | Diario 09/11, `scripts/fase_a.py --sin-tendencia`, notebook 03 §5 |
| D22 | 10/11/2026 | **Diseño de la fase B** (concreta D16). Por horizonte y red (D18), con los datos de D19 y D21 y **sin tendencia, que pasa a ser lo normal en el entrenamiento** (la fase A original lo desactiva de forma explícita). **40 intentos de Optuna por red**: el primero, la estructura base; los 10 primeros, al azar e iguales para las tres redes; después, Optuna propone cerca de los que mejor van. **Espacio, igual para todas:** neuronas 8-128, 1 o 2 capas, dropout 0-0,5, velocidad de aprendizaje 0,0001-0,003, L2 no o 0,000001-0,01, lote 32, 64 o 128. **Puntuación:** MAE / ingenuo juntando los pliegues; a 1 año, media de 3 semillas por intento; a 1 semana y a 3 meses, 1 semilla, y las 3 mejores de cada red se repiten con las semillas 43 y 44. **Poda:** desde el 2.º pliegue y a partir del 11.º intento, se abandona el intento que va peor que la mediana de los anteriores en ese punto. **Elección:** la mejor media de las 3 semillas; las que quedan a menos de un ruido empatan y gana la de menos parámetros. Sin cambios: parada temprana (limitación a 1 año) y ventana de 252 días a 1 semana | Mismas condiciones y presupuesto para las tres redes, como pide el enunciado. El espacio incluye redes pequeñas y muy reguladas para comprobar H8. A 1 año el azar entre semillas (0,06) es tan grande que, con una sola, la búsqueda premiaría al más afortunado. La poda ahorra tiempo sin cambiar el criterio. Cambiar la ventana de 1 semana después de ver los resultados rompería la regla D19 | ✅ (finalistas: D23; a 1 semana, 20 intentos: D24) | `config.py`, `busqueda.py`, `scripts/fase_b.py`, Diario 10/11 |
| D23 | 10/11/2026 | **La estructura base siempre entra en la final de la fase B.** Las finalistas de cada red son las 3 mejores de la búsqueda y, si no está entre ellas, el intento 1 (la estructura base); todas se miden con las semillas 42, 43 y 44 y se elige con la regla de D22 | A 3 meses, con una semilla por intento, las 3 mejores de cada red ganaron la primera ronda con suerte (la GRU, 0,89-0,90 con la semilla 42 y 0,96 con la 43 y la 44), y la base, mejor con 3 semillas (0,922 frente a 0,937), se quedaba fuera. La pregunta de la fase B es si hay algo mejor que la base, y para responderla la base tiene que competir en igualdad. No puede empeorar el resultado: solo evita quedarse con una configuración afortunada. **Resultado:** a 3 meses, la RNN y la GRU se quedan con la base; a 1 año no cambia nada | ✅ | `busqueda.finalistas_b`, Diario 10/11 (noche) |
| D24 | 10/11/2026 | **A 1 semana, 20 intentos por red en lugar de 40**: los 10 primeros al azar (iguales para las tres redes) y 10 de Optuna. Confirmación y elección como a 3 meses, con D23 | Con la ventana de 252 días, 40 intentos tardarían unas 15 h: la previsión de D22 se quedó corta (×1,6). Hay poco que ganar: a 3 meses la búsqueda no mejoró la base, y a 1 semana la fase A dio 0,98-1,01 en todo. El azar entre semillas a 1 semana es muy pequeño (0,002), así que con una semilla por intento la comparación es fiable. Las tres redes mantienen el mismo presupuesto | ✅ | `config.INTENTOS_FASE_B`, Diario 10/11 (noche) |

### Hipótesis abiertas

| ID | Hipótesis | Cómo se comprobará | Estado |
|---|---|---|---|
| H1 | Las redes mejorarán algo al ingenuo a 5 días, pero no a 63 ni a 252 | Tabla comparativa en test | abierta · en validación (fase A, confirmada con semillas) **no se cumple**: se mejora a 63 días (≈ 6 %) y apenas a 5 (≈ 1 %) |
| H2 | La variación de ayer del WTI anticipa el Brent de hoy (correlación ≈ 0,17), probablemente porque EE. UU. cierra después que Londres | Comparar el modelo con y sin WTI a 5 días | abierta |
| H3 | El modelo aportará más en la anchura del intervalo (riesgo) que en la dirección del precio | Cobertura y anchura de los intervalos frente a los empíricos | abierta |
| H4 | Predecir variaciones funciona mejor que predecir niveles; una red entrenada con precios tiende a copiar el precio de ayer | Experimento de control al final (D15) | abierta |
| H5 | Las conclusiones (red ganadora y horizontes en los que aporta) no dependen de la partición elegida | Prueba de robustez con la partición A (D10) | abierta |
| H6 | El indicador de nivel (precio frente a su media anual) mejora sobre todo a 63 y 252 días, porque los precios muy altos o muy bajos tienden a corregir | Estudio con y sin el indicador, en validación | **no se cumple en las redes** (el indicador las empeora). La corrección sí existe a 252 días, pero el lineal la aprovecha sobre todo con la ventana de 252 días (Diario 09/11). Sin tendencia, tampoco: a 1 año las 11 mejores combinaciones son sin nivel (1,056 con él frente a 1,022 sin él, D21) |
| H7 | Parte del mal resultado a 1 año se debe a la subida media del train, que redes y lineal proyectan al futuro (+3 % a +12 % al año según el pliegue). Sin ella, las redes mejoran a 1 año; a 3 meses y a 1 semana apenas cambia | Experimento sin tendencia (D20) | **se cumple**: a 1 año las redes pasan de 1,114 a 1,044; a 3 meses y a 1 semana, empate (Diario 09/11) |
| H8 | A 1 año, las redes pierden frente al lineal con los mismos datos (1,03 frente a 0,82) porque tienen demasiada capacidad: con unas 17 respuestas independientes, una red pequeña o muy regulada debería acercarse al lineal | Fase B (D22): si a 1 año ganan configuraciones pequeñas o muy reguladas, y si se acercan a 0,82 | **se cumple en parte**: el problema es aprender demasiado, no tener muchos parámetros. A 1 año gana aprender despacio (velocidad ≈ 0,0002 y lote 128): la velocidad es lo que más influye (correlación 0,8 con el error) y el tamaño apenas, si acaso a favor de las redes grandes. Las elegidas paran en la 1.ª época y hacen previsiones prudentes, en la dirección del lineal pero de un tercio a la mitad de su tamaño. Pasan de 1,01-1,06 a 0,88-0,89, sin llegar al lineal (0,82), que va por delante los tres años (Diario 10/11, noche) |

### Limitaciones y problemas conocidos

- El README del repo oficial del curso está desactualizado: el enunciado está en `docs/assignment/ENUNCIADO.pdf` (no en `docs/caso_uso_petroleo.pdf`) y el script es `scripts/download_data.py` (no `descarga_datos_petroleo.py`).
- La cesta de la OPEP (ORB) no está en el dataset: no está en FRED y el script no la descarga.
- La EIA publica el Brent con unos días de retraso, y el script rellena esos días con el último valor.
- Smart App Control (Windows) puede bloquear versiones recién publicadas de librerías con DLL.
- El EDA consulta FRED para identificar los días de cotización (sin conexión usa una regla aproximada).
- La causa del pico de 2026 (138,21 $, 07/04/2026) está sin documentar.
- Equipo de trabajo: Samsung Galaxy Book6 (Intel Core Ultra 7 355, gráfica integrada, 16 GB), **sin GPU NVIDIA**. El problema es pequeño y en CPU se estima entre 30 s y 2 min por entrenamiento. Para los entrenamientos largos: enchufado y sobre una mesa, protección de la batería activada al 80 % (Samsung Settings → Batería y rendimiento) y modo optimizado; con `--hilos 4` va más fresco, aunque algo más lento.
- **Parada temprana a 1 año:** el trozo del train que decide cuándo parar tiene unas 3 respuestas independientes, así que la época de parada es casi azar. Se mantiene igual para todos (D22); las 3 semillas por intento promedian también este azar.
- **Hay GPU disponible en la universidad** para los entrenamientos más pesados (ajuste de hiperparámetros, reentrenamiento anual). Implicaciones:
  - el código debe funcionar igual en CPU y en GPU, eligiendo el dispositivo automáticamente;
  - el repo debe poder clonarse y ejecutarse allí con `poetry install`;
  - la máquina de la universidad es **Windows** → se usa PyTorch (D11);
  - el PyTorch que se instala por defecto en Windows desde PyPI **solo usa CPU**; para la GPU hay que instalar la versión con CUDA desde el repositorio de PyTorch, que depende del modelo de GPU y del driver (pendiente de comprobar allí con `nvidia-smi`).

---

## Entradas

### 04/11/2026 · Arranque y lectura del enunciado

**Hecho**
- Lectura del repo oficial del curso y del enunciado (`docs/assignment/ENUNCIADO.pdf`, 4 páginas).
- Materiales del curso copiados al repo: `docs/`, `scripts/`, `pyproject.toml`, `poetry.lock` y `.gitattributes`.

**Lo esencial del enunciado**
- Comparar RNN, LSTM y GRU para predecir el Brent a 5, 63 y 252 días hábiles, en igualdad de condiciones y frente al modelo ingenuo («precio futuro = precio de hoy»).
- Validación walk-forward, escalador ajustado solo con train, métricas MSE, MAE y RMSE (opcional: acierto de dirección).
- Aplicación (p. ej. Streamlit): elegir horizonte; mostrar precio previsto, variación, intervalo de incertidumbre, explicación sencilla, eventos del ciclo económico y actualización de datos.
- Entrega: **máximo 5 diapositivas** (si hay más, no se evalúa), con enfoque de venta. El código solo va en GitHub, con un README que explique cómo ejecutarlo. «No intensificar en la parte técnica».

**Problemas y soluciones**
- El lector de PDF no funcionaba (falta poppler) → se extrajo el texto con `pypdf` en un entorno temporal, fuera del repo.
- El README oficial está desactualizado → se decide esperar antes de seguir sus pasos. Al final los pasos eran válidos, salvo las rutas citadas en *Limitaciones*.

### 05/11/2026 · Entorno y descarga de datos

**Hecho**
- Entorno creado con Poetry (`poetry install`) y datos descargados con `scripts/download_data.py` → `data/petroleo_dataset.csv`.

**Problemas y soluciones**
- `poetry` no está en el PATH → se invoca con la ruta completa `%APPDATA%\Python\Scripts\poetry.exe`.
- La terminal de VS Code tenía en el PATH el `.venv` de otro proyecto (caso del cáncer de mama) → `poetry env use` apuntando al Python 3.12 del sistema y `virtualenvs.in-project = true` (D1).

### 06/11/2026 · Revisión del entorno, commit inicial y EDA

**Hecho**
- Entorno renombrado a `.venv` (`virtualenvs.prompt`) y recreado.
- Comprobados todos los pasos del README oficial.
- Commit inicial `c078d89` con los materiales y la configuración, y push a `main`.
- Dependencias añadidas: `ipykernel`, `nbconvert`, `matplotlib` y `statsmodels`.
- Notebook `notebooks/01_eda.ipynb`, con 9 secciones; cada una termina en una conclusión y una decisión.
- Este diario y el README del proyecto.

**Problemas y soluciones**
- **`import pandas` fallaba** con *«Una directiva de Control de aplicaciones bloqueó este archivo»*.
  - Causa: había desaparecido `poetry.lock`, así que `poetry install` resolvió pandas 3.1.1 (recién publicado) y Smart App Control bloqueó su DLL.
  - Solución: restaurar el `poetry.lock` oficial, que vuelve a pandas 3.1.0 (D2). ✅
- La primera importación de `statsmodels` tardó 41 s porque Smart App Control escanea las DLL nuevas. Después carga con normalidad.
- **El CSV mezcla calendarios.**
  - Hipótesis inicial: las filas con el Brent repetido son festivos.
  - Comprobado contra FRED: de 572 repeticiones, 502 son relleno y 70 son empates reales; las 2 últimas filas son copias por el retraso de la EIA (D3).

**Hallazgos del EDA**
- Brent: máximo de 143,95 $ (03/07/2008), mínimo de 9,12 $ (21/04/2020), pico de 138,21 $ (07/04/2026), último dato real 107,03 $ (03/11/2026).
- Precio no estacionario; variación diaria estacionaria, con colas muy gruesas (curtosis en exceso de 64). La volatilidad llega en rachas.
- El pasado del Brent apenas anticipa su variación; la volatilidad sí es predecible.
- Error del modelo ingenuo (MAE): 2,65 $ a 5 días, 9,77 $ a 63 días y 18,95 $ a 252 días.
- El Brent cotiza unas 243 sesiones al año, no 252.

**Deshecho o descartado**
- ❌ Usar los futuros del Brent como variable: solo existen desde 2007 y obligarían a descartar 7 años. El futuro del WTI repite la información del WTI spot.
- ❌ Gas natural, tipo del BCE y USD/EUR como variables: sin relación diaria con el Brent o redundantes.
- Corregido en el EDA: el máximo de 2012 se atribuía a la Primavera Árabe, pero se debió sobre todo a las sanciones a Irán. El evento se renombra «Máximo de 2011-2012 (Libia e Irán)».
- Corregido en el EDA: «252 sesiones = un año natural» no es exacto (≈ 12,5 meses con el calendario del Brent).
- Corregido en el EDA: los histogramas por horizonte recortaban los valores extremos con `clip`, lo que creaba picos falsos en los bordes. Ahora se filtran.

**Elección de la partición train / validación / test**
- El enunciado no fija fechas de corte, solo reglas: walk-forward, sin mezclar fechas, la misma partición para las tres redes y el escalador ajustado solo con train.
- Principio acordado: la partición se elige **antes de entrenar** y con criterios fijados de antemano. No vale entrenar con varias y quedarse con la que dé mejores resultados, ni siquiera en validación: cada partición tiene un examen distinto y se acabaría eligiendo el más fácil.
- Criterios: train con regímenes variados, validación con algún episodio de estrés, test reciente y representativo, y suficientes años independientes para evaluar el horizonte de 252 días.
- Se compararon 6 candidatas (EDA §8.1):
  - D (test 2024-hoy) y C (validación 2020-2022) se descartan porque dejan solo 2-3 años independientes.
  - F (70/15/15) es casi igual que A, pero corta a mitad de año.
  - B recorta más el train sin ganar nada frente a E.
- Finalistas: **A** (2000-2018 · 2019-2022 · 2023-hoy) y **E** (2000-2017 · 2018-2021 · 2022-hoy). Empatan en casi todo; los separa la solidez del test a 252 días (4 años independientes en E frente a 3 en A) y que E incluye en el test las crisis de 2022 y 2026.
- **Decisión: E** (D7). Como prueba de robustez, al final se repetirá la evaluación con A (D10, H5).
- Detalle de E: el train tiene 4.261 días; la validación, 1.017 (volatilidad del 64 %); el test, 1.223 (971 orígenes a 252 días). En el test el precio sube solo el 32 % de las veces a 252 días, frente al 58 % del histórico: la tendencia del train no se mantiene.

**Ideas apuntadas para más adelante**
- Variante opcional: evaluar el test **reentrenando cada año** (entrenar hasta 2021 → predecir 2022, reentrenar hasta 2022 → predecir 2023…). Es más realista y conecta con el requisito de actualización dinámica de la app. Coste estimado: unos 15 entrenamientos más (15-20 min en CPU) si una sola red predice los tres horizontes.
- Una red que prediga los tres horizontes a la vez divide por 3 el número de entrenamientos frente a una red por horizonte.

**Deshecho o descartado (partición)**
- ❌ Partición A como principal (era la propuesta inicial del EDA): se sustituye por E y queda como prueba de robustez.

**Cierre del EDA: validación de las decisiones**
- Método: para cada decisión se revisa la evidencia del EDA, la alternativa y el coste de equivocarse.
  - Las que el EDA demuestra quedan firmes.
  - Las que solo se pueden confirmar entrenando se aprueban como punto de partida y se vigilan con una hipótesis (H#). Si los resultados las contradicen, se revisan y se anota aquí.
- D3, D4, D5, D8 y D9 aprobadas. Si surgen imprevistos, se revisarán sobre la marcha.
- **Corrección de D8:** con cuantiles fijos, la horquilla tendría siempre la misma anchura, lo que contradice que la volatilidad es predecible (EDA §5). Se pasa a cuantiles relativos a la volatilidad reciente.
- **D9 concretada:** antes decía «recortar o usar pérdida robusta»; ahora es recorte de entradas en los percentiles 1-99 del train + pérdida Huber.
- **D6 cambiada:** en lugar de fijar 60 días, se prueban 20, 60 y 120 días (preferencia de trabajo: probar varios valores de los parámetros para comparar sus efectos).
- Principio para todo el proyecto: siempre que sea razonable, **probar alternativas y presentar la comparación** (estudio de sensibilidad), manteniendo las condiciones iguales para las tres redes.

**Pendiente**
- [x] Revisar el EDA y validar las decisiones 🟡 (D3-D6, D8, D9).
- [x] Decidir si `data/petroleo_dataset.csv` se versiona o se regenera con el script → se mantiene (D12).
- [x] Commit del EDA, el diario, el README y las dependencias nuevas.
- [ ] Commit de la elección de partición (EDA §8 y diario).
- [ ] Documentar la causa del pico de 2026.
- [ ] Al final del proyecto: prueba de robustez con la partición A (D10).
- [ ] En la universidad: ejecutar `nvidia-smi` para anotar el modelo de GPU y la versión de CUDA del driver.

### 06/11/2026 (tarde) · Preprocesamiento

**Hecho**
- Antes de construir se acordaron estos añadidos:
  - **estudio de recorte** (sin recorte, 0,5-99,5 % y 1-99 %);
  - **dos indicadores del Brent** (volatilidad de 21 días y nivel frente a su media anual, este con y sin);
  - **calendario del Brent en un archivo** (`data/dias_brent.csv`);
  - **configuración única y comprobaciones automáticas**.
- Paquete `src/oil_price/` (D14), instalado con Poetry: se cambió `package-mode = false` por `packages = [{ include = "oil_price", from = "src" }]` en `pyproject.toml`. Módulos:
  - `config.py`: parámetros;
  - `datos.py`: carga y limpieza;
  - `preprocesado.py`: entradas, objetivos, recorte y escalado, fichas y particiones;
  - `validaciones.py`: comprobaciones;
  - `evaluacion.py`: métricas y modelo ingenuo;
  - `graficos.py`: estilo de los gráficos.
- `scripts/generar_dias_brent.py` y `data/dias_brent.csv` (6.501 días) (D13).
- `tests/test_preprocesado.py`: 16 pruebas con `pytest`, sobre todo de fugas de información (alterar el futuro no cambia el pasado, el escalado no ve datos posteriores al train, la purga es correcta…). Todas pasan.
- Notebook `notebooks/02_preprocesamiento.ipynb`: recorre el proceso paso a paso con 1.350 comprobaciones superadas en las 90 combinaciones del estudio.
- Listón del modelo ingenuo sobre las fichas definitivas (MAE): validación 2,39 $ / 10,22 $ / 20,86 $ y test 3,99 $ / 11,94 $ / 16,50 $ (a 5 / 63 / 252 sesiones). Coincide con el EDA.

**Problemas y soluciones**
- **Recortar los indicadores apagaba la alarma de tormenta.** Al dibujar 2020, la volatilidad recortada quedaba fija en el 86 % durante tres meses, cuando la real llegó al 340 %. Era el riesgo previsto al plantear D9. Solución: recortar solo las variaciones diarias; los indicadores ya son suaves y van en logaritmo (D9 actualizada, prueba automática añadida).
- **Las entradas empezaban el 11/12/2001 y no en septiembre**, como se esperaba. Hipótesis inicial: error en el cálculo. Causa real: en 2001-2002 la EIA publicó solo ≈ 194 cotizaciones al año (frente a ≈ 251 desde 2006), y el indicador de nivel necesita 252. No es un error; queda anotado.
- **Una prueba de la purga fallaba.** Daba por hecho que en 2015 hubo menos de 252 sesiones y no era así. Se reescribió para comprobar la regla exacta (objetivo conservado ⇔ fecha del objetivo ≤ límite del bloque).
- `valores_no_positivos` devolvía todas las celdas: en pandas 3, `stack()` ya no descarta los vacíos. Se añadió `dropna()`.
- **VS Code y la terminal usaban el Python del caso del cáncer de mama.**
  - Primera hipótesis: intérprete mal seleccionado en VS Code. Se añadió `.vscode/settings.json` para fijar el `.venv` del proyecto, pero `python` seguía apuntando al otro entorno.
  - Causa real: la carpeta `Caso-Cancer-de-mama\.venv\Scripts` estaba en el **PATH permanente de usuario de Windows, en primera posición**, y «secuestraba» el comando `python` en cualquier terminal. (Explica también lo visto el 05/11.)
  - Solución: quitar esa entrada del PATH de usuario, con copia de seguridad previa en `%USERPROFILE%\backup_PATH_usuario_2026-11-06.txt`. Hay que reiniciar VS Code para que surta efecto.
  - Lección: un entorno virtual nunca debe estar en el PATH permanente; se activa por proyecto.

**Deshecho o descartado**
- ❌ Recortar todas las entradas por igual (idea inicial de D9): se sustituye por recortar solo las variaciones diarias.
- ❌ Guardar las fichas o un CSV procesado en disco: no hace falta (se generan en menos de 1 s y el escalado cambia en cada pliegue).

**Pendiente**
- [x] Commit del preprocesamiento (08/11/2026).
- [ ] Modelado: instalar PyTorch y definir las tres redes con una misma estructura.
- [ ] Al final del proyecto: experimento de control «predecir precios» (D15, H4).

### 08/11/2026 · Arranque del modelado

**Hecho**
- Commit `585cd1d` con todo el preprocesamiento y push a `main`.
- PyTorch 2.15.0 (versión CPU) instalado con Poetry (D11).
- **Medición de tiempos en el portátil** (CPU, 8 hilos; red de 64 unidades, ~4.800 fichas de train):

  | Ventana | RNN | LSTM | GRU |
  |---|---|---|---|
  | 20 días | 0,21 s/época | 0,25 s/época | 0,40 s/época |
  | 60 días | 0,47 s/época | 0,49 s/época | 1,10 s/época |
  | 120 días | 0,81 s/época | 0,89 s/época | 2,13 s/época |

  Con unas 40 épocas, cada entrenamiento dura entre **6 s y 1,4 min** (≈ 0,4 min de media). Los estudios previstos caben en el portátil; la GPU de la universidad no es imprescindible.
- Observación: en CPU la GRU es más lenta que la LSTM, aunque tiene menos parámetros (14.403 frente a 19.139), porque PyTorch tiene la LSTM más optimizada en CPU. El tiempo de entrenamiento de la tabla comparativa depende del hardware y de la implementación, y así se indicará.
- Parámetros con 64 unidades: RNN 4.931 · GRU 14.403 · LSTM 19.139.

**Problemas y soluciones**
- **Smart App Control bloquea ahora `poetry.exe`**, tanto el lanzador de `%APPDATA%\Python\Scripts` como el de `%APPDATA%\pypoetry\venv\Scripts`, aunque el 06/11 funcionaba. Son lanzadores sin firma.
  - Solución: invocar Poetry a través de su Python interno, que sí está firmado: `& "$env:APPDATA\pypoetry\venv\Scripts\python.exe" -m poetry <orden>`. Actualizado en el README.
- La primera importación de PyTorch tardó 41 s (escaneo de las DLL nuevas); después carga con normalidad.

**Construcción del modelado (parte independiente de los horizontes)**
- Pregunta abierta al profesor: ¿una red con tres salidas o una red por horizonte? Mientras tanto se construye lo que sirve en ambos casos.
- `src/oil_price/modelos.py`: `RedRecurrente` (misma estructura para las tres; solo cambia la celda) y `ModeloLineal` (Ridge, D17).
- `src/oil_price/entrenamiento.py`:
  - pérdida Huber que ignora las respuestas purgadas;
  - objetivos escalados por horizonte;
  - Adam, recorte de gradientes y reducción automática de la velocidad;
  - parada temprana con el último 15 % del train, con purga, guardando la mejor versión;
  - reproducible con semilla y GPU automática si la hay.
- `evaluacion.py`: errores por ficha (para juntar pliegues), comparación con el ingenuo y puntuación de selección (D16).
- Parámetros de entrenamiento en `config.py`. 23 pruebas automáticas, todas correctas (7 nuevas: forma de la salida, pérdida con purga, parada temprana sin fuga, reproducibilidad, aprendizaje en un problema sintético, modelo lineal).

**Primera prueba con datos reales** (solo pliegue 1: entrena hasta 2017 y valida en 2018; configuración base; ventana 60; recorte 1-99). **No es una conclusión, solo una comprobación del circuito.**

| Modelo | MAE/ingenuo corto | medio | largo | Parámetros | Mejor época / épocas |
|---|---|---|---|---|---|
| RNN | 0,99 | 1,04 | 1,17 | 4.931 | 4 / 14 |
| LSTM | 1,08 | 1,26 | 4,08 | 19.139 | 12 / 22 |
| GRU | 0,99 | 0,99 | 1,60 | 14.403 | 2 / 12 |
| Lineal | 1,01 | 1,06 | 1,11 | 1.443 | — |

- Las curvas muestran el patrón de **memorización**: la pérdida de train baja mucho (LSTM: de 0,34 a 0,16) mientras la de parada se queda plana (≈ 0,33-0,36), y la mejor época llega pronto (2-4 en RNN y GRU). Es coherente con el EDA: la señal es débil y las redes aprenden ruido enseguida.
- **El largo plazo es el punto peligroso**: la LSTM base comete 4 veces el error del ingenuo a 252 días en 2018. Con pocas observaciones independientes, la red aprende tendencias del pasado que no se repiten.
- Implicaciones para la búsqueda (fase B): la regularización (dropout, L2, redes más pequeñas, velocidad menor) será clave. Conviene asegurar que el espacio de búsqueda incluye redes pequeñas y dropout alto.
- Notebook `notebooks/03_modelado.ipynb`, sección 1: curvas de aprendizaje, tablas y previsiones frente a la realidad en 2018 (cuadrícula horizonte × red). Muestra dos problemas a resolver en las fases A y B:
  - **memorización**: el error de train baja y el de parada no;
  - **sesgo alcista a largo plazo**: las redes proyectan la subida de 2002-2008. La LSTM prevé 80-120 $ cuando el precio real estuvo en 55-75 $.

  A 5 sesiones, las redes van pegadas al ingenuo (el «espejismo» de D15).

**Decisión sobre los horizontes**
- Tras releer el enunciado, nada impide usar una red por horizonte → **D18: una red por horizonte** (9 modelos: 3 tipos × 3 horizontes). Queda resuelta la pregunta pendiente.

**Preparación de la fase A**
- Commit `1655228` con los modelos, el entrenamiento y el notebook 03.
- Ventanas ampliadas a 10, 20, 40, 60, 120 y 252 días, elegidas por horizonte (D6 actualizada). Notebook 02 actualizado: 2.700 comprobaciones en 180 combinaciones, todas correctas.
- `pp.por_horizonte()`: fichas de un solo horizonte, solo las que tienen respuesta (D18).
- `src/oil_price/experimentos.py` y `scripts/fase_a.py`: lanzador de la fase A.
  - Recorre horizonte × ventana × recorte × nivel × red × pliegue, más el modelo lineal con sus 6 fuerzas de regularización.
  - Guarda cada resultado en `resultados/fase_a.csv` y las curvas en `fase_a_curvas.csv`.
  - Reanudable, con registro de progreso, 6 núcleos por defecto y opción `--ventanas` para repartir el trabajo.
  - Se omite el pliegue 2021 a 252 sesiones (1 sola respuesta; mínimo 20).
- 36 pruebas automáticas, todas correctas (13 nuevas: fichas por horizonte, reanudación, formato del archivo, resumen ponderado).
- Coste: no es un problema. Si hace falta mucho entrenamiento, se usará la GPU de la universidad. Se puede dejar corriendo de noche en el portátil (suspensión desactivada con el cargador conectado).

**Problemas encontrados por la prueba de humo** (precisamente para eso se hace)
- **El archivo de resultados quedaba mal formado.** Las filas del lineal (18 columnas) y las de las redes (23) se escribían con formatos distintos y al releerlo fallaba. Solución: formato fijo de columnas para todas las filas.
- **La reanudación no reconocía lo ya hecho** y repetía todos los entrenamientos. Causa: en pandas 3, al convertir a texto, los valores vacíos (el `alfa` de las redes) siguen siendo vacíos y no el texto «nan», así que la clave guardada nunca coincidía con la buscada. Solución: convertir los vacíos explícitamente en ''. Comprobado con tres pasadas (la tercera no entrena nada) y una prueba automática.
- Los resultados de la prueba de humo coinciden en todas las pasadas: el entrenamiento es reproducible.

**Estimación del tiempo de la fase A: ≈ 14 h en el portátil** (más de lo previsto)
- Segundos por época (6 núcleos, pliegue más grande):

  | Ventana | RNN | LSTM | GRU |
  |---|---|---|---|
  | 10 | 0,40 | 0,51 | 0,73 |
  | 20 | 0,76 | 0,77 | 1,21 |
  | 40 | 1,06 | 1,21 | 2,30 |
  | 60 | 1,43 | 1,67 | 3,51 |
  | 120 | 2,89 | 3,14 | 6,87 |
  | 252 | 5,47 | 6,25 | 13,78 |

- **El tiempo está en el propio entrenamiento con ventanas largas**: medir las curvas solo supone un 10-15 % y usar 8 núcleos en vez de 6 no lo acelera. Las ventanas de 120 y 252 días suponen ≈ 70 % del total (≈ 10 h); las de 10 a 60, ≈ 30 % (≈ 4 h).
- Las redes recurrentes en GPU con ventanas largas suelen acelerarse mucho más que en CPU; son las candidatas naturales para la GPU de la universidad.

**Lanzamiento de la fase A: ventanas cortas en el portátil**
- Plan acordado: ventanas de 10 a 60 días en el portátil, de día y con Pablo delante; ventanas de 120 y 252 días, más adelante (GPU de la universidad u otra tanda).
- Prueba con el ordenador delante (inicio 19:05, 6 núcleos, `python scripts/fase_a.py --ventanas 10 20 40 60`): **sin incidencias** (ruido y temperatura normales, el portátil se puede seguir usando). Se deja continuar.
- A los 33 minutos: 194 de 792 entrenamientos de redes. Tiempo medio por entrenamiento: 2,5 s (10 días), 10,6 s (20 días), ≈ 20 s (40 días). Estimación total para las ventanas cortas: ≈ 3,5 h.
- La estimación de «quedan» del lanzador es optimista al principio, porque promedia lo hecho y empieza por las ventanas más rápidas. Mejora posible: estimar con el tiempo medio de cada ventana.
- **Ventanas cortas terminadas en 2,0 h** (792 entrenamientos de redes y 1.584 del lineal, sin duplicados ni vacíos), mucho menos que lo estimado (≈ 3,5 h): la parada temprana corta la mayoría de entrenamientos en 11-26 épocas.
- **Ventanas largas (120 y 252) lanzadas a las 21:09** para dejarlas toda la noche (`--ventanas 120 252`, 396 entrenamientos). Estimación: ≈ 4,5 h.
- Fallo menor detectado: con `--ventanas`, el lanzador contaba como «ya hechos» los entrenamientos de las otras ventanas y mostraba «quedan ≈ 0,0 h». Solo afectaba al aviso, no a los resultados. Corregido para próximas ejecuciones; el proceso en marcha sigue con el aviso erróneo.

**Primeros resultados de la fase A (provisionales: ventanas 10-60, estructura base, una semilla)**
- Notebook 03, sección 2:
  - curva de error según la ventana;
  - mapa de calor de las 36 combinaciones (escala mínima ±5 % para no colorear el ruido);
  - efectos del nivel y del recorte;
  - clasificación provisional;
  - estabilidad por año;
  - modelo lineal.
- **1 semana:** todo entre 0,99 y 1,01. Ni las redes ni el lineal mejoran al ingenuo de forma apreciable; ventana, recorte y nivel no influyen.
- **3 meses:** la mejora más clara. Las mejores combinaciones dan 0,93 de media (LSTM 0,90, GRU 0,91), y la mejora es estable en los cuatro años. Factor decisivo: **sin indicador de nivel** (0,95 frente a 1,01). Las redes superan al lineal (0,95).
- **1 año:** las redes base empeoran al ingenuo un 13-35 %, salvo en 2020. El **lineal mejora al ingenuo un 12-14 %** (0,86-0,88). Con cautela: solo 3 pliegues, 2020 pesa mucho y las redes base memorizan enseguida (mejor época 2-5).
- Hipótesis afectadas (pendientes de confirmar con todas las ventanas y la fase B):
  - **H1** no se cumple por ahora: se mejora a 3 meses y no a 1 semana;
  - **H6** no se cumple en las redes (el nivel las empeora), aunque el lineal lo aprovecha a 1 año.

### 09/11/2026 · Resultados completos de la fase A

**Hecho**
- Ventanas largas (120 y 252 días) terminadas durante la noche: 396 entrenamientos de redes en 4,1 h, sin incidencias.
- **Fase A completa:** 1.188 entrenamientos de redes y 2.376 del modelo lineal, sin duplicados ni vacíos.
- Tiempo medio por entrenamiento con 252 días: GRU 78 s, LSTM 41 s, RNN 40 s (con 10 días: 5, 3 y 3 s).
- Notebook 03, sección 2, regenerado con las 6 ventanas; deja de ser provisional. Nueva tabla: el mejor modelo lineal de cada horizonte, año a año.

**Resultados de la fase A** (validación 2018-2021, estructura base, una semilla; MAE / ingenuo, por debajo de 1 mejora al ingenuo)

| Horizonte | Mejor combinación (media de las 3 redes) | Media redes | Mejor red individual | Mejor lineal |
|---|---|---|---|---|
| 1 semana | 252 días, sin recorte, sin nivel | 0,990 | 0,983 (LSTM, 252 días) | 0,988 (20 días) |
| 3 meses | 60 días, sin recorte, sin nivel | 0,926 | 0,901 (GRU, 40 días) | 0,951 (10 días) |
| 1 año | 120 días, recorte 0,5-99,5, con nivel | 1,124 | 1,074 (RNN, 120 días) | 0,759 (252 días) |

- **1 semana:** todo entre 0,98 y 1,01, en las redes y en el lineal. Ventana, recorte y nivel no influyen: las diferencias (≈ 0,5 %) son ruido.
- **3 meses:** la mejora más clara (6-7 % de media; LSTM y GRU, 9-10 %). Dos candidatas, ambas sin nivel:
  - **60 días sin recorte** (0,926): la mejor, y la LSTM y la GRU mejoran al ingenuo los cuatro años. Pero es frágil: con recorte 1-99 pasa a 1,004.
  - **20 días** (0,933-0,936): da prácticamente lo mismo con los tres recortes, aunque en 2018 apenas mejora al ingenuo.
  - Las separa menos de un 1 %: empate dentro del ruido.
  - Las ventanas de 120 y 252 días no mejoran a las cortas.
- **1 año:** las 36 combinaciones de las redes empeoran al ingenuo (1,12-1,30), y las redes aciertan la dirección solo el 46 % de las veces. **El lineal mejora al ingenuo con todas las ventanas** (0,79-0,90 de media) y llega a 0,76 con 252 días.
- **Qué hace el lineal a 1 año** (comprobado con sus previsiones): **apuesta por la corrección**. Tras una subida fuerte prevé una bajada y tras un desplome, un rebote; sus previsiones van en sentido contrario a la variación del último año. Por año:
  - 2018: prevé una bajada y la hubo (0,81);
  - 2019: no aporta nada (1,02), porque la caída por la COVID era imprevisible;
  - 2020: prevé un rebote fuerte tras el desplome, y lo hubo aún mayor (0,54).

  Casi toda la ventaja viene de 2020. Además, el 0,76 es el mejor de 216 intentos (36 combinaciones × 6 fuerzas de regularización), así que es algo optimista: el test dirá si se sostiene.
- **Otros:**
  - el recorte apenas influye (≤ 2 %);
  - el indicador de nivel empeora a las redes a 3 meses (0,96 sin él frente a 1,01 con él) y a 1 año;
  - las redes base memorizan con todas las ventanas (mejor época media entre la 4 y la 6);
  - la ventana de 252 días multiplica el coste sin mejorar a las redes.

**Hipótesis**
- **H1** no se cumple en validación: se mejora a 3 meses, no a 1 semana. A 1 año, solo el lineal. La comprobación definitiva sigue siendo el test.
- **H6** no se cumple en las redes. La idea de corrección sí funciona a 1 año, pero el lineal la toma sobre todo de la ventana de 252 días, que contiene la misma información que el indicador (cuánto ha subido o bajado el precio en el último año).

**Implicaciones para la fase B**
- A 1 año, el reto es que las redes dejen de empeorar al ingenuo. Las redes pequeñas y muy reguladas del espacio de búsqueda son la ocasión de corregirlo, y el lineal marca el listón.
- A 3 meses hay margen real; a 1 semana es difícil esperar mejoras.

**Preparación de la confirmación con semillas (D19)**
- Commit `2d1bccc` con la fase A completa, la sección 2 del notebook 03 y el diario, subido a GitHub.
- `experimentos.py`:
  - `finalistas()`: las 3 mejores combinaciones de cada horizonte;
  - `ejecutar_confirmacion()`: las repite con otras semillas; es reanudable y prevé el tiempo a partir de lo que tardó cada entrenamiento en la fase A;
  - `decidir()`: la regla D19, escrita y probada **antes** de ver los resultados.
- `scripts/fase_a_semillas.py`, con la opción `--solo-mostrar` para ver las finalistas y el tiempo previsto sin entrenar.
- El paso «entrenar una red y medirla» pasa a una función común para la fase A y la confirmación. Comprobado: la fase A reorganizada da exactamente los mismos números.
- **La semilla 42 es reproducible:** repetida con el nuevo lanzador, da los mismos errores y las mismas épocas que en la fase A, así que no hace falta volver a entrenarla.
- Claves de reanudación más robustas: un número entero guardado como decimal (43.0) se reconoce igual.
- 41 pruebas automáticas, todas correctas (5 nuevas).
- **Finalistas:** 198 entrenamientos, ≈ 1 h en el portátil.

  | Horizonte | Finalistas (ventana · recorte · nivel → fase A) |
  |---|---|
  | 1 semana | 252 · ninguno · sin → 0,990 · 60 · 0,5-99,5 · sin → 0,992 · 120 · 1-99 · sin → 0,993 |
  | 3 meses | 60 · ninguno · sin → 0,926 · 20 · 1-99 · sin → 0,933 · 20 · ninguno · sin → 0,934 |
  | 1 año | 120 · 0,5-99,5 · con → 1,124 · 40 · ninguno · sin → 1,132 · 60 · ninguno · sin → 1,137 |

- **Qué esperamos ver** (apuntado antes de lanzar):
  - el ruido entre semillas será pequeño en la media de las tres redes a 1 semana y a 3 meses (≈ 1 %), mayor en cada red por separado y mucho mayor a 1 año;
  - las finalistas empeorarán algo con las semillas nuevas: parte de su ventaja en la fase A era suerte (al elegir la mejor de 36, se elige también la más afortunada);
  - a 1 semana, las tres empatarán;
  - a 3 meses, se verá si la ventaja de los 60 días es real o si empata con los 20 días (en ese caso ganan los 20 días);
  - a 1 año, ninguna semilla bajará de 1: el fallo de las redes es sistemático, no mala suerte.
- Lo que las semillas **no** resuelven: los años de validación son siempre los mismos. Elegir entre muchas opciones con los mismos años deja algo de optimismo, y para eso está el test, que se usa una sola vez.

- Regla D19 aprobada por Pablo. **Confirmación lanzada a las 13:21** en el portátil (`python scripts/fase_a_semillas.py`, 6 núcleos).
- Notebook 03: nueva sección 3 preparada (puntos por semilla con la zona de empate, regla aplicada, estabilidad de cada red y elección final), probada con los resultados parciales. La tabla de contenidos pasa a 5 secciones (3: cierre de la fase A; 4: fase B; 5: test).

**Resultados de la confirmación con semillas (D19)**
- Terminada en 1,04 h (13:21-14:23): 198 entrenamientos nuevos, sin duplicados ni vacíos; con la semilla 42 de la fase A, 297 en total. La GRU con 252 días tardó 124 s por entrenamiento, más que en la fase A (78 s, de noche).
- **Datos elegidos para cada horizonte** (MAE / ingenuo, media de las 3 redes y las 3 semillas):

  | Horizonte | Elegida | MAE / ingenuo | Ruido | Cómo se decide |
  |---|---|---|---|---|
  | 1 semana | 252 días, sin recorte, sin nivel | 0,992 | 0,002 | Gana con las 3 semillas; las otras quedan fuera del empate por 0,2-0,4 % |
  | 3 meses | 20 días, sin recorte, sin nivel | 0,936 | 0,011 | Las 3 finalistas empatan; gana la ventana más corta y más sencilla, que además tiene la mejor media |
  | 1 año | 120 días, recorte 0,5-99,5, con nivel | 1,114 | 0,033 | Gana con claridad (las otras dos, 1,18) |

- **Lo esperado frente a lo obtenido:**
  - ✓ El azar crece con el horizonte. Al cambiar la semilla, la media de las 3 redes varía un 0,2 % del error del ingenuo a 1 semana (menos de lo previsto), un 1,1 % a 3 meses y un 3,3 % a 1 año; cada red por separado, más (0,4-0,5 %, 1,2-2,4 % y 4,5-5,9 %).
  - ✓ 8 de las 9 finalistas empeoran con las semillas nuevas: parte de su ventaja en la fase A era suerte. El caso más claro, la LSTM con 60 días a 3 meses: 0,902 en la fase A; 0,983 y 0,969 con las semillas nuevas.
  - ✓ A 3 meses, la ventaja de los 60 días era suerte (de 0,926 a 0,95 con las semillas nuevas): empatan y ganan los 20 días.
  - ✓ A 1 año, nada baja de 1 (la mejor red con la mejor semilla, 1,07): el fallo es sistemático.
  - ✗ A 1 semana no hay empate: gana la de 252 días con las 3 semillas, aunque por un margen sin importancia práctica.
- **Año a año, las elegidas** (media de las 3 redes):
  - 1 semana: 0,986-0,997 todos los años; mejora al ingenuo apenas un 1 %.
  - 3 meses: mejora al ingenuo los 4 años (0,98 en 2018, 0,97 en 2019, 0,93 en 2020 y 0,82 en 2021). La RNN es la más regular (0,92-0,96); la GRU empeora algo en 2018 (1,01) y la LSTM, en 2019 (1,06).
  - 1 año: una apuesta (1,08 en 2018, 1,87 en 2019 y 0,55 en 2020).
- **Estabilidad de cada red** (estructura base): la GRU es la más estable a 1 semana y a 3 meses; la RNN, a 1 año, por poco; la LSTM es la que más cambia con la semilla a 3 meses y a 1 año. Con 3 semillas, la medida es aproximada.
- **Indicador de nivel:** que la elegida a 1 año lo lleve es un caso aislado. Con 120 días y los otros dos recortes da parecido con él y sin él, y de media empeora a las redes (1,22 con él frente a 1,18 sin él). H6 no cambia.
- Notebook 03, sección 3 completa: figura por semilla con la zona de empate, regla aplicada, estabilidad de cada red, elección, tabla año a año de las elegidas y lectura.

**Para hablar antes de la fase B**
- A 1 semana, la ventana elegida (252 días) es la más cara: entrenar con ella cuesta 4-5 veces más que con 60 días, y la mejora sobre el ingenuo es de un 1 %. Sería el horizonte más lento de la fase B.

**Diagnóstico antes de la fase B: la tendencia media** (repaso de todo lo observado con Pablo)
- **Memorización:** existe en todos los horizontes y crece con él. En la fase A, el error de train baja un 18 % / 52 % / 64 % (1 semana / 3 meses / 1 año) y el del trozo de parada, solo un 1 % / 7 % / 20 %. La parada temprana evita lo peor, pero incluso la versión temprana de la red ya ha aprendido cosas que no se repiten.
- **Causa de fondo a 1 año:** pocas respuestas independientes (unas 17 entre 2000 y 2017, una por año) para redes de 5.000-19.000 parámetros, y un pasado que no se repite (subida hasta 2008, desplome de 2014, COVID).
- **Tendencia media (hallazgo):** cuando no aprenden nada útil, las redes y el lineal no prevén «sin cambio», como el ingenuo, sino la subida media del train. Es lo primero que aprende una red.
  - A 1 año, esa media es de +11,8 % (pliegue 2018), +6,1 % (2019) y +3,1 % (2020), con la combinación elegida.
  - Un «modelo» que solo prevé esa media da MAE / ingenuo 1,82 / 1,15 / 0,97, y **1,16 los tres juntos**. A 3 meses da 0,986; a 1 semana, 0,997 (notebook 03, sección 4.1).
  - Las redes elegidas apenas mejoran a la media sola a 1 año (1,11 frente a 1,16): su resultado está muy cerca de «proyectar la media». A 3 meses sí la mejoran con claridad (0,936 frente a 0,986, todos los años), aunque parte de su ventaja es la tendencia. A 1 semana, casi toda su pequeña ventaja parecía la tendencia (0,992 frente a 0,997); el experimento D20 lo desmintió.
  - No todo es la tendencia: a 1 año las redes también apuestan por la corrección, y en 2019 les sale peor que a la media sola (1,87 frente a 1,15).
  - Parte del sesgo alcista de la primera prueba venía de aquí.
  - **Corrección:** en la primera estimación dije «≈ 1,3» porque promedié los cocientes de cada año. Juntando los errores en dólares, como en todo el estudio, es 1,16. El año 2018 tiene un error en dólares pequeño y no debe pesar como los demás.
- **Parada temprana a 1 año:** elige la mejor época con unas 3 respuestas independientes (10-12 a 3 meses, más de 100 a 1 semana). Es casi azar; pendiente de decidir para la fase B (por ejemplo, que Optuna busque también el número de épocas).
- **Validación a 1 año:** cada año equivale a uno o dos resultados independientes. Con muchos intentos es fácil elegir uno afortunado; hay que buscar con prudencia y decirlo en las conclusiones.
- **Implicación:** la fase B, al regular más las redes, las acercaría a la media del train, y a 1 año eso podría empeorar en vez de mejorar. → **D20** (experimento sin tendencia, antes de la fase B) e hipótesis **H7**.

**Preparación del experimento sin tendencia (D20)**
- Opción `sin_tendencia` en el entrenamiento (`config.ENTRENAMIENTO`, apagada por defecto) y en `ModeloLineal`. La red guarda la tendencia que se le ha quitado.
- `experimentos.py`:
  - `eleccion()`: reconstruye la combinación elegida de cada horizonte (D19) a partir de los resultados;
  - `ejecutar_tendencia()`: el experimento, reanudable;
  - el bucle de entrenamiento de redes pasa a ser común para la confirmación y este experimento.
- `scripts/tendencia.py`, con `--solo-mostrar` y `--horizontes`.
- Comprobado: con la opción apagada, la fase A se reproduce exactamente (red y lineal), y la confirmación no tiene nada pendiente.
- 44 pruebas automáticas, todas correctas (3 nuevas: el lineal y la red sin tendencia no proyectan la media; la elección junta la fase A y la confirmación).
- Previsto: 99 entrenamientos de redes (≈ 0,8 h en el portátil, sobre todo la ventana de 252 días a 1 semana) y el lineal completo (396 combinaciones × pliegues, unos minutos).
- **Qué esperamos ver** (apuntado antes de lanzar):
  - 1 año: las redes mejoran claramente; ganan en 2018 y 2019 (años de bajada) y pierden en 2020 (rebote).
  - 3 meses: cambio pequeño, dentro del ruido o algo peor (2021, año de subida, se beneficiaba de la tendencia).
  - 1 semana: sin cambio (la tendencia es de un 0,1 % por semana).
  - Lineal a 1 año: mismo patrón por años (mejor en 2018 y 2019, peor en 2020); el resultado conjunto es incierto.
- Mientras corría: la referencia «solo la media» (`experimentos.solo_la_media`) y la regla D20 como función (`adoptar_sin_tendencia`), con su prueba (45 pruebas en total). Notebook 03, sección 4 nueva, probada con los resultados parciales.
- **Lanzado por Pablo a las 18:41** (con ello, regla D20 aprobada). Terminado en 1,23 h: 99 entrenamientos de redes y 2.376 del lineal, sin duplicados ni vacíos.

**Resultados del experimento sin tendencia (D20)** (MAE / ingenuo; redes: media de las 3 redes y las 3 semillas)

| Horizonte | Con tendencia | Sin tendencia | Diferencia | Ruido | Se adopta |
|---|---|---|---|---|---|
| 1 semana | 0,992 | 0,993 | +0,001 | 0,002 | sin tendencia (empate) |
| 3 meses | 0,936 | 0,937 | +0,001 | 0,011 | sin tendencia (empate) |
| 1 año | 1,114 | **1,044** | −0,070 | 0,033 | sin tendencia (mejora) |

- **1 año:** la tendencia explicaba unas tres quintas partes de lo que las redes perdían frente al ingenuo.
  - Mejoran las tres redes (entre 0,06 y 0,08 cada una) y con las tres semillas, aunque con la 44 apenas (1,107 → 1,100).
  - Año a año: 2018 de 1,08 a 0,93 (ya mejor que el ingenuo), 2019 de 1,87 a 1,68, 2020 de 0,55 a 0,59.
  - Siguen un 4 % peor que el ingenuo: queda el problema de fondo para la fase B.
  - Aciertan la dirección más a menudo (del 55 % al 60 %).
  - El azar entre semillas crece (1,01 / 1,03 / 1,10).
- **3 meses:** mismo resultado, pero mejor repartido. Mejora en 2019 (de 0,97 a 0,94) y empeora en 2021, año de subida (de 0,82 a 0,89). **La ventaja de las redes a 3 meses es señal, no tendencia.**
- **1 semana:** sin cambios. Lo dicho en el diagnóstico («a 1 semana, casi toda su pequeña ventaja es la tendencia») **no se confirma**: sin tendencia siguen en 0,993.
- **Lineal** (misma regla → sin tendencia en los tres horizontes):
  - 1 año: su mejor versión pasa de 0,759 a 0,714, pero con otra combinación (120 días, sin recorte, sin nivel, alfa 1, casi sin regularizar) y muy irregular (1,36 en 2018, 0,85 en 2019, 0,42 en 2020). Es la mejor de 216: hay que tomarla con cautela.
  - Con la combinación de antes (252 días, alfa 1.000), de 0,759 a 0,743. La mediana de las 216 versiones, de 0,89 a 0,84.
  - 3 meses: de 0,951 a 0,959; 1 semana: de 0,988 a 0,989 (empates).
- **Lo esperado frente a lo obtenido:**
  - ✓ Las redes cumplen todo lo esperado: mejoran con claridad a 1 año, ganando en 2018 y 2019 y perdiendo en 2020, y apenas cambian a 3 meses y a 1 semana.
  - ✗ El lineal no cumple el patrón: con la misma combinación, en 2018 empeora (de 0,81 a 0,95), porque ya apostaba por una bajada y sin tendencia la exagera.
- **H7 se cumple.** D20 pasa a ✅: todo lo que sigue (fase B y test) se hace sin tendencia.
- Notebook 03, sección 4 completa y ejecutada (la sección 1 vuelve a dar los mismos números).

**Para hablar antes de la fase B**
- **Propuesta (regla D20):** repetir la fase A de 1 año sin tendencia, porque los datos de 1 año se eligieron con tendencia y quitarla cambia mucho el resultado (por ejemplo, el indicador de nivel podía estar compensándola). A 3 meses y a 1 semana el resultado no cambia, así que la elección se mantiene.
- Pasar `sin_tendencia` a activado por defecto al preparar la fase B (la fase A seguirá reproduciéndose indicándolo de forma explícita).
- Parada temprana a 1 año (unas 3 respuestas independientes) y coste de la ventana de 252 días a 1 semana.

**Commit y fase A de 1 año sin tendencia (D21)**
- Commit `52d80ee` (confirmación con semillas y experimento sin tendencia), con el visto bueno de Pablo. Sin subir a GitHub.
- Pablo aprueba repetir la fase A de 1 año sin tendencia → **D21**.
- `ejecutar_fase_a` y `ejecutar_confirmacion` admiten `horizontes` y `sin_tendencia`. Los resultados van a `fase_a_sin_tendencia.csv` y `fase_a_sin_tendencia_semillas.csv`, sin tocar los originales. Scripts con `--horizontes` y `--sin-tendencia`.
- La fase A estima ahora el tiempo restante con lo que tardó cada entrenamiento en la fase A original, si existe (antes era optimista al principio).
- Protección: la confirmación se niega a elegir finalistas si la fase A de esos horizontes no está completa. Así las dos se pueden lanzar encadenadas sin riesgo.
- Comprobado: la fase A original y su confirmación siguen igual (nada pendiente). Prueba de humo de las dos piezas encadenadas en una carpeta aparte. 45 pruebas correctas.
- Previsto: 324 entrenamientos de redes (1,2 h en la fase A original, de noche) y 54 de la confirmación; unas 2 h en total de día.
- **Qué esperamos ver** (apuntado antes de lanzar; la prueba de humo ya dio, con 10 días y sin recorte, 1,02 sin nivel y 1,06 con nivel):
  - todas las combinaciones mejoran frente a la fase A con tendencia;
  - si el indicador de nivel estaba compensando la tendencia, deja de destacar y las finalistas serán sobre todo sin nivel;
  - con la estructura base, la mejor media sigue cerca de 1 (entre 1,00 y 1,05): lo que queda es para la fase B.

- Lanzado por Pablo (las dos piezas encadenadas). Fase A: 324 entrenamientos en 1,26 h; confirmación: 54 en 4 minutos. Sin errores, duplicados ni vacíos.

**Resultados de la fase A de 1 año sin tendencia (D21)** (MAE / ingenuo, media de las 3 redes)
- **Mejoran las 36 combinaciones:** de media, de 1,20 a 1,04 (la que menos, 0,03; la que más, 0,26).
- **El indicador de nivel deja de destacar:** las 11 mejores son sin nivel (1,056 con él frente a 1,022 sin él). La elegida antes (120 días, con nivel) cae al puesto 14 de 36: con tendencia ganaba en parte porque la compensaba.
- El recorte apenas importa (1,03-1,04). Van mejor las ventanas cortas (20 y 40 días: 1,02-1,03) que las de 60 y 252 (1,05-1,06).
- Comprobación: la combinación elegida antes da exactamente los mismos números que en el experimento D20. Las dos tandas son comparables.
- **Confirmación con semillas:**

  | Finalista | Semilla 42 (fase A) | 43 | 44 | Media |
  |---|---|---|---|---|
  | 40 días, sin recorte, sin nivel | 0,973 | 1,102 | 0,981 | 1,019 |
  | 20 días, recorte 1-99, sin nivel | 0,980 | 1,083 | 0,978 | 1,014 |
  | **20 días, recorte 0,5-99,5, sin nivel** | 0,985 | 1,080 | 1,015 | **1,027** |

  - Ruido 0,060, el doble que con tendencia (0,033). Una red sola cambia mucho con la semilla: la LSTM con 40 días da 0,92 con una semilla y 1,35 con otra (2,6 en 2018).
  - La mejor de la fase A pasa de 0,973 a 1,042 con las semillas nuevas: otra vez, parte de la ventaja era suerte.
  - Las tres empatan. Gana la ventana más corta (20 días) y, con la misma ventana, el recorte más suave. La de 1-99 tiene una media algo mejor, pero por 0,013, una quinta parte del ruido.
- **Elección de 1 año (D21): 20 días, recorte 0,5-99,5, sin nivel (1,027).** Frente a la anterior sin tendencia (1,044), rinden igual dentro del azar. Pero la nueva es más sencilla, entrena más rápido y es más regular año a año (1,02 / 1,43 / 0,72 frente a 0,93 / 1,68 / 0,59).
- **Las redes siguen sin mejorar al ingenuo a 1 año.** Sin tendencia, una red que no aprende nada da exactamente 1 (prevé «sin cambio»). Con 1,03, lo que aprenden de media resta en vez de sumar.
- **El lineal, con los mismos datos, da 0,82** (0,75 / 1,04 / 0,67; acierta si sube o baja el 70 % de las veces; las redes, el 54 %). Es la comparación más limpia que tenemos: mismos datos y años, sin tendencia; solo cambia el modelo. Apunta a que el problema de las redes a 1 año no está en los datos, sino en que tienen demasiada capacidad para tan pocas respuestas independientes.
- **Lo esperado frente a lo obtenido:**
  - ✓ Mejoran todas las combinaciones.
  - ✓ El indicador de nivel deja de destacar; las finalistas son todas sin nivel.
  - ✓ La mejor media confirmada queda entre 1,00 y 1,05 (1,014-1,027).
  - ✗ No esperábamos que el azar entre semillas se duplicara sin tendencia.
- **Datos de partida para la fase B**, todos sin tendencia:

  | Horizonte | Datos | MAE / ingenuo | Ruido | Elegidos en |
  |---|---|---|---|---|
  | 1 semana | 252 días, sin recorte, sin nivel | 0,993 | 0,002 | D19 |
  | 3 meses | 20 días, sin recorte, sin nivel | 0,937 | 0,011 | D19 |
  | 1 año | 20 días, recorte 0,5-99,5, sin nivel | 1,027 | 0,060 | D21 |

- Notebook 03, sección 5 nueva: las 36 combinaciones con y sin tendencia, efecto de cada opción, confirmación con semillas, comparación año a año con la elección anterior, el lineal y «solo la media», datos de partida para la fase B y lectura. La fase B pasa a ser la sección 6 y el test, la 7. Ejecutado de principio a fin; las secciones 1 a 4 dan los mismos números.

**Para hablar antes de la fase B**
- **Posible hipótesis H8:** a 1 año, las redes pierden frente al lineal (1,03 frente a 0,82 con los mismos datos) por exceso de capacidad. Con pocas respuestas independientes, una red pequeña o muy regulada debería acercarse al lineal. Se comprobaría en la fase B: si Optuna prefiere a 1 año redes pequeñas y con mucho dropout o L2, y si así se acercan al lineal.
- A 1 año, el azar entre semillas (0,06) es grande frente a las diferencias que buscará la fase B. Puede hacer falta más de una semilla por intento, o confirmar con más semillas al final.
- Siguen pendientes: parada temprana a 1 año, coste de la ventana de 252 días a 1 semana y activar `sin_tendencia` por defecto.

**Pendiente**
- Commit de D21 (código, resultados, notebook 03 y diario), con el visto bueno de Pablo.
- Hablar los puntos de arriba antes de preparar la fase B.
- Fase B (Optuna) sin tendencia, confirmación con semillas y examen final en test.

### 10/11/2026 · Diseño y preparación de la fase B

**Hecho**
- Commit `22f221c` (D21) y subida a GitHub de los dos commits pendientes (`52d80ee` y `22f221c`).
- Repaso con Pablo de los puntos pendientes antes de la fase B; los aprueba todos → **D22** e **H8**:
  - **H8 (capacidad):** el espacio de búsqueda incluye redes pequeñas (desde 8 neuronas: una LSTM de unos 600 parámetros en lugar de 19.000) y muy reguladas (dropout hasta 0,5, L2 hasta 0,01).
  - **Semillas:** a 1 año, cada intento se mide con 3 semillas (con 20 días es barato: 3-6 s por entrenamiento); a 1 semana y a 3 meses, con una, y se confirman las 3 mejores de cada red.
  - **Parada temprana a 1 año:** se deja igual para todos y se anota como limitación. La alternativa (que Optuna busque el número de épocas) complica el entrenamiento y no lo resuelve del todo.
  - **Ventana de 252 días a 1 semana:** se mantiene; se activa la poda y se lanza de noche. Se puede reanudar si no termina.
  - **Sin tendencia por defecto.**
- Cuidado del portátil en los entrenamientos largos (pregunta de Pablo): no es malo para el procesador, que se protege solo si se calienta; lo que más desgasta es la batería. Protección de la batería ya activada al 80 % y modo optimizado (ver Limitaciones).
- **Optuna 5.0.0** añadido con Poetry (`poetry add optuna`). Smart App Control no puso problemas.
- `config.py`:
  - `ENTRENAMIENTO["sin_tendencia"] = True`;
  - datos elegidos de cada horizonte (`DATOS_FASE_B`), intentos, semillas por intento, espacio de búsqueda y poda.
- `experimentos.py`: la fase A y su confirmación indican la tendencia de forma explícita. `resumir` admite resultados sin alfa (fase B).
- `busqueda.py` (nuevo):
  - búsqueda por red y horizonte, poda, confirmación con semillas y regla de elección (`decidir_configuracion`);
  - cada entrenamiento y cada intento se guardan en cuanto terminan (`fase_b.csv`, `fase_b_intentos.csv`, `fase_b_semillas.csv` y sus curvas);
  - al relanzar, los intentos cerrados se cargan en Optuna y el que quedó a medias se repite con los mismos valores, sin volver a entrenar lo guardado.
- `scripts/fase_b.py`, con `--solo-mostrar`, `--horizontes` (en el orden en que se hacen), `--modelos`, `--intentos` e `--hilos`; registro en `fase_b.log`.
- Notebook 03, sección 1: la prueba inicial indica «con tendencia» de forma explícita. Vuelto a ejecutar; da los mismos números.
- **Comprobaciones:**
  - 51 pruebas correctas. Son 6 nuevas: rangos de Optuna, L2, estructura base, regla de elección, búsqueda cortada y reanudada con poda y confirmación, y que `DATOS_FASE_B` coincide con la elección de la fase A.
  - La fase A, con y sin tendencia, se reproduce exactamente (una combinación de 1 año, diferencia 0).
  - Prueba de humo con datos reales (2 intentos de la RNN a 1 año y a 3 meses): el primer intento (estructura base) reproduce exactamente lo ya medido (9 entrenamientos a 1 año y 12 a 3 meses, mismas épocas).
  - La prueba de humo encontró un fallo, ya corregido: al elegir a 1 año, que no tiene confirmación, se juntaba una tabla vacía. La relanzada continuó donde se quedó.
- **Tiempo previsto** (con los tiempos de la fase A, algo optimistas porque corrió de noche; sin contar la poda): 1 año, 1,1 h; 3 meses, 0,6 h; 1 semana, 9,9 h (la GRU, 4,5 h).

**Qué esperamos ver** (apuntado antes de lanzar)
- **1 año:**
  - si H8 es cierta, las mejores configuraciones serán pequeñas o muy reguladas;
  - la mejor de 40 bajará de 1 (entre 0,93 y 0,98), pero parte será suerte: con 3 semillas, el azar de cada intento es de unos ±0,035, y al quedarse con la mejor de 40 se elige también la más afortunada;
  - aun así, seguirá lejos del lineal (0,82).
- **3 meses:** mejora pequeña sobre la estructura base (de 0,937 a 0,91-0,93), y la confirmación con semillas recortará parte de ella.
- **1 semana:** casi nada que ganar (0,985-0,995).
- En cada horizonte, las tres redes quedarán muy cerca entre sí, con diferencias del orden del ruido.
- La poda abandonará alrededor de un tercio de los intentos.

**Pendiente**
- Pablo lanza la fase B: primero 1 año y 3 meses (`python scripts/fase_b.py --horizontes largo medio`, unas 2 h) y, de noche, 1 semana (`--horizontes corto`).
- Al terminar: notebook 03, sección 6 (fase B), H8 y diario.
- Commit de D22 (código, Optuna, pruebas, notebook y diario), con el visto bueno de Pablo.
- Después: examen final en test, robustez con la partición A (D10), control de precios (D15), aplicación y diapositivas.

### 10/11/2026 (noche) · Resultados de la fase B a 1 año y 3 meses

**Hecho**
- Pablo lanzó `python scripts/fase_b.py --horizontes largo medio` (6 hilos). Terminó en 2,54 h sin incidencias: 240 intentos, 1.450 entrenamientos y 72 de confirmación.
- Análisis de `fase_b_intentos.csv`, `fase_b.csv` y `fase_b_semillas.csv`. Para ver qué prevén las redes a 1 año, se reentrenaron la RNN y la GRU elegidas y la RNN base (semilla 42, los 3 años); reproducen exactamente lo guardado.

**Resultados a 1 año** (media de 3 semillas)

| Red | Base (intento 1) | Elegida | Configuración elegida | Parámetros |
|---|---|---|---|---|
| RNN | 1,011 | **0,893** | 75 neuronas × 1 capa · velocidad 0,00025 · lote 128 · dropout 0,21 · L2 5·10⁻⁵ | 6.376 |
| LSTM | 1,006 | **0,882** | 119 × 2 · velocidad 0,00026 · lote 128 · dropout 0,34 · L2 2·10⁻⁵ | 175.288 |
| GRU | 1,063 | **0,893** | 108 × 2 · velocidad 0,00014 · lote 128 · dropout 0,10 · L2 1·10⁻⁴ | 108.649 |
| Lineal (mismos datos) | | 0,820 | | |

- **Lo que más influye es la velocidad de aprendizaje:** cuanto más lenta, mejor (correlación de rangos 0,8 con el error de 2018-2019, en los 120 intentos). El lote grande también ayuda (−0,5). El tamaño apenas influye (−0,2 a −0,3, y a favor de las grandes), y el dropout tampoco.
- Optuna lo encuentra pronto: entre los intentos 11 y 40, las tres redes se concentran en velocidad ≈ 0,0002, lote 128 y con L2. El mejor de los 10 primeros (al azar) daba 0,95-0,98; el de los 30 siguientes, 0,88-0,89.
- **La mejor época de las elegidas es la 1.ª** (en 2018 y 2019; en 2020, entre la 8.ª y la 21.ª): la red apenas se aleja de su punto de partida. Sus previsiones van en la misma dirección que las del lineal (correlación 0,75-0,91), pero son de un tercio a la mitad de grandes: son **prudentes**.
- **Casi toda la mejora está en 2019**, el año en que el Brent bajó y las redes base preveían subidas. Media de las tres redes por año:

  | | 2018 | 2019 | 2020 |
  |---|---|---|---|
  | Base | 1,02 | 1,43 | 0,72 |
  | Elegidas | 1,01 | 1,10 | 0,69 |
  | Lineal | 0,75 | 1,04 | 0,67 |

- Las tres redes empatan dentro del ruido (0,015 / 0,023 / 0,039).
- **Cautela:** son 3 años de validación y la mejor de 40 intentos. La concordancia entre semillas a lo largo de los intentos es moderada (correlación 0,45-0,59), así que parte de la ventaja es suerte. Lo dirá el test.

**Resultados a 3 meses** (media de 3 semillas)

| Red | Base | Mejor de la búsqueda | Elegida (D23) |
|---|---|---|---|
| RNN | 0,943 | 0,943 (intento 9) | **base**: empatan y tiene menos parámetros (4.737) |
| LSTM | 0,946 | 0,943 (intento 27) | **intento 27**: 53 neuronas × 1 capa, 13.198 parámetros |
| GRU | **0,922** | 0,937 (intento 33) | **base** (14.081 parámetros) |
| Lineal | | 0,972 | |

- **La búsqueda no mejora la base.** Las 3 finalistas de cada red ganaron la primera ronda con suerte. Con la semilla 42 sacaron de media 0,935 (RNN), 0,934 (LSTM) y 0,896 (GRU); con la 43 y la 44, 0,954, 0,954 y 0,959.
- **Ningún valor influye en el error** (todas las correlaciones por debajo de 0,25): cualquier configuración razonable rinde igual. A 3 meses lo que importaba eran los datos (fase A).
- Las redes siguen por delante del lineal (0,92-0,94 frente a 0,97).

**Frente a lo esperado** (apuntado antes de lanzar)
- **1 año:** mejor de lo esperado (0,88-0,89 frente a 0,93-0,98) y, como se esperaba, lejos del lineal. No ganan redes pequeñas, sino lentas: H8 se cumple solo en parte.
- **3 meses:** ni siquiera la pequeña mejora esperada.
- **Las tres redes, muy cerca entre sí:** se cumple.
- **Poda:** 28 % de los intentos. A 1 año, 8 de 120, porque Optuna ya buscaba en la zona buena; a 3 meses, 59 de 120.
- **Tiempo:** 2,54 h frente a 1,6 h previstas (×1,6). La previsión se basa en la estructura base, y la búsqueda prueba redes más grandes, lotes más pequeños y velocidades más lentas. A 1 semana, en lugar de 9,9 h, serían unas 15 h.

**Problemas y soluciones**
- A 3 meses, la estructura base no entraba en la final. Con la semilla 42 la GRU base quedó 4.ª (0,912) y se quedó fuera, aunque con 3 semillas era la mejor (0,922 frente a 0,937). → **D23**: la base siempre es finalista.
  - `finalistas_b` la añade si no está entre las 3 mejores, y la previsión de tiempo cuenta 4 finalistas.
  - Prueba nueva: 52 en total, todas correctas.
  - A 1 año no cambia la elección.

- 1 semana: con 40 intentos tardaría unas 15 h para una ganancia probablemente mínima. Opciones habladas con Pablo: 20 intentos, 40 o sin búsqueda. → **D24**: 20 intentos.
  - `INTENTOS_FASE_B` pasa a ser por horizonte (20 / 40 / 40); la elección y el script lo leen de ahí, y `--intentos` sigue sirviendo para cambiarlo.
  - Plan con `--solo-mostrar`: 6,0 h previstas a 1 semana; con el desfase observado y la poda, unas 8-9 h.

**Decisiones**
- **D23** y **D24** (Resumen vivo). H8, actualizada.

**Pendiente**
- Pablo lanza de noche `python scripts/fase_b.py --horizontes medio corto`:
  - primero, a 3 meses, solo repite la base con las semillas 43 y 44 (24 entrenamientos, un par de minutos); debe dar exactamente lo calculado arriba, porque la base reproduce los resultados anteriores;
  - después, la búsqueda a 1 semana con 20 intentos.
- Notebook 03, sección 6 (fase B). Commit de D22, D23 y D24, con el visto bueno de Pablo.
- Después: examen final en test, robustez con la partición A (D10), control de precios (D15), aplicación y diapositivas.
