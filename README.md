# StreamView Analytics - Visualización de Datos

## Descripción del Proyecto
Este proyecto fue desarrollado como una solución integral de visualización de datos para **StreamView Analytics**, una plataforma internacional de streaming digital. El dashboard audita el catálogo de películas y series para responder una pregunta de gestión: **¿dónde concentrar la inversión en licencias para sostener la retención de suscriptores?** Está pensado para el equipo de Contenidos y Adquisiciones.

Proyecto del ramo ADY1104 (Visualización de Datos), DUOC UC. Autores: Maicol Hernández · Francis Moya.

## Hallazgos y tesis
Antes de construir un solo gráfico, el análisis exploratorio (`notebooks/analisis_exploratorio.ipynb`) auditó la calidad de los datos: el reparto de títulos por año resultó demasiado regular para ser real (exactamente 1.000 por año y formato, sugiriendo datos sintéticos o muestreados por cuotas); `rating` resultó idéntica a `vote_average` en las 32.000 filas, así que no aporta una clasificación por edad; 20 de los 28 géneros existen en un solo formato porque el origen usa taxonomías distintas para películas y series; el año 2025 está incompleto (68 % de los títulos sin votos, frente a 11 % en años anteriores); y `popularity` es un índice muy asimétrico (el promedio casi duplica la mediana). Estos cinco hallazgos son la razón detrás de decisiones concretas del dashboard: no se analiza volumen por año, se descarta `rating`, los géneros no se fusionan entre formatos, 2025 se muestra pero fuera de los extremos de tendencia, y todo el dashboard resume con la **mediana**, no el promedio.

Sobre el conjunto por defecto (2015–2025, ambos formatos, 22.000 títulos), dos hechos sostienen la tesis del Resumen — **«Las series rinden más que las películas y deben priorizarse»**:
1. Su ventaja en **popularidad** se achica: de 4,4× en 2015 a 1,2× en 2024 (las series bajan 34 % en 2020; las películas suben de 10,3 a 27,7 entre 2020 y 2024).
2. Su ventaja en **valoración alta** crece: de +23 a +34 puntos porcentuales en el mismo período, superando a las películas los once años — esta métrica no depende del índice de popularidad de TMDB, por eso es la que sostiene la prioridad.

De ahí salen las tres acciones de «Qué hacer» del Resumen: priorizar series; licenciar películas de los géneros que rinden sobre su formato (Aventura, Acción y Suspenso); y diversificar hacia Filipinas y México sin recortar los mercados actuales. La tesis y las tres acciones **se calculan en cada filtro, nunca se escriben a mano**: con un solo formato filtrado no hay con qué comparar popularidad o valoración entre formatos, así que el Resumen cambia a un ranking de géneros por ese formato en vez de forzar una comparación que ya no aplica. El detalle completo del análisis, con sus gráficos y una celda que verifica con `assert` cada cifra citada, está en el notebook.

## Qué muestra el dashboard
Cuatro indicadores globales (siempre visibles) y seis páginas, en un riel de navegación a la izquierda, ordenadas como una narración, de la conclusión a la acción:

| Página | Qué responde |
|---|---|
| **Resumen** | La tesis y, debajo, la razón: con ambos formatos, el gráfico de brechas por año junto a «Qué hacer», las tres decisiones que se desprenden de él; con un solo formato filtrado, un ranking de géneros por popularidad relativa a ese formato (la tesis, en ese caso, habla de géneros). |
| **Géneros** | Un solo gráfico: volumen y popularidad relativa a su formato de los 15 géneros con más títulos, coloreados por el formato en que existen. |
| **Mercados** | Países de origen por formato, con indicador de concentración, popularidad relativa por país y conteo por primer país o por coproducción. |
| **Evolución** | Popularidad o valoración mediana por año, Película vs Serie. |
| **Valoración** | Composición de cada formato por nivel de valoración (alta, media, baja y sin votos), con leyenda de niveles. |
| **Matriz** | Popularidad vs valoración por título, con los cuatro cuadrantes contados y, en una lista, los títulos en riesgo de abandono (con su descarga). |

Al pie del riel, el botón **CSV** descarga el conjunto filtrado y el botón **Datos** abre un resumen de la fuente de datos, de lo que controla el análisis y de sus limitaciones clave. El texto completo (métricas derivadas, criterios de corte y limitaciones) está en `docs/metodologia.md`.

Cada gráfico lleva un título que enuncia su conclusión (se recalcula con los filtros) y un subtítulo; en Géneros, Evolución y Valoración, la columna derecha también trae un recuadro con el método. Todas las cifras se calculan sobre el conjunto filtrado y usan formato es-CL (`10.305`, `23,2`). Géneros y países se muestran en español.

**Convención de color:** rojo = Película, gris = Serie en todo gráfico que separa por formato. Excepciones, siempre con leyenda: el gráfico de géneros colorea por el formato en que existe cada género (rojo solo películas, gris claro solo series, gris oscuro ambos), y las barras de Valoración usan el nivel (intensidad, con su propia leyenda) dentro del color del formato.

