# Bitácora de Trazabilidad y Uso Ético del Agente OpenCode

## Datos generales

| Campo | Detalle |
|-------|---------|
| Autora | Deisy Elizabeth Calle Calle (código 36) |
| Carrera | Ingeniería en Telemática, Facultad de Informática y Electrónica, ESPOCH, Riobamba |
| Asignatura | Sistemas Distribuidos y Paradigmas de la Computación (ETL1TP50) |
| Unidad | Unidad 2 |
| Fecha | 13/11/2026 |
| Agente | OpenCode v2.3.0 (terminal) |
| Modelo | DeepSeek V4.1 Flash Free (modelos gratuitos de OpenCode) |
| Entorno | Windows 10, Python 3.14.3, pandas 3.1.1, matplotlib 3.11.2, Quarto 1.11.9, TinyTeX 2026 |

## Nota de entorno

Intenté primero usar OpenRouter con los modelos Nemotron 3 Ultra y Gemma 4 31B, pero la plataforma devolvía el error 401 «User not found» aunque la clave era válida. Por esa razón continué el trabajo con DeepSeek V4.1 Flash Free, disponible entre los modelos gratuitos de OpenCode. Esta bitácora conserva el registro de las etapas, los prompts literales, los resultados obtenidos y las correcciones aplicadas durante la supervisión humana.

## Índice

