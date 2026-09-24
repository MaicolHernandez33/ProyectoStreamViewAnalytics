"""
Sistema de diseño único de StreamView Analytics.

Todo color, tamaño tipográfico, formato numérico y layout de Plotly compartido
vive en este archivo. Ningún otro módulo debe escribir un color literal
(hex, rgb/rgba o nombre CSS como "gray"): se importa desde aquí.

Uso típico:
    from src import theme
    st.markdown(theme.ESTILOS, unsafe_allow_html=True)
    fig = theme.aplicar_layout(px.line(...))
    valor = theme.fmt_float(23.2)  # "23,2"
"""

# ============================================================
# COLORES
# ============================================================
# Fondos y estructura (solo estos tres tonos en todo el dashboard)
BG = "#0E0E10"          # fondo general de la app — gris muy oscuro, nunca negro puro
SURFACE = "#17171A"     # tarjetas, sidebar y paneles (un único tono "superficie")
BORDER = "#2A2A2E"      # bordes y líneas divisorias

# Texto (solo dos tonos)
TEXT = "#F2F2F3"        # texto primario
TEXT_MUTED = "#9A9AA0"  # texto secundario — contraste verificado: 6,89:1 sobre BG (WCAG AA exige 4,5:1)

# Identidad de formato — REGLA SEMÁNTICA INVIOLABLE: rojo = Película, gris = Serie,
# siempre, en todos los gráficos. Nunca se usa PELICULA para representar "ambos formatos".
#
# PELICULA identifica el formato Película dentro de los gráficos. El mismo rojo se usa
# como color de marca en elementos de interfaz que no codifican datos (logo, indicador
# de pestaña, bordes decorativos). Nunca aparece dentro de un gráfico representando algo
# distinto de Película. Si un borde o separador decorativo queda ubicado junto a un gráfico (como el
# panel de hallazgo, al lado del gráfico de cada pestaña) y podría confundirse con esa
# identidad de formato, usa BORDER en su lugar — así queda en el CSS del panel (`st-key-panel_`, `.panel-sep`) más abajo.
PELICULA = "#E50914"
SERIE = "#B3B3B8"
COLOR_FORMATO = {"Película": PELICULA, "Serie": SERIE}

# Acentos semánticos — cada uno tiene un uso acotado y documentado
ACENTO = "#F5C518"      # ámbar — UN solo significado, en todo el dashboard: la línea (y sus rótulos) de valoración alta del
                        # gráfico de brechas del Resumen (charts.brechas_resumen) — es EL hallazgo que sostiene la tesis y el
                        # color que dirige la lectura del gráfico hacia él. `.aviso` es NEUTRO (border BORDER, texto TEXT_MUTED):
                        # un aviso es secundario frente al hallazgo que sostiene la tesis, no compite por el mismo color.
                        # Nunca una escala ni un segundo uso.
POSITIVO = "#2ECC71"    # SOLO para variaciones positivas (deltas)
NEGATIVO = "#E50914"    # variaciones negativas / alertas

# Añadido a la lista original: el tono de lo que NO es ni Película ni Serie (géneros que existen en ambos formatos, barra de
# progreso del primer KPI, líneas de referencia). Sin este tono no hay dónde poner esos elementos sin inventar un color fuera
# de este archivo o reutilizar sin querer PELICULA/SERIE (que tienen un significado propio).
NEUTRO = "#6E6E73"

# Puntos "apagados" de la matriz (populares por DEBAJO del P75): sobre el fondo casi no se ven,
# a propósito, para que el ojo vaya a los que sí importan. Valor fijado por la especificación.
PUNTO_APAGADO = "#3A3A3E"

# Nivel de valoración (Alta > Media > Baja) en las barras 100% apiladas: cada fila usa el color de SU formato (rojo=Película,
# gris=Serie) y el nivel se codifica por opacidad. Así el ámbar no se usa como escala y rojo/gris conservan su significado.
OPACIDAD_NIVEL = {"alta": 1.0, "media": 0.70, "baja": 0.40}
# Separación entre los segmentos de cada barra de Valoración (px, en el color de fondo): el límite se ve sin depender de la opacidad.
SEPARACION_SEGMENTOS_PX = 2
CONTRASTE_MINIMO_TEXTO = 4.5  # WCAG AA para texto normal: un rótulo dentro de un segmento solo va dentro si lo cumple

TRANSPARENTE = "rgba(0,0,0,0)"


def plot_config(nombre: str, siempre_visible: bool = True) -> dict:
    """Config de st.plotly_chart con UN solo botón: descargar el gráfico como PNG (Fase 6). Ninguno de los otros
    botones de Plotly (zoom, selección, etc.) aparece. `nombre` da el nombre del archivo descargado; con
    `siempre_visible=False` el botón solo aparece al pasar el mouse (para los mini-gráficos del Resumen)."""
    return {
        "displaylogo": False,
        "displayModeBar": True if siempre_visible else "hover",
        "modeBarButtons": [["toImage"]],
        "toImageButtonOptions": {"format": "png", "filename": f"streamview_{nombre}", "scale": 2},
    }


