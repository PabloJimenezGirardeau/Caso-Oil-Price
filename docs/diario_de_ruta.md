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
| D15 | 06/11/2026 | **Experimento de control para H4, al final:** la red ganadora, con su mejor configuración, entrenada también para predecir el **precio** en lugar de la variación. Se compara su error con el del ingenuo y el de nuestra red, se dibuja el «espejismo» (línea que sigue al precio con un día de retraso) y se comprueba si su predicción se parece más al precio real o al de ayer | Versión mínima: pocos entrenamientos, código reutilizado. Aporta evidencia para H4 y una figura muy clara para la presentación, sin multiplicar el estudio **Resultado (13/11):** con precios, la RNN se equivoca un 54 % más que el ingenuo a 1 semana (1,544) y un 3 % más a 3 meses (1,028), frente a 0,993 y 0,938 con variaciones; a 1 semana parece acertar (correlación de niveles 0,95). H4 se cumple | ✅ | Diario 06/11 y 13/11, `control_precios.py`, notebook 03 §13.5 |
| D16 | 08/11/2026 | **Búsqueda de la mejor configuración de cada red en dos fases.** Fase A (común): las 18 combinaciones de ventana × recorte × nivel con una estructura base, en las 3 redes y los 4 pliegues; se elige la mejor de media. Fase B (por red): **Optuna** con el mismo espacio y **40 intentos por red** (neuronas, capas, dropout, velocidad de aprendizaje en rango continuo 0,0001-0,003, regularización L2, tamaño de lote). Fijo para las tres: Adam, Huber, parada temprana con un trozo final del train (guarda la mejor versión), reducción automática de la velocidad, recorte de gradientes. Criterio fijado de antemano: error / error del ingenuo, promediado en horizontes y pliegues; las 3 mejores configuraciones se confirman con 3 semillas; empate → la de menos parámetros. Curvas de aprendizaje de las ganadoras | El enunciado pide un presupuesto de ajuste similar, no la misma configuración: cada red compite con su mejor versión. Optuna explora mejor que una rejilla con el mismo número de intentos y dice qué parámetros importan | ✅ (la fase B se concreta en D22) | Diario 08/11 |
| D17 | 08/11/2026 | **Modelo lineal (Ridge) como referencia extra** en la comparativa, con las mismas fichas y el mismo criterio; su regularización se elige en los mismos pliegues de validación. Se prescinde de él si resultara costoso | Peldaño intermedio entre el ingenuo y las redes: responde a «¿hacía falta una red neuronal?». No lo pide el enunciado; suma credibilidad | ✅ | Diario 08/11 |
| D18 | 08/11/2026 | **Una red por horizonte**: cada tipo de red (RNN, LSTM, GRU) se entrena y se ajusta por separado para 5, 63 y 252 sesiones, es decir, 9 modelos. El presupuesto de ajuste de D16 (fase B) se aplica a cada par red-horizonte | El enunciado no lo impide. La prueba inicial mostró que el largo plazo se comporta muy distinto (memoriza y proyecta tendencias): separado, no contamina al corto y medio plazo, y cada horizonte puede tener su propia configuración | ✅ | Diario 08/11 |
| D19 | 09/11/2026 | **Elección de los datos de cada horizonte (cierre de la fase A).** Las 3 mejores combinaciones de cada horizonte (media de las 3 redes) se repiten con 2 semillas más (43 y 44; la 42 ya está en la fase A) y se toma la media de las 3 semillas. **Ruido:** desviación típica entre semillas (media de las finalistas del horizonte). Empatan con la mejor las finalistas a menos de un ruido de ella. Entre las empatadas gana la ventana más corta (D6) y, con la misma ventana, la más sencilla (menos recorte, sin nivel). El lineal no se repite porque no tiene azar | Con una sola semilla, muchas diferencias de la fase A son menores que el azar del propio entrenamiento. La regla se fija antes de ver los resultados para no elegir a conveniencia | ✅ | `experimentos.decidir`, Diario 09/11 |
| D20 | 09/11/2026 | **Experimento sin tendencia, antes de la fase B.** La combinación elegida de cada horizonte (D19) se repite con las 3 semillas **sin la subida media del train**: la red aprende la variación respecto a esa media y, para el futuro, supone tendencia cero, como el ingenuo. El lineal se repite igual (sin término fijo), con todas las combinaciones y fuerzas de regularización. **Regla, fijada antes de ver los resultados:** en cada horizonte se adopta «sin tendencia» si no empeora más de un ruido (el de D19: 0,002 / 0,011 / 0,033) frente a «con tendencia», comparando la media de las 3 redes y las 3 semillas; si empeora más, se mantiene la tendencia. El lineal sigue la misma regla con su mejor versión de cada variante. Si se adopta a 3 meses o a 1 año, se propone repetir la fase A de ese horizonte sin tendencia antes de la fase B | Un modelo que no aprende nada útil proyecta la subida media del train, y a 1 año eso solo ya cuesta 1,16 veces el error del ingenuo (las redes elegidas, 1,11). Con unos 14 años de datos esa media no es fiable (margen de unos ±9 puntos), y la fase B, al regular más las redes, las acercaría a ella. Tendencia cero es lo que supone el ingenuo y lo habitual con precios de mercado; en caso de empate se prefiere por prudente. **Resultado: se adopta sin tendencia en los tres horizontes** (a 1 año, de 1,114 a 1,044; empate a 1 semana y a 3 meses) | ✅ | Diario 09/11, `scripts/tendencia.py`, notebook 03 §4 |
| D21 | 09/11/2026 | **Fase A de 1 año, repetida sin tendencia.** Las 36 combinaciones de 1 año con las 3 redes y la semilla 42, sin tendencia; las 3 mejores se repiten con las semillas 43 y 44 y se elige con la regla D19. Sustituye a la elección de 1 año de D19. A 1 semana y a 3 meses se mantiene la elección de D19, porque sin tendencia el resultado no cambia. El lineal no se repite (sin tendencia ya está completo, D20) | Los datos de 1 año se eligieron con tendencia, y quitarla cambia el resultado en 0,07; el indicador de nivel, por ejemplo, podía estar compensando la tendencia. **Resultado: a 1 año, 20 días, recorte 0,5-99,5, sin nivel (1,027)**, en lugar de 120 días con nivel (1,044 sin tendencia). Rinden igual dentro del azar, pero la nueva es más sencilla, más rápida y más regular por años | ✅ | Diario 09/11, `scripts/fase_a.py --sin-tendencia`, notebook 03 §5 |
| D22 | 10/11/2026 | **Diseño de la fase B** (concreta D16). Por horizonte y red (D18), con los datos de D19 y D21 y **sin tendencia, que pasa a ser lo normal en el entrenamiento** (la fase A original lo desactiva de forma explícita). **40 intentos de Optuna por red**: el primero, la estructura base; los 10 primeros, al azar e iguales para las tres redes; después, Optuna propone cerca de los que mejor van. **Espacio, igual para todas:** neuronas 8-128, 1 o 2 capas, dropout 0-0,5, velocidad de aprendizaje 0,0001-0,003, L2 no o 0,000001-0,01, lote 32, 64 o 128. **Puntuación:** MAE / ingenuo juntando los pliegues; a 1 año, media de 3 semillas por intento; a 1 semana y a 3 meses, 1 semilla, y las 3 mejores de cada red se repiten con las semillas 43 y 44. **Poda:** desde el 2.º pliegue y a partir del 11.º intento, se abandona el intento que va peor que la mediana de los anteriores en ese punto. **Elección:** la mejor media de las 3 semillas; las que quedan a menos de un ruido empatan y gana la de menos parámetros. Sin cambios: parada temprana (limitación a 1 año) y ventana de 252 días a 1 semana | Mismas condiciones y presupuesto para las tres redes, como pide el enunciado. El espacio incluye redes pequeñas y muy reguladas para comprobar H8. A 1 año el azar entre semillas (0,06) es tan grande que, con una sola, la búsqueda premiaría al más afortunado. La poda ahorra tiempo sin cambiar el criterio. Cambiar la ventana de 1 semana después de ver los resultados rompería la regla D19 | ✅ (finalistas: D23; a 1 semana, 20 intentos: D24; ampliación: D25) | `config.py`, `busqueda.py`, `scripts/fase_b.py`, Diario 10/11 |
| D23 | 10/11/2026 | **La estructura base siempre entra en la final de la fase B.** Las finalistas de cada red son las 3 mejores de la búsqueda y, si no está entre ellas, el intento 1 (la estructura base); todas se miden con las semillas 42, 43 y 44 y se elige con la regla de D22 | A 3 meses, con una semilla por intento, las 3 mejores de cada red ganaron la primera ronda con suerte (la GRU, 0,89-0,90 con la semilla 42 y 0,96 con la 43 y la 44), y la base, mejor con 3 semillas (0,922 frente a 0,937), se quedaba fuera. La pregunta de la fase B es si hay algo mejor que la base, y para responderla la base tiene que competir en igualdad. No puede empeorar el resultado: solo evita quedarse con una configuración afortunada. **Resultado:** a 3 meses, la RNN y la GRU se quedan con la base; a 1 año no cambia nada | ✅ | `busqueda.finalistas_b`, Diario 10/11 (noche) |
| D24 | 10/11/2026 | **A 1 semana, 20 intentos por red en lugar de 40**: los 10 primeros al azar (iguales para las tres redes) y 10 de Optuna. Confirmación y elección como a 3 meses, con D23 | Con la ventana de 252 días, 40 intentos tardarían unas 15 h: la previsión de D22 se quedó corta (×1,6). Hay poco que ganar: a 3 meses la búsqueda no mejoró la base, y a 1 semana la fase A dio 0,98-1,01 en todo. El azar entre semillas a 1 semana es muy pequeño (0,002), así que con una semilla por intento la comparación es fiable. Las tres redes mantienen el mismo presupuesto. **Resultado:** 15,4 h; la búsqueda no mejora la base (elegidas 0,991-0,994 frente a 0,988-0,997), como se esperaba | ✅ | `config.INTENTOS_FASE_B`, Diario 10/11 (noche) y 11/11 |
| D25 | 10/11/2026 | **Ampliación de la búsqueda:** si la configuración elegida de una red (tras la confirmación) está en el último cuarto de sus intentos, esa red recibe 20 intentos más, una sola vez. Igual en los tres horizontes y las tres redes | Una elegida tardía indica que Optuna seguía encontrando mejoras: a 1 año, la LSTM pasó de 0,930 (tras 30 intentos) a 0,882 (intento 37). Se mira la elegida y no la mejor de la primera ronda, porque a 1 semana y a 3 meses esa es en parte suerte. Una sola vez, para acotar el tiempo. Con 20 intentos a 1 año, la RNN y la LSTM se habrían quedado en 0,95-0,96. **Aplicación:** 1 año, la LSTM pasa de 40 a 60 intentos (RNN 28 y GRU 20, no); 3 meses, ninguna (elegidas 1, 27 y 1); 1 semana, ninguna (elegidas 11, 8 y 15 de 20). **Resultado a 1 año:** la mejor nueva da 0,881 (intento 45), empatada con la 37 (0,882), que se mantiene por tener menos parámetros. La búsqueda ya estaba estabilizada | ✅ | `scripts/fase_b.py --intentos`, Diario 10/11 (noche) |
| D26 | 11/11/2026 | **El examen final en test se aplaza:** antes, seguir trabajando para mejorar las redes. La fase B queda cerrada como referencia de lo que da ajustar la configuración | Tras la fase B, las redes siguen lejos del objetivo: no aportan a 1 semana (0,99), mejoran un 6-8 % al ingenuo a 3 meses y a 1 año van por detrás del lineal (0,88-0,89 frente a 0,82). El test se usa una sola vez (D7), así que solo tiene sentido con la versión final. Decisión de Pablo | ✅ | Diario 11/11 |
| D27 | 11/11/2026 | **Estabilidad: promedio de semillas.** Las 9 configuraciones elegidas en la fase B, sin volver a elegir nada, se entrenan con 10 semillas (42-51) y se guardan sus previsiones. Se mide el error de una red suelta frente al promedio de 2, 3, 5 y 10 semillas, y la estabilidad: cuánto cambian la nota y las previsiones entre grupos de semillas distintos. El promedio es la media de los precios que prevé cada semilla. **Regla, fijada antes de ver los resultados:** se adopta el promedio de 5 semillas, igual para las tres redes; la curva de 1 a 10 solo describe el efecto | La semilla (hasta 0,04 a 1 año) y la época de parada, que es medio azar, hacen que cada entrenamiento salga distinto. Así cuesta saber si una mejora es real, y en la aplicación la previsión cambiaría al reentrenar. Promediar no puede empeorar el error (su MAE nunca supera la media del de sus semillas) y no elige nada, así que no añade riesgo de sobreajustar la validación. Además, las semillas 45-51 no se usaron para elegir: dan una estimación más honesta del error de las elegidas. **Resultado:** se adopta el promedio de 5. Mejora poco el error (0,001-0,009), pero a 3 meses reduce a la mitad cuánto cambia la previsión de unas semillas a otras. Con las semillas nuevas, la fase B resulta optimista: 0,03-0,07 peor a 1 año y hasta 0,02 a 3 meses. Notas de referencia desde ahora (promedio de 5): 1 semana 0,991-0,993; 3 meses 0,924-0,950; 1 año 0,906-0,937 (lineal 0,820) | ✅ | `estabilidad.py`, `scripts/estabilidad.py`, Diario 11/11 (tarde) y 12/11, notebook 03 §7 |
| D28 | 12/11/2026 | **Combinación de red y lineal.** La previsión combinada es la media, a partes iguales, del precio que prevé la red (promedio de 5 semillas, D27) y del que prevé el lineal de referencia (sin tendencia, mismos datos, su mejor regularización). Se calcula con las previsiones ya guardadas, sin entrenar, solo en validación. **Regla, fijada antes de calcular:** en cada horizonte, con la media de las tres redes, se adopta la combinación si mejora a la mejor de las dos opciones por separado (red sola o lineal) en más del azar que queda con 5 semillas (D27); si empata, se queda la opción sola, por sencilla. La curva con otros pesos (0; 0,25; 0,5; 0,75; 1) es solo descriptiva | A 1 año el lineal es mejor que las redes, y a 3 meses al revés, pero cada uno falla en años distintos (el lineal en 2021, las redes en 2019). Combinar es la forma más sencilla de aprovechar los dos. Mitad y mitad no se elige con la validación, así que no añade riesgo de sobreajustarla (problema 5), y el error de la mezcla nunca supera la media de los errores de las dos. **Resultado: no se adopta en ningún horizonte.** 1 semana, empate (0,990 frente a 0,992 de la red sola; azar 0,003); 3 meses, algo peor que la red sola (0,945 frente a 0,938); 1 año, peor que el lineal (0,851 frente a 0,820). A 1 año las redes son una copia en pequeño del lineal: misma dirección (correlación 0,94-0,95) y la mitad o dos tercios de su tamaño | ✅ | `combinacion.py`, Diario 12/11 (tarde), notebook 03 §8 |
| D29 | 12/11/2026 | **Validación hacia atrás (2010-2017).** Las configuraciones elegidas en la fase B, sin volver a elegir nada (promedio de 5 semillas, 42-46) y el lineal de referencia se evalúan en cada año de 2010 a 2017, entrenando solo con lo anterior. No se usa nada posterior al 31/12/2017. 3 meses y 1 año. **Criterio, fijado antes de calcular:** la ventaja a 3 meses es real si la media de las tres redes gana al ingenuo en al menos 9 de los 12 años (2010-2021) y queda por debajo de 1 con los años juntos; dudosa con 7-8; no se sostiene con 6 o menos (1 año: 8 de 10) | La validación tiene 4 años (3 a 1 año), se ha usado muchas veces para elegir y puede ser favorable a la señal de los modelos (Diario 12/11, noche: en 2006-2017 la regla de la volatilidad no gana al ingenuo a 3 meses). Ocho años que nunca se usaron para elegir dicen, sin tocar el test, si la ventaja es real. No elige nada. **Resultado:** 3 meses, **dudosa**: gana 7 de 12 años, 1,023 con los 12 juntos y 1,073 en 2010-2017 (0,933 en 2018-2021); 1 año, **no se sostiene**: 4 de 10, tanto las redes como el lineal. La validación era un periodo favorable | ✅ | `hacia_atras.py`, Diario 12/11 (noche), notebook 03 §10 |
| D30 | 12/11/2026 | **Rango de incertidumbre del 80 %.** Se comparan tres rangos, ajustados solo con errores ya conocidos al empezar cada año (previsiones fuera de muestra de 2010-2021): el **rango ingenuo** (percentiles 10-90 de las variaciones pasadas, alrededor del precio de hoy; la referencia), un rango fijo alrededor de la red y **A, el rango según la volatilidad** (D8: errores pasados divididos por la volatilidad de 21 días y multiplicados por la de hoy). Medidas: cobertura, anchura y la puntuación de intervalos (α = 0,2), por años y por tercios de volatilidad. **Regla, fijada antes de calcular:** en cada horizonte, con la media de las tres redes, gana el de mejor nota entre los que aciertan el 75-85 % en total y al menos el 70 % en cada tercio de volatilidad; si gana el ingenuo, la aplicación usa ese y lo dice. El 50 % y el 95 %, solo como información | El enunciado pide un rango para cada previsión. Si el precio no se puede prever (D29), lo útil es decir cuánto puede moverse, y la volatilidad sí se puede prever (H3). Ajustar solo con lo ya conocido evita mirar el futuro, y el rango ingenuo dice si el nuestro aporta algo **Resultado:** a 3 meses y a 1 año se adopta **A3, el rango centrado** (simétrico alrededor de la previsión, con la memoria aprendida de los días nerviosos y sin estrecharse por debajo de la volatilidad normal). A 3 meses cumple la regla (79 %, nota 0,873); a 1 año tiene la mejor nota (0,706), pero acierta el 71 % y se presenta como orientativo. A 1 semana gana **A2, el rango según la volatilidad con memoria** (82 %, nota 0,871): allí la calma sí dura, y el suelo de A3 lo deja demasiado ancho. Las redes que dan el rango (B) no se adoptan | ✅ | `incertidumbre.py`, `rango_redes.py`, Diario 12/11 (noche) y 13/11, notebook 03 §12 |
| D31 | 12/11/2026 | **Reentrenar las redes con todo el entrenamiento.** Sin trozo de parada temprana y con un número fijo de épocas: la mediana de sus mejores épocas en la estabilidad (3 meses: RNN 7, LSTM 4, GRU 6; 1 año: 1). Se evalúa en 2010-2021. **Regla, fijada antes de calcular:** sustituye a la versión actual si, con todos los años, la media de las tres redes mejora la nota con los años juntos y gana al ingenuo en al menos tantos años | Hasta ahora la red no aprende de los últimos años del entrenamiento (15 % de parada más la purga): para prever 2020 a 1 año, aprende con fichas hasta mediados de 2015, y el lineal con todo. Es la única objeción que podría cambiar la conclusión, y afecta al modelo final de la aplicación. **Resultado:** se adopta a 1 año (de 0,984 a 0,956; gana 6 de 10 años en lugar de 4; el veredicto pasa a «dudosa»), y no a 3 meses (empeora de 1,023 a 1,048) | ✅ | Diario 12/11 (noche) y 13/11 |
| D32 | 13/11/2026 | **El centro del rango.** Con el rango elegido en cada horizonte (A2 a 1 semana; A3 a 3 meses y a 1 año), se compara el rango centrado en la previsión de las redes con el mismo centrado en el precio de hoy. **Regla, fijada antes de calcular:** se mantiene el centro de las redes solo si mejora la nota al menos un 1 % con los años juntos y en más de la mitad de los años; si no, el precio de hoy (salvo que así deje de cumplir la regla de D30) | Las redes no ganan al ingenuo (D29), y el centro de un rango debe ser la mejor previsión disponible; en empate, lo más sencillo. **Resultado:** gana el precio de hoy en los tres horizontes (las redes empeoran la nota un 0,2 %, un 2,6 % y un 1,3 %). Notas finales frente al rango ingenuo: 0,870, 0,851 y 0,716 | ✅ | `incertidumbre.py`, Diario 13/11, notebook 03 §12.6 |
| D33 | 13/11/2026 | **Protocolo del examen final en test**, fijado antes de tocarlo: se congela todo; cada red se entrena una vez con todo hasta el 31/12/2021 y prevé 2022-3/11/2026 (D7); se miden la nota, Diebold-Mariano y la cobertura del rango, sin contar años ganados; conclusiones fijadas («sin evidencia de ventaja», «ventaja posible, no confirmada», «peor que el ingenuo»). Red de la aplicación, elegida antes: la mejor de cada horizonte en 2010-2021 (LSTM a 1 semana, RNN a 3 meses y a 1 año) | Elegir o ajustar después de ver el test lo invalidaría; con 4-5 años, contar años ganados no sirve (controles) | ✅ aprobado, pendiente de ejecutar | Diario 13/11 |
| D34 | 13/11/2026 | **Previsión del 10/11, después del test:** desde el último dato de la foto (3/11), con las redes del test y con las finales (reentrenadas con todo hasta el 3/11), guardada con commit antes de descargar datos nuevos. La actualización automática del CSV se descarta | Propuesta del profesor: ver el rendimiento con datos que nadie ha visto. Un solo dato: demostración, no evaluación | pendiente | Diario 13/11 |
| D35 | 14/11/2026 | **Web del proyecto** (GitHub Pages, carpeta `web/`): estática, lee los JSON que genera `scripts/exportar_web.py` a partir de `resultados/`, con las mismas funciones que el notebook 03. Lo que no existe se enseña como pendiente (examen final, previsión del 10/11, previsión de cada red). El rango de hoy es **provisional**: el elegido en cada plazo, centrado en el precio de hoy, ajustado solo con lo conocido antes del 1/1/2022 | Presentar el proyecto a un público de inversores sin inventar ninguna cifra. El rango provisional permite enseñar el panel sin tocar el test: no usa ninguna respuesta de 2022-2026, solo la volatilidad del 3/11/2026, que es una entrada | ✅ hecha; provisional hasta D33 y D34 | `scripts/exportar_web.py`, `web/README.md`, Diario 14/11 |

