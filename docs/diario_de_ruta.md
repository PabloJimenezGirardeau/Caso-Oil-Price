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
| D16 | 08/11/2026 | **Búsqueda de la mejor configuración de cada red en dos fases.** Fase A (común): las 18 combinaciones de ventana × recorte × nivel con una estructura base, en las 3 redes y los 4 pliegues; se elige la mejor de media. Fase B (por red): **Optuna** con el mismo espacio y **40 intentos por red** (neuronas, capas, dropout, velocidad de aprendizaje en rango continuo 0,0001-0,003, regularización L2, tamaño de lote). Fijo para las tres: Adam, Huber, parada temprana con un trozo final del train (guarda la mejor versión), reducción automática de la velocidad, recorte de gradientes. Criterio fijado de antemano: error / error del ingenuo, promediado en horizontes y pliegues; las 3 mejores configuraciones se confirman con 3 semillas; empate → la de menos parámetros. Curvas de aprendizaje de las ganadoras | El enunciado pide un presupuesto de ajuste similar, no la misma configuración: cada red compite con su mejor versión. Optuna explora mejor que una rejilla con el mismo número de intentos y dice qué parámetros importan | ✅ | Diario 08/11 |
| D17 | 08/11/2026 | **Modelo lineal (Ridge) como referencia extra** en la comparativa, con las mismas fichas y el mismo criterio; su regularización se elige en los mismos pliegues de validación. Se prescinde de él si resultara costoso | Peldaño intermedio entre el ingenuo y las redes: responde a «¿hacía falta una red neuronal?». No lo pide el enunciado; suma credibilidad | ✅ | Diario 08/11 |
| D18 | 08/11/2026 | **Una red por horizonte**: cada tipo de red (RNN, LSTM, GRU) se entrena y se ajusta por separado para 5, 63 y 252 sesiones, es decir, 9 modelos. El presupuesto de ajuste de D16 (fase B) se aplica a cada par red-horizonte | El enunciado no lo impide. La prueba inicial mostró que el largo plazo se comporta muy distinto (memoriza y proyecta tendencias): separado, no contamina al corto y medio plazo, y cada horizonte puede tener su propia configuración | ✅ | Diario 08/11 |

### Hipótesis abiertas

| ID | Hipótesis | Cómo se comprobará | Estado |
|---|---|---|---|
| H1 | Las redes mejorarán algo al ingenuo a 5 días, pero no a 63 ni a 252 | Tabla comparativa en test | abierta · en validación (fase A) **no se cumple**: se mejora a 63 días y no a 5 |
| H2 | La variación de ayer del WTI anticipa el Brent de hoy (correlación ≈ 0,17), probablemente porque EE. UU. cierra después que Londres | Comparar el modelo con y sin WTI a 5 días | abierta |
| H3 | El modelo aportará más en la anchura del intervalo (riesgo) que en la dirección del precio | Cobertura y anchura de los intervalos frente a los empíricos | abierta |
| H4 | Predecir variaciones funciona mejor que predecir niveles; una red entrenada con precios tiende a copiar el precio de ayer | Experimento de control al final (D15) | abierta |
| H5 | Las conclusiones (red ganadora y horizontes en los que aporta) no dependen de la partición elegida | Prueba de robustez con la partición A (D10) | abierta |
| H6 | El indicador de nivel (precio frente a su media anual) mejora sobre todo a 63 y 252 días, porque los precios muy altos o muy bajos tienden a corregir | Estudio con y sin el indicador, en validación | **no se cumple en las redes** (el indicador las empeora). La corrección sí existe a 252 días, pero el lineal la aprovecha sobre todo con la ventana de 252 días (Diario 09/11) |

### Limitaciones y problemas conocidos

- El README del repo oficial del curso está desactualizado: el enunciado está en `docs/assignment/ENUNCIADO.pdf` (no en `docs/caso_uso_petroleo.pdf`) y el script es `scripts/download_data.py` (no `descarga_datos_petroleo.py`).
- La cesta de la OPEP (ORB) no está en el dataset: no está en FRED y el script no la descarga.
- La EIA publica el Brent con unos días de retraso, y el script rellena esos días con el último valor.
- Smart App Control (Windows) puede bloquear versiones recién publicadas de librerías con DLL.
- El EDA consulta FRED para identificar los días de cotización (sin conexión usa una regla aproximada).
- La causa del pico de 2026 (138,21 $, 07/04/2026) está sin documentar.
- Equipo de trabajo: Samsung Galaxy Book6 (Intel Core Ultra 7 355, gráfica integrada, 16 GB), **sin GPU NVIDIA**. El problema es pequeño y en CPU se estima entre 30 s y 2 min por entrenamiento.
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

**Pendiente**
- Elegir la combinación de datos de cada horizonte (D6/D16), con Pablo: confirmar las mejores con más semillas para medir el ruido y aplicar «empate → ventana más corta».
- Fase B (Optuna), confirmación con semillas y examen final en test.