def rgba(color_hex: str, alpha: float) -> str:
    """Convierte un token hex a 'rgba(r,g,b,alpha)' para usos translúcidos (resplandores,
    zonas sombreadas) sin tener que escribir un color nuevo fuera de este archivo."""
    h = color_hex.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def mezclar(color_hex: str, alpha: float, fondo_hex: str = None) -> str:
    """Color resultante de poner `color_hex` con opacidad `alpha` sobre `fondo_hex` (BG por defecto), como hex opaco. Sirve
    para calcular el contraste real de un segmento translúcido con el texto que lleva encima."""
    fondo = fondo_hex or BG
    c, f = color_hex.lstrip("#"), fondo.lstrip("#")
    canales = [round(int(f[i:i + 2], 16) + (int(c[i:i + 2], 16) - int(f[i:i + 2], 16)) * alpha) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(canales)


def _luminancia(color_hex: str) -> float:
    """Luminancia relativa WCAG de un color hex."""
    h = color_hex.lstrip("#")
    canales = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def contraste(color_a: str, color_b: str) -> float:
    """Razón de contraste WCAG entre dos colores hex (WCAG AA pide 4,5 para texto normal)."""
    la, lb = sorted((_luminancia(color_a), _luminancia(color_b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def texto_sobre(fondo_hex: str) -> str:
    """El token de texto (TEXT o BG) que se lee mejor sobre `fondo_hex`: para rótulos dentro de
    segmentos de color, sin decidir a ojo cuál usar en cada fondo."""
    return TEXT if contraste(TEXT, fondo_hex) >= contraste(BG, fondo_hex) else BG


# ============================================================
# TIPOGRAFÍA — exactamente 4 tamaños en todo el dashboard
# ============================================================
FUENTE = "Inter, Arial, sans-serif"
FUENTE_MONO = "'JetBrains Mono', Consolas, 'SFMono-Regular', monospace"

# El número de 32px es EL ÚNICO elemento de 32px de su página: la tesis en el Resumen, el número del panel derecho en cada
# pestaña analítica. El valor de un KPI ya no usa este tamaño (ver TAM_KPI_VALOR): con 4 valores por fila, 32px competía con
# la tesis por la atención; ahora la tesis es inconfundiblemente el elemento más grande de la página.
TAM_KPI_NUMERO, PESO_KPI_NUMERO = 32, 700   # tesis del Resumen · número del panel de hallazgo en cada pestaña analítica
TAM_KPI_VALOR = 20                          # el valor de cada celda de la franja de KPIs (mismo tamaño que un título de sección, en 700)
TAM_TITULO_SECCION, PESO_TITULO_SECCION = 20, 600  # título de una sección / pestaña
TAM_CUERPO, PESO_CUERPO = 14, 400           # texto de lectura normal
TAM_CAPTION, PESO_CAPTION = 12, 400         # etiquetas, notas al pie, texto secundario

ANCHO_POPOVER_REM = 34  # ancho máximo del cuerpo de un popover (líneas de más de ~110 caracteres se leen mal)
ALTO_TARJETA_GRAFICO = 520  # alto de referencia de la tarjeta del gráfico en una pestaña analítica (el de la Matriz, la más alta)


# ============================================================
# FORMATO NUMÉRICO ES-CL — punto de miles, coma decimal
# ============================================================
def fmt_int(n) -> str:
    """10305 -> '10.305' (entero, punto de miles, sin decimales)."""
    return f"{round(float(n)):,}".replace(",", ".")


def fmt_float(n, d: int = 1) -> str:
    """23.2 -> '23,2' ; -4.5 -> '-4,5' (d decimales, coma decimal, punto de miles)."""
    texto = f"{float(n):,.{d}f}"
    entero, _, decimal = texto.partition(".")
    entero = entero.replace(",", ".")
    return f"{entero},{decimal}" if d > 0 else entero


def fmt_pct(fraccion, d: int = 0) -> str:
    """0.473 -> '47%' ; 0.473 con d=1 -> '47,3%'. `fraccion` es 0-1, no 0-100."""
    return f"{fmt_float(fraccion * 100, d)}%"


_FRACCIONES_CONOCIDAS = ((0.5, "la mitad"), (0.25, "un cuarto"), (0.75, "tres cuartos"), (1 / 3, "un tercio"), (2 / 3, "dos tercios"))
_TOLERANCIA_FRACCION = 0.03  # puntos de fracción (3 pp): 0,26 se lee "un cuarto", pero 0,30 ya no


def fmt_fraccion(fraccion) -> str | None:
    """0.50 -> 'la mitad' ; 0.26 -> 'un cuarto' (dentro de 3 pp de una fracción común); 0.40 -> None (sin fracción
    común cerca: quien llama debe usar fmt_pct). Para títulos-mensaje en prosa ('la mitad de las series…') en vez
    de un porcentaje, cuando el valor real cae cerca de la fracción — la cifra que lo origina sigue siendo la real,
    esto solo cambia cómo se lee."""
    cercana = min(_FRACCIONES_CONOCIDAS, key=lambda fp: abs(fp[0] - fraccion))
    return cercana[1] if abs(cercana[0] - fraccion) <= _TOLERANCIA_FRACCION else None


def fmt_abrev(n) -> str:
    """Abrevia valores de eje sobre 1.000: 2400 -> '2 mil', 10500 -> '10,5 mil'.
    Bajo 1.000 usa fmt_int normal. Mismo criterio en todos los gráficos."""
    n = float(n)
    if abs(n) < 1000:
        return fmt_int(n)
    miles = n / 1000
    decimales = 0 if miles == round(miles) else 1
    return f"{fmt_float(miles, decimales)} mil"


def paso_agradable(rango: float, n_ticks: int = 5) -> float:
    """Step 'redondo' (1, 2 o 5 × una potencia de 10) para que un eje con `n_ticks`
    marcas caiga en números fáciles de leer, en vez de valores arbitrarios."""
    import math
    if rango <= 0:
        return 1
    paso_crudo = rango / max(n_ticks, 1)
    magnitud = 10 ** math.floor(math.log10(paso_crudo))
    residuo = paso_crudo / magnitud
    escala = 1 if residuo < 1.5 else 2 if residuo < 3 else 5 if residuo < 7 else 10
    return escala * magnitud


def tick_abreviado(valor_max, n_ticks: int = 5):
    """(tickvals, ticktext) en pasos redondos entre 0 y valor_max, con ticktext abreviado
    ('2 mil') cuando supera 1.000 — mismo criterio en todos los gráficos. Para usar con
    fig.update_xaxes(tickvals=..., ticktext=...) en el eje que lleva la magnitud."""
    paso = paso_agradable(valor_max, n_ticks)
    n = int(valor_max // paso) + 1
    vals = [round(paso * i) for i in range(n + 1)]
    return vals, [fmt_abrev(v) for v in vals]


# ============================================================
# LAYOUT COMPARTIDO DE PLOTLY
# ============================================================
def aplicar_layout(fig):
    """Estilo común a todo gráfico Plotly del dashboard: fondo transparente, grilla
    solo horizontal en BORDER, sin líneas de eje, margen uniforme, hoverlabel en SURFACE."""
    fig.update_layout(
        font=dict(family=FUENTE, color=TEXT, size=TAM_CUERPO),
        plot_bgcolor=TRANSPARENTE,
        # plot_bgcolor y paper_bgcolor transparentes: en el dashboard el gráfico vive DENTRO de una tarjeta SURFACE
        # ([class*="st-key-grafico_"]) y debe fundirse con ella, no verse como un recuadro más oscuro dentro de otro.
        # `src/exportar.py` (donde la figura se guarda suelta, sin tarjeta detrás) pone un fondo sólido antes de escribir el PNG.
        paper_bgcolor=TRANSPARENTE,
        modebar=dict(bgcolor=TRANSPARENTE, color=TEXT_MUTED, activecolor=TEXT),
        separators=",.",  # es-CL: coma decimal, punto de miles — verificado con un render real (12345.6 -> "12.345,6")
        margin=dict(l=40, r=20, t=20, b=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text="",
            bgcolor=TRANSPARENTE, bordercolor=BORDER, borderwidth=1,
            font=dict(size=TAM_CAPTION, color=TEXT_MUTED),
        ),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER, font=dict(family=FUENTE, color=TEXT)),
    )
    # Solo grilla horizontal: se apoya en que la mayoría de los gráficos del dashboard
    # son de barras horizontales o líneas, donde la referencia útil es el eje de valor (Y
    # en barras horizontales es categórico, X es el de valor — por eso se activa la grilla
    # vertical ahí; en gráficos de línea/dispersión el valor va en Y). aplicar_layout deja
    # ambos ejes sin grilla por defecto; cada gráfico activa la que corresponda a su eje
    # de magnitud con fig.update_xaxes(showgrid=True) / update_yaxes(showgrid=True).
    fig.update_xaxes(showgrid=False, gridcolor=BORDER, zeroline=False, showline=False, linecolor=BORDER)
    fig.update_yaxes(showgrid=False, gridcolor=BORDER, zeroline=False, showline=False, linecolor=BORDER)
    return fig


# ============================================================
# CSS — inyectado una vez en la página
# ============================================================
ESTILOS = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.main .block-container {{ background:{BG} !important; }}
.stApp {{ font-family:{FUENTE}; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ background:transparent !important; }}
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {{ font-family:{FUENTE}; }}
.block-container {{ padding-top:1rem; padding-bottom:2rem; }}
/* Bloque superior compacto (punto 8): menos aire entre header, fila de filtros, KPIs y pestañas. */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {{ gap:.6rem; }}
[data-testid="stMain"] [data-testid="stTabs"] {{ margin-top:8px; }}
[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stAppDeployButton"] {{ display:none; }}
[data-testid="stMainMenu"] {{ display:none; }}  /* el menú de tres puntos no ejecuta ninguna acción útil aquí */
hr {{ border-color:{BORDER} !important; }}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ color:{TEXT}; }}

/* Sidebar (Paso 2: es el RIEL de navegación, ya no los filtros): mismo tono SURFACE que el resto de los paneles */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {{ background:{SURFACE} !important; }}
[data-testid="stSidebar"] {{ border-right:1px solid {BORDER}; }}

[data-testid="stSlider"] [role="slider"] {{ background-color:{PELICULA}; }}
[data-testid="stMain"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] {{ min-height:0; margin-bottom:0; }}
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] {{ min-height:28px; gap:4px 14px; }}

/* ============================================================
   RIEL DE NAVEGACIÓN (Paso 2, reemplaza a st.tabs) — NOTA DE AISLACIÓN
   ============================================================
   Todo lo de aquí abajo hasta el cierre de esta nota depende de cómo Streamlit arma el DOM de `st.navigation`
   (`position="sidebar"`), NO de una API pública documentada como estable entre versiones. Para que una actualización
   de Streamlit que cambie ese DOM rompa esto en UN SOLO LUGAR (este bloque) y de forma VISIBLE (test roto, nunca un
   silencio), se siguen dos reglas estrictas:
     1. Solo se selecciona por `[data-testid="…"]` (el propio Streamlit los documenta como su API para tests/CSS) y
        por atributos HTML/ARIA estándar (`[aria-current="page"]`, `[data-variant="…"]`) — NUNCA por una clase
        `st-emotion-cache-*` o `eXXXXXXX` (esas son hashes de Emotion, se regeneran en cada build y NO son estables
        ni siquiera entre dos ejecuciones del mismo Streamlit).
     2. Como no se toca el DOM (nada de JavaScript ni HTML propio): si un testid llegara a desaparecer en una versión
        futura, el riel no se rompe ni lanza una excepción — simplemente pierde el estilo y vuelve al de Streamlit
        por defecto (una lista de enlaces normal, fea pero funcional). `tests/verificar_pantalla.py` fija en Chrome
        real que el riel realmente luce angosto y con el ícono activo en rojo — si un testid desapareciera, esa
        comprobación (y ninguna otra) fallaría, señalando el problema en este bloque exacto. */
[data-testid="stSidebar"] {{ min-width:84px !important; max-width:84px !important; }}
/* La causa real del logo y el CSV desalineados (puntos 1 y 2 de esta corrección): Streamlit le pone a este
   contenedor 20px de padding IZQUIERDO Y DERECHO por defecto (pensado para el sidebar ancho de filtros del Paso 1,
   nunca se había notado porque ese sidebar tenía mucho más margen que perder). Con el riel angosto de 84px, esos
   40px de padding dejaban solo 44px reales de espacio interior — la mitad del riel — y encima descentrados, porque
   ni siquiera el padding izquierdo y el derecho eran iguales en la práctica (medido: el contenido quedaba centrado
   dentro de esos 44px, no dentro de los 84px del riel). `padding:4px 0 0` (sin padding lateral) es la causa raíz;
   una vez corregida, `width:100%` en los hijos de abajo alcanza sin necesitar ningún otro ajuste. */
[data-testid="stSidebarContent"] {{ display:flex; flex-direction:column; height:100%; padding:4px 0 0 !important; }}
[data-testid="stSidebarHeader"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarUserContent"] {{ width:100% !important; }}
/* padding-top:18px (no 4px): que el logo no toque el borde de arriba del riel. */
[data-testid="stSidebarHeader"] {{ flex:none; padding:18px 0 8px; display:flex; justify-content:center; }}
/* El <div> que envuelve st.logo no tiene testid propio (selector estructural, hijo directo de stSidebarHeader — no
   una clase st-emotion-cache-*). */
[data-testid="stSidebarHeader"] > div {{ display:flex; justify-content:center; width:100%; }}
/* st.logo (el propio testid del <img>, no uno genérico): el ancho intrínseco del SVG no se calcula solo dentro
   de un padre flex angosto sin esto — se queda en 0×0. */
[data-testid="stSidebarLogo"] {{ width:36px !important; height:16px !important; max-width:none !important; object-fit:contain; }}
/* El botón nativo para colapsar el riel (flecha) queda encima del logo y no aporta nada: el riel ya es angosto y
   no tiene sentido colapsarlo. Única regla que depende de este testid — si desapareciera en una versión futura de
   Streamlit, el botón simplemente reaparece (no rompe nada más allá de eso). */
[data-testid="stSidebarCollapseButton"] {{ display:none !important; }}
[data-testid="stSidebarNav"] {{ flex:none; }}
[data-testid="stSidebarNavItems"] {{ display:flex; flex-direction:column; gap:2px; padding:4px 8px; width:100%; box-sizing:border-box; }}
[data-testid="stSidebarNavLinkContainer"] {{ width:100%; }}
/* Cada página: ícono ARRIBA, texto ABAJO (Streamlit por defecto los pone lado a lado) */
[data-testid="stSidebarNavLink"] {{
    display:flex !important; flex-direction:column; align-items:center; gap:4px; width:100%;
    padding:10px 4px; border-radius:8px; text-align:center; text-decoration:none;
}}
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{ color:{TEXT_MUTED}; font-size:{TAM_TITULO_SECCION}px; }}
[data-testid="stSidebarNavLink"] span[label] [data-testid="stMarkdownContainer"] p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; font-weight:500; line-height:1.25; }}
/* Página activa: SOLO ícono en PELICULA y texto en TEXT/600 — sin fondo. Con fondo (versión anterior) la cápsula no
   cubría bien el bloque ícono+texto (quedaba corta o descentrada según el alto real del texto) y se leía como un
   recorte, no como una selección; el rojo del ícono y el peso del texto ya bastan para marcar "dónde estoy" sin
   necesitar una segunda señal. `background:transparent !important` porque Streamlit le pone un fondo propio a la
   página activa (un gris que no es ninguno de los tokens del sistema) que hay que anular explícitamente — quitar
   solo MI regla de fondo no alcanzaba. Inactivas: ícono y texto en TEXT_MUTED (ver la regla de arriba). */