1. [Datos generales](#datos-generales)
2. [Nota de entorno](#nota-de-entorno)
3. [Resumen de etapas](#resumen-de-etapas)
4. [Etapas en orden cronológico](#etapas-en-orden-cronológico)
   - [Etapa 1: Benchmark](#etapa-1-benchmark)
   - [Etapa 2: Configuración Quarto/IEEE](#etapa-2-configuración-quartoieee)
   - [Etapa 3: Redacción del artículo](#etapa-3-redacción-del-artículo)
   - [Etapa 4: Interrupción humana en la Tabla II](#etapa-4-interrupción-humana-en-la-tabla-ii)
   - [Etapa 5: Corrección de referencias](#etapa-5-corrección-de-referencias)
   - [Etapa 6: Corrección técnica y README](#etapa-6-corrección-técnica-y-readme)
   - [Etapa 7: Reestructuración de la bitácora, auditoría final y ajustes](#etapa-7-reestructuración-de-la-bitácora-auditoría-final-y-ajustes)
5. [Supervisión humana](#supervisión-humana)
6. [Limitaciones del uso de IA](#limitaciones-del-uso-de-ia)
7. [Declaración de integridad académica](#declaración-de-integridad-académica)

## Resumen de etapas

| Etapa | Objetivo | Archivos generados | Intervención humana |
|-------|----------|--------------------|---------------------|
| 1. Benchmark | Construir el simulador de eventos discretos y generar los datos experimentales. | `benchmark.py`, `results.csv` | Validé la verdad de referencia con 0 discrepancias sobre 2 018 046 pares y ordené re-ejecutar el experimento completo tras una sobrescritura accidental del CSV. |
| 2. Configuración Quarto/IEEE | Preparar la base editorial del artículo con IEEEtran, referencias y estilo de citación. | `_quarto.yml`, `ieee.csl`, `references.bib`, `articulo.qmd` de prueba | Instalé paquetes LaTeX faltantes, cambié a `pdflatex` con Times, neutralicé `parskip`, ajusté leyendas y exigí tablas en LaTeX puro. |
| 3. Redacción del artículo | Redactar el artículo completo en español con datos reales y formato IEEE Conference. | `articulo.qmd`, `articulo.pdf`, figuras PNG 300 dpi | Ajusté la extensión de 5 a 4 páginas, unifiqué unidades, corregí ecuaciones y verifiqué la cabecera con afiliación. |
| 4. Tabla II | Corregir el ciclo de ajustes de la Tabla II sin degradar el resto del artículo. | `articulo.qmd` | Interrumpí al agente y propuse imprimir la tabla dentro de un bloque raw de LaTeX con una etiqueta de chunk sin prefijo `tbl-`. |
| 5. Referencias | Corregir dos alucinaciones bibliográficas detectadas en el PDF. | `references.bib`, `articulo.pdf` | Detecté la sede incorrecta de Fidge 1988 y los editores incorrectos de Almeida 2008; ordené un único render de verificación. |
| 6. Corrección técnica y README | Corregir el error LPWAN y cerrar la entrega del repositorio. | `articulo.qmd`, `articulo.pdf`, `README.md`, `PROMPTS_OPENCODE.md` | Detecté que 127 bytes corresponde a IEEE 802.15.4, no a LPWAN; revisé el README y confirmé las 4 páginas finales. |
| 7. Reestructuración, auditoría y ajustes | Reorganizar la bitácora, auditar el repositorio y cerrar los detalles finales. | `PROMPTS_OPENCODE.md`, `README.md`, `ieee-preamble.tex`, `articulo.pdf` | Revisé visualmente el PDF, el README y la bitácora; pedí la reestructuración, la auditoría y los ajustes finales. |

## Etapas en orden cronológico

### Etapa 1: Benchmark

**Prompt (versión resumida: se condensaron la lista de métricas / de referencias, el contenido y las instrucciones son los mismos):**

````text
Actúa como investigador experto en sistemas distribuidos. Crea benchmark.py (Python 3, solo librería estándar) para un artículo científico: "Evaluación Comparativa de Relojes Vectoriales vs. Lamport: Consumo de Memoria y Detección de Eventos Concurrentes en Topologías de Malla".
DISEÑO EXPERIMENTAL
1. Simulador de eventos discretos con cola de prioridad (heapq). N procesos; cada proceso genera 100 eventos: locales (prob. 0.4) o envíos (prob. 0.6) a un vecino aleatorio. Recepciones con retardo de red base 10 ms + jitter asíncrono uniforme [0, 50] ms, para provocar reordenamiento.
2. Topologías: "malla_completa" (todos con todos) y "malla_parcial" (cada nodo con k=3 vecinos, grafo conexo garantizado).
3. Implementa en cada proceso ambos relojes con sus reglas formales: Lamport (contador entero; incrementa en evento local/envío; en recepción max(local, recibido)+1) y Vectorial (lista de N enteros; incrementa su posición; en recepción máximo componente a componente y luego incrementa).
4. Verdad de referencia (ground truth) INDEPENDIENTE de los relojes: construye el grafo de causalidad (orden de programa + aristas envío→recepción) y calcula happens-before por alcanzabilidad. Úsalo para validar que los relojes vectoriales detectan el 100% de la concurrencia.
5. Para no hacer O(E^2), muestrea 20 000 pares aleatorios de eventos por ejecución y clasifícalos: causales o concurrentes.
MÉTRICAS POR EJECUCIÓN Y POR RELOJ: bytes_por_proceso y bytes_por_mensaje (8 bytes por entero) y overhead_total_bytes; memoria_tracemalloc_bytes; pares_muestreados, pares_concurrentes_reales, concurrentes_detectados, falsos_ordenamientos, tasa_deteccion; consistencia_causal; tiempo_ms (time.perf_counter_ns); mensajes_totales.
PARÁMETROS: N = 4, 8, 16, 32, 64; 30 repeticiones por configuración con semillas fijas (semilla = 1000 + repetición). Argumento --rapido (N=4, 8, 16 y 5 repeticiones).
SALIDAS: results.csv con todas las columnas y una tabla resumen por consola (media ± desviación estándar).
CALIDAD: código modular (clases Proceso, RelojLamport, RelojVectorial, Simulador), docstrings y comentarios en español, type hints, main(). Primero ejecuta --rapido, corrige errores y luego ejecuta completo. Verifica tasa_deteccion vectorial = 1.0 y consistencia_causal = 100% en ambos.
````

**Resultado del agente.** Se creó `benchmark.py` con solo la librería estándar de Python, estructurado en las clases `Proceso`, `RelojLamport`, `RelojVectorial` y `Simulador`, con docstrings, comentarios en español, *type hints* y función `main()`. El simulador usa una cola de prioridad `heapq`, programa recepciones con retardo base de 10 ms más *jitter* uniforme de `[0, 50]` ms y evalúa ambos relojes sobre las mismas trazas. La verdad de referencia se calcula por alcanzabilidad sobre el grafo de causalidad, con independencia de los relojes. La ejecución completa generó `results.csv` con 600 filas: 300 ejecuciones (5 valores de `N` × 2 topologías × 30 repeticiones) medidas para los dos relojes, con 20 000 pares muestreados por ejecución.

**Correcciones y validaciones.** Durante las pruebas, una ejecución con `--rapido` sobrescribió `results.csv`; ordené re-ejecutar el experimento completo para restaurar las 600 filas definitivas. Validé la verdad de referencia con **0 discrepancias sobre 2 018 046 pares** causales. Comprobé que la tasa de detección del reloj vectorial fuera `1.0` y que la consistencia causal fuera `100 %` en ambos relojes.

### Etapa 2: Configuración Quarto/IEEE

**Prompt (versión resumida: se condensaron la lista de métricas / de referencias, el contenido y las instrucciones son los mismos):**

````text
Ahora prepara la base del artículo en Quarto con formato IEEE Conference.
1. Crea references.bib con estas 8 referencias REALES (no inventes ninguna; usa los DOI exactos): Lamport 1978 (CACM, DOI 10.1145/359545.359563); Fidge 1988 (11th ACSC, 56-66); Mattern 1989 (Parallel and Distributed Algorithms, 215-226); Charron-Bost 1991 (IPL, DOI 10.1016/0020-0190(91)90055-M); Schwarz y Mattern 1994 (Distributed Computing, DOI 10.1007/BF02277859); Raynal y Singhal 1996 (IEEE Computer, DOI 10.1109/2.485846); Almeida, Baquero y Fonte 2008 (OPODIS, LNCS 5401, DOI 10.1007/978-3-540-92221-6_18); Kshemkalyani y Singhal 2008 (Cambridge University Press).
2. Crea _quarto.yml para renderizar articulo.qmd a PDF con: documentclass IEEEtran, classoption conference, dos columnas, papersize letter, idioma español (lang: es), bibliography references.bib, citas en estilo IEEE numérico (descarga el CSL oficial de IEEE como ieee.csl), number-sections, figuras en alta resolución (fig-dpi 300), execute con echo: false y warning: false.
3. Verifica que Quarto y TinyTeX funcionan renderizando un articulo.qmd de prueba mínimo (título + un párrafo con una cita). Si falta algún paquete LaTeX, instálalo con tlmgr o quarto install. No escribas todavía el artículo completo.

Al terminar, muéstrame el índice del archivo.
````

**Resultado del agente.** Se crearon `references.bib` con las ocho referencias solicitadas y los DOI indicados, `ieee.csl` con el estilo numérico IEEE, `_quarto.yml` con IEEEtran en modo *conference*, dos columnas, tamaño carta, `lang: es`, `number-sections`, figuras a 300 dpi y ejecución silenciosa, y un `articulo.qmd` mínimo de prueba con título, un párrafo y una cita. El render de prueba produjo un PDF válido y confirmó que Quarto, TinyTeX e IEEEtran funcionaban en conjunto.

**Correcciones y validaciones.** Faltaban paquetes LaTeX: instalé `ieeetran`, `babel-spanish` y `hyphen-spanish` con `tlmgr`. El render inicial con LuaLaTeX sustituía las fuentes Times de IEEEtran; cambié el motor a `pdflatex` y fijé `fontfamily: times`. Pandoc cargaba `parskip` y anulaba la sangría de párrafo; la neutralicé en `ieee-preamble.tex` con `\parindent` y `\parskip`. Ajusté las leyendas mediante `\AtBeginDocument` y `\captionsetup`. Las tablas Markdown producían `longtable`, inviable en dos columnas, así que se decidió escribirlas en LaTeX puro. Un corte de internet interrumpió la instalación y el render; la tarea se reanudó sin perder la configuración ya validada.

### Etapa 3: Redacción del artículo

**Prompt (texto literal):**

````text
Ahora escribe el artículo científico completo en articulo.qmd (en español, formato IEEE Conference, 3 a 4 páginas exactas en PDF), usando los datos reales de results.csv. Mantén el _quarto.yml, ieee-preamble.tex y references.bib ya creados.

CABECERA
- Título: "Evaluación Comparativa de Relojes Vectoriales vs. Lamport: Análisis de Consumo de Memoria y Detección de Eventos Concurrentes en Topologías de Malla"
- Autora: Deisy Elizabeth Calle Calle (código 36) — Carrera de Ingeniería en Telemática, Facultad de Informática y Electrónica, Escuela Superior Politécnica de Chimborazo (ESPOCH), Riobamba, Ecuador — calleelizabeth640@gmail.com
- Resumen (150-200 palabras) con cifras clave reales y Palabras clave (relojes lógicos, relojes vectoriales, causalidad, concurrencia, sistemas distribuidos).

SECCIONES
I. Introducción: problema del tiempo en sistemas distribuidos, motivación, y 3 hipótesis: H1 (los vectoriales detectan 100% de la concurrencia y Lamport 0%), H2 (el overhead vectorial crece O(N) y el de Lamport es O(1)), H3 (la malla parcial genera más concurrencia que la completa). Contribuciones del trabajo.
II. Fundamentos y trabajo relacionado: relación happened-before, condición de reloj de Lamport, relojes vectoriales de Fidge y Mattern, cota inferior de Charron-Bost (tamaño N necesario), alternativas (Interval Tree Clocks, compresión de Singhal-Kshemkalyani). Incluye las ecuaciones de actualización en LaTeX. Cita todas las referencias de references.bib.
III. Metodología experimental: simulador de eventos discretos, topologías, modelo de jitter, verdad de referencia por alcanzabilidad, muestreo de pares, métricas y entorno (versión de Python, SO). Tabla 1: parámetros del experimento.
IV. Resultados: genera las figuras con bloques de código Python (pandas + matplotlib) que lean results.csv, estilo profesional (fuente serif, tamaño legible, colores diferenciados, cuadrícula suave, leyenda, barras de error de desviación estándar, ancho de una columna):
  - Fig. 1: bytes de metadatos por mensaje vs N (escala log2 en X), ambos relojes y ambas topologías.
  - Fig. 2: overhead total acumulado (KB) vs N.
  - Fig. 3: pares concurrentes reales y tasa de detección por reloj y topología.
  - Fig. 4: tiempo de actualización de relojes (ms) vs N.
  - Tabla 2: resumen media ± desviación estándar por topología, N y reloj (las columnas más importantes), calculada desde results.csv.
  Referencia cada figura y tabla en el texto y describe los resultados con las cifras reales.
V. Discusión crítica: aceptación o rechazo de cada hipótesis con evidencia; compromiso entre expresividad causal y escalabilidad; por qué Lamport sigue siendo útil (orden total, exclusión mutua); diferencia entre bytes teóricos y memoria medida con tracemalloc; implicaciones para telemática (IoT, redes de sensores, mallas); amenazas a la validez (simulación vs red real, muestreo de pares, overhead de Python, tamaño de N).
VI. Conclusiones y trabajo futuro.
Referencias (automáticas desde references.bib, estilo IEEE).

TABLAS Y FIGURAS (OBLIGATORIO)
- Sigue tu advertencia: genera la Tabla 1 y la Tabla 2 en LaTeX (\begin{table}[!t] + tabular + booktabs), la Tabla 2 calculada desde results.csv con un bloque Python con #| output: asis. No uses tablas markdown.
- Guarda las figuras como PNG a 300 dpi desde los bloques Python e insértalas con leyenda numerada, de forma que compile sin errores en dos columnas.

ESTILO DE REDACCIÓN (OBLIGATORIO)
- Todo el artículo en PRIMERA PERSONA DEL SINGULAR, porque es una investigación individual: "diseñé", "implementé", "ejecuté", "observé", "propongo", "concluyo". Nunca uses "nosotros", "se realizó" ni la voz pasiva impersonal.
- Tono académico, técnico y preciso, sin frases genéricas ni de relleno.
- Cada afirmación cuantitativa debe salir de los datos reales de results.csv.
- En la metodología menciona en primera persona que usé el agente OpenCode como asistente de codificación y que audité y validé el código y los resultados (por ejemplo, que verifiqué la verdad de referencia con 0 discrepancias).

FINAL
Renderiza con quarto render articulo.qmd, verifica que el PDF tiene entre 3 y 4 páginas (ajusta el texto o el tamaño de las figuras si no), que no hay errores, que todas las figuras y tablas aparecen numeradas y que las citas salen como [1], [2]... Muéstrame el número de páginas final.
````

**Resultado del agente.** Se redactó `articulo.qmd` completo en español y en primera persona del singular, con las seis secciones solicitadas, las hipótesis H1–H3, cuatro figuras generadas desde `results.csv` con pandas y matplotlib en PNG a 300 dpi, y dos tablas en LaTeX puro. El render produjo `articulo.pdf` en formato IEEE Conference, con figuras y tablas numeradas y citas en orden `[1]`–`[8]`.

**Correcciones y validaciones.** El primer render ocupaba 5 páginas; ajusté el texto y el tamaño de las figuras hasta alcanzar las 4 páginas requeridas. Unifiqué las unidades de almacenamiento a KB/MB decimales (división entre 1000) en el texto, la Tabla II y la Fig. 2. Reemplacé las ecuaciones por entornos `aligned` para que compilaran correctamente en dos columnas. Verifiqué que la cabecera incluyera nombre, afiliación y correo mediante el bloque de autoría de IEEEtran, y que «Palabras clave» apareciera en español.

### Etapa 4: Interrupción humana en la Tabla II

**Prompt.** No se envió un prompt nuevo: interrumpí directamente al agente durante la ejecución.

**Resultado del agente.** El agente había entrado en un ciclo de ajustes de la Tabla II. Quarto reprocesaba el bloque `#| output: asis` y deformaba el entorno `table*`: lo convertía en `table`, duplicaba la etiqueta e insertaba un `[!t]` literal dentro de la tabla. Cada intento exigía un render de casi un minuto y no corregía la causa.

**Correcciones y validaciones.** Interrumpí el ciclo y cambié la estrategia: el bloque Python debía imprimir la tabla completa envuelta en un bloque raw ```` ```{=latex} ````, y la etiqueta del chunk no debía empezar por `tbl-` para que el sistema de referencias cruzadas de Quarto no la interceptara. Con ese enfoque, la Tabla II quedó calculada desde `results.csv`, con 20 filas correctas y sin artefactos de Quarto.

### Etapa 5: Corrección de referencias

**Prompt (texto literal):**

````text
Última corrección (supervisión humana). Revisé el PDF y encontré dos alucinaciones en references.bib:
1. Fidge 1988: elimina la ciudad "Sydney" (es incorrecta; la conferencia ACSC 1988 se realizó en Brisbane). Deja solo el nombre de la conferencia, páginas 56-66 y año.
2. Almeida 2008 (Interval Tree Clocks): los editores correctos de OPODIS 2008 (LNCS 5401) son T. P. Baker, A. Bui y S. Tixeuil, no "T. P. Baker y C. Cachin".

Después:
3. Renderiza con quarto render articulo.qmd UNA sola vez y confirma que sigue en 4 páginas y sin errores. No cambies nada más del artículo.
4. Actualiza PROMPTS_OPENCODE.md añadiendo este prompt y estas correcciones humanas: que interrumpí al agente cuando entró en un ciclo de ajustes de la Tabla 2 y que detecté y corregí 2 alucinaciones en las referencias. Si existe mis_prompts.txt en la carpeta, verifica que los prompts de la bitácora coincidan con el texto real.
5. Asegúrate de que .gitignore excluya también mis_prompts.txt, y que NO excluya articulo.pdf ni ieee-preamble.tex.
6. Muéstrame la lista final de archivos de la carpeta.
````

**Resultado del agente.** Se corrigieron las dos entradas de `references.bib`. La referencia de Fidge 1988 quedó sin ciudad, solo con el nombre de la conferencia, las páginas 56–66 y el año. La referencia de Almeida 2008 quedó con los editores T. P. Baker, A. Bui y S. Tixeuil. Un único `quarto render articulo.qmd` produjo `articulo.pdf` de 4 páginas, sin errores.

**Correcciones y validaciones.** La revisión humana detectó y corrigió dos alucinaciones bibliográficas que ya estaban impresas en el PDF:

| # | Entrada | Error detectado | Corrección aplicada |
|---|---------|-----------------|---------------------|
| 1 | `fidge1988timestamps` | Atribuía la 11th Australian Computer Science Conference (1988) a **Sydney**; la sede fue Brisbane. | Se eliminó el campo `address`; quedan conferencia, páginas 56–66 y año. |
| 2 | `almeida2008interval` | Editores de OPODIS 2008 (LNCS 5401) como «T. P. Baker y C. Cachin». | Editores correctos: **T. P. Baker, A. Bui y S. Tixeuil**. |

Verifiqué en el PDF final que la referencia [2] ya no menciona ciudad alguna y que la [8] lista «T. P. Baker, A. Bui, y S. Tixeuil, Eds.».

### Etapa 6: Corrección técnica y README

**Prompt (texto literal):**

````text
Estoy en el repositorio de mi investigación (lee articulo.qmd, PROMPTS_OPENCODE.md, results.csv y _quarto.yml para tener el contexto). Haz solo esto:

1. Revisé el PDF y encontré un error técnico en la sección V-C (Implicaciones para telemática): dice "enlaces LPWAN con MTU de 127 bytes", pero 127 bytes es el tamaño de trama de IEEE 802.15.4 (base de Zigbee y 6LoWPAN), no de LPWAN. Cámbialo por "enlaces IEEE 802.15.4 (Zigbee/6LoWPAN) con tramas de 127 bytes" sin alterar el resto del artículo. Renderiza con quarto render articulo.qmd UNA vez y confirma 4 páginas sin errores.

2. Crea README.md profesional: título, autora Deisy Elizabeth Calle Calle (código 36), Ingeniería en Telemática, ESPOCH, asignatura Sistemas Distribuidos y Paradigmas de la Computación (ETL1TP50); abstract; hipótesis H1-H3; tabla de resultados clave con cifras reales de results.csv; estructura del repositorio; requisitos (Python 3, pandas, matplotlib, jupyter, Quarto, TinyTeX); guía de reproducción paso a paso (python benchmark.py y quarto render articulo.qmd); explicación de ieee.csl e ieee-preamble.tex; y enlace a PROMPTS_OPENCODE.md.

3. Añade al final de PROMPTS_OPENCODE.md este prompt y la corrección técnica (LPWAN → IEEE 802.15.4) como parte de mi supervisión humana.

4. Muéstrame la lista final de archivos.
````

**Resultado del agente.** Se corrigió la sección V-C de `articulo.qmd`, se creó `README.md` con el resumen, las hipótesis H1–H3, las tablas de resultados calculadas desde `results.csv`, la estructura del repositorio, los requisitos, la guía de reproducción y la explicación de `ieee.csl` e `ieee-preamble.tex`, y se actualizó esta bitácora. El render final produjo `articulo.pdf` de 4 páginas, sin errores.

**Correcciones y validaciones.** La revisión humana detectó un error conceptual: el texto atribuía a LPWAN una MTU de 127 bytes, cuando ese valor corresponde al tamaño máximo de trama de IEEE 802.15.4, base de Zigbee y 6LoWPAN.

| Ubicación | Texto anterior | Texto corregido |
|-----------|----------------|-----------------|
| §V-C, párrafo sobre `N=64` | «en enlaces **LPWAN con MTU de 127 bytes** ese costo es prohibitivo» | «en enlaces **IEEE 802.15.4 (Zigbee/6LoWPAN) con tramas de 127 bytes** ese costo es prohibitivo» |

La corrección se limitó a esa frase: no se modificó ninguna otra parte del artículo, ni las cifras, ni las figuras, ni las tablas. Se ejecutó un único `quarto render articulo.qmd`, que produjo `articulo.pdf` sin errores y con 4 páginas. La verificación sobre el texto extraído del PDF confirmó `LPWAN` = 0 apariciones, `802.15.4` = 1 y `Zigbee/6LoWPAN` = 1. También comprobé que el README no alterara el artículo y que las cifras coincidieran con `results.csv`.

### Etapa 7: Reestructuración de la bitácora, auditoría final y ajustes

**Prompt (resumen).** Cuatro solicitudes sucesivas:

- **(a) Reestructuración de la bitácora.** Reorganizar `PROMPTS_OPENCODE.md` como una bitácora profesional con nueve secciones: título, tabla de datos, nota de entorno, índice, tabla resumen de etapas, etapas cronológicas con prompt, resultado y correcciones, supervisión humana, limitaciones del uso de IA y declaración de integridad académica. Eliminar la nota sobre `mis_prompts.txt` y la frase que indicaba que los prompts del benchmark no estaban transcritos.
  **Intervención humana:** revisé visualmente el PDF, el README y la bitácora, y pedí la reestructuración.
- **(b) Auditoría final de ocho puntos.** Verificar los archivos obligatorios y de apoyo, la cobertura de `.gitignore`, la compilación de `benchmark.py`, las 600 filas y columnas de `results.csv`, el contenido del PDF, las cifras del README, la estructura de la bitácora y los datos de la autora, sin modificar archivos ni ejecutar el benchmark.
  **Intervención humana:** revisé visualmente el PDF, el README y la bitácora, y pedí la auditoría.
- **(c) Cabecera con código 36.** Añadir «Código 36 — Sistemas Distribuidos y Paradigmas de la Computación (ETL1TP50)» bajo el correo en el bloque de autor, renderizar y confirmar que el artículo seguía en cuatro páginas; después registrar la corrección en la supervisión humana.
  **Intervención humana:** revisé visualmente el PDF, el README y la bitácora, y pedí la corrección.
- **(d) Ajustes finales.** Actualizar en `README.md` la URL de clonado y el comentario de `.gitignore`; en esta bitácora, cambiar las etiquetas de las Etapas 1 y 2 y añadir esta Etapa 7.
  **Intervención humana:** revisé visualmente el PDF, el README y la bitácora, y pedí estos ajustes.

**Resultado del agente.** Se reorganizó la bitácora con las nueve secciones solicitadas y se añadieron los prompts históricos de las Etapas 1 y 2 con su etiqueta de versión resumida. La auditoría final verificó los ocho puntos: siete cumplieron y el punto 8 quedó parcial porque el PDF no mostraba el código 36 ni ETL1TP50. En (c) se añadió esa línea en `ieee-preamble.tex`; el primer render subió a cinco páginas, se compactó únicamente el interlineado del bloque de autor y el render final quedó en cuatro páginas. En (d) se verificó que el README ya contenía la URL y el comentario solicitados, y se actualizó esta bitácora.

**Correcciones y validaciones.** Revisé visualmente el PDF, el README y la bitácora antes de cada solicitud. La auditoría dejó constancia de 7 de 8 puntos conformes y de la parcialidad del punto 8, resuelta al añadir el código y la asignatura en la cabecera. Confirmé que el PDF final conserva las cuatro páginas, las referencias [1]–[8], las figuras 1–4 y las tablas I–II.

## Supervisión humana

- Revisé el PDF página por página antes de cada entrega.
- Contrasté las cifras del texto con la Tabla II y con `results.csv`.
- Verifiqué que las 8 referencias son reales y que los DOI disponibles coinciden con las fuentes originales.
- Detecté 3 errores —2 alucinaciones bibliográficas y 1 error técnico— y los corregí.
- Interrumpí al agente cuando entró en un ciclo de ajustes de la Tabla II.
- Comprobé la estructura del repositorio y la correspondencia entre los archivos entregables y las instrucciones de la asignatura.
- Añadí en `ieee-preamble.tex` la línea «Código 36 — Sistemas Distribuidos y Paradigmas de la Computación (ETL1TP50)» bajo el correo y confirmé que el PDF sigue en 4 páginas.

## Limitaciones del uso de IA

El agente alucinó datos bibliográficos: inventó la sede de Fidge 1988 y atribuyó editores incorrectos a Almeida 2008. También entró en ciclos de ajuste cuando una solución de maquetación no funcionaba, y perdió el contexto de los primeros prompts al resumir su memoria durante sesiones largas. Por esas razones, toda salida del agente fue auditada: contrasté las referencias con las fuentes originales, verifiqué las cifras contra `results.csv`, revisé el PDF compilado y corregí manualmente cada error antes de considerarlo parte de la entrega.

## Declaración de integridad académica

Declaro que soy la autora de esta investigación y que el trabajo intelectual, el diseño experimental, el análisis y las conclusiones son míos. Usé OpenCode únicamente como asistente de codificación y maquetación. Revisé, validé y corregí todo el código, los datos y el texto; comprobé la verdad de referencia, las cifras, las figuras, las tablas y las referencias bibliográficas. Los resultados no fueron alterados y las referencias incluidas son reales. Asumo la responsabilidad final sobre el contenido del artículo y de este repositorio.

**Firma:** Deisy Elizabeth Calle Calle  
**Riobamba, 13 de noviembre de 2026**