### Hipótesis abiertas

| ID | Hipótesis | Cómo se comprobará | Estado |
|---|---|---|---|
| H1 | Las redes mejorarán algo al ingenuo a 5 días, pero no a 63 ni a 252 | Tabla comparativa en test | abierta · en validación (fase A, confirmada con semillas) **no se cumple**: se mejora a 63 días (≈ 6 %) y apenas a 5 (≈ 1 %). Tras la fase B, igual: ≈ 1 % a 5 días, 6-8 % a 63 y 11-12 % a 252 (el lineal, 18 %) (Diario 11/11). Con el promedio de 5 semillas (D27): ≈ 1 % a 5 días, 5-8 % a 63 y 6-9 % a 252 (Diario 12/11). **Con 12 años (D29), ningún horizonte mejora al ingenuo de forma fiable:** a 63 días, dudosa (7 de 12 años, 1,023 con los años juntos); a 252, no se sostiene (4 de 10) |
| H2 | La variación de ayer del WTI anticipa el Brent de hoy (correlación ≈ 0,17), probablemente porque EE. UU. cierra después que Londres | Comparar el modelo con y sin WTI a 5 días | **no se cumple** a 1 semana: sin el WTI, el lineal queda igual (0,9984 frente a 0,9987, empeora solo en 4 de 12 años), y la relación de partida (0,22 hasta 2017) desaparece en 2018-2021 (−0,04) (Diario 13/11) |
| H3 | El modelo aportará más en la anchura del intervalo (riesgo) que en la dirección del precio | Cobertura y anchura de los intervalos frente a los empíricos | **se cumple en parte** (D30, D32): el rango elegido, centrado en el precio de hoy, mejora al rango ingenuo un 13 % a 1 semana, un 15 % a 3 meses y un 28 % a 1 año, sobre todo en las tormentas; la dirección no se mejora de forma fiable (D29) |
| H4 | Predecir variaciones funciona mejor que predecir niveles; una red entrenada con precios tiende a copiar el precio de ayer | Experimento de control al final (D15) | **se cumple**: con precios, la RNN da 1,544 a 1 semana y 1,028 a 3 meses (con variaciones, 0,993 y 0,938); a 1 semana parece acertar (correlación de niveles 0,95) y está más cerca del precio de hoy que del futuro. A 3 meses, además, tira hacia el precio típico del train (Diario 13/11) |
| H5 | Las conclusiones (red ganadora y horizontes en los que aporta) no dependen de la partición elegida | Prueba de robustez con la partición A (D10) | abierta |
| H6 | El indicador de nivel (precio frente a su media anual) mejora sobre todo a 63 y 252 días, porque los precios muy altos o muy bajos tienden a corregir | Estudio con y sin el indicador, en validación | **no se cumple en las redes** (el indicador las empeora). La corrección sí existe a 252 días, pero el lineal la aprovecha sobre todo con la ventana de 252 días (Diario 09/11). Sin tendencia, tampoco: a 1 año las 11 mejores combinaciones son sin nivel (1,056 con él frente a 1,022 sin él, D21) |
| H7 | Parte del mal resultado a 1 año se debe a la subida media del train, que redes y lineal proyectan al futuro (+3 % a +12 % al año según el pliegue). Sin ella, las redes mejoran a 1 año; a 3 meses y a 1 semana apenas cambia | Experimento sin tendencia (D20) | **se cumple**: a 1 año las redes pasan de 1,114 a 1,044; a 3 meses y a 1 semana, empate (Diario 09/11) |
| H8 | A 1 año, las redes pierden frente al lineal con los mismos datos (1,03 frente a 0,82) porque tienen demasiada capacidad: con unas 17 respuestas independientes, una red pequeña o muy regulada debería acercarse al lineal | Fase B (D22): si a 1 año ganan configuraciones pequeñas o muy reguladas, y si se acercan a 0,82 | **se cumple en parte**: el problema es aprender demasiado, no tener muchos parámetros. A 1 año gana aprender despacio (velocidad ≈ 0,0002 y lote 128): la velocidad es lo que más influye (correlación 0,8 con el error; 0,76 con los 140 intentos tras D25) y el tamaño apenas, si acaso a favor de las redes grandes. Las elegidas paran en la 1.ª época y hacen previsiones prudentes, en la dirección del lineal pero de un tercio a la mitad de su tamaño. Pasan de 1,01-1,06 a 0,88-0,89, sin llegar al lineal (0,82), que va por delante los tres años (Diario 10/11, noche). **Con 10 semillas (D27), menos aún:** con las semillas nuevas dan 0,92-0,96, y el promedio de 5, 0,91-0,94. En 2018 y 2019 casi todas se quedan con la 1.ª época: más que aprender despacio, no aprenden. Solo ganan al ingenuo en 2020 (Diario 12/11). **D28:** su previsión es una copia en pequeño de la del lineal (correlación 0,94-0,95, la mitad o dos tercios de su tamaño); no encuentran nada que el lineal no vea |

### Limitaciones y problemas conocidos

- El README del repo oficial del curso está desactualizado: el enunciado está en `docs/assignment/ENUNCIADO.pdf` (no en `docs/caso_uso_petroleo.pdf`) y el script es `scripts/download_data.py` (no `descarga_datos_petroleo.py`).
- La cesta de la OPEP (ORB) no está en el dataset: no está en FRED y el script no la descarga.
- La EIA publica el Brent con unos días de retraso, y el script rellena esos días con el último valor.
- Smart App Control (Windows) puede bloquear versiones recién publicadas de librerías con DLL.
- El EDA consulta FRED para identificar los días de cotización (sin conexión usa una regla aproximada).
- La causa del pico de 2026 (138,21 $, 07/04/2026) está sin documentar.
- Equipo de trabajo: Samsung Galaxy Book6 (Intel Core Ultra 7 355, gráfica integrada, 16 GB), **sin GPU NVIDIA**. El problema es pequeño y en CPU se estima entre 30 s y 2 min por entrenamiento. Para los entrenamientos largos: enchufado y sobre una mesa, protección de la batería activada al 80 % (Samsung Settings → Batería y rendimiento) y modo optimizado; con `--hilos 4` va más fresco, aunque algo más lento. **Cargador:** el portátil necesita uno USB-C de 65 W; con uno de 20 W la batería baja al entrenar aunque esté enchufado (≈ 4-5 W con 4 hilos). Con el ahorro de energía de Windows aguanta, pero tarda más (Diario 11/11).
- **La señal de los modelos es una sola: la volatilidad del Brent** (Diario 12/11, noche). Tras las tormentas de caída, el precio rebotó; pero la regla no distingue una tormenta de caída de una de subida. En validación ya falló una vez (septiembre de 2019), y la única gran tormenta de la validación (2020) fue de caída.
- **Parada temprana a 1 año:** el trozo del train que decide cuándo parar tiene unas 3 respuestas independientes, así que la época de parada es casi azar. Se mantiene igual para todos (D22); las 3 semillas por intento promedian también este azar. **Con 10 semillas (D27):** en 2018 y 2019, el 80-100 % de los entrenamientos se queda con la 1.ª época, y la nota de cada semilla depende de dónde para cada año (de 0,87 a 0,99). El promedio de 5 semillas no lo resuelve.
- **Poda de la fase B a 3 meses:** con una semilla, la nota tras 2 años anticipa poco la final (correlación 0,33; tras 3 años, 0,64; a 1 año, con 3 semillas, 0,77), así que la poda corta algo a ciegas. Comprobado hacia atrás con los intentos 1-10, que nunca se podan: ninguno de los que habría cortado acabó entre los 3 mejores. Como a 3 meses todas las configuraciones rinden igual dentro del azar, no se pierde nada relevante.
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
- [x] Commit de la elección de partición (EDA §8 y diario).
- [ ] ~~Documentar la causa del pico de 2026.~~ Se quita (13/11): necesitaría información de fuera sobre años del test.
- [ ] Al final del proyecto: prueba de robustez con la partición A (D10). Solo después del test: su validación usa 2022.
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
- [x] Modelado: instalar PyTorch y definir las tres redes con una misma estructura.
- [x] Al final del proyecto: experimento de control «predecir precios» (D15, H4). Hecho el 13/11: H4 se cumple.

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

**Preguntas de Pablo, respondidas con los resultados**
- **¿Perjudica bajar a 20 intentos?** A 1 año, sí lo habría hecho: tras 20 intentos, la RNN y la LSTM iban por 0,949 y 0,959, y llegaron a 0,893 y 0,882 en los intentos 28 y 37. A 3 meses no cambia nada (0,933 / 0,938 / 0,893 tras 20, frente a 0,933 / 0,931 / 0,893 tras 40). A 1 semana se espera lo segundo, porque las redes ya están pegadas al ingenuo y no hay un error grande que corregir. Por si acaso → **D25**.
- **¿La poda ha hecho perder algo?** A 1 año poda poco (8 de 120) y bien: los que habría cortado entre los intentos 1-10 acabaron entre los últimos. A 3 meses corta algo a ciegas, pero sin perder nada relevante (ver Limitaciones).
- **¿Redes aún más lentas a 1 año?** No. Con lote 128, las más lentas (0,0001-0,00015) dan 0,966 de mediana, frente a 0,951 entre 0,00015 y 0,00025. Las de 0,00011-0,00013 dan 0,95-1,01, y ninguna está entre las mejores. Más lento lleva al ingenuo, porque la red no aprende nada; más rápido, a memorizar. El límite a 1 año no es la velocidad: las redes ya prevén cambios más pequeños que el lineal y aun así pierden contra él.
- **¿Cómo mejorar a 3 meses?** Ajustar la red no sirve. Opciones:
  - **promediar las previsiones de 3 semillas:** el MAE del promedio nunca es peor que la media de los tres, y la previsión es más estable para la app;
  - **información nueva** (por ejemplo, futuros frente a contado): obliga a reabrir los datos y la fase A, así que se deja como mejora futura.

**Decisiones**
- **D23**, **D24** y **D25** (Resumen vivo). H8, actualizada.

**Pendiente**
- ~~D25 a 1 año~~ Hecho: `python scripts/fase_b.py --horizontes largo --modelos LSTM --intentos 60`, 21 min. De los 20 intentos nuevos, 4 se podan y el mejor da 0,881 (intento 45), frente a 0,882 del 37. Las finalistas son la 45, la 37 y la 42 (0,884), empatadas; se mantiene la 37, la de menos parámetros. La LSTM ya había llegado a su techo.
- Decidir si se prueba en validación el promedio de 3 semillas (unas 1 h de entrenamientos, después de 1 semana). → Sigue pendiente (Diario 11/11).
- ~~Pablo lanza de noche `python scripts/fase_b.py --horizontes medio corto`~~ Hecho (Diario 11/11):
  - primero, a 3 meses, solo repite la base con las semillas 43 y 44 (24 entrenamientos, un par de minutos); debe dar exactamente lo calculado arriba, porque la base reproduce los resultados anteriores;
  - después, la búsqueda a 1 semana con 20 intentos.
- ~~Notebook 03, sección 6 (fase B). Commit de D22, D23 y D24~~ Hecho: commit de D22-D24 el 10/11; sección 6 el 11/11.
- Después: examen final en test, robustez con la partición A (D10), control de precios (D15), aplicación y diapositivas. → El test se aplaza (D26).

### 11/11/2026 · Fase B a 1 semana y cierre de la fase B

**Hecho**
- Pablo lanzó de noche `python scripts/fase_b.py --horizontes medio corto --hilos 4`. Terminó en 15,4 h sin incidencias: 11,1 h de búsqueda y 4,3 h de final. Fue más lento de lo previsto por el ahorro de energía (ver *Problemas*).
- 3 meses: la base se repitió con las semillas 43 y 44 (D23) y la elección quedó como se había calculado: la RNN y la GRU se quedan con la base, y la LSTM con el intento 27.
- 1 semana: 60 intentos (10 podados) y la final de cada red con 3 semillas. Ninguna elegida cae en el último cuarto, así que no hay ampliación (D25).
- Análisis de la fase B completa. **Notebook 03, sección 6**:
  - cómo avanza la búsqueda;
  - qué influye en el error;
  - la final con 3 semillas;
  - la elegida frente a la base y al lineal, también año a año;
  - curvas de aprendizaje de las elegidas;
  - la poda.

**Resultados a 1 semana** (media de 3 semillas)

| Red | Base (intento 1) | Elegida | Configuración elegida | Parámetros |
|---|---|---|---|---|
| RNN | 0,997 | 0,994 (intento 11) | 38 neuronas × 2 capas · velocidad 0,00012 · lote 128 · dropout 0,02 · L2 1·10⁻⁵ | 4.789 |
| LSTM | 0,988 | 0,991 (intento 8) | 23 × 1 · velocidad 0,00034 · lote 64 · dropout 0,41 · sin L2 | 2.968 |
| GRU | 0,993 | 0,994 (intento 15) | 8 × 1 · velocidad 0,00037 · lote 64 · dropout 0,25 · sin L2 | 417 |
| Lineal (mismos datos) | | 0,993 | | |

- **La búsqueda no mejora la base.** Cada año todo queda entre 0,98 y 1,01. Las redes aciertan si sube o baja el 54-56 % de las veces.
- **La diferencia entre configuraciones es del mismo tamaño que el azar entre semillas** (≈ 0,005): la búsqueda no puede distinguir una configuración buena de una afortunada. Las finalistas empeoran con las semillas 43 y 44 (de 0,985-0,991 a 0,992-0,996), como a 3 meses.
- Casi ningún valor influye. Aprender despacio ayuda un poco (correlación 0,20).
- **El lineal elige la regularización más fuerte de las probadas** (alfa 100.000): lo mejor es casi no predecir.
- Como todas empatan, la regla se queda con las redes más pequeñas. La GRU elegida tiene 8 neuronas.
- **Poda:** 10 de 60. La nota tras 2 años anticipa bien la final (0,65), y el mejor podado iba por 0,992, frente al 0,981 del mejor completo.

**La fase B completa** (MAE / ingenuo, media de 3 semillas)