### Uso
* **Riel de navegación** (izquierda, angosto): logo, las 6 páginas (ícono + texto; la activa, resaltada con su ícono en rojo) y, al pie, **CSV** y **Datos**.
* **Filtros** (barra horizontal, arriba de los indicadores): **Formato** (Ambos/Película/Serie) y tres botones — **Años**, **Género** y **País** — que abren un popover con el control (deslizador, o chips de selección) y muestran la selección actual en su propio texto; el que tiene una selección activa queda resaltado. Al final de la barra, **Limpiar filtros** (si hay algún filtro activo) o «Vista completa, sin filtros». Los filtros se guardan en la sesión y se mantienen al cambiar de página.
* Mercados indica cuántos títulos tienen país registrado, porque ese denominador difiere del indicador global (va en su propio subtítulo). Cada gráfico tiene un botón para **descargarlo como PNG**.
* Si una combinación de filtros deja 0 títulos, el dashboard lo dice y sugiere qué filtro relajar.
* Si se elige un solo formato, Evolución y Valoración avisan que comparan ambos.

## Estructura del Repositorio
* `DECISIONES.md`: **las reglas y decisiones vigentes del proyecto** (color, tipografía, formato es-CL, redacción de recomendaciones, decisiones tomadas y descartadas, cifras validadas y criterio de trabajo). Léelo antes de modificar algo.
* `requirements.txt`: dependencias con las versiones mínimas con que se probó. `requirements-dev.txt`: herramientas de desarrollo (hoy solo `pyflakes`); incluye a `requirements.txt`.
* `.streamlit/config.toml`: tema nativo de Streamlit (colores del «chrome» que el CSS no alcanza). **Debe mantenerse sincronizado con `src/theme.py`** (ver más abajo).
* `data/`: los dos archivos CSV de origen (películas y series).
* `dashboard/app.py`: entrypoint de la app (multipágina, `st.navigation`). Solo arma el riel y llama a `_shell.preparar()` y a `pg.run()`; no tiene lógica propia.
* `dashboard/_shell.py`: lo común a las 6 páginas — carga de datos, header, barra de filtros horizontal, franja de KPIs y CSV/«Datos» del riel. Deja su resultado en `st.session_state` para que cada página lo lea (un app multipágina de archivos no puede recibir argumentos).
* `dashboard/pages/`: una página por archivo (`resumen.py`, `generos.py`, `mercados.py`, `evolucion.py`, `valoracion.py`, `matriz.py`). Cada una lee el contexto de `_shell.contexto()` y solo llama a `src/`.
* `dashboard/assets/logo_sv.svg`: el logo del riel (`st.logo`).
* `src/`: lógica del dashboard, sin duplicar código entre gráficos.
  * `data_loader.py`: carga y une los CSV, y traduce géneros y países al español.
  * `metrics.py`: todos los cálculos y umbrales (por ejemplo, el corte de valoración de riesgo).
  * `charts.py`: los gráficos Plotly (uno por función).
  * `kpis.py`: el HTML de la franja de indicadores de la cabecera (4 celdas con ícono, en un solo contenedor).
  * `exportar.py`: regenera los PNG de `images/` con esos mismos gráficos (ver más abajo).
  * `narrative.py`: títulos-mensaje, paneles de hallazgo/recomendación, notas al pie y tablas.
  * `metodologia.py`: el contenido del popover «Datos» (pie del riel) y el texto completo de metodología y limitaciones (sus cifras se calculan, no se escriben a mano). `python -m src.metodologia` genera `docs/metodologia.md`.
  * `theme.py`: sistema de diseño único (colores, tipografía, formato de números y estilos).
* `docs/metodologia.md`: metodología completa (fuente de datos, tablas de métricas derivadas y de criterios de corte, y limitaciones), para usarla en el informe. **Se genera desde `src/metodologia.py`; no se edita a mano.**
* `notebooks/analisis_exploratorio.ipynb`: el análisis exploratorio que llevó a las decisiones del dashboard (calidad de los datos, distribuciones y hallazgos que sustentan la tesis), ejecutado y con sus salidas visibles. Reutiliza `src/`; no forma parte de la aplicación.
* `tests/`: scripts de auditoría (reglas de diseño, cifras validadas con cálculo independiente, dashboard en varios estados y medidas en un navegador real). Cómo correrlos, en `tests/README.md`.
* `images/`: un PNG por gráfico principal, generado por `src/exportar.py` con los filtros por defecto (no se editan a mano).

## Cómo se construyó
El proyecto se hizo en rondas, cada una verificada con la auditoría automatizada antes de pasar a la siguiente:

1. **Análisis exploratorio** (notebook): integración de los dos CSV, cinco preguntas sobre calidad de datos, distribuciones de `popularity`/`vote_average` y los hallazgos que sustentan la tesis (sección anterior).
2. **Dashboard base**: seis páginas (Resumen + 5 analíticas) con títulos-mensaje que enuncian su conclusión —recalculada con los filtros, nunca escrita a mano— y un panel de hallazgo con su recomendación.
3. **Rediseño de contenido (Paso 1):** franja de 4 KPIs en un solo contenedor (antes, tarjetas sueltas); el panel de cada página pasó a número + hallazgo + recomendación; y las notas al pie largas de cada gráfico se reemplazaron por un recuadro corto con el método.
4. **Rediseño de navegación (Paso 2):** la barra lateral con pestañas (`st.tabs`) se reemplazó por un riel angosto de íconos (`st.navigation`) y una barra de filtros horizontal (`st.segmented_control`/`st.pills`/`st.popover`/`st.multiselect`), con el botón CSV y el popover «Datos» al pie del riel. Una ronda de ajuste posterior corrigió el centrado del logo y los íconos del riel, e incluyó un hallazgo puntual: el logo estaba descentrado dentro de su propio archivo SVG, no solo por el CSS del contenedor que lo envuelve.
5. **Simplificación de la interfaz:** se retiró el título «Cómo leer este gráfico» de las páginas donde el recuadro de método se mostraba siempre abierto (Géneros, Evolución, Valoración), y se eliminó por completo donde vivía dentro de un menú desplegable (Mercados, Matriz).
6. **Aseguramiento de calidad**, en paralelo a cada ronda: cuatro scripts de auditoría (`tests/`, ver más abajo) comprueban que el código cumple las reglas de diseño, que las cifras coinciden con un cálculo independiente hecho desde el CSV crudo (sin usar `src/`), que el dashboard no lanza excepciones ni dibuja un gráfico vacío en varios estados de filtros, y que las medidas reales en un navegador Chrome (tamaños, alineación, contraste) coinciden con lo decidido.

Cada decisión de diseño, su motivo y las alternativas descartadas quedan registrados en `DECISIONES.md`; el detalle de qué comprueba cada script de auditoría está en `tests/README.md`.

## Fuentes de Datos
Conjuntos de datos hasta 2025, con 16.000 películas y 16.000 series:
- `netflix_movies_detailed_up_to_2025.csv`
- `netflix_tv_shows_detailed_up_to_2025.csv`

Las limitaciones de estos datos (reparto sintético 50/50, `popularity` como índice relativo, año 2025 incompleto, entre otras) están declaradas en el botón **Datos** del riel del dashboard y, completas, en `docs/metodologia.md`.

## Herramientas Utilizadas
- **Lenguaje:** Python 3.10
- **Análisis:** Pandas, NumPy
- **Dashboard:** Streamlit y Plotly
- **Imágenes:** Kaleido (necesita un Chrome o Chromium instalado)
- **Notebook exploratorio:** `ipykernel` (y `nbconvert` para ejecutarlo por línea de comandos); sus gráficos son imágenes estáticas hechas con Kaleido
- **Auditoría (`tests/`):** las mismas dependencias, más Chrome o Chromium para `verificar_pantalla.py`; `pyflakes` es opcional y está en `requirements-dev.txt`

Versiones con las que se probó: Streamlit 1.64.0, Pandas 2.3.3, NumPy 2.2.6, Plotly 7.1.0, Kaleido 1.4.0, ipykernel 7.2.0. El dashboard usa opciones recientes de Streamlit (por ejemplo `width="stretch"`), por lo que conviene una versión igual o posterior.

## Instalación y Ejecución
Sigue estos pasos desde la terminal, posicionado en la carpeta raíz del proyecto. Usar `python -m` evita problemas con la variable de sistema PATH en distintos equipos.

1. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar el dashboard:**
   ```bash
   python -m streamlit run dashboard/app.py
   ```
   Se abre en el navegador, normalmente en `http://localhost:8501`. Con los 32.000 registros, la primera carga tarda alrededor de 2 segundos y las siguientes menos de 1, porque los datos quedan en caché.

3. **Regenerar las imágenes de `images/`** (opcional; reemplaza los PNG con los gráficos actuales y sus títulos):
   ```bash
   python -m src.exportar
   ```
   *Limitación conocida:* los PNG se dibujan con Arial y no con Inter (la fuente del dashboard), porque Kaleido usa las fuentes instaladas en el sistema y Inter no lo está. Si se instala Inter en el sistema antes de exportar, Chrome debería usarla (no se comprobó aquí).

4. **Regenerar `docs/metodologia.md`** (opcional; hace falta si cambia un umbral o un texto de `src/metodologia.py`):
   ```bash
   python -m src.metodologia
   ```

5. **Ejecutar la auditoría** (opcional; ≈1 minuto, desde la raíz del proyecto):
   ```bash
   python tests/correr_todo.py
   ```
   Detalle de cada verificación en `tests/README.md`.

6. **Abrir o reejecutar el notebook** (opcional): ábrelo en VS Code o Jupyter, o vuelve a ejecutarlo por completo con
   ```bash
   jupyter nbconvert --to notebook --execute --inplace notebooks/analisis_exploratorio.ipynb
   ```