[data-testid="stSidebarNavLink"][aria-current="page"] {{ background:{TRANSPARENTE} !important; }}
[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {{ color:{PELICULA}; }}
[data-testid="stSidebarNavLink"][aria-current="page"] span[label] [data-testid="stMarkdownContainer"] p {{ color:{TEXT}; font-weight:600; }}
[data-testid="stSidebarNavLink"]:not([aria-current="page"]):hover {{ background:{rgba(TEXT_MUTED, 0.08)}; }}
[data-testid="stSidebarNavSeparator"] {{ display:none; }}  /* separador nativo: el propio layout (logo -> nav -> pie) ya distingue las zonas */
/* Pie del riel (CSV, «Datos»): empujado al fondo con margin-top:auto — stSidebarContent es flex-column (arriba).
   Ícono + texto en FILA (no arriba/abajo como en la nav): Streamlit arma el contenido de un botón con su propio
   contenedor flex interno (sin testid propio) — forzarlo a columna partía "CSV" letra por letra en 3 líneas. */
[data-testid="stSidebarUserContent"] {{ margin-top:auto; padding:8px; display:flex; flex-direction:column; gap:6px; box-sizing:border-box; }}
/* El <div> que envuelve cada botón (CSV, Datos) tampoco tiene testid propio — mismo motivo que el del logo. */
[data-testid="stSidebarUserContent"] > div {{ width:100% !important; }}
[data-testid="stSidebarUserContent"] [data-testid="stElementContainer"] {{ width:100% !important; }}
/* El botón CSV lleva un `help=` (tooltip nativo), y Streamlit envuelve ese caso en dos spans adicionales
   (`.stTooltipHoverTarget`, `.stTooltipIcon` — clases propias de Streamlit, no un hash de Emotion) que el botón
   «Datos» no tiene por no llevar tooltip; sin ensancharlos también a ellos, el botón CSV quedaba más angosto que
   el resto de la columna y su contenido se lo llevaba por delante el `justify-content:flex-end` que Streamlit les
   pone en línea (quedaba corrido a la derecha en vez de compartir el eje central del riel). */
[data-testid="stSidebarUserContent"] [data-testid="stDownloadButton"],
[data-testid="stSidebarUserContent"] .stTooltipHoverTarget,
[data-testid="stSidebarUserContent"] .stTooltipIcon {{ width:100% !important; }}
[data-testid="stSidebarUserContent"] button {{
    width:100% !important; min-height:0; padding:8px 6px; background:transparent; border:none; white-space:nowrap;
    box-sizing:border-box;
}}
[data-testid="stSidebarUserContent"] button p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; white-space:nowrap; }}
[data-testid="stSidebarUserContent"] button:hover {{ background:{rgba(TEXT_MUTED, 0.08)}; border-radius:8px; }}
[data-testid="stSidebarUserContent"] [data-testid="stPopover"] > div {{ width:100%; }}
/* — fin de la nota de aislación del riel — */