| Horizonte | RNN | LSTM | GRU | Lineal | Mejora frente al ingenuo |
|---|---|---|---|---|---|
| 1 semana | 0,994 | 0,991 | 0,994 | 0,993 | ≈ 1 % |
| 3 meses | 0,943 | 0,943 | 0,922 | 0,972 | 6-8 % |
| 1 año | 0,893 | 0,882 | 0,893 | **0,820** | 11-12 % (lineal, 18 %) |

- **Las tres redes empatan en los tres horizontes.**
- **Frente al lineal:**
  - a 3 meses las redes le ganan, sobre todo en 2018 y 2021; en 2019 gana el lineal;
  - a 1 año gana el lineal los tres años;
  - a 1 semana empatan todos con el ingenuo.
- **La búsqueda solo sirve a 1 año**, y lo que encuentra es aprender despacio.
- **H1 sigue sin cumplirse:** las redes aportan a 3 meses y a 1 año, y no a 1 semana.

**Frente a lo esperado:**
- **Resultado:** se esperaba que la búsqueda no cambiara nada a 1 semana, y así fue.
- **Tiempo:** 15,4 h frente a las 8-9 h esperadas, casi el doble. Influyen el ahorro de energía, los 4 hilos y que la búsqueda prueba redes grandes y lentas (un intento llegó a 49 minutos).

**Problemas y soluciones**
- **La batería bajaba con el portátil enchufado.** Windows decía «cargando», pero en media hora entrenando el nivel bajó de 47,2 a 45,1 Wh, unos 4-5 W. La causa probable es un cargador de 20 W (de iPad); el portátil necesita 65 W.
  - Con el ahorro de energía de Windows y la pantalla apagada, la batería dejó de bajar: subió de 45,1 a 46,9 Wh en una hora.
  - El precio: el entrenamiento fue más lento.
  - Pablo compra un cargador Anker Nano II de 65 W. Anotado en *Limitaciones*.
- **Notebook, qué influye en el error:** con la nota final solo cuentan los intentos que sobrevivieron a la poda, y a 3 meses eso daba correlaciones de hasta −0,4 que no aparecían en el análisis anterior. Se usa la nota tras 2 años, que tienen todos los intentos, como en el análisis del 10/11.

**Decisiones**
- **D26**: el examen final en test se aplaza para seguir mejorando las redes. Pablo: «estamos lejos del resultado deseado».

**Pendiente**
- Buscar cómo mejorar las redes. Ajustar la configuración ya no da más de sí: el límite está en otra parte (los datos que reciben, cómo se entrenan o cómo se combinan). Las ideas se deciden con Pablo antes de lanzar nada.
- Sigue pendiente decidir si se prueba en validación el promedio de 3 semillas. → Se hace con 5 (D27, Diario 11/11, tarde).
- Después: examen final en test, robustez con la partición A (D10), control de precios (D15), aplicación y diapositivas.

### 11/11/2026 (tarde) · Siguientes pasos y diseño de la estabilidad (D27)

**Hecho**
- Repaso con Pablo de los mayores problemas tras la fase B:
  1. **poca señal y pocos datos independientes:** a 1 año, unas 17 respuestas en el train y 3 años de validación;
  2. **redes inestables:** la semilla y la época de parada cambian el resultado;
  3. **a 1 año, el lineal gana a las redes;**
  4. **información limitada;**
  5. **riesgo de sobreajustar la validación:** cientos de configuraciones elegidas sobre 2018-2021.
- Orden acordado: primero la estabilidad (problema 2), con cautela por el problema 5.
- Restricción de Pablo para la información nueva: solo lo que está en los CSV del proyecto o lo que permita el enunciado.
- **Pregunta de Pablo sobre las curvas de la sección 1.1** (mejores épocas 2, 4 y 12). No es un fallo de la parada temprana:
  - la pérdida de parada no baja nunca (oscila entre 0,32 y 0,37), así que la «mejor época» es el punto más bajo de un zigzag plano y cae casi al azar;
  - la LSTM paró la más tarde y fue la peor;
  - con velocidades más lentas la curva se suaviza (fase B, 1 semana: mejor época 17-45), pero el error no mejora.
  - El azar de la época de parada sí es un problema de estabilidad → D27.
- **D27** implementada:
  - `busqueda._entrenar_y_prever`: el entrenamiento de la fase B, que devuelve también la previsión;
  - `estabilidad.py`: ejecución reanudable, comprobación contra la fase B, promedio, nota, curva según el número de semillas y cambio de la previsión;
  - `scripts/estabilidad.py`;
  - 6 pruebas nuevas, entre ellas que el promedio nunca tenga más error que la media de sus semillas y que la ejecución se reanude sin repetir. 58 en total, todas correctas.
- Prueba real pequeña (RNN de 1 año y de 3 meses, 3 semillas):
  - la nota calculada desde las previsiones guardadas coincide con la de cada entrenamiento;
  - las semillas de la fase B se reproducen salvo redondeo (2·10⁻⁷ $ de diferencia en el MAE, por usar 4 hilos en lugar de 6).

**Lo esperado** (apuntado antes de lanzar)
- **Error:** mejora pequeña, de 0,00 a 0,02, mayor a 1 año.
- **Estabilidad:** el azar del resultado baja a menos de la mitad (con 5 semillas, en teoría a 1/√5 ≈ 0,45).
- **Lo que no cambiará:** la distancia con el lineal a 1 año y el empate entre redes.
- **A 1 año, las semillas nuevas (45-51) pueden dar algo peor que las de la elección (42-44):** parte del 0,88-0,89 puede ser suerte. En la prueba, la semilla 50 de la RNN dio 0,92.

**Ejecución** (6 hilos, ya con el cargador de 65 W y sin ahorro de energía)
- Terminada en 5,1 h, más de las 3-4 h previstas: casi todo es 1 semana, que fue al ritmo de la fase B.
- Completa: 330 entrenamientos (9 redes × 10 semillas × 3 o 4 años) y 81.900 previsiones, sin huecos ni repetidos.
- Las 9 comprobaciones salen bien: las semillas 42-44 reproducen la fase B exactamente (1 año RNN, LSTM y GRU; 3 meses LSTM) o salvo redondeo (las demás, como mucho 5·10⁻⁷ $ de diferencia en el MAE).

**Pendiente**
- Analizar (→ hecho el 12/11):
  - la curva de 1 a 10 semillas;
  - el azar entre grupos;
  - el cambio de la previsión;
  - la nota con las semillas 45-51 frente a las 42-44.
- Notebook 03: sección nueva antes del examen final (→ hecho el 12/11, §7).
- Commit, con el visto bueno de Pablo.

### 12/11/2026 · Resultados de la estabilidad (D27) y siguientes pasos

**Hecho**
- Análisis de la estabilidad y sección 7 del notebook 03 («Estabilidad: promedio de semillas»). El examen final en test pasa a ser la sección 8.
- Repaso con Pablo de los problemas tras la estabilidad, de más a menos grave:
  1. **a 1 año las redes no aprenden** y el lineal es mejor;
  2. **sobreajuste de la validación**, ya confirmado;
  3. **a 1 semana no hay nada que ganar** (0,99): no se invierte más tiempo ahí;
  4. **inestabilidad:** el promedio de 5 la reduce a 3 meses; a 1 año el problema es el 1;
  5. **poca información:** los futuros del Brent empiezan en 2007, pero el futuro del WTI está en el CSV desde 2000, y su diferencia con el contado (si el mercado espera subidas o bajadas) no se usa;
  6. **tiempo:** quedan el test, la aplicación y las 5 diapositivas, y el enunciado pide no intensificar en lo técnico.

**Resultados** (detalle en el notebook 03, §7)

| | Fase B (semillas 42-44) | Semillas nuevas (45-51) | Promedio de 5 (adoptado) | Lineal |
|---|---|---|---|---|
| 1 semana · RNN | 0,994 | 0,995 | 0,993 | 0,993 |
| 1 semana · LSTM | 0,991 | 1,000 | 0,992 | |
| 1 semana · GRU | 0,994 | 0,992 | 0,991 | |
| 3 meses · RNN | 0,943 | 0,947 | 0,941 | 0,972 |
| 3 meses · LSTM | 0,943 | 0,966 | 0,950 | |
| 3 meses · GRU | 0,922 | 0,937 | 0,924 | |
| 1 año · RNN | 0,893 | 0,920 | 0,908 | 0,820 |
| 1 año · LSTM | 0,882 | 0,923 | 0,906 | |
| 1 año · GRU | 0,893 | 0,958 | 0,937 | |

- **Lo esperado frente a lo obtenido:**
  - **error:** mejora de 0,001 a 0,009, dentro de lo esperado, pero mayor a 3 meses que a 1 año;
  - **estabilidad:** a 3 meses se cumple. El cambio de la previsión baja a 0,37-0,55 de lo que cambia con una semilla (teoría: 0,45): el precio previsto se mueve un 0,8-1,4 % con otras 5 semillas, frente al 1,7-2,9 % con una sola. A 1 año queda muy desigual (0,17-0,66);
  - **lo que no cambia:** se cumple; la distancia con el lineal a 1 año crece;
  - **semillas nuevas a 1 año:** dan peor, como se temía, y más de lo esperado (0,03-0,07).
- **La fase B era optimista** (problema 5): las elegidas ganaron en parte por suerte. A 3 meses, hasta 0,02; a 1 semana, nada.
- **A 1 año, las redes no aprenden:**
  - en 2018 y 2019, 57 de los 60 entrenamientos se quedan con la 1.ª época: la red apenas se mueve de su punto de partida. Solo en 2020 aprende algo (mejor época mediana, la 8.ª-12.ª);
  - las peores semillas (0,96-0,99) son las que paran distinto: en 2020 también se quedan con la 1.ª época (GRU 45, 47, 49 y 51; LSTM 46 y 49) o en 2019 siguen aprendiendo y se equivocan (RNN 47 y GRU 48, con 1,34-1,40 ese año);
  - las redes solo ganan al ingenuo en 2020 (0,67-0,77), el rebote tras el COVID. En 2018 no lo mejoran (0,99-1,10) y en 2019 pierden (1,13-1,15). El lineal les gana en 2018 (0,75) y en 2019 (1,04).
- **A 3 meses, las redes siguen ganando al lineal** (0,924-0,950 frente a 0,972), y de forma más regular: el lineal gana en 2019 (0,89) pero falla mucho en 2021 (1,14). Es el horizonte donde aportan.

**Decisiones**
- Se adopta el promedio de 5 semillas en los tres horizontes (regla de D27). Las notas de referencia de la validación pasan a ser las del promedio de 5.
- Plan propuesto:
  1. cerrar la estabilidad (notebook, diario y commit);
  2. combinar red y lineal (D28), con las previsiones ya guardadas y sin entrenar;
  3. a 1 año, una red que corrige al lineal: parte de su previsión y solo aprende lo que le falta;
  4. congelar los modelos, hacer el test una sola vez y la robustez con la partición A;
  5. aplicación y diapositivas.
  - Opcional, si hay tiempo: la diferencia entre el futuro y el contado del WTI como información nueva, solo a 3 meses.
  - Pablo aprueba empezar por los pasos 1 y 2, por partes.
- **Cautela con el problema 5:**
  - solo valen las cifras con 10 semillas;
  - cada experimento nuevo lleva su regla escrita antes y nada que afinar;
  - como mucho 2 o 3 experimentos más antes del test.

**Pendiente**
- Commit de la estabilidad, con el visto bueno de Pablo. (→ hecho: `abcffc5`, subido a GitHub)
- D28: combinar red y lineal. Antes de calcular, fijar la regla (sin pesos que afinar) y apuntar lo esperado.
- Fijar con Pablo la fecha para congelar los modelos.

**Notas**
- Mapa conceptual del notebook 03 (secciones 1-7) en una página visual, para repasar todo lo visto. Se guarda solo en local, en `notas_locales/` (excluida de git), sin subir.
- Pablo pide que el test no se use sin su aprobación explícita.

### 12/11/2026 (tarde) · Combinación de red y lineal (D28)

**Diseño** (D28)
- Previsión combinada: la media, a partes iguales, del precio que prevé la red (promedio de 5 semillas) y del que prevé el lineal.
- El lineal es el de referencia de la fase B (0,993 / 0,972 / 0,820). Sus previsiones se recalculan con las mismas fichas que las redes; antes de usarlas se comprueba que dan su nota de siempre.
- Las redes usan los dos grupos de 5 semillas de D27 (42-46 y 47-51), y la nota es la media de los dos, como la nota adoptada en D27.
- Solo validación (2018-2021). El test no se toca.
- **Regla** (fijada antes de calcular): ver D28.

**Lo esperado** (apuntado antes de calcular)
- **1 año:** entre las dos, más cerca del lineal (0,83-0,86). Seguramente no le gane: las redes prevén en su misma dirección pero más corto, y mezclarlas acorta la previsión del lineal. No se adoptaría.
- **3 meses:** algo mejor que la red sola (0,92-0,94), porque fallan en años distintos. Puede quedarse dentro del azar.
- **1 semana:** nada (0,99). No se adoptaría.

**Hecho**
- `combinacion.py`: previsiones del lineal de referencia con las mismas fichas que las redes, combinación, curva de pesos y regla de D28. 6 pruebas nuevas, entre ellas que la mezcla nunca tiene más error que la media de las dos; 64 en total, todas correctas.
- El lineal recalculado da exactamente su nota guardada en los tres horizontes (0,993 / 0,972 / 0,820), en las mismas 2.730 fichas que las redes. Su regularización: 100.000 a 1 semana, 1.000 a 3 meses y 1 a 1 año (casi sin regularizar).
- Notebook 03, sección 8 («Combinación de red y lineal»). El examen final pasa a ser la sección 9.

**Resultados** (media de las tres redes; detalle en el notebook 03, §8)

| | Red sola | Lineal | Mitad y mitad | Azar con 5 semillas | Se queda |
|---|---|---|---|---|---|
| 1 semana | 0,992 | 0,993 | 0,990 | 0,003 | red sola (empate) |
| 3 meses | 0,938 | 0,972 | 0,945 | 0,008 | red sola |
| 1 año | 0,917 | 0,820 | 0,851 | 0,022 | lineal |

- **Lo esperado frente a lo obtenido:**
  - 1 año: se cumple (0,846-0,861; no se adopta);
  - 3 meses: no se cumple. Esperaba una pequeña mejora y la mezcla queda algo peor que la red sola;
  - 1 semana: se cumple (empate).
- **A 1 año, las redes son una copia en pequeño del lineal:**
  - su previsión va en la misma dirección (correlación 0,94-0,95) y se mueve la mitad o dos tercios (0,48-0,72);
  - cuanto más peso tiene el lineal en la mezcla, mejor, sin excepción, y año a año la mezcla queda siempre detrás del lineal;
  - las redes no encuentran nada que el lineal no vea.
- **A 3 meses, red y lineal se parecen demasiado** (correlación 0,76-0,83, mismo tamaño). La mezcla gana en 2019, el buen año del lineal (de 0,95 a 0,91), pero pierde más en 2021, su mal año (de 0,89 a 1,01).
- **A 1 semana, al revés:** casi no se parecen (0,23-0,25), y la mitad y mitad es el mejor punto de la curva, pero solo gana 0,001-0,004, del tamaño del azar.

**Decisiones**
- D28 cerrada: no se adopta la combinación. A 1 semana y a 3 meses, la red sola; a 1 año, el mejor modelo de validación sigue siendo el lineal.
- **No se hace, por ahora, la red que parte del lineal a 1 año** (paso 3 del plan del 12/11): con estos datos las redes no encuentran nada que el lineal no vea, y lo más probable es que se quedara en el lineal. Solo se reconsidera si aparece información nueva que las redes aprovechen.
- Pablo no quiere pasar todavía al test: se sigue investigando.

**Pendiente** (plan propuesto a Pablo)
1. **Entender qué ve el lineal** (qué variables y qué días pesan), sobre todo a 1 año. Sin entrenar. Sirve para elegir la información nueva y para la explicación de la aplicación.
2. **Información nueva, en un solo experimento**, solo a 3 meses y a 1 año, con la regla escrita antes y 10 semillas: por ejemplo, la diferencia entre el futuro y el contado del WTI, la diferencia entre el Brent y el WTI, o el tipo del BCE. Todo está en el CSV y el enunciado lo permite.
3. **Incertidumbre:** el intervalo del 80 % (D8) y su cobertura en cada año, calibrando cada año con los otros tres (H3).
4. **¿Es real la ventaja a 3 meses?** Años que gana, cuánto puede ser azar y acierto de la dirección.
- Commit de D28, con el visto bueno de Pablo. (→ hecho: `8f2c643`)

### 12/11/2026 (noche) · Qué ve cada modelo (paso 1)

**Hecho**
- `explicacion.py`:
  - aportación exacta de cada variable a la previsión del lineal;
  - el lineal reajustado sin cada variable y con solo ella;
  - para redes y lineal, cuánto empeora la nota al desordenar cada variable entre fichas, y cuánto cambia la previsión en situaciones típicas (volatilidad al doble o a la mitad; Brent y WTI un 10 % más abajo que hace un mes).
- `scripts/importancia.py`: reentrena las redes elegidas con las semillas 42-46, a 3 meses y a 1 año, y guarda `resultados/importancia.csv` y `resultados/efectos.csv`. Tardó 8 minutos (lo lancé yo, por ser corto). Sin desordenar nada, la nota de cada red coincide exactamente con la de su promedio en la estabilidad.
- 6 pruebas nuevas (70 en total, todas correctas).
- Notebook 03, sección 9 («Qué ve cada modelo»). El examen final pasa a ser la sección 10.

**Resultados**
- **El lineal mira casi solo la volatilidad del Brent** del último mes:

  | | Todas las variables | Solo la volatilidad | Todas menos la volatilidad |
  |---|---|---|---|
  | 1 semana | 0,993 | 0,992 | 1,001 |
  | 3 meses | 0,972 | 0,968 | 1,011 |
  | 1 año | 0,820 | 0,853 | 0,981 |

  - Es lo que más mueve su previsión: dos tercios a 1 año (correlación 0,99 con la previsión entera), más de un tercio a 3 meses y la mitad a 1 semana.
  - Su regla es «tras la tormenta, rebote». Con la volatilidad al doble de lo normal prevé un 7 % más a 3 meses y un 35 % más a 1 año.
  - Lo demás pesa poco: a 1 año, el cobre y el dólar (sin ellos, 0,833-0,834) y algo de corrección tras las caídas (un 10 % abajo en un mes → un 3 % más).
