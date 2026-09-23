# tests/ — auditoría del dashboard

Cuatro scripts de verificación que recogen el método de trabajo de `DECISIONES.md` (sección 7): reglas de diseño, cifras validadas por cálculo independiente, dashboard en varios estados y medidas en un navegador real. No son pruebas unitarias: comprueban que el dashboard **cumple lo decidido**. Cada uno termina con código de salida 0 si todo está bien y 1 si algo falla, y dice cuál comprobación falló y por qué.

## Cómo correrlos

Desde la **raíz del proyecto**:

```bash
python tests/correr_todo.py                    # los cuatro, con un resumen final (≈1 minuto)
python tests/correr_todo.py --sin-navegador    # omite el que necesita Chrome
python tests/verificar_reglas.py               # o uno solo
```

Necesitan lo de `requirements.txt` y, para `verificar_pantalla.py`, **Chrome o Chromium** instalado (si no está en la ruta habitual, defina la variable de entorno `CHROME_PATH`). `pyflakes` es una herramienta de desarrollo y **no** está en `requirements.txt`: está en `requirements-dev.txt` (`pip install -r requirements-dev.txt`). Si está instalada, `verificar_reglas.py` la usa; si no, lo avisa y sigue.

## Qué verifica cada uno

| Script | Cómo mira | Qué comprueba |
|---|---|---|
| `verificar_reglas.py` | Lee el código (estático) | Que el código compile y pase pyflakes; ningún color ni tamaño de texto literal fuera de `theme.py`; solo los tamaños de texto permitidos; ámbar únicamente como la línea de hallazgo del Resumen (`charts.brechas_resumen`, `.aviso` es neutro) y verde sin uso; `.panel-sep` en `BORDER`; `.streamlit/config.toml` igual a los tokens de `theme.py`; sin «retorno», «Mantener» ni lo descartado; sin cifras de referencia escritas en los textos; el slider de la Matriz tomado de `metrics.py`; opacidades de Valoración (1,0 / 0,70 / 0,40), separación de 2 px en `BG` entre segmentos, porcentaje escrito en cada segmento con títulos y contraste ≥ 4,5:1 de toda etiqueta dentro de un segmento; las 6 páginas del riel (Metodología ya no es página ni pestaña), cada una como archivo en `dashboard/pages/`; el riel (`st.navigation(position="sidebar")`, `st.logo`) y su CSS aislado (solo testids/ARIA, nunca una clase `st-emotion-cache-*`); la barra de filtros horizontal (`st.container(key="barra_filtros")` en `dashboard/_shell.py`, con `st.segmented_control`/`st.pills`/`st.multiselect`); que el sidebar ya no tenga «Reiniciar filtros» ni «Contexto del análisis»; el popover «Datos» en `_shell.py` con el estilo que comparte con CSV y su contenido (3 puntos, limitaciones clave y línea final, sin tablas ni código); que `docs/metodologia.md` esté **al día** con `src/metodologia.py` y traiga sus secciones y tablas; traducciones que cubren todos los géneros y países de los CSV; y que `images/` tenga exactamente los PNG que genera `src/exportar.py`. |
| `verificar_cifras.py` | Recalcula con pandas desde el CSV crudo, **sin usar `src/`** | Las cifras de la sección 4 de `DECISIONES.md` (KPIs, Matriz y sus zonas, popularidad relativa por género y por país, concentración de mercados, razón series/películas y ventaja en valoración alta por año, brecha de valoración mediana). Cada una se compara con el cálculo independiente, con lo que devuelve `src/metrics.py` y con el valor escrito en `DECISIONES.md`. Incluye el caso de Drama (10.305 con las etiquetas repetidas deduplicadas; 10.306 sin deduplicar). |
| `verificar_estados.py` | `streamlit.testing.v1.AppTest` (sin navegador) | Corre la app completa en 7 estados (por defecto, solo Película, solo Serie, género = Drama, país = México, año 2024 y una combinación que deja 0 títulos) con los dos modos de conteo de países y las dos métricas de Evolución. Es un app multipágina de ARCHIVOS (`dashboard/pages/*.py`): visita cada una con `AppTest.switch_page` (la única forma de multipágina que sabe manejar — no funciona con páginas declaradas como función). En cada estado: sin excepciones; exactamente 6 páginas; el popover «Datos» existe (también con 0 títulos) con su contenido; 4 KPIs con el denominador explícito; Resumen con tesis y 3 tarjetas; **0 oraciones idénticas entre el Resumen y las otras páginas ni el popover**; ninguna recomendación que pida reducir o recortar ni que frene algo con popularidad relativa > 1; que el **título-mensaje de cada página analítica sea verdadero**, recalculándolo por su cuenta desde el CSV y comparándolo con el texto renderizado; y que **ningún gráfico de ninguna página, en ningún estado, quede vacío** (≥ 1 traza con datos reales) **ni con un eje fuera de su dominio esperado** (años, cantidad de títulos, valoración, países, proporciones…) — `streamlit.testing.v1` por sí solo solo detecta excepciones, no figuras vacías; así se encontró el bug real del gráfico de brechas del Resumen con un solo formato filtrado (`DECISIONES.md`, sección 6). |
| `verificar_pantalla.py` | Chrome real sin ventana, controlado por CDP | A 1920×1080: KPIs sin desborde y con el subtexto en una línea; bloque superior medido; tesis y 3 tarjetas visibles sin scroll; el titular de la tesis como único elemento de 32 px del Resumen; el **riel de navegación** (Paso 2): angosto (~84 px), con el logo (`st.logo`) arriba, sus 6 páginas, la activa con fondo resaltado y su ícono en `PELICULA` (rojo), y CSV + «Datos» al pie — es la comprobación en pantalla de la nota de aislación de `theme.py` (si un testid de Streamlit del que depende ese CSS desapareciera en una versión futura, esta es la comprobación que fallaría); la **barra de filtros horizontal**: Formato como `segmented_control` de 3 opciones y los 3 popover (Años/Género/País) mostrando su selección; el popover «Datos» **abre** con sus 3 puntos y sus limitaciones clave (sin tablas ni código, sin recortes) y se cierra; y que el fondo de cada gráfico sea transparente (se funde con la tarjeta). A 1600, 1440 y 1366 px: KPIs sin desborde y riel igual de angosto. Además hace clic en las 6 páginas del riel y en el desplegable de la Matriz. |