/* Fase 3 — el H1 vuelve al área principal (revierte la Corrección 5 de una ronda anterior, que lo
   había quitado por redundante con el logo de la sidebar): ahora trae contexto de decisión propio
   (rango de años + la pregunta que responde el dashboard), no es un simple repetidor del logo. */
.hdr-title {{ font-size:{TAM_TITULO_SECCION}px; font-weight:{PESO_TITULO_SECCION}; color:{TEXT}; line-height:1.3; }}
.hdr-sub {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; margin-top:6px; }}
.hdr-sub, .hdr-sub * {{ color:{TEXT_MUTED} !important; }}
.hdr-right {{ text-align:right; }}
.hdr-date {{ font-size:{TAM_CAPTION}px; letter-spacing:.1em; text-transform:uppercase; color:{TEXT_MUTED}; margin-bottom:6px; }}
/* Encabezado: «Datos hasta AAAA» y «Generado el FECHA» — dos líneas de texto, reemplazan el chip «Corte de datos» (un
   dato de la fuente y uno de la ejecución, ninguno cambia con los filtros; por eso no son un chip de filtro activo). */
.hdr-meta {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.7; }}
.grad-line {{ height:1px; background:linear-gradient(90deg,{PELICULA},{rgba(PELICULA, 0)}); margin:6px 0 4px; }}
.vista-completa {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; letter-spacing:.02em; }}
/* Cuerpo del popover: mismo tono SURFACE que los demás paneles y ancho de lectura acotado. */
[data-testid="stPopoverBody"] {{ background:{SURFACE}; border:1px solid {BORDER}; max-width:{ANCHO_POPOVER_REM}rem !important; max-height:85vh !important; }}  /* Streamlit fija ambos máximos en línea (70vh de alto) */
.sobre .meto-lista {{ margin:0 0 16px; }}
.sobre .meto-lista li {{ margin-bottom:8px; }}
.sobre-cierre {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; }}