- **Las redes también miran sobre todo la volatilidad:**
  - **3 meses:** con la misma fuerza que el lineal o más (al doble: un 8-12 % más, frente al 7 %). Además aprovechan algo del último mes del Brent (un 10 % abajo → un 3 % más, frente al 1 % del lineal), del cobre (la RNN) y del VIX (la GRU). Ese «algo más» explica su ventaja sobre el lineal;
  - **1 año:** solo la volatilidad, y con menos de la mitad de fuerza (al doble: un 12-15 % más, frente al 35 %). Nada más. Es la copia en pequeño de D28.
- **Por qué funciona:** la volatilidad alta llegó casi siempre con desplomes (2008, 2014-2016, 2020), y después el precio se recuperó. En validación, casi toda la ventaja a 1 año está en el rebote de 2020.
- **El riesgo ya aparece en validación:** el 16/09/2019, tras el ataque a las instalaciones petroleras saudíes, el Brent saltó un 12 % (de 61,25 a 68,42 $). La volatilidad subió por una subida, no por una caída, y el lineal previó entre el 13/09 y el 31/10 un 17-35 % más a un año. Lo que pasó fue un 29-43 % menos.

**Decisiones**
- Para la información nueva (paso 2), lo prometedor es medir mejor el estrés del mercado: el VIX en nivel (ahora solo entra su variación diaria) y la volatilidad del Brent a más plazo. Añadir más variaciones diarias, no. Se propone a Pablo el diseño antes de calcular (D29).
- Para la aplicación, la explicación de la previsión a 3 meses y a 1 año: depende sobre todo de lo nervioso que esté el mercado, y tras las tormentas el precio suele recuperarse. Puede invalidarla una tormenta que venga de una subida.

**Pendiente**
- D29: diseño del experimento de información nueva, con su regla y lo esperado, antes de calcular. Pendiente del visto bueno de Pablo. (→ no se hace por ahora: ver abajo)
- Comprobar en el train (2000-2017), sin tocar el test, si tras las subidas bruscas de volatilidad el precio también rebota. (→ hecho: ver abajo)
- Commit del paso 1, con el visto bueno de Pablo. (→ hecho por Pablo a mano: `e43c413`)

### 12/11/2026 (noche) · Información nueva: estudio en el entrenamiento (paso 2)

**Hecho**
- Antes de gastar la validación, un estudio **solo con datos hasta 2017** (sin tocar validación ni test), en tres partes. Lo hace `cribado.py` (notebook 03, §11); al principio se hizo con scripts de trabajo, y las cifras se han ajustado a las del módulo:
  1. las tormentas del train (el 10 % de días con más volatilidad), una a una;
  2. la relación de cada medida candidata con la variación posterior;
  3. una validación por años dentro del train: modelos lineales pequeños, entrenados con lo anterior, prevén cada año de 2006 a 2017.

**Resultados**
- **Tormentas:** 15 episodios en 2000-2017. 12 llegaron tras una caída, y después el precio subió de media un 9 % en 3 meses y un 23 % en un año (un día cualquiera: un 1,7 % y un 5,2 %). Solo 3 llegaron tras una subida, y después el precio también subió. En el train no hay ningún caso como el de septiembre de 2019 (tormenta de subida seguida de caída), así que los modelos no pueden aprender esa diferencia.
- **Ninguna candidata mejora a la volatilidad de un mes sola** en la validación por años dentro del train:

  | Añadido a la volatilidad de un mes | 3 meses | 1 año |
  |---|---|---|
  | Nada (lo de ahora) | 1,046 | 0,964 |
  | Volatilidad a 3 meses | 1,099 | 0,977 |
  | VIX en nivel | 1,084 | 1,057 |
  | Volatilidad de las caídas · de las subidas (cada una añadida) | 1,057 · 1,061 | 0,971 · 0,972 |
  | Futuro del WTI frente al contado | 1,045 | 0,960 |
  | Brent frente al WTI · dólar · cobre (frente a su media del año) | 1,06-1,08 | 0,98-0,99 |
  | Gas frente al Brent | 1,192 | 1,262 |
  | Tipo del BCE (cambio en un año) | 1,069 | 0,951 |

  - El gas frente al Brent parece muy relacionado con lo que pasó después (correlación 0,48 a 1 año), pero al prever años nuevos falla mucho: es una tendencia de esos años, no una señal.
  - El tipo del BCE mejora algo a 1 año, pero en 2018-2021 apenas cambió: allí no podría ayudar.
- **Lo más importante:** en 2006-2017, la regla de la volatilidad es peor que el ingenuo a 3 meses (1,046) y apenas lo mejora a 1 año (0,964). En 2018-2021 funciona mucho mejor (0,968 y 0,853), sobre todo por 2020, un desplome con rebote muy rápido. En las caídas largas (2008, 2014-2016) el precio siguió bajando meses después de la tormenta. **La validación puede ser un periodo favorable a la regla.**

**Decisiones**
- **Información nueva: se deja sin explorar por ahora** (decisión de Pablo). El estudio en el train no apoya ninguna candidata, así que no se gasta la validación en probarlas.
- **Se adelanta el paso 4 y se mejora:** en lugar de mirar solo los 4 años de validación, las configuraciones elegidas se prueban también en 2010-2017 (D29).

### 12/11/2026 (noche) · Validación hacia atrás (D29, paso 4)

**Diseño** (D29, fijado antes de calcular)
- **Qué:** las configuraciones elegidas en la fase B, sin volver a elegir nada, con su promedio de 5 semillas (42-46, D27), y el lineal de referencia con su misma regularización. Se evalúan en cada año de 2010 a 2017, entrenando solo con lo anterior, como en la validación.
- **Por qué es limpia:** esos años nunca se usaron para elegir nada (solo se miró 2018-2021), y no se usa nada posterior al 31/12/2017: las fichas cuya respuesta cae después se descartan. A 1 año, el último año evaluado es 2016. El test no se toca.
- **Dónde:** 3 meses (8 años nuevos, 12 con la validación) y 1 año (7 nuevos, 10 en total). 1 semana queda fuera: con la ventana de 252 días tardaría horas, y allí ningún modelo aporta.
- **Qué se mide:** la nota de cada año; cuántos años gana cada modelo al ingenuo; la nota con todos los años juntos y un intervalo (remuestreando años); y cuántas veces acierta si el precio sube o baja.
- **Criterio, fijado antes de ver nada** (media de las tres redes, los 12 años de 3 meses):
  - **ventaja real:** gana al ingenuo en al menos 9 de los 12 años y queda por debajo de 1 con los años juntos. Sin ninguna ventaja, ganar 9 o más de 12 años sale el 7 % de las veces, como sacar 9 caras en 12 tiradas;
  - **dudosa:** gana 7 u 8 años;
  - **no se sostiene:** gana 6 o menos.
  - A 1 año, lo mismo con 10 años: real con 8 o más.

**Lo esperado** (apuntado antes de calcular)
- **3 meses:** menos ventaja que en validación. Entre 0,96 y 1,02 de media en 2010-2017, ganando al ingenuo en la mitad de esos años o algo más. Con los 12 años, entre «dudosa» y «real».
- **1 año:** alrededor de 1 (0,95-1,05) en 2010-2017. El lineal, algo mejor que las redes pero lejos de su 0,82. Las caídas largas de 2014-2016 deberían salir mal.

**Hecho**
- `hacia_atras.py` (años 2010-2017 sin nada posterior a 2017, ejecución reanudable, medidas y criterio), `scripts/hacia_atras.py` y 6 pruebas nuevas, entre ellas que ninguna ficha mira después de 2017. 76 en total, todas correctas.
- Pablo lanzó `python scripts/hacia_atras.py`: 225 entrenamientos en 11,9 minutos (la mitad de lo previsto).
- `estabilidad.leer_previsiones` y `combinacion.previsiones_lineal` admiten otros archivos y otros años.
- Notebook 03, sección 10 («Validación hacia atrás»). El examen final pasa a ser la sección 11.

**Resultados** (media de las tres redes; detalle en el notebook 03, §10)

| | 2010-2017 | 2018-2021 (validación) | Todos los años | Años que gana | Veredicto |
|---|---|---|---|---|---|
| 3 meses · redes | 1,073 | 0,933 | 1,023 (0,96-1,10) | 7 de 12 | **dudosa** |
| 3 meses · lineal | 1,047 | 0,972 | 1,020 | 5 de 12 | no se sostiene |
| 1 año · redes | 1,024 | 0,901 | 0,984 (0,86-1,14) | 4 de 10 | **no se sostiene** |
| 1 año · lineal | 0,982 | 0,820 | 0,928 (0,76-1,16) | 4 de 10 | no se sostiene |

- **3 meses:** las redes ganan solo 3 de los 8 años nuevos (2010, 2016 y 2017). Sin ninguna ventaja, ganar 7 o más de 12 años pasa el 39 % de las veces. La RNN es la más regular: 0,994 con los 12 años, la única por debajo de 1.
- **1 año:** unos pocos años muy buenos (2014, 2016 y 2020) compensan muchos malos (2010-2012, 2015 y 2019).
- **Peores años:** 2011-2012, con el precio por encima de 100 $ casi todo el tiempo (a 1 año, también 2010), y 2015, la caída larga.
- **Dirección:**
  - a 3 meses, la RNN acierta si sube o baja el 58 % de las veces, frente al 54 % de decir siempre «sube»;
  - a 1 año, el lineal acierta el 64 % (el precio bajó en el 54 % de las fichas) y las redes el 52-57 %.
- **Lo esperado frente a lo obtenido:**
  - 3 meses: peor de lo esperado (1,073 en 2010-2017 frente a 0,96-1,02), y el veredicto queda en el extremo bajo de lo previsto (dudosa);
  - 1 año: se cumple en la media, pero no en los años: 2014 y 2016 salen bien, y 2010-2012, que no esperaba, mal.

**Decisiones**
- **Conclusión del estudio, con 12 años:** ninguna red mejora al ingenuo de forma fiable en ningún horizonte. La ventaja a 3 meses de la validación era sobre todo de esos años: dudosa con el criterio fijado. A 1 año, ni las redes ni el lineal se sostienen. Es la respuesta a lo que pide el enunciado («en qué horizontes la predicción aporta valor y en cuáles no»).
- Expectativa para el test (cuando Pablo lo apruebe): alrededor de 1 en los tres horizontes.
- Para la aplicación, el valor estará más en decir cuánto puede moverse el precio (incertidumbre, paso 3) que en la dirección.

**Pendiente**
- Commit de D29, con el visto bueno de Pablo.
- Paso 3, incertidumbre: el intervalo del 80 % (D8) y su cobertura año a año. Ahora se puede comprobar en 12 años (2010-2021), no solo en 4.
- Commit de D29: hecho y subido a GitHub (`78b8e44`).

### 12/11/2026 (noche) · Comparación con el proyecto de un compañero

**Hecho**
- Pablo compara nuestro proyecto con el de un compañero que hace el mismo caso. Se le pasó una descripción del nuestro, sin código ni enlace al repositorio (`notas_locales/`, fuera de git), y él pasó la suya.
- **Coincidencias:**
  - 9 redes que predicen la variación logarítmica, validación año a año, escalado solo con el train, parada temprana con el último 15 %, Optuna, semillas y un Ridge de referencia;
  - 1 semana ≈ ingenuo; a 3 meses, «señal» en validación (0,93-0,94) que no se sostiene fuera;
  - domina la volatilidad de 21 días; el azar entre semillas es tan grande como las diferencias; la RNN simple es la más estable y barata a 3 meses.
- **Diferencias:** usan 16 variables (con ratios cobre/Brent y oro/Brent, base del WTI, VIX en nivel…), validan en 2019-2023, miden el RMSE frente al ingenuo con la media de los años, promedian las 5 mejores configuraciones y la media de las tres redes, y tienen una versión «ajustada» (la previsión por un factor entre 0 y 1).

**Problemas y soluciones**
- **Su test (2024-2026) cae dentro del nuestro (2022 hasta hoy).** Lo que cuentan de su test es información sobre nuestro examen final. **No se usa para elegir nada nuestro**, para que nuestro test siga siendo limpio.

**Deshecho o descartado** (decisión de Pablo: «ni de broma»)
- ❌ Usar el test más de una vez (ellos lo han usado dos veces y su 0,919 de validación fue 1,147 en el test).
- ❌ Promediar las 5 mejores configuraciones de la búsqueda: es caro y su mejora se deshizo con más semillas (de 0,901 a 0,938).
- ❌ Dar más peso a los años recientes al entrenar: a ellos les empeoró.

**Diseño de las tres pruebas que salen de la comparación** (fijado antes de calcular; solo validación y 2010-2017, sin tocar el test)
1. **Media de las tres redes:** la previsión es la media de los precios que prevén la RNN, la LSTM y la GRU, cada una con su promedio de las semillas 42-46. Con las previsiones ya guardadas, en los 12 años de 3 meses y los 10 de 1 año. **Regla:** se adopta para la aplicación si, con todos los años juntos, mejora a cada red por separado y gana al ingenuo en al menos tantos años como la mejor de ellas.
2. **Previsión prudente:** la variación prevista se multiplica por un factor de 0 a 1, en pasos de 0,1 (0 es el ingenuo). El factor se elige con unos años y se comprueba con otros: con 2010-2017 se comprueba en 2018-2021, y al revés. **Regla:** se adopta si, en los dos sentidos, mejora a la red sin ajustar en los años en que se comprueba. El factor que mejor va con los 12 años juntos solo describe cuánta señal hay.
3. **Ratios cobre/Brent y oro/Brent** (como ellos: puntuación z a 252 días del logaritmo del ratio). Criba solo con datos hasta 2017, igual que la del paso 2: modelos lineales pequeños que prevén cada año de 2006 a 2017 con lo anterior, añadiendo cada ratio a la volatilidad de un mes. **Regla:** pasa la criba si mejora a la volatilidad sola en al menos 0,02 y en más de la mitad de los años. Solo si pasa se propondría un experimento con las redes.

**Lo esperado** (apuntado antes de calcular)
1. **Media de las tres redes:** mejor que la media de sus notas, eso está garantizado, pero cerca de la mejor red y sin ganarle con claridad. A 3 meses, 0,99-1,01 con los 12 años (la RNN, 0,994); a 1 año, 0,96-0,98.
2. **Prudente:** elegido con 2010-2017, el factor saldrá pequeño a 3 meses (0-0,3), y en 2018-2021 perderá parte de la ventaja. Elegido con 2018-2021 saldrá cerca de 1 y no mejorará 2010-2017. No se adoptaría. Con los 12 años, un factor de 0,3-0,6.
3. **Ratios:** probablemente no pase la criba, como el resto de candidatas; si algo, a 1 año.

**Resultados** (notebook 03, §11)
1. **Media de las tres redes: no se adopta.**
   - **3 meses:** 1,016 con los 12 años juntos. Es mejor que la LSTM (1,044) y la GRU (1,030), pero peor que la RNN sola (0,994), y gana 7 años, como cada red.
   - **1 año:** 0,981, frente a 0,966 de la RNN y 0,968 de la GRU. Gana 4 años, frente a 5 de la RNN.
   - Confirma que la RNN es la mejor y la más regular.
2. **Previsión prudente: no se adopta en ningún modelo.**
   - **A 3 meses, los dos periodos piden lo contrario:** con 2010-2017, el mejor factor es 0 (no prever nada, el ingenuo) para las tres redes; con 2018-2021, es 1 (prever con toda la fuerza). Por eso, elegido en un periodo, nunca mejora en el otro.
   - Es la señal más clara de que lo que aprenden las redes no es estable de un periodo a otro.
   - Con los 12 años juntos, el mejor factor a 3 meses es 0-0,6 y mejora al ingenuo como mucho un 1 % (RNN con 0,6: 0,989).
   - A 1 año, elegido con 2010-2017, el factor está entre 0 y 0,5, y en 2018-2021 empeora (por ejemplo, la RNN pasa de 0,894 a 0,949).
3. **Ratios cobre/Brent y oro/Brent: no pasan la criba.**
   - Añadidos a la volatilidad de un mes, empeoran: el cobre/Brent, 0,057 a 3 meses y 0,034 a 1 año; el oro/Brent, 0,013 en los dos.
   - Parecen relacionados con lo que pasa después (correlación 0,26-0,31 el cobre/Brent), pero no ayudan a prever años nuevos. Pasa lo mismo que con el gas.
- **Lo esperado frente a lo obtenido:**
  - la previsión prudente y los ratios salen como se esperaba;
  - la media de las tres redes, algo peor de lo esperado (1,016 frente a 0,99-1,01 a 3 meses; 0,981 frente a 0,96-0,98 a 1 año).

**Decisiones**
- No se adopta ninguna de las tres ideas. La comparación con el compañero refuerza la conclusión de D29: con estos datos, la ventaja de las redes no es estable fuera de los años en que se eligió.
- Para la aplicación, la RNN simple es la candidata: la más regular a 3 meses en los 12 años y la más barata. Coincide además con lo que ve el compañero en sus curvas de aprendizaje.
- Ideas de la comparación que sí se tomarán para la aplicación y la tabla final:
  - un semáforo de fiabilidad por horizonte;
  - la aplicación publicada en internet para la demostración;
  - el RMSE y la media por años, además de la nota con los años juntos.

**Pendiente**
- Pasar al código y al notebook las cribas con el train y las ideas 1 y 2. (→ hecho: `cribado.py`, funciones nuevas en `hacia_atras.py`, 8 pruebas nuevas (84 en total) y notebook 03, §11; el examen final pasa a ser la sección 12)
- Paso 3, incertidumbre.

### 12/11/2026 (noche) · Incertidumbre: planteamiento (paso 3)