`_comun.py` y `_navegador.py` son utilidades compartidas (contador de comprobaciones; servidor de Streamlit y cliente de Chrome).

## Comparar antes y después de un cambio (regresión)

`verificar_estados.py` puede guardar todo lo que renderiza el dashboard y compararlo después con otra ejecución. Sirve para demostrar que un refactor **no cambió nada visible**:

```bash
python tests/correr_todo.py --guardar antes.json     # antes del cambio
# ... se edita el código ...
python tests/correr_todo.py --comparar antes.json    # después: además de todo lo anterior, exige un renderizado idéntico
```

Lo guardado incluye el pie de página con la fecha («Generado: …»): compare ejecuciones del mismo día.

## Si algo falla

- Una comprobación de `verificar_cifras.py` que falla dice los tres valores (independiente, dashboard y `DECISIONES.md`): si los dos primeros coinciden y el tercero no, cambió el dato o la regla y hay que decidir si se actualiza `DECISIONES.md`; si el dashboard difiere del cálculo independiente, hay un error en `src/`.
- Si `verificar_estados.py` marca un título como falso, muestra el texto renderizado y el recalculado uno debajo del otro. Si marca un gráfico vacío o con el eje fuera de dominio, muestra cuántas trazas tenía y qué valores quedaron fuera de rango.
- Si `verificar_pantalla.py` no encuentra Chrome, se omite y lo avisa: eso **no** cuenta como aprobado.
- Sin internet, el navegador no carga la fuente Inter y usa Arial: las medidas del navegador pueden variar un poco.
- `verificar_pantalla.py` da clic real en el riel entre una página y otra: si algo se ve intermitente (un marcador que a veces no aparece justo después del clic), es una carrera de tiempos del navegador headless contra el rerender de Streamlit, no un error del dashboard — el script ya espera el marcador correcto de cada página (recuadro fijo o expander) antes de medir, con un margen y un reintento corto.