/* ============================================================
   BARRA DE FILTROS HORIZONTAL (Paso 2, reemplaza a los filtros de la barra lateral) — misma nota de aislación que
   el riel: solo testids/atributos estándar (`[data-variant]`, `aria-checked`, `aria-pressed`), scopeados bajo
   `.st-key-barra_filtros` para no afectar ningún otro control del dashboard. Si Streamlit cambiara este DOM, la
   barra pierde el estilo (vuelve a los controles nativos, funcionales) en vez de romperse.
   ============================================================ */
/* margin-top:20px: separación de la línea roja (.grad-line) de arriba — quedaban prácticamente pegadas. */
.st-key-barra_filtros {{ margin-top:20px; margin-bottom:10px; }}
.st-key-barra_filtros [data-testid="stWidgetLabel"] {{ display:none; }}  /* «Formato»/«Años»/«Género»/«País»: el propio control ya lo dice */
/* Streamlit reparte el ancho disponible en partes iguales entre los hijos directos de un contenedor horizontal
   (`st.container(horizontal=True)`), así que cada control quedaba con un ancho distinto según su contenido mínimo
   (huecos irregulares: Años lejos de Género, País "flotando" al centro). `flex:0 0 auto` los vuelve al ancho de su
   contenido, agrupados a la izquierda (el `justify-content` por defecto ya es flex-start); el espacio sobrante queda
   libre a la derecha, antes de «Limpiar filtros»/«Vista completa». */
.st-key-barra_filtros > div {{ flex:0 0 auto !important; width:fit-content !important; }}
/* Formato (st.segmented_control): un punto de color antes de «Película»/«Serie» — 2do y 3er botón del grupo, en ese
   orden fijo (Ambos, Película, Serie). Es la MISMA identidad rojo=Película/gris=Serie del resto del dashboard. */
.st-key-barra_filtros button[data-variant="segmented_control"]:nth-of-type(2) p::before {{ content:"●"; color:{PELICULA}; margin-right:5px; }}
.st-key-barra_filtros button[data-variant="segmented_control"]:nth-of-type(3) p::before {{ content:"●"; color:{SERIE}; margin-right:5px; }}
/* La opción activa de Formato: Streamlit la resalta con el color "primary" del tema — que es PELICULA, el mismo rojo
   que en los gráficos significa "Película" — y "Ambos"/"Serie" seleccionados quedaban con ese rojo sin relación con
   el dato. Fondo BORDER sólido y texto TEXT, sin borde ni halo rojo; los puntos de color (arriba) siguen siendo los
   únicos rojos de la barra. */