**Decisiones**
- **Nivel del rango: 80 %** (cuantiles 10-90, como en D8). El enunciado lo pone como ejemplo («por ejemplo, un intervalo del 80 %»), no lo obliga. Se mantiene porque con 10-12 años se puede comprobar si acierta el 80 % de las veces, y es lo bastante estrecho para ayudar a decidir. Un 95 % dependería de los pocos casos extremos (a 1 año, 2 o 3 episodios independientes).
- **Idea aprobada por Pablo:** medir también el 50 % y el 95 %, solo como información, sin cambiar el principal.
- Plan aprobado: rango ingenuo como referencia; candidato A (rango según la volatilidad, D8) sin entrenar; candidato B (redes que dan el rango) según cómo salga el A. El diseño detallado, la regla y lo esperado se apuntan antes de calcular.
- **1 semana:** para comprobar el rango con 11 años en lugar de 3, Pablo lanza la validación hacia atrás de 1 semana (`python scripts/hacia_atras.py --horizontes corto`, unas 2-4 h). Mientras, el candidato A se hace a 3 meses y a 1 año.

**Diseño del candidato A** (D30, fijado antes de calcular; solo con previsiones fuera de muestra de 2010-2021, sin tocar el test)
- **Errores con los que se ajusta:** los de las previsiones de cada red (promedio de las semillas 42-46) y del lineal en 2010-2021 (validación hacia atrás y validación). El rango de un año se ajusta **solo con errores ya conocidos al empezar ese año**: los de fichas cuya respuesta llegó antes del 1 de enero. Por eso se evalúa desde 2011 a 3 meses (11 años) y desde 2012 a 1 año (2012-2016 y 2018-2020, 8 años).
- **Tres rangos que se comparan**, todos del 80 %:
  - **rango ingenuo (la referencia):** centrado en el precio de hoy, con los percentiles 10 y 90 de las variaciones a h sesiones de todos los años anteriores (desde 2000). Misma anchura en calma y en tormenta;
  - **rango fijo alrededor de la red:** centrado en la previsión de la red, con los percentiles 10 y 90 de sus errores pasados. Separa el efecto de centrar en la red del de usar la volatilidad;
  - **A, rango según la volatilidad:** centrado en la previsión de la red, con los percentiles 10 y 90 de sus errores pasados divididos por la volatilidad del momento (la de 21 días, llevada al horizonte con la raíz del tiempo), y multiplicados por la volatilidad de hoy. Más ancho en tormenta y más estrecho en calma (D8).
- **Medidas:** cobertura (cuántas veces el precio real quedó dentro), anchura media (en % del precio), y una nota que junta las dos: la anchura más un castigo de 10 veces lo que el precio se sale (la puntuación habitual de los intervalos, con α = 0,2). Por años, con todos los años juntos y por tercios de volatilidad (calma, normal y tormenta).
- **Regla** (en cada horizonte, con la media de las tres redes): se elige el rango con mejor nota entre los que aciertan entre el 75 % y el 85 % de las veces en total y al menos el 70 % en cada tercio de volatilidad. Si ninguno cumple, el de mejor nota, diciendo que su cobertura no es la prometida. Si gana el rango ingenuo, la aplicación usa ese y lo dice.
- **Solo como información:** la cobertura de los rangos del 50 % y del 95 % con el mismo método.

**Lo esperado** (apuntado antes de calcular)
- **Rango ingenuo:** en total, cerca del 80 %, pero desigual: más del 90 % en calma y menos del 65 % en tormenta.
- **Rango fijo alrededor de la red:** parecido al ingenuo, porque la red está casi en el precio de hoy.
- **A:** entre el 78 % y el 82 % en total, y más parejo entre calma y tormenta (70-85 %). Nota entre un 5 % y un 15 % mejor que el ingenuo a 3 meses; a 1 año, poca mejora o ninguna (0-5 %), porque la volatilidad de hoy dice poco de la de dentro de un año.

**Resultados del candidato A** (con un script de trabajo y `incertidumbre.py`; todavía no está en el notebook. Media de las tres redes; 3 meses en 2011-2021 y 1 año en 2012-2016 y 2018-2020)

| | Cobertura | Calma | Normal | Tormenta | Anchura (% del precio) | Nota frente al ingenuo |
|---|---|---|---|---|---|---|
| 3 meses · rango ingenuo | 77 % | 77 % | 87 % | 68 % | 44 % | 1 |
| 3 meses · fijo alrededor de la red | 70 % | 66 % | 79 % | 65 % | 36 % | 0,96 |
| 3 meses · A (volatilidad) | 76 % | **55 %** | 82 % | **90 %** | 55 % | 0,955 |
| 1 año · rango ingenuo | 67 % | 62 % | 78 % | 63 % | 98 % | 1 |
| 1 año · fijo alrededor de la red | 52 % | 35 % | 57 % | 63 % | 84 % | 1,13 |
| 1 año · A (volatilidad) | 60 % | 32 % | 61 % | 86 % | 248 % | 1,72 |

- **Ninguno cumple la regla en ningún horizonte.** Aplicándola (el de mejor nota si ninguno cumple): a 3 meses, A (un 4,5 % mejor nota que el ingenuo, pero sin la cobertura prometida); a 1 año, el rango ingenuo (que acierta solo el 67 %).
- **A exagera la volatilidad:**
  - en calma se queda corto (55 % a 3 meses) y en tormenta se pasa (90 %);
  - a 1 año da rangos absurdos en las tormentas (de más del 200 % del precio).
- **La volatilidad se calma con el tiempo.** La de hoy guía bien la próxima semana, solo en parte los próximos 3 meses y casi nada el año siguiente. Multiplicar el rango por la volatilidad de hoy, como decía D8, exagera en los horizontes largos.
- **Las grandes caídas empiezan en calma.** A mediados de 2014 y a finales de 2019 la volatilidad era baja, y el rango estrecho de A no vio venir la caída. Por eso A falla justo en calma.
- **A 1 año, ningún rango es fiable.** Hasta el rango ingenuo se queda en el 67 %. En 2014 no acertó ninguno (0 %): la caída de un 50 % en un año se salió de todo. Con 8 años de evaluación hay unos 8 movimientos anuales independientes, que no bastan para ajustar un rango del 80 %.
- Los modelos con errores propios tienen, además, poco con lo que ajustarse al principio: en 2012, a 1 año, solo los errores de 2010. Sale sesgado, y su cobertura es del 0 %.
- **Niveles, como información** (RNN):
  - 3 meses: el 50 % cubre el 46 % (ingenuo) y el 46 % (A); el 95 % cubre el 92 % y el 90 %;
  - 1 año: el 50 % cubre el 26 % y el 39 %; el 95 %, el 90 % y el 70 %.
- **Lo esperado frente a lo obtenido:**
  - el rango ingenuo, como se esperaba, aunque menos desigual en calma;
  - A, no: esperaba que fuera más parejo entre calma y tormenta, y es más desigual;
  - a 3 meses mejora la nota un 4,5 % (esperaba un 5-15 %); a 1 año, mucho peor (esperaba un empate).

**Diseño de A2** (fijado antes de calcular, tras ver el fallo de A)
- **Idea:** como A, el rango se ensancha con la volatilidad, pero solo lo que dura de verdad el nerviosismo, aprendido del pasado. Cada año, con las variaciones ya conocidas, se mide la «memoria» m: cuánto anticipa la volatilidad de hoy el tamaño de los movimientos siguientes. Es la pendiente de una regresión del logaritmo del tamaño del movimiento sobre el logaritmo de la volatilidad relativa a la normal (la mediana), limitada entre 0 y 1. Con m = 0, el rango es fijo; con m = 1, es como A. El ancho se multiplica por (volatilidad de hoy / normal) elevado a m.
- **Con qué se ajusta:** con todas las variaciones a h sesiones conocidas antes de cada año, desde 2001, como el rango ingenuo. Los errores de las redes solo existen desde 2010 y no conocen la caída de 2008; como la previsión de la red está casi en el precio de hoy, esas variaciones hacen de errores pasados.
- **Centro:** la previsión de cada red. Comparado con el ingenuo, solo cambia el centro (muy poco) y el ancho según la volatilidad con memoria.
- **Regla:** la misma de D30, ahora con cuatro rangos (ingenuo, fijo, A y A2).
- **Las redes que dan el rango (B), después, y solo si mejoran a A2** (decisión de Pablo).
- **Cautela:** A2 se define después de ver fallar a A. Para no ajustarlo a mano a lo que salga, su único parámetro, la memoria, se aprende de los datos pasados.

**Lo esperado de A2** (apuntado antes de calcular)
- **Memoria:** a 3 meses, entre 0,3 y 0,6; a 1 año, entre 0 y 0,3. A 1 semana, cuando la tengamos, entre 0,7 y 0,9.
- **3 meses:** acierta el 77-82 % en total, al menos el 70 % en calma y el 75 % en tormenta. Nota entre un 3 % y un 10 % mejor que el ingenuo, y debería cumplir la regla.
- **1 año:** casi como el ingenuo (memoria baja), con una cobertura del 67-70 %. Como el ingenuo, no cumpliría la regla: a 1 año ningún rango es fiable.

**Resultados de A2** (media de las tres redes; mismos años que A)

| | Cobertura | Calma | Normal | Tormenta | Anchura | Nota frente al ingenuo |
|---|---|---|---|---|---|---|
| 3 meses · rango ingenuo | 77 % | 77 % | 87 % | 68 % | 44 % | 1 |
| 3 meses · **A2** | **78 %** | 63 % | 87 % | **83 %** | 45 % | **0,876** |
| 1 año · rango ingenuo | 67 % | 62 % | 78 % | 63 % | 98 % | 1 |
| 1 año · **A2** | **73 %** | 58 % | 78 % | **84 %** | 102 % | **0,762** |

- **A2 es el de mejor nota en los dos horizontes:** un 12 % mejor que el ingenuo a 3 meses y un 24 % a 1 año, con casi la misma anchura media. Acierta mucho más en las tormentas (83-84 % frente a 63-68 %), y el año que más gana es 2020 (a 3 meses, 57 % frente a 34 %; a 1 año, 75 % frente a 33 %).
- **Sigue sin cumplir la regla:** en calma se queda en el 63 % (3 meses) y el 58 % (1 año), por debajo del 70 %. Las grandes caídas empiezan en calma (2014, 2020), y ningún rango basado en la volatilidad puede verlas venir. En 2014, a 1 año, ningún rango acertó ni una vez.
- **Aplicando la regla** (si ninguno cumple, el de mejor nota, diciéndolo): **A2 en los dos horizontes**, avisando de que en calma acierta menos de lo prometido.
- **Memoria aprendida:**
  - 3 meses: entre 0,41 y 0,61 según el año;
  - 1 año: entre 0,37 y 1. En 2014 y 2015 vale 1 porque la caída de 2008 enseñó que, tras una tormenta, llega un año de grandes movimientos.
- **Niveles, como información** (A2):
  - 3 meses: el 50 % cubre el 43 % y el 95 %, el 94 %;
  - 1 año: el 50 % cubre el 31 % y el 95 %, el 87 %.
- **Lo esperado frente a lo obtenido:**
  - 3 meses: la memoria y la cobertura, como se esperaba; la calma, peor (63 % frente a al menos el 70 %); la nota, mejor de lo esperado (12 % frente a 3-10 %);
  - 1 año: mejor de lo esperado (73 % y nota un 24 % mejor, frente a «casi como el ingenuo»), con más memoria de la esperada (0,37-1 frente a 0-0,3).

**Diseño de B: redes que dan el rango** (decisión de Pablo: probarlo; fijado antes de calcular)
- **Qué cambia en la red:** en lugar de un número, da tres, los percentiles 10, 50 y 90 de la variación a h sesiones. El 50 es la previsión central y el 10 y el 90, el rango del 80 %. Se entrena con la pérdida por cuantiles («pinball»), la que premia que cada percentil caiga donde debe. Si al prever los tres salen desordenados, se ordenan.
- **Todo lo demás igual:** las configuraciones elegidas en la fase B (sin volver a buscar), los mismos datos de cada horizonte, sin tendencia, la misma parada temprana (ahora con la pérdida por cuantiles) y las semillas 42-46. El rango de las cinco semillas es la media de sus percentiles.
- **Años:** se entrena en 2010-2021 (hacia atrás y validación), a 3 meses y a 1 año. Unos 330 entrenamientos, unos 20-30 minutos.
- **Candidato B:** los percentiles 10 y 90 que da la red, sin más ajuste: la red ya aprende de todos los años anteriores, incluida la caída de 2008. Como información, B ajustado con sus propios errores pasados ya conocidos (solo existen desde 2010).
- **Regla:** la de D30, en los mismos años que A2. **B solo se adopta si mejora a A2** (decisión de Pablo): mejor nota que A2 y que cumpla las condiciones de cobertura al menos tan bien como A2.

**Lo esperado de B** (apuntado antes de calcular)
- **No mejora a A2.** Las redes ven más cosas que la volatilidad, pero la criba con datos hasta 2017 no encontró nada que avise de las caídas.
- **Sin ajustar, la cobertura se aleja del 80 %.** A 1 año las redes paraban en la primera época y casi no aprendían, así que el rango puede salir demasiado estrecho.
- **En calma no mejora:** seguirá por debajo del 70 %.

**Resultados de B** (`rango_redes.py`, `scripts/rango_redes.py`: 330 entrenamientos en 54 minutos, lanzados por mí; mejor época mediana, la 5.ª. Media de las tres redes, mismos años que A2)

| | Cobertura | Calma | Normal | Tormenta | Anchura | Nota frente al ingenuo |
|---|---|---|---|---|---|---|
| 3 meses · A2 | 78 % | 63 % | 87 % | 83 % | 45 % | **0,876** |
| 3 meses · B | 72 % | 64 % | 78 % | 73 % | 36 % | 0,918 |
| 3 meses · B ajustado (información) | 72 % | 63 % | 80 % | 74 % | 37 % | 0,920 |
| 1 año · A2 | **73 %** | 58 % | 78 % | **84 %** | 102 % | 0,762 |
| 1 año · B | 71 % | **76 %** | 78 % | 57 % | 69 % | **0,746** |
| 1 año · B ajustado (información) | 73 % | 81 % | 80 % | 60 % | 77 % | 0,772 |

- **3 meses: B no mejora a A2.** Su rango es más estrecho (36 % frente a 45 %) y acierta menos (72 %), sobre todo en las tormentas.
- **1 año: B tiene una nota un 2 % mejor, pero no mejora a A2 en cobertura.** Acierta menos en total (71 % frente a 73 %) y su peor tercio es algo peor (57 % en tormenta frente a 58 % en calma). Además, la ventaja depende de la red: con la RNN y la LSTM, B es mejor (144 frente a 152 y 161); con la GRU, peor (168 frente a 153).
- **B y A2 fallan en situaciones opuestas:**
  - B acierta en calma y falla en tormenta: en 2020, a 1 año, acierta el 24 % (A2, el 74 %);
  - A2 al revés: en 2014, a 1 año, B acierta el 70 % y A2 nada.
- **Lo esperado frente a lo obtenido:**
  - a 3 meses, como se esperaba: no mejora a A2 y su cobertura se aleja del 80 %;
  - a 1 año, no se cumple que fallara en calma: es al revés, acierta en calma y falla en tormenta. Tampoco que el rango saliera demasiado estrecho por parar en la 1.ª época: con la pérdida por cuantiles, la mejor época mediana es la 5.ª.

**Decisiones**
- **Con la regla de D30 y la condición de Pablo** (B solo si mejora a A2 en nota y en cobertura), **se queda A2 en los dos horizontes.**
  - A 3 meses, B tiene peor nota.
  - A 1 año, la nota de B es un 2 % mejor, pero cubre peor y depende de la red.
  - En ninguno de los dos horizontes cumple nadie la regla del todo: en la aplicación habrá que decir que en calma (A2) el rango acierta menos de lo prometido.
- **Para preguntar a la revisión externa:** combinar A2 y B, que fallan en situaciones opuestas. Habría que hacerlo con una regla fijada antes, porque probar mezclas contra los mismos años es ajustar a la validación.
- **Pendiente:** 1 semana, cuando termine la validación hacia atrás de 1 semana; la sección 12 del notebook; las pruebas y el commit.

**Resultados de B** (330 entrenamientos en 54 minutos; lanzado por mí en segundo plano y no interrumpido al reanudarse la sesión. Media de las tres redes, mismos años que A2)

| | Cobertura | Calma | Normal | Tormenta | Anchura | Nota frente al ingenuo |
|---|---|---|---|---|---|---|
| 3 meses · A2 | 78 % | 63 % | 87 % | 83 % | 45 % | **0,876** |
| 3 meses · B (redes) | 72 % | 64 % | 78 % | 73 % | 36 % | 0,918 |
| 1 año · A2 | **73 %** | 58 % | 78 % | **84 %** | 102 % | 0,762 |
| 1 año · B (redes) | 71 % | **76 %** | 78 % | 57 % | 69 % | **0,746** |

- **3 meses: B es peor que A2.** Su rango es más estrecho (36 % frente a 45 %), pero acierta menos (72 %), y su nota es peor (0,918 frente a 0,876).
- **1 año: B tiene una nota algo mejor que A2** (0,746 frente a 0,762, un 2 %), **pero cumple peor las condiciones de cobertura:** acierta menos en total (71 % frente a 73 %) y su peor tercio también es más bajo (57 % frente a 58 %). Además, la diferencia de nota es pequeña y varía mucho de una red a otra: con la GRU, B es peor que A2 (nota 168 frente a 153).
- **Aplicando la regla** («B solo se adopta si mejora a A2»: mejor nota y cobertura al menos tan buena): **B no se adopta en ningún horizonte. Se queda A2 en los dos.**
- **Lo interesante: a 1 año, B y A2 fallan en momentos opuestos.**
  - B acierta en calma (76 %) y falla en tormenta (57 %); A2, al revés (58 % y 84 %).
  - B cubre la caída de 2014 (75 %, frente al 0 % de todos los demás) y 2015, pero falla en 2019-2020 (37 % y 30 %).
  - Combinarlos ahora sería elegir después de ver los resultados (problema 5); no se hace.
