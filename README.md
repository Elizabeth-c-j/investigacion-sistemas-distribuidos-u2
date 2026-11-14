# Evaluación Comparativa de Relojes Vectoriales vs. Lamport

### Análisis de consumo de memoria y detección de eventos concurrentes en topologías de malla

**Autora:** Deisy Elizabeth Calle Calle — código **36**  
**Carrera:** Ingeniería en Telemática, Facultad de Informática y Electrónica  
**Institución:** Escuela Superior Politécnica de Chimborazo (ESPOCH), Riobamba, Ecuador  
**Asignatura:** Sistemas Distribuidos y Paradigmas de la Computación (**ETL1TP50**)

[![Artículo](https://img.shields.io/badge/Art%C3%ADculo-PDF-8A1538)](articulo.pdf)
[![Bitácora](https://img.shields.io/badge/Bit%C3%A1cora-PROMPTS__OPENCODE.md-1F4E79)](PROMPTS_OPENCODE.md)
[![Datos](https://img.shields.io/badge/Datos-results.csv-2E7D32)](results.csv)

**Documento final:** [`articulo.pdf`](articulo.pdf) (4 páginas, formato IEEE Conference)  
**Bitácora de prompts y supervisión humana:** [`PROMPTS_OPENCODE.md`](PROMPTS_OPENCODE.md)

---

## Resumen

Comparo los relojes de Lamport y los vectoriales en consumo de metadatos, memoria y capacidad de detectar concurrencia. Implementé un simulador de eventos discretos con *jitter* uniforme de $[0, 50]$ ms sobre un retardo base de 10 ms y ejecuté 300 simulaciones en mallas completa y parcial ($k=3$) con $N \in \{4, 8, 16, 32, 64\}$ y 30 repeticiones. Verifiqué la verdad de referencia por alcanzabilidad exacta sobre el grafo de causalidad, independiente de ambos relojes, y clasifiqué 20 000 pares aleatorios por ejecución. El reloj vectorial detectó el 100 % de los pares concurrentes con cero falsos ordenamientos, mientras que Lamport detectó el 0 %; ambos conservaron el 100 % de consistencia causal. Para $N=64$ el vectorial consumió 512 B por mensaje frente a 8 B (64 veces más) y acumuló 1,96 MB frente a 30,6 KB, con un pico medido de 36,36 KB frente a 3,07 KB y un costo de actualización de 12,30 ms frente a 1,76 ms. La malla parcial generó hasta un 46,9 % más de concurrencia. Concluyo que el vectorial es imprescindible para razonar sobre concurrencia y que Lamport sigue siendo eficiente cuando basta un orden total.

**Palabras clave:** relojes lógicos, relojes vectoriales, causalidad, concurrencia, sistemas distribuidos.

---

## Hipótesis y veredicto

| ID | Hipótesis | Evidencia | Veredicto |
|:--:|-----------|-----------|:---------:|
| **H1** | El reloj vectorial detecta el 100 % de los eventos concurrentes; Lamport detecta el 0 % porque su orden escalar es total. | Detección vectorial = 1,000 y detección Lamport = 0,000 en las cinco magnitudes de $N$ y ambas topologías; cero falsos ordenamientos vectoriales. | **Aceptada** |
| **H2** | El overhead vectorial crece con $N$ ($8N$ bytes por mensaje y por proceso) y el de Lamport permanece constante (8 bytes). | 32, 64, 128, 256 y 512 B por mensaje para $N=4\ldots64$; Lamport se mantiene en 8 B en todos los casos. | **Aceptada** |
| **H3** | La malla parcial, con menos caminos causales, produce más eventos concurrentes que la completa. | Incremento de pares concurrentes del 17,7 % ($N=8$), 31,5 % ($N=16$), 44,1 % ($N=32$) y 46,9 % ($N=64$); sin diferencia en $N=4$. | **Aceptada** |

---

## Resultados clave

Cifras calculadas como media de 30 repeticiones por configuración a partir de [`results.csv`](results.csv) (600 filas = 300 ejecuciones × 2 relojes). Las unidades de almacenamiento son decimales: 1 KB = 1000 B y 1 MB = 1000 KB.

### Consumo de metadatos, memoria y tiempo

| $N$ | Bytes/mensaje<br>Lamport | Bytes/mensaje<br>Vectorial | Overhead acumulado<br>Lamport (KB) | Overhead acumulado<br>Vectorial (KB) | Memoria pico<br>Lamport (KB) | Memoria pico<br>Vectorial (KB) | Actualización<br>Lamport (ms) | Actualización<br>Vectorial (ms) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4  | 8 | 32  | 1,9    | 7,6     | 0,19 | 0,36  | 0,09 | 0,16  |
| 8  | 8 | 64  | 3,8    | 30,5    | 0,38 | 0,97  | 0,19 | 0,41  |
| 16 | 8 | 128 | 7,7    | 122,5   | 0,77 | 2,95  | 0,33 | 0,96  |
| 32 | 8 | 256 | 15,3   | 489,1   | 1,54 | 9,99  | 0,79 | 3,36  |
| 64 | 8 | 512 | 30,6   | 1.960,1 | 3,07 | 36,36 | 1,76 | 12,30 |

En $N=64$ el reloj vectorial transporta **64 veces más metadatos por mensaje**, acumula **64 veces más overhead**, ocupa **11,8 veces más memoria pico** y cuesta **7,0 veces más tiempo** de actualización que Lamport.

### Concurrencia y detección

| $N$ | Pares concurrentes<br>malla completa | Pares concurrentes<br>malla parcial | Δ parcial vs. completa | Detección<br>vectorial | Detección<br>Lamport | Consistencia<br>causal |
|---:|---:|---:|---:|---:|---:|---:|
| 4  | 3.703  | 3.703  | 0,0 %  | 1,000 | 0,000 | 100,00 % |
| 8  | 5.627  | 6.622  | +17,7 % | 1,000 | 0,000 | 100,00 % |
| 16 | 7.370  | 9.691  | +31,5 % | 1,000 | 0,000 | 100,00 % |
| 32 | 8.941  | 12.888 | +44,1 % | 1,000 | 0,000 | 100,00 % |
| 64 | 10.438 | 15.337 | +46,9 % | 1,000 | 0,000 | 100,00 % |

**Lectura telemática:** con $N=64$ el vectorial añade 512 B a cada mensaje. En enlaces IEEE 802.15.4 (Zigbee/6LoWPAN), cuya trama máxima es de 127 B, ese costo es prohibitivo y obliga a comprimir marcas o a emplear *Interval Tree Clocks*; en mallas WiFi o Ethernet, en cambio, el overhead es despreciable y la detección exacta mejora la observabilidad sin comprometer el ancho de banda.

---

## Estructura del repositorio

```text
investigacion-sistemas-distribuidos-u2/
├── articulo.qmd            # Fuente Quarto del artículo (texto, ecuaciones, tablas y figuras)
├── articulo.pdf            # PDF final compilado, 4 páginas, formato IEEE Conference
├── benchmark.py            # Simulador de eventos discretos y generador de results.csv
├── results.csv             # 600 filas: 300 ejecuciones × 2 relojes (datos primarios)
├── _quarto.yml             # Configuración de Quarto: IEEEtran, pdflatex, figuras PNG 300 dpi
├── ieee.csl                # Estilo de citación IEEE (CSL) usado por citeproc
├── ieee-preamble.tex       # Ajustes tipográficos y bloque de autoría para IEEEtran
├── references.bib          # Bibliografía en BibTeX (8 referencias)
├── PROMPTS_OPENCODE.md     # Bitácora literal de prompts e intervenciones humanas
├── README.md               # Este archivo
└── .gitignore              # Excluye artefactos temporales de compilación y notas personales
```

Las figuras se regeneran en `.quarto/_freeze/articulo/figure-pdf/` durante el render; el directorio `.quarto/` es interno y está excluido del control de versiones.

---

## Requisitos

| Componente | Versión usada | Función |
|------------|---------------|---------|
| **Python** | 3.14.3 (compatible con 3.10+) | Ejecuta el simulador y los bloques del artículo |
| **pandas** | 3.1.1 | Carga, agrega y resume `results.csv` |
| **matplotlib** | 3.11.2 | Genera las cuatro figuras en PNG |
| **Jupyter** | Motor de ejecución | Quarto ejecuta los chunks `{python}` mediante Jupyter |
| **Quarto** | 1.11.9 | Renderiza `articulo.qmd` a PDF |
| **TinyTeX** | 2026 | Distribución LaTeX con `pdflatex` e `IEEEtran` |

> El artículo usa `pdf-engine: pdflatex` y `fontfamily: times` porque `IEEEtran` está diseñada para `pdflatex` y sus fuentes PostScript Times. LuaLaTeX sustituiría la tipografía y alteraría el formato.

Instalación de las dependencias de Python:

```bash
python -m pip install --upgrade pip
python -m pip install pandas matplotlib jupyter
```

Instalación de Quarto y TinyTeX (si no están disponibles):

```bash
quarto install tinytex
quarto check
```

---

## Guía de reproducción

### 1. Preparar el entorno

```bash
git clone https://github.com/Elizabeth-c-j/investigacion-sistemas-distribuidos-u2.git
cd investigacion-sistemas-distribuidos-u2

python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install pandas matplotlib jupyter
```

### 2. Regenerar los datos

```bash
python benchmark.py
```

El script ejecuta las 300 simulaciones (5 valores de $N$ × 2 topologías × 30 repeticiones), evalúa ambos relojes sobre las mismas trazas y escribe `results.csv` con 600 filas. Las semillas son deterministas (`SEMILLA_BASE + repeticion`), por lo que las cifras son reproducibles.

Para una verificación rápida (menos nodos y repeticiones):

```bash
python benchmark.py --rapido
```

También se puede cambiar la ruta de salida:

```bash
python benchmark.py --salida resultados_alternativos.csv
```

> Si se usa `--rapido` o `--salida`, el artículo seguirá leyendo `results.csv`; restáurelo con una ejecución completa antes de renderizar.

### 3. Compilar el artículo

```bash
quarto render articulo.qmd
```

El comando ejecuta los chunks de Python (que leen `results.csv` y generan las figuras), aplica `ieee.csl` y `references.bib` mediante citeproc, y produce `articulo.pdf`.

### 4. Verificar el resultado

- `articulo.pdf` debe tener **4 páginas**.
- Las figuras 1–4 deben aparecer numeradas y referenciadas en el texto.
- Las tablas I–II deben aparecer en LaTeX puro, sin `longtable`.
- Las citas deben salir como `[1]`–`[8]`.
- La consola no debe mostrar errores de compilación ni bloques `overfull`/`underfull`.

---

## Configuración editorial

### `ieee.csl`

Archivo en **Citation Style Language** que implementa el estilo numérico IEEE. Pandoc lo usa a través de `cite-method: citeproc` (definido en `_quarto.yml`) para transformar las claves de `references.bib` en citas `[1]`, `[2]`, … y construir la lista final de referencias con el orden de aparición. Al ser citeproc, **no se ejecuta BibTeX ni Biber**: toda la bibliografía se resuelve dentro de Pandoc.

### `ieee-preamble.tex`

Preámbulo LaTeX que Quarto inyecta con `include-in-header` después de cargar los paquetes de Pandoc. Resuelve cuatro incompatibilidades entre Pandoc y `IEEEtran`:

1. **Sangría de párrafo:** `parskip` anula la sangría; se restauran `\parindent = 1em` y `\parskip = 0pt`.
2. **Leyendas:** se difiere `\captionsetup` a `\AtBeginDocument` para obtener etiqueta en negrita, separada por punto y con tamaño IEEE.
3. **Autoría:** se reemplaza el `\author{...}` plano de Pandoc por `\IEEEauthorblockN` y `\IEEEauthorblockA` (nombre, afiliación y correo), y se traduce `\IEEEkeywordsname` a «Palabras clave».
4. **Flotantes:** se ajustan `\textfloatsep`, `\intextsep` y `\floatsep` para que cuatro figuras y dos tablas convivan con el texto sin páginas casi vacías.

### `_quarto.yml`

Fija el formato IEEE Conference en dos columnas, tamaño carta, `pdflatex` + Times, figuras PNG a 300 dpi, `longtable: false` (las tablas se escriben en LaTeX puro porque `longtable` no funciona a dos columnas) y la integración de `ieee.csl`, `references.bib` y `ieee-preamble.tex`.

---

## Bitácora y supervisión humana

El archivo [`PROMPTS_OPENCODE.md`](PROMPTS_OPENCODE.md) documenta, en orden cronológico, las **7 etapas** del trabajo:

1. **Benchmark y datos:** diseño del simulador, generación de `results.csv` y validación de la verdad de referencia.
2. **Configuración Quarto/IEEE:** `_quarto.yml`, `ieee.csl`, `references.bib` y ajustes de IEEEtran, `pdflatex` y tablas en LaTeX.
3. **Redacción del artículo:** las seis secciones, las figuras y tablas, y el ajuste final a 4 páginas.
4. **Interrupción humana en el ciclo de la Tabla II:** cambio a un bloque raw de LaTeX para evitar los artefactos de Quarto.
5. **Corrección de 2 alucinaciones bibliográficas:** sede de Fidge 1988 y editores de Almeida 2008.
6. **Corrección técnica LPWAN → IEEE 802.15.4 y creación del README:** corrección de la sección V-C y cierre documental del repositorio.
7. **Reestructuración de la bitácora, auditoría final de 8 puntos y ajustes:** verificación del repositorio y adición de «Código 36 — Sistemas Distribuidos y Paradigmas de la Computación (ETL1TP50)» en la cabecera.

La bitácora incluye además las secciones de **supervisión humana**, **limitaciones del uso de IA** y la **declaración de integridad académica firmada** por la autora.

---

## Cómo citar este trabajo

```text
Calle Calle, D. E. (2026). Evaluación Comparativa de Relojes Vectoriales vs. Lamport:
Análisis de Consumo de Memoria y Detección de Eventos Concurrentes en Topologías de Malla.
Investigación de Sistemas Distribuidos y Paradigmas de la Computación (ETL1TP50),
Escuela Superior Politécnica de Chimborazo (ESPOCH), Riobamba, Ecuador.
```

---

**Licencia y uso académico.** Trabajo de investigación individual presentado para la asignatura ETL1TP50. El código y los datos se comparten con fines de verificación y reproducción académica.