.st-key-barra_filtros button[data-variant="segmented_control"][aria-checked="true"] {{
    background-color:{BORDER} !important; border-color:{BORDER} !important; color:{TEXT} !important;
    box-shadow:none !important; outline:none !important;
}}
.st-key-barra_filtros button[data-variant="segmented_control"][aria-checked="true"] p {{ color:{TEXT} !important; }}
/* Años/Género/País: cada uno es st.popover dentro de un st.container(key="filtro_…") — dos variantes de key según
   tenga selección activa o no (nunca se varía el key del popover mismo: perdería su estado abierto/cerrado a medio
   clic). Mismo tamaño que el botón «Limpiar filtros» de al lado. */
[class*="st-key-filtro_"] [data-testid="stPopover"] button {{
    min-height:32px; padding:4px 12px; background:transparent; border:1px solid {BORDER}; border-radius:6px;
}}
[class*="st-key-filtro_"] [data-testid="stPopover"] button p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; }}
[class*="st-key-filtro_"][class*="_activo"] [data-testid="stPopover"] button {{ border-color:{TEXT_MUTED}; background:{rgba(TEXT_MUTED, 0.1)}; }}
[class*="st-key-filtro_"][class*="_activo"] [data-testid="stPopover"] button p {{ color:{TEXT}; font-weight:600; }}
.filtro-pop-titulo {{ font-size:{TAM_CUERPO}px; font-weight:600; color:{TEXT}; margin-bottom:2px; }}
.filtro-pop-ayuda {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; margin-bottom:12px; }}
/* «Quitar selección» (dentro del popover) y «Limpiar filtros» (al final de la barra): enlace de texto, no un botón —
   mismo estilo que la descarga de la lista de riesgo de la Matriz (.st-key-descargar_riesgo). */
.st-key-quitar_anios button, .st-key-quitar_genero button, .st-key-quitar_pais button, .st-key-btn_limpiar button {{
    background:{TRANSPARENTE}; border:none; padding:4px 0; min-height:0;
}}
.st-key-quitar_anios button p, .st-key-quitar_genero button p, .st-key-quitar_pais button p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; text-decoration:underline; }}
.st-key-btn_limpiar button {{ min-height:32px; padding:4px 10px; }}
.st-key-btn_limpiar button p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; text-decoration:none; }}
.st-key-quitar_anios button:hover p, .st-key-quitar_genero button:hover p, .st-key-quitar_pais button:hover p,
.st-key-btn_limpiar button:hover p {{ color:{TEXT}; }}
/* Pills de Género (dentro de su popover): mismo lenguaje que un chip — borde BORDER sin seleccionar, relleno
   PELICULA/SERIE… no: son géneros, no formatos, así que el estado "elegido" es NEUTRO (no hay un formato que codificar). */
[data-testid="stPopoverBody"] button[data-variant="pills"][aria-pressed="true"] {{ background:{rgba(NEUTRO, 0.35)} !important; }}
/* Aviso: mismo lenguaje visual que los paneles (SURFACE + borde izquierdo), pero NEUTRO — un aviso es secundario frente
   al hallazgo que sostiene la tesis (la línea ACENTO del gráfico de brechas del Resumen), así que no compite con él por
   el mismo color. Borde y texto en tonos neutros (BORDER, TEXT_MUTED), nunca ACENTO. */
.aviso {{ background:{SURFACE}; border:1px solid {BORDER}; border-left:3px solid {BORDER}; border-radius:6px; padding:12px 16px;
         font-size:{TAM_CUERPO}px; color:{TEXT_MUTED}; line-height:1.5; margin:4px 0 14px; }}

/* Franja de KPIs: UNA franja SURFACE con borde y radio 12 (no 4 tarjetas), dividida en 4 celdas por líneas verticales
   (border-left en cada celda menos la primera). Alto automático: crece con el contenido, no hay un alto fijo que desbordar. */
.kpi-franja {{ display:flex; background:{SURFACE}; border:1px solid {BORDER}; border-radius:12px; overflow:hidden; }}
.kpi-celda {{ flex:1 1 0; display:flex; align-items:center; gap:12px; padding:14px 16px; min-width:0; border-left:1px solid {BORDER}; }}
.kpi-celda:first-child {{ border-left:none; }}
/* Ícono en círculo de 40px. Neutro por defecto (fondo TEXT_MUTED muy tenue); «Títulos en riesgo» es la única celda con
   ícono y fondo en NEGATIVO (alerta) — así se distingue de un vistazo sin que el rojo aparezca en ningún otro KPI. */
.kpi-icono {{ flex:none; width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center;
             background:{rgba(TEXT_MUTED, 0.12)}; color:{TEXT_MUTED}; }}
.kpi-icono svg {{ width:20px; height:20px; }}
.kpi-icono--riesgo {{ background:{rgba(NEGATIVO, 0.15)}; color:{NEGATIVO}; }}
.kpi-textos {{ min-width:0; }}
.kpi-etiqueta {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.3; }}  /* sentence case: nunca mayúsculas */
.kpi-valor {{ font-size:{TAM_KPI_VALOR}px; font-weight:{PESO_KPI_NUMERO}; color:{TEXT}; line-height:1.25; white-space:nowrap; }}
.kpi-detalle {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.3; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }}

/* Panel de hallazgo (derecha de cada pestaña analítica): número (EL 32px de la página) -> hallazgo -> línea -> «Recomendación»
   (etiqueta) -> su texto en 14px 600, para que se lea como una instrucción, no como un dato más. */