- Las redes que dan el rango aprenden más que las de un número: a 1 año, su mejor época mediana es la 4.ª-6.ª, frente a la 1.ª. Su percentil 50, como previsión central, no mejora al ingenuo a 3 meses (1,05) y a 1 año da 0,93-0,99.
- Ajustar B con sus errores pasados (solo información) apenas cambia nada a 3 meses y a 1 año sube la cobertura al 73 %, con peor nota.
- **Lo esperado frente a lo obtenido:**
  - B no mejora a A2 y su cobertura sin ajustar se aleja del 80 % (71-72 %), como se esperaba;
  - lo que no esperaba: a 1 año acierta mejor en calma (76 %) que A2, aunque falla más en tormenta.

**Decisiones**
- **D30: el rango del 80 % es A2 (volatilidad con memoria) a 3 meses y a 1 año.** Ninguno cumple del todo la regla: en calma A2 acierta menos de lo prometido (63 % y 58 %). La aplicación debe decirlo, y a 1 año el rango se presenta como orientativo.
- Las redes que dan el rango no se adoptan. Respuesta a H3 (el modelo aporta más en el riesgo que en la dirección): se cumple en parte. El rango que mejor funciona depende de la volatilidad, pero lo construye una regla sencilla, no las redes.
- 1 semana: pendiente de la validación hacia atrás (opción 2), con el mismo método (A2).

### 12/11/2026 (noche) · Comprobaciones del método y del rango

**Hecho**
- **Los rangos fallan mucho más por abajo que por arriba** (lo prometido es un 10 % por cada lado):

  | | Falla por abajo | Falla por arriba |
  |---|---|---|
  | 3 meses · ingenuo | 14 % | 8 % |
  | 3 meses · A2 | 17 % | 5 % |
  | 1 año · ingenuo | 23 % | 10 % |
  | 1 año · A2 | 23 % | 4 % |
  | 1 año · B (redes) | 17 % | 12 % |

  - El rango ingenuo y A2 usan las variaciones pasadas **sin centrar**, así que llevan dentro la subida media histórica (a 1 año, una mediana del +9 % entre 2001 y 2017). Eso empuja el rango hacia arriba, y no es coherente con D20 (sin tendencia).
  - B, que se entrena sin tendencia, está más equilibrado.
  - Se corregirá en A3 (ver más abajo).

**Diseño de D31: las redes, reentrenadas con todo el entrenamiento** (fijado antes de calcular)
- **El problema:**
  - la red se entrena con el 85 % inicial del entrenamiento, usa el 15 % final solo para decidir cuándo parar, y después **no se reentrena con todo**;
  - además, la purga quita otro trozo antes del de parada. Por ejemplo, para prever 2020 a 1 año, la red aprende con fichas hasta mediados de 2015, mientras que el lineal aprende con todo;
  - la comparación con el lineal no es del todo justa, y el modelo final de la aplicación también se quedaría sin los últimos años.
- **El experimento:** cada red se entrena con **todo** el entrenamiento (purgado como siempre), sin trozo de parada, durante un **número fijo de épocas**: la mediana de sus «mejores épocas» en la estabilidad (10 semillas y 4 años), redondeada.
  - 3 meses: RNN 7, LSTM 4 y GRU 6;
  - 1 año: 1 época en las tres;
  - todo lo demás, igual: configuraciones de la fase B, sin tendencia y semillas 42-46.
- **Dónde:** 2010-2021 (validación hacia atrás y validación), a 3 meses y a 1 año. 1 semana, más adelante.
- **Solo como información:** la RNN con 3 y con 10 épocas fijas, en los dos horizontes.
- **Regla:** la versión con todo el entrenamiento sustituye a la actual si, con todos los años (12 a 3 meses y 10 a 1 año), la media de las tres redes mejora la nota con los años juntos y gana al ingenuo en al menos tantos años como ahora. Con la versión que quede se repite el veredicto de D29.
- **Lo esperado:**
  - **3 meses:** poco cambio (±0,02). Quizá algo mejor en 2018-2021, por ver los años recientes, pero el veredicto no cambia (dudosa);
  - **1 año:** con 1 sola época, las redes siguen casi sin aprender: casi igual que ahora (0,98) y el veredicto no cambia;
  - **con 10 épocas a 1 año** (solo información), peor: aprenden demasiado de pocos episodios.

**Comprobaciones de robustez** (`comprobaciones.py`, con las previsiones guardadas; el test no se toca)
- **Intervalo de la nota remuestreando bloques de 2 años contiguos** (los años vecinos comparten respuestas solapadas):
  - 3 meses: redes 0,95-1,11 (antes 0,96-1,10);
  - 1 año: redes 0,88-1,14; lineal 0,78-1,19.
  - El veredicto de D29 no cambia.
- **La nota con otras medidas** (12 años a 3 meses y 10 a 1 año):

  | | MAE en $ (la de siempre) | RMSE en $ | MAE en variación (%) | Mediana de los años |
  |---|---|---|---|---|
  | 3 meses · RNN · LSTM · GRU | 0,994 · 1,044 · 1,030 | 1,006 · 1,052 · 1,044 | 0,962 · 0,987 · 0,976 | 0,958 · 0,989 · 0,989 |
  | 3 meses · lineal | 1,020 | 0,994 | 0,991 | 1,028 |
  | 1 año · RNN · LSTM · GRU | 0,966 · 1,017 · 0,968 | 0,939 · 0,996 · 0,939 | 0,937 · 0,966 · 0,941 | 1,036 · 1,114 · 1,043 |
  | 1 año · lineal | 0,928 | 0,879 | 0,897 | 1,082 |

  - En variación (que no da más peso a los años de 100 $), las redes salen algo mejor a 3 meses (0,96-0,99).
  - Con la mediana de los años, a 1 año pierden en un año típico (1,04-1,11).
  - Nada cambia el veredicto: **no hay evidencia de ventaja.** Con 12 años, solo se detectarían mejoras de alrededor del 8 % o más, así que una mejora real más pequeña podría pasar desapercibida. La conclusión se dirá así: «sin evidencia de ventaja», no «sin ventaja».
- **Contraste de Diebold-Mariano** (error absoluto en $ frente al ingenuo, con varianza corregida por el solapamiento):
  - 3 meses y 1 año: ningún modelo se distingue del ingenuo (p de 0,19 a 0,83);
  - 1 semana, solo con 2018-2021: la LSTM y la GRU quedan justo en el límite (p = 0,046 y 0,049; unos 3 céntimos menos de error). Pero son los años con los que se eligieron, y se comparan cuatro modelos. La validación hacia atrás de 1 semana lo aclarará.
- **Redes por parejas, año a año:**
  - 3 meses: la RNN gana a la LSTM 8 de 12 años y a la GRU otros 8 de 12; la LSTM y la GRU, 6 de 12 cada una;
  - 1 año: la RNN gana a la LSTM 7 de 10 y a la GRU 6 de 10; la GRU gana a la LSTM 8 de 10.
  - 8 de 12 pasa por azar casi una vez de cada cinco: **las tres redes son indistinguibles**, con la RNN ligeramente por delante.
- **Margen de las coberturas** (error típico, contando solo fichas independientes): ±6,5 puntos en total y ±11 por tercio a 3 meses; **±16 en total y ±32 por tercio a 1 año**. A 1 año, los filtros de cobertura de la regla no distinguen un método de otro. La regla no se cambia, porque estaba fijada, pero los márgenes acompañarán a las coberturas.
- **B frente a A2, año a año:**
  - B tiene mejor nota la mayoría de los años: 8 de 11 a 3 meses y 6 de 8 a 1 año;
  - pero se hunde en las tormentas fuertes: en 2020, 255 frente a 175 a 3 meses y 498 frente a 219 a 1 año. Con los años juntos, esas tormentas deciden;
  - B es más eficiente en tiempos normales; A2 acierta cuando más importa.
- **La memoria de A2, con un método robusto** (medianas del tamaño del movimiento por deciles de volatilidad):
  - 3 meses: casi igual (0,35-0,65 frente a 0,41-0,61);
  - 1 año: en los últimos años, casi 0 (2016: 0,19; 2018-2020: 0,02-0,10, frente a 0,37-0,47 con la regresión). La regresión directa se deja llevar por los movimientos casi nulos;
  - **la ventaja de A2 a 1 año depende de cómo se estime la memoria:** es frágil.
- **Suelo en calma, comprobado solo con datos hasta 2009** (antes de todos los años evaluados):
  - por debajo de la volatilidad mediana, la memoria es 0 en los dos horizontes: la calma de hoy no anticipa movimientos más pequeños después;
  - por encima, a 3 meses es casi 1 (las tormentas duran); a 1 año, 0 con el método robusto y 0,5 con la regresión.

**Diseño de A3** (fijado antes de calcular)
- **Centro:** la previsión de la red, como A2.
- **Ancho simétrico y sin tendencia:** ± el percentil 80 de |variación pasada escalada − su mediana|, con todas las variaciones conocidas antes de cada año desde 2001. Así se quita la subida media histórica y cada lado tiene la mitad de los fallos.
- **Escala con suelo:** (máximo(volatilidad de hoy, normal) / normal) elevado a m. En calma no se estrecha, como justifican los datos hasta 2009.
- **La memoria m se estima solo con los días de volatilidad por encima de la normal,** con el método robusto, cada año y con lo ya conocido.
- **Regla:** la de D30, con A3 entre los candidatos. A3 sustituye a A2 si gana con esa regla.
- **Lo esperado:**
  - fallos equilibrados (alrededor del 10 % por cada lado) y mejor cobertura en calma, cerca del 75 % a 3 meses;
  - nota parecida a la de A2 a 3 meses;
  - a 1 año, con una memoria robusta casi nula, parecido al rango ingenuo pero centrado, con un 70-75 % de cobertura.

**Estado al cerrar la sesión** (12/11/2026, noche)
- **D31 en marcha:** `python scripts/entreno_completo.py`, 550 entrenamientos que se guardan según terminan. Si se corta, se relanza igual y continúa. Falta analizarlo con su regla.
- **A3:** diseñado y apuntado arriba; falta calcularlo (en `incertidumbre.py` todavía no existe).
- **1 semana:** falta lanzar la validación hacia atrás (`python scripts/hacia_atras.py --horizontes corto`), y después aplicarle los rangos.
- **Notebook 03, sección 12 (incertidumbre):** el código está preparado en el generador, pero falta ejecutarlo y escribir la lectura. Faltan también secciones para D31 y para las comprobaciones de robustez.
- **Pruebas pendientes:** `comprobaciones.py` y `entreno_completo.py`. `incertidumbre.py` y `rango_redes.py` ya las tienen (93 pruebas, todas correctas).
- **Commit pendiente,** con el visto bueno de Pablo: todo lo posterior a `78b8e44` (sección 11, incertidumbre, redes que dan el rango, D31 y comprobaciones).

### 12/11/2026 (noche) · Resultado de D31 y A3

**Resultados de D31** (550 entrenamientos en 7,7 minutos; media de las tres redes, promedio de las semillas 42-46)

| | Versión actual | Con todo el entrenamiento |
|---|---|---|
| 3 meses (12 años) | 1,023 · gana 7 de 12 · dudosa | 1,048 · gana 6 de 12 · no se sostiene |
| 1 año (10 años) | 0,984 · gana 4 de 10 · no se sostiene | **0,956 · gana 6 de 10 · dudosa** (bloques de 2 años: 0,93-1,02) |

- **A 1 año, entrenar con todo mejora y estabiliza:** desaparecen los años desastrosos (2010: de 1,25 a 0,93; 2012: de 1,52 a 1,00), aunque empeora algo en 2018-2020 (de 0,89-0,91 a 0,96-0,98). El lineal sigue por delante (0,928).
- **A 3 meses empeora,** sobre todo en 2012-2013 (de 1,39 a 1,65 y de 1,05 a 1,42).
- **Solo información:** la RNN con 3 épocas fijas da 0,988 a 3 meses y **0,893 a 1 año**; con 10 épocas, 1,013 y 0,923. Sugiere que con 1 época la red de 1 año aprende poco, pero elegir 3 épocas después de verlo sería ajustar a la validación. **No se adopta.**
- **Lo esperado frente a lo obtenido:**
  - a 3 meses esperaba poco cambio y empeora 0,025;
  - a 1 año esperaba casi lo mismo y mejora (0,984 → 0,956) y cambia el veredicto;
  - con 10 épocas a 1 año esperaba peor que con 1, y sale mejor (0,923 frente a 0,941).

**Decisiones**
- **Con la regla de D31:** a 1 año, las redes se entrenan con todo el entrenamiento y 1 época fija; a 3 meses se mantiene la versión con parada temprana. El veredicto de 1 año pasa a «dudosa».
- **El modelo final de la aplicación** se entrenará de la misma forma: con todo, hasta el último dato.

**Resultados de A3** (media de las tres redes; mismos años que A2; centros con las redes de siempre)

| | Cobertura | Calma | Normal | Tormenta | Anchura | Nota frente al ingenuo | Falla abajo · arriba |
|---|---|---|---|---|---|---|---|
| 3 meses · A2 | 78 % | 63 % | 87 % | 83 % | 45 % | 0,876 | 17 % · 5 % |
| 3 meses · **A3** | **79 %** | **71 %** | 82 % | 84 % | 49 % | **0,873** | 16 % · 5 % |
| 1 año · A2 | 73 % | 58 % | 78 % | 84 % | 102 % | 0,762 | 23 % · 4 % |
| 1 año · **A3** | 71 % | 62 % | 72 % | 80 % | 106 % | **0,706** | 26 % · 3 % |

- **3 meses: A3 cumple la regla entera,** el primer rango que lo consigue: 79 % en total y al menos el 70 % en cada tercio. El suelo en calma sube la cobertura en calma de 63 % a 71 % sin perder en tormenta. Es algo más ancho que A2, con una nota igual o mejor.
- **1 año: A3 tiene la mejor nota de todos** (0,706, frente a 0,762 de A2 y 0,746 de B), pero ningún rango cumple la regla a 1 año.
- **Memoria aprendida** (solo días nerviosos, método robusto): 1 todos los años a 3 meses (una tormenta dura los 3 meses enteros) y 0,46-0,71 a 1 año.
- **Los fallos siguen cargados hacia abajo,** aunque A3 está centrado y sin tendencia. Ya no es por la subida media del pasado: en 2010-2021 el Brent cayó más de lo que subió, y un rango centrado en el precio de hoy falla más en las caídas de esa década.
- **Niveles, como información:** a 3 meses, el 50 % cubre el 49 % y el 95 %, el 93 %; a 1 año, el 51 % y el 98 %.
- **Lo esperado frente a lo obtenido:**
  - calma a 3 meses cerca del 75 %: 71 %;
  - nota parecida a la de A2: se cumple;
  - a 1 año, el 70-75 %: se cumple, y con mejor nota de la esperada;
  - fallos equilibrados por arriba y por abajo: **no se cumple.**

**Decisiones**
- **Con la regla de D30, se adopta A3 en los dos horizontes:** a 3 meses, cumpliendo la regla; a 1 año, por tener la mejor nota, diciendo que su cobertura (71 %, con un margen de unos ±16 puntos) no es la prometida y que el rango es orientativo.
- **Para la aplicación:** el rango de 1 año se presentará como escenarios, con la cobertura y su margen y el caso malo de 2014 a la vista. Las redes de 1 año se entrenarán con todo el entrenamiento (D31).
- **Hecho después:** notebook 03 con las secciones 12 (rango del 80 %) y 13 (robustez y D31), ejecutado sin errores; pruebas de `comprobaciones.py` y `entreno_completo.py` (101 pruebas, todas correctas); README al día.

**Estado al cerrar la sesión** (12/11/2026, noche)
- **1 semana en marcha:** `python scripts/hacia_atras.py --horizontes corto`, 120 entrenamientos (RNN, LSTM y GRU, 2010-2017, semillas 42-46). Si se corta, se relanza igual y continúa. Después: su criterio de D29 y los rangos a 1 semana.
- **Repetir los rangos** con las redes de 1 año de D31 como centro (cambia poco, porque el ancho no depende del centro).
- **Commit pendiente,** con el visto bueno de Pablo, cuando termine la de 1 semana (antes, los `hacia_atras*.csv` irían a medias): todo lo posterior a `78b8e44`.

### 13/11/2026 · 1 semana: validación hacia atrás y rango

- Commit de lo anterior (sección 11, incertidumbre, redes que dan el rango, D31, comprobaciones, secciones 12-13 del notebook): hecho y subido a GitHub (`29e3b4a`).
- La validación hacia atrás de 1 semana terminó: 120 entrenamientos en 75 minutos (RNN, LSTM y GRU elegidas en la fase B, 2010-2017, semillas 42-46, nada posterior a 2017).

**Diseño** (fijado antes de calcular)
- **Criterio:** el de D29 a 3 meses, que también tiene 12 años (8 hacia atrás y 4 de validación), con la media de las tres redes:
  - **ventaja real:** gana al ingenuo en 9 o más años y queda por debajo de 1 con los años juntos;
  - **dudosa:** gana 7 u 8;
  - **no se sostiene:** gana 6 o menos.
- **Rango del 80 %:** los mismos candidatos y la misma regla de D30 que a 3 meses y a 1 año.

**Lo esperado** (apuntado antes de calcular)
- **Redes:** entre 0,99 y 1,01 con los 12 años, ganando unos 6: «no se sostiene» o, como mucho, «dudosa». El lineal, parecido.
- **La pequeña ventaja de la LSTM y la GRU en 2018-2021** (Diebold-Mariano, p ≈ 0,05) se diluye con los 12 años: p por encima de 0,10.
- **Rango A3:**
  - cobertura entre el 78 y el 82 %, con calma y tormenta más parejas que a 3 meses;
  - memoria entre 0,7 y 0,9 (ya apuntado en D30);
  - nota frente al rango ingenuo mejor que a 3 meses (entre 0,80 y 0,87), porque a una semana la volatilidad de hoy dice más.

**Resultados: la previsión** (media de las tres redes, promedio de las semillas 42-46)

| | 2010-2017 | 2018-2021 (validación) | Todos los años | Años que gana | Veredicto |
|---|---|---|---|---|---|
| 1 semana · redes | 1,009 | 0,990 | 1,002 (0,99-1,01) | 8 de 12 | **dudosa** |
| 1 semana · lineal | 1,002 | 0,993 | 0,999 (0,99-1,01) | 7 de 12 | dudosa |

- **«Dudosa» por la regla, igual que el ingenuo en la práctica:**
  - gana 8 años, pero por muy poco (entre 0,980 y 0,999), y pierde 2011 por más (1,040);
  - con los años juntos queda en 1,002: la previsión media de las tres se equivoca lo mismo que el ingenuo (0,01 céntimos de diferencia por previsión);
  - ganar 8 o más de 12 años sin ninguna ventaja pasa el 19 % de las veces;
  - la regla de D29 no previó este caso (muchos años ganados por poco y la nota con los años juntos por encima de 1). No se cambia, pero se dice.
- **La ventaja de la LSTM y la GRU en 2018-2021 desaparece:** con los 12 años, ninguna red se distingue del ingenuo (Diebold-Mariano: p entre 0,25 y 0,45; la media de las tres, 0,99). En 2010-2017, la RNN y la GRU se equivocan algo más que el ingenuo (p = 0,06 y 0,08).
- **La LSTM es la más regular:** 0,997 con los 12 años, gana 8, y queda por delante de la GRU en 9 de los 12. Las diferencias, de menos del 1 %.
- **La media de las tres no se adopta a 1 semana** (regla de D29): no mejora a la LSTM (1,000 frente a 0,997).
- **Peor año: 2011,** en las tres redes (entre 1,03 y 1,07).
- **Otras medidas** (RMSE, error en %, mediana de los años): todas entre 0,994 y 1,007.

**Resultados: el rango del 80 %** (media de las tres redes; 2011-2021, porque el primer año no tiene errores anteriores)

| | Cobertura | Calma · normal · tormenta | Anchura | Nota / ingenuo |
|---|---|---|---|---|
| ingenuo | 84 % | 96 · 84 · 72 | 12,4 % | 1,000 |
| fijo | 76 % | 89 · 77 · 62 | 9,7 % | 0,993 |
| volatilidad (A) | 80 % | 74 · 79 · 87 | 12,9 % | 0,893 |
| **memoria (A2)** | **82 %** | **82 · 81 · 84** | 12,1 % | **0,871** |
| centrado (A3) | 84 % | 93 · 81 · 78 | 12,3 % | 0,904 |

- **Margen de la cobertura:** ±1,6 puntos (a 1 semana hay muchas fichas independientes: 555).
- **Con la regla de D30 gana A2:** cumple (82 %, peor tercio 81 %) y tiene la mejor nota. A3 también cumple, pero se pasa en calma (93 %).
- **Por qué A3 no gana aquí:** su suelo (no estrechar el rango por debajo de la volatilidad normal) se apoyaba en que a 3 meses y a 1 año la calma no dura. A una semana sí dura, y el rango de A3 queda demasiado ancho en calma. A2, sin suelo, queda parejo.
- **A2 es el más estable por años:** entre el 75 % (2020) y el 89 % (2019). El ingenuo va del 59 % (2020) al 100 % (2013).
- **Memoria:** A2, entre 0,61 y 0,83; A3, entre 0,58 y 0,98.
- **Fallos casi equilibrados** (A2): 9,6 % por abajo y 8,1 % por arriba.
- **Niveles, como información** (A2): el 50 % cubre el 53 % y el 95 %, el 95 %.

**Lo esperado frente a lo obtenido**
- Redes entre 0,99 y 1,01, ganando unos 6 años: 1,002 y 8 años. «Dudosa», el extremo alto de lo previsto.
- La ventaja de la LSTM y la GRU se diluye (p por encima de 0,10): se cumple (0,45 y 0,39).
- Rango A3:
  - cobertura del 78-82 %: 84 %;
  - calma y tormenta más parejas que a 3 meses: **no se cumple** (93 y 78);
  - memoria entre 0,7 y 0,9: más o menos (A3, 0,58-0,98; A2, 0,61-0,83);
  - nota entre 0,80 y 0,87: A3, 0,904 (peor); A2, 0,871 (en el límite). Mirar la volatilidad ayuda a 1 semana lo mismo que a 3 meses (0,873), no más.

**Decisiones**
- **1 semana, previsión:** «dudosa» por la regla de D29, y en la práctica igual que el ingenuo. Se mantiene la conclusión del estudio: ninguna red mejora al ingenuo de forma fiable en ningún horizonte.
- **1 semana, rango:** A2, por la regla de D30. Queda A2 a 1 semana y A3 a 3 meses y a 1 año: la misma idea (el ancho crece con la volatilidad de hoy), con distinto ajuste según cuánto dura la calma en cada horizonte.
- **Código:** `hacia_atras.previsiones_doce_años` admite `horizontes=` y el criterio tiene 1 semana (mismos umbrales que a 3 meses).

- **Notebook 03:** 1 semana añadida a las secciones 10 (validación hacia atrás), 12 (rango) y 13 (robustez: otras medidas, Diebold-Mariano con los 12 años y por periodos, parejas). Ejecutado sin errores.

**Pendiente**
- Repetir los rangos con las redes de 1 año de D31 como centro.

### 13/11/2026 · Controles del procedimiento y límites de la validación hacia atrás

**Límite de la validación hacia atrás** (no cambia nada, pero hay que decirlo). 2010-2017 nunca se usó para elegir configuraciones, pero no es del todo independiente:
- la ventana, las variables y el «sin tendencia» se eligieron con modelos entrenados con datos de 2000-2017;
- el análisis exploratorio vio toda la serie.

Ese sesgo favorece a los modelos. Como el resultado es negativo, la conclusión es robusta. Lo que sí está contaminado es la nota de 2018-2021 (0,90-0,93 a 3 meses), porque con esos años se eligió todo.

**Diseño de los controles** (fijado antes de calcular). Comprueban el procedimiento entero (fichas, purga, escalado, entrenamiento, evaluación y criterio de D29) con el lineal de referencia, que tarda segundos. Mismos años (12 a 1 semana y a 3 meses, 10 a 1 año), mismos datos y misma regularización.
- **Control negativo (sin señal):** las respuestas del entrenamiento se desplazan en círculo un número de fichas al azar (al menos un año más el horizonte). Conservan cómo se mueve el precio, pero ya no corresponden a sus entradas: no hay nada que aprender. 20 repeticiones por horizonte.
- **Control positivo (señal plantada):**
  - se añade a las entradas un «chivato»: la respuesta verdadera más ruido, solo en el último día de la ventana. Con menos ruido, más señal;
  - el ruido se fija para que el mejor previsor posible mejore al ingenuo un 1, 2, 4, 8 y un 16 %;
  - 10 repeticiones por nivel y horizonte;
  - es el caso más fácil: la señal es igual de fuerte todos los años, y una real seguramente iría y vendría.
- **Qué se mide:** la nota con los años juntos, los años que gana y el veredicto con el criterio de D29, contando en qué parte de las repeticiones sale cada veredicto.

**Lo esperado** (apuntado antes de calcular)
- **Negativo:** nota entre 1,00 y 1,03; «no se sostiene» en al menos el 90 % de las repeticiones y «real» en ninguna. Si saliera «dudosa» o «real» a menudo (más del 20 %), el criterio sería demasiado blando: habría que decirlo y revisarlo antes del test.
- **Positivo:**
  - 3 meses: con una mejora del 8 %, «real» casi siempre (80 % o más); con un 4 %, mezcla de «dudosa» y «real»; con un 2 % o menos, no se detecta;
  - 1 año: hace falta más, alrededor del 16 %;
  - 1 semana: los años varían muy poco (0,98-1,04), así que bastaría con un 2-4 %;
  - la mejora medida, algo menor que la del mejor previsor, por la regularización y el ruido de las otras entradas.
- **Para qué sirve:** sustituye la estimación «solo se detectarían mejoras del 8 % o más» por una medida en cada horizonte.

**Hecho:** `controles.py` (control negativo y positivo con el lineal, medidas y resumen), `scripts/controles.py` y 4 pruebas nuevas (entre ellas, que el ruido elegido da la mejora prometida). 210 repeticiones en 5,6 minutos, en `resultados/controles.csv`.

**Resultados**

| | Sin señal: nota media (rango) | Sin señal: veredicto | Con la señal plantada más fuerte (16 %) |
|---|---|---|---|
| 1 semana | 1,004 (1,00-1,02) | «no se sostiene» 85 %, «dudosa» 15 % | nota 0,991, gana 8 de 12: «dudosa» siempre |
| 3 meses | 1,042 (0,98-1,13) | «no se sostiene» 90 %, «dudosa» 10 % | nota 0,915, gana 7 de 12: «dudosa» siempre |
| 1 año | 1,118 (0,95-1,31) | «no se sostiene» 95 %, «dudosa» 5 % | nota 0,842, gana 6-7 de 10: «dudosa» siempre |

- **Sin señal, el criterio no se engaña:** ninguna repetición sale «real». Pero «dudosa» sale entre el 5 y el 15 % de las veces sin ninguna señal.
- **Con señal, el criterio no llega nunca a «real»,** en ninguna repetición ni horizonte:
  - a 3 meses, un lineal un 8,5 % mejor que el ingenuo con los años juntos solo gana 7 de 12 años, porque los años en que el lineal ya iba mal (2011-2012) siguen mal;
  - a 1 año, un 16 % mejor gana 6-7 de 10;
  - «real» pide una ventaja que se mantenga casi todos los años, y un modelo con años muy malos no la tiene aunque de media sea bastante mejor.
- **A 1 semana, el control positivo no dice nada del criterio.** La regularización del lineal (100.000, elegida porque allí no había señal) solo aprovecha el 2-4 % del chivato: con el 16 % plantado mejora un 0,9 %. Con esa regularización, el lineal no aprovecharía ni una señal fuerte. A 3 meses (regularización 1.000) aprovecha el 64-82 % y a 1 año (1), todo.
- **Sin señal, el lineal sale peor que el ingenuo a 3 meses y a 1 año** (1,042 y 1,118): aprender de respuestas que no corresponden cuesta, sobre todo a 1 año.
- **Solo como información (no estaba previsto): una prueba de permutación.** El lineal de verdad a 1 año (0,928) queda por debajo de las 20 repeticiones sin señal (la mejor, 0,953): aprende algo real a 1 año (sobre todo de la volatilidad, sección 9), aunque no baste para ganar al ingenuo de forma fiable. A 3 meses (1,020) y a 1 semana (0,999) queda dentro de lo que da un lineal sin señal.

**Lo esperado frente a lo obtenido**
- Sin señal:
  - nota entre 1,00 y 1,03: solo a 1 semana. A 3 meses y a 1 año, peor (1,042 y 1,118);
  - «real» en ninguna repetición: se cumple;
  - «no se sostiene» en al menos el 90 %: a 1 semana se queda en el 85 %.
- Con señal: **no se cumple.** Esperaba «real» casi siempre con una mejora del 8 % a 3 meses y del 16 % a 1 año, y no sale nunca. Esperaba una mejora medida algo menor que la plantada, y a 1 semana y a 3 meses es mucho menor, por la regularización.

**Decisiones**
- **El criterio de D29 no se cambia** (estaba fijado), y el control negativo lo respalda: no da falsos «real». Pero las conclusiones se precisan:
  - «real» exige una ventaja que se mantenga casi todos los años, algo que ni con una señal plantada fuerte alcanza un modelo con años malos;
  - «dudosa» no distingue entre no tener señal (sale el 5-15 % de las veces sin ninguna) y tener una señal apreciable. Los «dudosa» de 1 semana, 3 meses y 1 año no son evidencia de ventaja;
  - la frase «con 12 años solo se detectarían mejoras de alrededor del 8 % o más» se sustituye por lo medido: con este criterio, ni un 8-9 % a 3 meses ni un 16 % a 1 año llegan a «real» si el modelo tiene años malos. La conclusión sigue siendo «sin evidencia de ventaja», no «sin ventaja».
- **Propuesta para el protocolo del test:** con unos 4 años, contar años ganados no sirve. Mejor la nota con los años juntos y su intervalo, sabiendo de antemano que no será concluyente.
- **Notebook 03:** sección 13.4 (controles) y la frase sobre los límites de la validación hacia atrás en la lectura de la sección 10.

### 13/11/2026 · Antes del test (1): el centro del rango (D32)

**Qué falta.** El rango de 1 año se calculó con las redes de siempre como centro, pero a 1 año se adoptaron las redes entrenadas con todo (D31). Y queda una pregunta abierta: si las redes no ganan al ingenuo, ¿para qué centrar el rango en su previsión y no en el precio de hoy?

**Diseño** (fijado antes de calcular)
- **(a) 1 año con las redes de D31 como centro:** se repiten todos los rangos a 1 año con la media de las semillas 42-46 de las redes de D31, y se aplica otra vez la regla de D30.
- **(b) El centro (D32):** en cada horizonte, con el rango elegido (A2 a 1 semana; A3 a 3 meses y a 1 año), se compara el rango centrado en la previsión de las redes con el mismo rango centrado en el precio de hoy (variación prevista cero). Todo lo demás, igual: mismos años, mismas fichas, mismos errores pasados.
- **Regla, fijada antes de calcular:**
  - se mantiene el centro de las redes solo si, con la media de las tres, mejora la nota del rango al menos un 1 % con los años juntos **y** en más de la mitad de los años;
  - si no, el rango se centra en el precio de hoy: es más sencillo y coherente con que las redes no ganan al ingenuo;
  - excepción: si centrado en el precio de hoy dejara de cumplir la regla de D30 donde el de las redes la cumple, se mantiene el de las redes.

**Lo esperado** (apuntado antes de calcular)
- **(a):** A3 sigue siendo el elegido a 1 año, con una cobertura parecida (70-74 %) y una nota parecida (0,69-0,72 frente al ingenuo).
- **(b):**
  - a 1 semana y a 3 meses, las redes prevén variaciones muy pequeñas: la nota cambia menos de un 1 % y se centra en el precio de hoy;
  - a 1 año, las redes de D31 prevén variaciones de varios puntos y podrían ayudar algo (hasta un 2-3 %). Es el único horizonte donde el centro de las redes podría mantenerse, pero no espero que gane en más de la mitad de los años.

**Hecho:** `incertidumbre.centro_hoy` y `regla_centro` (regla de D32).

**Resultados (a): 1 año con las redes de D31 como centro**
- **A3 sigue siendo el elegido:** nota 0,725 frente al ingenuo y cobertura del 69 %. Con las redes de siempre era 0,706 y 71 %: un poco peor.
- **Falla mucho más por abajo (26 %) que por arriba (5 %).**
- Ninguno cumple la regla a 1 año, como antes.

**Resultados (b): el centro del rango**

| | Rango | Nota, centro en las redes | Nota, centro en el precio de hoy | Mejora de las redes | Años que mejoran | Cobertura (peor tercio), precio de hoy | Centro elegido |
|---|---|---|---|---|---|---|---|
| 1 semana | A2 | 17,78 | 17,75 | −0,2 % | 6 de 11 | 82 % (81 %) | **precio de hoy** |
| 3 meses | A3 | 75,80 | 73,87 | −2,6 % | 4 de 11 | 79 % (75 %) | **precio de hoy** |
| 1 año | A3 | 147,86 | 145,90 | −1,3 % | 3 de 8 | 70 % (61 %) | **precio de hoy** |

- **En los tres horizontes, centrar el rango en la previsión de las redes lo empeora.** Lo que las redes mueven el centro añade error, no información.
- **A 3 meses es más claro:** el rango centrado en el precio de hoy, además de mejor nota (0,851 frente al ingenuo, antes 0,873), cumple mejor en el peor tercio (75 % frente a 71 %). En 2012, las redes alejaban mucho el rango de lo que pasó (nota 57,2 frente a 44,2).
- **Con el precio de hoy como centro, el rango ya no depende de qué red se use:** es el mismo para RNN, LSTM y GRU.

**Lo esperado frente a lo obtenido**
- (a): A3 sigue elegido, como esperaba; la cobertura (69 %) y la nota (0,725) quedan justo fuera de lo previsto (70-74 % y 0,69-0,72).
- (b):
  - a 1 semana, cambio de menos del 1 % y gana el precio de hoy: se cumple;
  - a 3 meses esperaba un cambio de menos del 1 %, y el precio de hoy gana por un 2,6 %;
  - a 1 año pensaba que las redes de D31 podrían ayudar algo; empeoran un 1,3 %.

**Decisiones**
- **D32: los rangos se centran en el precio de hoy en los tres horizontes,** con el ancho de A2 a 1 semana y de A3 a 3 meses y a 1 año. Notas frente al rango ingenuo: 0,870, 0,851 y 0,716.
- **Para la aplicación:** la previsión de cada red se muestra como punto, y el rango del 80 % alrededor del precio de hoy. Es coherente con la conclusión: dónde acabará el precio no lo sabemos mejor que el ingenuo; cuánto puede moverse, sí.
- **Notebook 03:** nueva sección 12.6 con (a) y (b).

### 13/11/2026 · Antes del test (2): experimento de control con precios (D15, H4)

**Diseño** (fijado antes de calcular; versión mínima de D15)
- **Qué:** la RNN (la más regular y la candidata para la aplicación), con su configuración elegida en la fase B, entrenada para prever el **precio** a 1 semana y a 3 meses en lugar de la variación.
- **Igualdad de condiciones:** mismas variables, pero en nivel (el precio del Brent, del WTI, del cobre… en lugar de su variación diaria; la volatilidad, igual). Misma ventana, recorte, escalado ajustado solo con el train, purga, pérdida, parada temprana, semillas (42-46, se promedia el precio previsto) y años (validación 2018-2021). El objetivo, el precio en t + h, se centra y escala con el train, como se hace habitualmente.
- **Qué se mide**, frente a nuestra RNN (la de variaciones, mismas fichas):
  - la nota (MAE / ingenuo, en $);
  - el «espejismo»: cuánto se parece la previsión al precio real futuro (correlación de niveles, que suele salir altísima y da la impresión de acertar);
  - si la previsión se parece más al precio de hoy que al de dentro de h sesiones (error medio frente a cada uno);
  - si lo que la previsión dice que cambiará el precio tiene relación con lo que cambió de verdad (correlación de los cambios);
  - un gráfico de un tramo de 2018-2021: la previsión con precios parece la línea real desplazada h sesiones.
- **H4 se cumple si** la red con precios no mejora a la de variaciones y su previsión se parece más al precio de hoy que al futuro.