[class*="st-key-panel_"] {{
    background:{SURFACE}; border-left:3px solid {BORDER}; border-radius:0 8px 8px 0;
    padding:20px; gap:0; box-shadow: inset 0 0 40px {rgba(BORDER, 0.15)};
}}
[class*="st-key-panel_"] [data-testid="stElementContainer"] {{ margin-bottom:0; }}
.panel-num {{ font-size:{TAM_KPI_NUMERO}px; font-weight:{PESO_KPI_NUMERO}; color:{TEXT}; line-height:1.3; margin-bottom:16px; padding-top:4px; letter-spacing:-0.02em; }}
.panel-desc {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.5; margin-top:0; }}
.panel-sep {{ height:1px; background:{BORDER}; margin:16px 0; }}
.panel-etiqueta {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; margin-bottom:4px; }}
.panel-txt {{ font-size:{TAM_CUERPO}px; font-weight:600; color:{TEXT}; line-height:1.5; }}

.footer {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; }}
/* Etiqueta pequeña de sección (mayúsculas, espaciada): encabezados «Lo esencial» / «Limitaciones clave» del popover. */
.seccion-etiqueta {{ font-size:{TAM_CAPTION}px; letter-spacing:.08em; text-transform:uppercase; color:{TEXT_MUTED}; font-weight:500; margin:0 0 8px; }}

/* Título-mensaje + subtítulo encima de cada gráfico: el titular enuncia la conclusión, el subtítulo dice qué se mira.
   margin-top:44px, para que el hueco real hasta la franja de KPIs de arriba quede en ≥32px (antes un div separador
   de 6px en dashboard/_shell.py lo dejaba prácticamente pegado). El margin-top en el propio título es más fiable que
   un <div> espaciador aparte, porque no depende de cómo Streamlit colapsa el alto de un elemento vacío entre dos
   bloques — aun así, 40px y no 32px: el HTML de la franja de KPIs (`kpis.franja_html`) a veces se renderiza unos
   px más alto que el contenedor que Streamlit le calculó (un desborde silencioso del propio Streamlit con HTML
   inyectado por `unsafe_allow_html`, no algo que este CSS pueda corregir de raíz), así que el margen incluye un
   colchón para seguir cumpliendo el mínimo pedido en ese caso. */
.grafico-titulo {{ font-size:{TAM_TITULO_SECCION}px; font-weight:{PESO_TITULO_SECCION}; color:{TEXT}; line-height:1.3; margin-top:44px; margin-bottom:6px; }}
.grafico-subtitulo {{ font-size:{TAM_CAPTION}px; font-weight:{PESO_CAPTION}; color:{TEXT_MUTED}; margin:0 0 16px; }}

/* Tarjeta del gráfico de cada pestaña analítica (columna izquierda, 8/12): un contenedor SURFACE con, en su cabecera, el
   control propio de la pestaña a la izquierda (conteo, métrica o el slider de votos) y la leyenda a la derecha. */
[class*="st-key-grafico_"] {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:12px; padding:18px 20px; }}
[class*="st-key-grafico_"] [data-testid="stElementContainer"] {{ margin-bottom:0; }}
.tarjeta-cabecera {{ display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-bottom:8px; min-height:28px; }}
/* El control de conteo/métrica no necesita su etiqueta nativa (el contexto de la tarjeta ya la da); el slider de
   votos mínimos de la Matriz SÍ la conserva, porque no hay otra pista de qué controla. */
[class*="st-key-grafico_"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] {{ display:none; }}
[class*="st-key-grafico_"] [data-testid="stSlider"] [data-testid="stWidgetLabel"] p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; }}

/* Leyenda HTML (reemplaza la leyenda nativa de Plotly, que ahora vive en la cabecera de la tarjeta, no sobre el gráfico). */
.leyenda {{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }}
.leyenda-item {{ display:inline-flex; align-items:center; font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; white-space:nowrap; }}
.leyenda-anillo {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; border:1.5px solid {NEUTRO}; background:{TRANSPARENTE}; }}
/* Leyenda de NIVELES de Valoración (reemplaza la de Película/Serie en esa pestaña: las filas del gráfico ya dicen su
   formato — lo que la leyenda debe explicar ahí es qué significa cada opacidad). Cuadrado NEUTRO en las tres opacidades
   reales de theme.OPACIDAD_NIVEL (muestra neutra: el color de fila es el formato, no el nivel) y el mismo tramado
   diagonal que usa el segmento «Sin votos» en el gráfico. */
.leyenda-nivel {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; }}
.leyenda-nivel--sinvotos {{ background-image:repeating-linear-gradient(45deg, {NEUTRO} 0 1.5px, {TRANSPARENTE} 1.5px 4px); border:1px solid {NEUTRO}; }}

/* Recuadro «Cómo leer»: reemplaza las notas al pie largas. SIN fondo, solo borde; ítems cortos, una idea cada uno.
   Sin título (se quitó de la interfaz); en Géneros, Evolución y Valoración. En Mercados y Matriz, donde este
   contenido vivía dentro de un st.expander cerrado, se eliminó del todo — por eso ya no hay CSS de stExpander aquí. */
.como-leer {{ border:1px solid {BORDER}; border-radius:8px; padding:14px 16px; margin-top:16px; }}
/* !important: Streamlit reinyecta un font-size propio sobre <li> de la misma especificidad; sin esto el ítem se ve
   ~16px en vez de los 12px pedidos (mismo problema, y misma solución, que .meto-lista li más abajo). */
.como-leer-lista, .como-leer-lista li {{ font-size:{TAM_CAPTION}px !important; color:{TEXT_MUTED}; line-height:1.6; }}
.como-leer-lista {{ margin:0; padding-left:18px; }}
.como-leer-lista li {{ margin-bottom:6px; }}
.como-leer-lista li:last-child {{ margin-bottom:0; }}

/* Listas del popover «ⓘ Sobre los datos» (Lo esencial y Limitaciones clave): texto de lectura normal, solo tamaños y colores del sistema. */
.meto-lista {{ font-size:{TAM_CUERPO}px; color:{TEXT}; line-height:1.6; padding-left:20px; margin:8px 0 0; }}
.meto-lista li {{ font-size:{TAM_CUERPO}px !important; margin-bottom:12px; }}
.meto-lista li::marker {{ color:{TEXT_MUTED}; }}

/* «N títulos cumplen el criterio», junto al slider de votos mínimos de la Matriz, ahora dentro de la cabecera de la tarjeta. */
.conteo-criterio {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; white-space:nowrap; }}

/* Resumen: la tesis es el ÚNICO elemento de 32px de la página, SIN recuadro (una frase, no una tarjeta).
   margin-top:44px: mismo criterio y mismo motivo que .grafico-titulo, más abajo. */
.tesis-titular {{ font-size:{TAM_KPI_NUMERO}px; font-weight:{PESO_KPI_NUMERO}; color:{TEXT}; line-height:1.3; margin-top:44px; }}
.tesis-soporte {{ font-size:{TAM_CUERPO}px; color:{TEXT_MUTED}; line-height:1.5; margin:8px 0 32px; }}
.resumen-col-titulo {{ font-size:{TAM_CUERPO}px; font-weight:600; color:{TEXT}; line-height:1.35; margin-bottom:2px; }}
.resumen-col-subtitulo {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.4; margin-bottom:12px; }}
/* «Qué hacer»: lista numerada, no tarjetas — sin números grandes (12px muted), acción en 14px 600, respaldo en 12px muted. */
.hacer-lista {{ display:flex; flex-direction:column; gap:16px; }}
.hacer-item {{ display:flex; gap:10px; }}
.hacer-indice {{ flex:none; font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.5; min-width:1em; }}
.hacer-accion {{ font-size:{TAM_CUERPO}px; font-weight:600; color:{TEXT}; line-height:1.4; margin-bottom:2px; }}
.hacer-respaldo {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; line-height:1.45; }}
/* Enlace al detalle en Matriz: visual de enlace (punto NEGATIVO + texto en negrita); en el Paso 1 no navega de verdad
   porque la navegación sigue siendo st.tabs (sin una forma programática de activar una pestaña) — se resuelve en el Paso 2. */
.hacer-enlace {{ display:flex; align-items:center; gap:8px; font-size:{TAM_CAPTION}px; font-weight:600; color:{TEXT}; margin-top:4px; }}
.hacer-enlace .dot {{ background:{NEGATIVO}; margin-right:0; }}

/* Mercados: lista «Mejor rendimiento frente a su formato» (columna derecha, debajo del panel; último elemento de la columna). */
.mercado-lista {{ margin:16px 0; }}
.mercado-lista-titulo {{ font-size:{TAM_CAPTION}px; font-weight:600; color:{TEXT}; margin-bottom:2px; }}
.mercado-lista-subtitulo {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; margin-bottom:10px; }}
.mercado-fila {{ display:flex; align-items:baseline; justify-content:space-between; gap:10px; padding:6px 0; border-top:1px solid {BORDER}; }}
.mercado-fila:first-of-type {{ border-top:none; }}
.mercado-pais {{ font-size:{TAM_CAPTION}px; font-weight:600; color:{TEXT}; flex:1 1 auto; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.mercado-titulos {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; flex:none; }}
.mercado-relativa {{ font-size:{TAM_CAPTION}px; font-weight:700; color:{TEXT}; flex:none; min-width:3.2em; text-align:right; }}

/* Matriz: lista ranking «Títulos en riesgo» (reemplaza la tabla + expander). */
.riesgo-lista {{ margin:16px 0; }}
.riesgo-lista-titulo {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px; font-size:{TAM_CAPTION}px; font-weight:600; color:{TEXT}; margin-bottom:2px; }}
.riesgo-lista-titulo span:last-child {{ font-weight:400; color:{TEXT_MUTED}; white-space:nowrap; }}
.riesgo-fila {{ display:flex; align-items:center; gap:10px; padding:7px 0; border-top:1px solid {BORDER}; }}
.riesgo-fila:first-of-type {{ border-top:none; }}
.riesgo-pos {{ flex:none; width:1.2em; font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; }}
.riesgo-info {{ flex:1 1 auto; min-width:0; }}
.riesgo-titulo {{ font-size:{TAM_CAPTION}px; font-weight:600; color:{TEXT}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block; }}
.riesgo-meta {{ display:flex; align-items:center; gap:5px; font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; }}
.riesgo-valor {{ flex:none; font-size:{TAM_CAPTION}px; font-weight:700; color:{NEGATIVO}; }}
.riesgo-aviso {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; margin:2px 0 10px; }}
/* Descarga de la lista de riesgo: un enlace de texto, no un botón — coherente con .riesgo-enlace (mismo estilo tipográfico). */
.st-key-descargar_riesgo button {{ background:{TRANSPARENTE}; border:none; padding:6px 0 0; min-height:0; }}
.st-key-descargar_riesgo button p {{ font-size:{TAM_CAPTION}px; color:{TEXT_MUTED}; text-decoration:underline; }}
.st-key-descargar_riesgo button:hover p {{ color:{TEXT}; }}
</style>"""