**Lo esperado** (apuntado antes de calcular)
- **Nota:** a 1 semana, entre 1,00 y 1,10 (nuestra RNN, 0,99); a 3 meses, entre 1,00 y 1,30 (la nuestra, por debajo de 1 en esos años).
- **Espejismo:** correlación de niveles por encima de 0,9 a 1 semana, aunque la previsión esté más cerca del precio de hoy que del futuro.
- **Cambios:** correlación entre el cambio previsto y el real por debajo de 0,1 en valor absoluto.
- **H4:** se cumple en los dos horizontes.

### 13/11/2026 · Antes del test (3): protocolo del examen final (D33, propuesta)

> Aprobado por Pablo el 13/11/2026, tras explicar los rangos y el contraste de Diebold-Mariano. Se fija antes de tocar el test y no se cambia después de verlo.

**Qué se congela**
- Los datos de cada horizonte y las configuraciones de las redes (fase B), con el promedio de las semillas 42-46 (D27).
- 1 semana y 3 meses: el entrenamiento de siempre, con parada temprana. 1 año: con todo el entrenamiento y épocas fijas (D31).
- El lineal de referencia, con su regularización, y el ingenuo.
- Los rangos del 80 %: A2 a 1 semana y A3 a 3 meses y a 1 año, centrados en el precio de hoy (D30, D32).
- La red de la aplicación y de la conclusión se fija ahora, no con el test (decisión de Pablo): la mejor de cada horizonte en los 12 años de 2010-2021. A 1 semana, la LSTM (0,997); a 3 meses, la RNN (0,994); a 1 año, la RNN entrenada con todo (0,941). Las diferencias entre redes no se distinguen del azar, y en el test se evalúan las tres igualmente.

**Cómo se ejecuta** (D7)
- Cada red se entrena **una vez** con todo lo anterior al 1/1/2022 (train y validación, con purga) y prevé todas las fichas desde el 1/1/2022 cuya respuesta se conoce (hasta el 3/11/2026).
- Los rangos se ajustan como en la validación: cada año, con lo conocido antes del 1 de enero.
- Se ejecuta una sola vez. Si apareciera un error de programación, se corrige solo ese error, se repite y se dice.

**Qué se mide, en cada horizonte**
- **Previsión** (cada red, la media de las tres y el lineal):
  - la nota (MAE / ingenuo, en $) con todo el test junto, y la de cada año;
  - el contraste de Diebold-Mariano frente al ingenuo;
  - el acierto de dirección.
  - El número de años ganados no se usa: con 4-5 años no sirve (controles, 13.4).
- **Rango:** la cobertura (total y por tercios de volatilidad, con su margen), la anchura, la nota frente al rango ingenuo y los fallos por abajo y por arriba.
- **Tabla comparativa final** (la que pide el enunciado): el test junto a los 12 años de 2010-2021.

**Qué se concluirá** (fijado ahora)
- **Previsión:**
  - si Diebold-Mariano no distingue el modelo del ingenuo (p ≥ 0,05): «en test, sin evidencia de ventaja». Junto con los 12 años, la conclusión del horizonte queda en «sin evidencia de ventaja»;
  - si es mejor que el ingenuo con p < 0,05: «mejor que el ingenuo en test». Si en los 12 años no se sostenía, la conclusión final es «ventaja posible, no confirmada»;
  - si es peor con p < 0,05: «peor que el ingenuo en test».
- **Rango:** cumple si la cobertura queda a menos de dos márgenes (errores típicos con fichas independientes) del 80 %. Si no, se dice si se queda corto o se pasa, y en qué tercio.
- **Entre redes:** no se elige una ganadora con el test. Si no se distinguen (comparación por parejas), se dice así.

**Lo esperado** (apuntado antes de calcular)
- Notas alrededor de 1 en los tres horizontes (entre 0,95 y 1,05), sin que Diebold-Mariano distinga ningún modelo del ingenuo.
- Rangos: a 1 semana y a 3 meses, cobertura entre el 75 y el 85 %. A 1 año, con unos 4 movimientos independientes, cualquier cobertura entre el 50 y el 100 % es posible: orientativo.

**Estado al cerrar la sesión** (13/11/2026, tarde)
- **D15 a medias:** `python scripts/control_precios.py` lleva 34 de 40 entrenamientos (3 meses completo; a 1 semana faltan la semilla 46 de 2020 y las 5 de 2021). Se relanza igual y continúa (unos 15-20 min). Después: analizarlo (`control_precios.espejismo`, frente a la RNN de variaciones y el ingenuo) y añadirlo al notebook 03 (sección 13.5).
- **Protocolo del test (D33):** propuesta escrita arriba, pendiente del visto bueno de Pablo.
- **Commit pendiente,** con el visto bueno de Pablo: validación hacia atrás de 1 semana, controles del procedimiento, D32 (centro del rango), D15 y protocolo, con sus pruebas, notebook, README y diario.

**Hecho (D15):** `control_precios.py` (base con las variables en nivel, entrenamiento reanudable, lectura y medidas del espejismo), `scripts/control_precios.py` y 2 pruebas nuevas. 40 entrenamientos: 3 meses en un minuto; 1 semana, unos 50 minutos (con precios la red tarda más en parar: 60 épocas de media).

**Resultados (D15)** (validación 2018-2021, promedio de las semillas 42-46)

| | Nota | Correlación de niveles | Error frente al precio futuro | Error frente al precio de hoy | Correlación de los cambios |
|---|---|---|---|---|---|
| 1 semana · RNN con precios | **1,544** | 0,949 | 3,68 $ | 3,26 $ | 0,16 |
| 1 semana · RNN (variaciones) | 0,993 | 0,975 | 2,37 $ | 0,29 $ | 0,08 |
| 3 meses · RNN con precios | **1,028** | 0,425 | 10,50 $ | 9,98 $ | 0,45 |
| 3 meses · RNN (variaciones) | 0,938 | 0,543 | 9,58 $ | 2,90 $ | 0,32 |

(El ingenuo: nota 1; correlación de niveles 0,975 a 1 semana y 0,537 a 3 meses; error frente al precio futuro, 2,39 $ y 10,22 $.)

- **A 1 semana, el espejismo de manual:** la previsión con precios se parece mucho al precio real (correlación de 0,95), así que en un gráfico «parece que acierta». Pero se equivoca un 54 % más que el ingenuo, y está más cerca del precio de hoy que del futuro. Peor en todos los años, sobre todo en 2020 (2,02), con precios que el train apenas había visto.
- **No copia el precio de hoy, lo copia con ruido:** se aparta de él 3,26 $ de media, cuando el precio se mueve 2,39 $ en una semana. Nuestra red, 0,29 $: casi el ingenuo.
- **A 3 meses tira hacia el precio típico del train:** se aparta unos 10 $ del precio de hoy, casi siempre hacia arriba (+4,4 $ de media), porque en 2018-2021 el precio estuvo por debajo de la media de 2000-2017. Esa vuelta a la media acierta a veces la dirección (correlación de los cambios 0,45, por ejemplo tras el desplome de 2020), pero falla en el tamaño, y en 2021 queda muy mal (1,265).
- **Con la regla fijada, H4 se cumple en los dos horizontes:** la red con precios no mejora a la de variaciones (1,544 frente a 0,993 y 1,028 frente a 0,938), y su previsión está más cerca del precio de hoy que del futuro (a 3 meses, por poco: 9,98 $ frente a 10,50 $).

**Lo esperado frente a lo obtenido**
- Nota: a 1 semana esperaba 1,00-1,10 y sale 1,544, mucho peor. A 3 meses, 1,028: dentro de lo previsto (1,00-1,30).
- Correlación de niveles por encima de 0,9 a 1 semana: se cumple (0,949).
- Correlación de los cambios por debajo de 0,1: **no se cumple** (0,16 y 0,45). Con precios, la red no solo copia: también tira hacia el precio típico del train, y eso a veces acierta la dirección.
- H4 en los dos horizontes: se cumple.

**Decisiones**
- **H4 se cumple:** prever la variación, y no el precio, es la elección correcta. Es la justificación del diseño para el trabajo y una figura clara para las diapositivas (el espejismo).
- **Notebook 03:** sección 13.5 (control con precios) y su lectura.
- **Pruebas:** 2 nuevas de la regla del centro (D32). 109 en total, todas correctas (`poetry run python -m pytest`: Smart App Control bloquea ahora el lanzador `pytest.exe`).

**Estado** (13/11/2026, tarde): lo previsto antes del test está hecho (rangos con D31, centro del rango D32, controles, D15). Pendiente: el visto bueno de Pablo al protocolo del test (D33). Red de la aplicación decidida: la mejor de cada horizonte (LSTM a 1 semana, RNN a 3 meses y a 1 año).

### 13/11/2026 · Cabos sueltos antes del test: H2

**Diseño** (fijado antes de calcular)
- **H2:** la variación de ayer del WTI anticipa el Brent de hoy, porque EE. UU. cierra después que Londres. Se prueba a 1 semana (el único horizonte donde podría notarse) con el lineal de referencia (misma regularización), en los 12 años de 2010-2021: con todas las variables y sin el WTI. Como información, también con solo el WTI.
- **Regla:** H2 se cumple a 1 semana si quitar el WTI empeora la nota del lineal al menos 0,005 con los años juntos y en más de la mitad de los años. Si no, no se cumple: el efecto, si existe, no se nota a 5 sesiones.
- **Lo esperado:** no se cumple. El WTI de ayer solo podría anticipar el primero de los 5 días, y la variación del Brent ya recoge parte. Cambio de la nota de menos de 0,005.

**Resultados (H2)** (lineal a 1 semana, 2010-2021)

| | Años juntos | Peor año | Mejor año |
|---|---|---|---|
| Todas las variables | 0,9987 | 2012 (1,025) | 2014 (0,946) |
| Sin el WTI | 0,9984 | 2012 (1,024) | 2014 (0,948) |
| Solo el WTI | 1,0003 | 2021 (1,002) | 2010 (0,998) |

- **Quitar el WTI no empeora el lineal:** mejora 0,0003 con los años juntos y empeora solo en 4 de los 12 años. **H2 no se cumple a 1 semana.**
- **Solo con el WTI, el lineal queda en 1,000:** no aporta nada.
- **La relación de partida se desvanece:** la correlación entre la variación del WTI de ayer y la del Brent de hoy es 0,22 en 2000-2017, pero −0,04 en 2018-2021. Aunque hubiera servido para el primer día, en los años recientes ya no está.
- **Lo esperado frente a lo obtenido:** se cumple (cambio de menos de 0,005, H2 no se cumple). No esperaba que la relación desapareciera en 2018-2021.

**Otras comprobaciones de hoy**
- **Los futuros del CSV son del vencimiento más cercano:** el del WTI casi coincide con el contado (diferencia mediana del 0,14 %; desde 2000) y el del Brent, desde 2007 (1,25 %). Sin vencimientos lejanos no hay curva de futuros que usar como referencia, y la criba ya probó futuro frente a contado sin resultado (sección 11).
- **H3, con las cifras finales:** el rango elegido y centrado en el precio de hoy (D32) mejora la nota del rango ingenuo un 13 % a 1 semana, un 15 % a 3 meses y un 28 % a 1 año, sobre todo en las tormentas.

### 13/11/2026 · Después del test: la previsión del 10/11 (D34)

- **Propuesta del profesor:** ver el rendimiento real del modelo con datos que todavía no se conocían.
- **La actualización automática del CSV se descarta:** complica más de lo que aporta. La foto del estudio (`data/petroleo_dataset.csv`, Brent hasta el 3/11/2026) no se toca.
- **D34, la previsión del 10/11, después del test:**
  - del 3/11 al 10/11 hay justo 5 sesiones: es la previsión a 1 semana desde el último dato de la foto. Ese precio no está en el CSV ni se ha mirado;
  - se prevé con dos versiones: las redes del test (entrenadas hasta 2021) y las redes finales, reentrenadas con todo hasta el 3/11/2026 (las elegidas: LSTM a 1 semana, RNN a 3 meses y a 1 año). Después del test, sus años se pueden usar para entrenar, nunca para volver a evaluar;
  - se guardan el precio previsto, el ingenuo (el precio del 3/11) y el rango del 80 %, y también las previsiones a 3 meses y a 1 año desde el 3/11;
  - **todo se guarda con commit antes de descargar datos nuevos.** Después, una descarga a mano con el script del curso, en otro archivo, y la comparación;
  - es un solo dato: sirve como demostración y para ver si el rango acierta, no para juzgar el modelo.
- **Tiempos previstos:** el test, unos 45-75 minutos de cálculo (casi todo a 1 semana: la RNN tarda unos 6 minutos por entrenamiento), más la preparación del script; el modelo final, unos 10-15 minutos.

**Estado al cerrar la sesión** (13/11/2026, tarde)
- Todo cerrado antes del test, salvo H1 y H5, que dependen de él.
- **Siguiente, cuando Pablo quiera:** programar y probar el test (D33, aprobado) y que Pablo lo lance; después, D34.
- **Pablo se pone con la presentación.**
- **Sin commit:** H2, H3 al día, tareas ordenadas, protocolo aprobado y D34 (solo el diario).

### 13-14/11/2026 · Web del proyecto (D35)

**Qué es.** Una web estática para presentar el proyecto a inversores y gestores de riesgo, con el mensaje «No sabemos adónde irá el Brent. Sabemos cuánto puede moverse». Se publica en GitHub Pages desde `web/` (la carpeta `docs/` no se toca).

**Hecho**
- **`scripts/exportar_web.py`:** genera los JSON de `web/data/` con las funciones del notebook 03 (`hacia_atras`, `incertidumbre`, `entreno_completo`, `control_precios`, `comprobaciones`). No entrena nada; menos de un minuto. Comprobado contra el diario: LSTM 0,997 a 1 semana, RNN 0,994 a 3 meses y 0,941 a 1 año; rango 82 %, 79 % y 70 %; mejoras del 13, 15 y 28 %; control con precios 1,544 y 0,993.
- **La web** (`web/index.html`, estilos con Tailwind compilado, JavaScript por módulos, gráficos en SVG propio y fondo en WebGL): hero con la serie de 2000-2026 que termina en el abanico del 80 %, panel de la previsión por plazos, hallazgos, «Calma y tormenta» (2019-2021), «El espejismo» (D15), método, tabla comparativa, usos y preguntas.
- **Flujo de publicación:** `.github/workflows/web.yml` (sube `web/` tal cual a GitHub Pages).
- **Documentación:** `web/README.md` (verla en local, actualizar datos, recompilar estilos, publicar, formato de los JSON pendientes).

**Decisiones de la web** (propuestas por Claude, aceptadas por Pablo el 13/11)
- **El abanico se centra en el precio de hoy** (D32) y la previsión de la red va dentro, como marca; así lo dice la web.
- **La tabla no colorea «menos de 1 = mejor»:** enseña la nota, los años ganados, el veredicto de la regla (D29) y que Diebold-Mariano no distingue ningún modelo del ingenuo (p más bajo, 0,07).
- **La previsión en vivo se describe como «guardada antes de descargar datos posteriores al 3/11»,** no «antes de conocer el precio», y enlazará el commit.
- **1 año, siempre «orientativo»,** con su cobertura (70 %) y su margen (± 16) a la vista.

**Decisión nueva: el rango provisional de hoy.** Para que el panel y el hero no queden vacíos antes de D33 y D34, el exportador calcula el rango del 3/11/2026 con `incertidumbre.rangos` (A2 a 1 semana; A3 a 3 meses y a 1 año), centrado en el precio de hoy y **ajustado solo con respuestas conocidas antes del 1/1/2022**. No usa nada del test: de 2022-2026 solo entra la volatilidad de 21 días del 3/11/2026 (0,60), que es una entrada. Resultado: 96,81-117,66 $ a 1 semana, 75,51-151,70 $ a 3 meses y 55,61-205,98 $ a 1 año. La web lo rotula «provisional». El definitivo (D34) se ajustará con lo conocido hasta entonces y lo sustituirá.

**Limitaciones**
- Solo para ordenador: sin versión para móvil (decisión de Pablo, 14/11). Por debajo de 1.024 px de ancho no se recoloca.
- Revisada con capturas automáticas de Edge sin pantalla (página entera, pestañas, interruptor y acordeón). Las animaciones de entrada al hacer scroll no se pueden comprobar así: hay que mirarlas en un navegador normal.
- Sin medir con Lighthouse (no hay Node en el equipo).
- En el pie quedan por rellenar el nombre del autor y la universidad.

**Pendiente**
- Tras D33: escribir `web/data/test.json` con las notas del examen final (formato en `web/README.md`).
- Tras D34: ampliar `prevision()` del exportador con las previsiones de las redes finales y el rango definitivo, y rellenar `web/data/en_vivo.json` (con el commit).
- Activar GitHub Pages (Settings → Pages → Source: «GitHub Actions») y publicar.
- **Sin commit:** todo lo de la web está sin subir, a la espera del visto bueno de Pablo.

### 14/11/2026 · Examen final en test (D33): preparación

- **Hecho:** `examen_final.py` (entrenamiento reanudable según el protocolo, lectura, tabla comparativa del enunciado, Diebold-Mariano con las conclusiones fijadas, rangos centrados en el precio de hoy y si cumplen), `scripts/examen_final.py` y 6 pruebas nuevas (115 en total, todas correctas). Las pruebas no entrenan ni evalúan nada en el test: las medidas se prueban con datos inventados, y con los datos reales solo se comprueban las fechas de la partición.
- **Salvaguarda:** sin `--ejecutar`, el script solo muestra el plan; no se puede lanzar el examen por accidente.
- **El plan (sin tocar resultados):**
  - 1 semana: 4.634 fichas de train y 1.218 evaluadas (del 3/1/2022 al 27/10/2026);
  - 3 meses: 4.808 y 1.160 (hasta el 5/8/2026);
  - 1 año: 4.619 y 971 (hasta el 4/11/2025), con todo el entrenamiento y épocas fijas (D31);
  - 45 entrenamientos (3 redes × 5 semillas × 3 horizontes), unos 55 minutos, y el lineal.
- **Pendiente:** commit del código antes de ejecutarlo, y que Pablo lance `python scripts/examen_final.py --ejecutar`.

