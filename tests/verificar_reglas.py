"""
Verificación ESTÁTICA de las reglas de DECISIONES.md: lee el código, no abre el dashboard.

    python tests/verificar_reglas.py

Comprueba: que el código compile (y pyflakes, si está instalado); ningún color literal fuera de theme.py; solo los tamaños de texto
permitidos; ámbar solo en `.aviso` y verde sin uso; `.panel-sep` en BORDER; config.toml sincronizado con theme.py; textos prohibidos
(«retorno», «Mantener», lo descartado); ninguna cifra de referencia escrita en un texto; el slider de la Matriz tomado de metrics.py;
opacidades y contraste de las etiquetas de Valoración; traducciones que cubren todos los géneros y países de los CSV; y que
images/ tenga exactamente los PNG que genera src/exportar.py.
"""
import ast
import inspect
import re
import subprocess
import sys

import pandas as pd

from _comun import RAIZ, Verificador

from src import charts, data_loader, exportar, kpis, metodologia, metrics, theme  # noqa: E402

v = Verificador("Reglas de diseño y de código (estático)")
ARCHIVOS = sorted([
    *(RAIZ / "src").glob("*.py"), RAIZ / "dashboard" / "app.py", RAIZ / "dashboard" / "_shell.py",
    *(RAIZ / "dashboard" / "pages").glob("*.py"),
])
FUERA_DE_THEME = [a for a in ARCHIVOS if a.name != "theme.py"]


def cadenas(ruta):
    """Literales de texto de un archivo, sin docstrings ni comentarios: lo que el programa puede mostrar en pantalla."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    docstrings = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and nodo.body:
            primero = nodo.body[0]
            if isinstance(primero, ast.Expr) and isinstance(primero.value, ast.Constant) and isinstance(primero.value.value, str):
                docstrings.add(id(primero.value))
    return [n.value for n in ast.walk(arbol) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


# ---------------------------------------------------------------- compilación y pyflakes
errores = []
for a in ARCHIVOS:
    try:
        compile(a.read_text(encoding="utf-8"), str(a), "exec")
    except SyntaxError as e:
        errores.append(f"{a.name}: {e}")
v.comprobar("Todo el código compila", not errores, "; ".join(errores))
pyflakes = subprocess.run([sys.executable, "-m", "pyflakes", *map(str, ARCHIVOS)], capture_output=True, text=True)
if "No module named pyflakes" in pyflakes.stderr:
    v.info("pyflakes no está instalado: se omite (pip install -r requirements-dev.txt)")
else:
    v.comprobar("pyflakes sin hallazgos", pyflakes.returncode == 0, pyflakes.stdout.strip()[:300])

# ---------------------------------------------------------------- colores
patron_color = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|(?<![\w.])rgba?\(|^(red|gr[ae]y|white|black|orange|amber|green|blue|yellow)$", re.I)
literales = [(a.name, s) for a in FUERA_DE_THEME for s in cadenas(a) if patron_color.search(s.strip()) or re.search(r"#[0-9A-Fa-f]{6}\b", s)]
v.comprobar("Ningún color literal fuera de theme.py", not literales, str(literales[:3]))

# ---------------------------------------------------------------- tamaños de texto
texto_css = theme.ESTILOS
tamanos = {m.strip().replace(" !important", "").replace("!important", "").strip() for m in re.findall(r"font-size:\s*([^;}]+)", texto_css)}
permitidos = {f"{t}px" for t in (theme.TAM_KPI_NUMERO, theme.TAM_TITULO_SECCION, theme.TAM_KPI_VALOR, theme.TAM_CUERPO, theme.TAM_CAPTION)}
permitidos |= {"1.25rem", ".8rem"}  # logo de la barra lateral (excepción documentada)
v.comprobar("El CSS solo usa los tamaños permitidos (32/20/14/12 px + excepción del logo)", tamanos <= permitidos, f"fuera de lo permitido: {sorted(tamanos - permitidos)}")
fuera = [a.name for a in FUERA_DE_THEME if re.search(r"font-size:\s*[\d.]", a.read_text(encoding="utf-8"))]  # «font-size:12px» a mano (con {theme.TAM_…} no cuenta)
codigo_plotly = [a.name for a in FUERA_DE_THEME if re.search(r"font\s*=\s*dict\([^)]*\bsize\s*=\s*\d", a.read_text(encoding="utf-8"))]
v.comprobar("Ningún tamaño de texto literal fuera de theme.py (CSS ni Plotly)", not fuera and not codigo_plotly, f"{fuera[:2]} {codigo_plotly}")

# ---------------------------------------------------------------- tokens con un único uso
lineas_acento = [ln for ln in texto_css.splitlines() if theme.ACENTO.lower() in ln.lower()]
v.comprobar("ACENTO (ámbar) no aparece en el CSS: `.aviso` es neutro (BORDER/TEXT_MUTED), su único uso es la línea de hallazgo del Resumen (Python, comprobado abajo)",
            len(lineas_acento) == 0, str(lineas_acento))
usos = {t: [a.name for a in FUERA_DE_THEME if re.search(rf"theme\.{t}\b", a.read_text(encoding="utf-8"))] for t in ("ACENTO", "POSITIVO", "PUNTO_APAGADO", "NEGATIVO")}
v.comprobar("ACENTO (ámbar) tiene UN solo uso documentado: la línea de valoración alta del gráfico de brechas del Resumen (charts.brechas_resumen) — el hallazgo que sostiene la tesis; en ningún otro archivo",
            usos["ACENTO"] == ["charts.py"], str(usos["ACENTO"]))
v.comprobar("POSITIVO sigue sin uso fuera de theme.py", not usos["POSITIVO"], str(usos["POSITIVO"]))
v.comprobar("NEGATIVO no se usa fuera de theme.py (queda contenido en el CSS de `.kpi-icono--riesgo` y `.riesgo-valor`)", not usos["NEGATIVO"], str(usos["NEGATIVO"]))
v.comprobar("PUNTO_APAGADO solo lo usa charts.py (puntos bajo el P75 de la Matriz)", usos["PUNTO_APAGADO"] == ["charts.py"], str(usos["PUNTO_APAGADO"]))
_linea_riesgo = next((ln for ln in texto_css.splitlines() if ".kpi-icono--riesgo" in ln), "")
v.comprobar("`.kpi-icono--riesgo` (el único KPI con ícono rojo) usa NEGATIVO", theme.NEGATIVO in _linea_riesgo, _linea_riesgo)
linea_sep = next(ln for ln in texto_css.splitlines() if ln.startswith(".panel-sep"))
v.comprobar("`.panel-sep` es BORDER liso (sin rojo ni degradado)", theme.BORDER in linea_sep and "gradient" not in linea_sep and theme.PELICULA not in linea_sep, linea_sep)
v.comprobar("El borde del panel de hallazgo es BORDER", f"border-left:3px solid {theme.BORDER}" in texto_css)

# ---------------------------------------------------------------- config.toml sincronizado con theme.py
config = dict(re.findall(r'^(\w+)\s*=\s*"([^"]+)"', (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"), re.M))
esperado = {"primaryColor": theme.PELICULA, "backgroundColor": theme.BG, "secondaryBackgroundColor": theme.SURFACE, "textColor": theme.TEXT}
v.comprobar(".streamlit/config.toml coincide con theme.py", {k: config.get(k, "").upper() for k in esperado} == {k: c.upper() for k, c in esperado.items()}, f"{config} vs {esperado}")

# ---------------------------------------------------------------- textos prohibidos y cifras escritas a mano
prohibidos = ("retorno", "período base", "periodo base", "En una mirada", "Tres recomendaciones", "alto retorno")
hallados = [(a.name, s[:70]) for a in FUERA_DE_THEME for s in cadenas(a) for p in prohibidos if p.lower() in s.lower()]
v.comprobar("Ningún texto menciona «retorno» ni lo descartado (período base, «En una mirada»…)", not hallados, str(hallados[:3]))
mantener = [(a.name, s[:70]) for a in FUERA_DE_THEME for s in cadenas(a) if s.startswith("Mantener")]
v.comprobar("Ningún texto empieza con «Mantener»", not mantener, str(mantener[:3]))
cifras = [(a.name, s[:70]) for a in FUERA_DE_THEME for s in cadenas(a) if re.search(r"\b1,0 =|\b4,4×|\b1,2×|\+23\b|\+34\b|\b22\.000\b|\b10\.305\b", s)]
v.comprobar("Ninguna cifra de referencia escrita a mano en los textos (1,0 =, 4,4×, +34, 22.000…)", not cifras, str(cifras[:3]))
app = (RAIZ / "dashboard" / "app.py").read_text(encoding="utf-8")
_shell_src = (RAIZ / "dashboard" / "_shell.py").read_text(encoding="utf-8")
_matriz_src = (RAIZ / "dashboard" / "pages" / "matriz.py").read_text(encoding="utf-8")
v.comprobar("El slider de la Matriz toma valor, mínimo, máximo y paso de metrics.py",
            all(c in _matriz_src for c in ("value=metrics.MIN_VOTOS_MATRIZ_DEFECTO", "min_value=metrics.MIN_VOTOS_MATRIZ_MINIMO", "max_value=metrics.MIN_VOTOS_MATRIZ_MAXIMO", "step=metrics.MIN_VOTOS_MATRIZ_PASO")))
# Paso 2: st.navigation (riel) reemplaza a st.tabs — las 6 páginas son archivos en dashboard/pages/, cada uno con su título.
_bloque_nav = re.search(r"PAGINAS\s*=\s*\[(.*?)\n\]", app, re.S)
_paginas_titulo = re.findall(r'title="([^"]+)"', _bloque_nav.group(1)) if _bloque_nav else []
_paginas_archivo = re.findall(r'st\.Page\("pages/([^"]+)"', _bloque_nav.group(1)) if _bloque_nav else []
v.comprobar("Las páginas son exactamente 6: Resumen, Géneros, Mercados, Evolución, Valoración y Matriz (Metodología ya no es una página ni una pestaña)",
            _paginas_titulo == ["Resumen", "Géneros", "Mercados", "Evolución", "Valoración", "Matriz"] and "st.tabs(" not in app, str(_paginas_titulo))
v.comprobar("Cada página declarada en PAGINAS existe como archivo en dashboard/pages/",
            all((RAIZ / "dashboard" / "pages" / a).exists() for a in _paginas_archivo) and len(_paginas_archivo) == 6, str(_paginas_archivo))
v.comprobar("El popover «Datos» está en dashboard/_shell.py, en la sidebar (pie del riel), con la etiqueta y la clave de metodologia.py",
            "st.sidebar.popover(metodologia.ETIQUETA_POPOVER" in _shell_src and metodologia.ETIQUETA_POPOVER == "Datos")
v.comprobar("CSV y «Datos» comparten las mismas reglas de estilo del pie del riel (selector común en theme.py, no una por widget)",
            '[data-testid="stSidebarUserContent"] button {' in texto_css)

# ---------------------------------------------------------------- riel de navegación y barra de filtros (Paso 2)
v.comprobar("st.navigation se llama con position=\"sidebar\" (riel angosto a la izquierda, no arriba ni oculto)", 'position="sidebar"' in app)
v.comprobar("El riel usa st.logo (no HTML propio) para la marca, arriba de la navegación", "st.logo(" in app)
_selectores_riel = ('[data-testid="stSidebarNavLink"]', '[aria-current="page"]', '[data-testid="stSidebarLogo"]', '[data-testid="stSidebarUserContent"]')
v.comprobar("El CSS del riel solo depende de testids de Streamlit y atributos ARIA estándar (nunca una clase st-emotion-cache-*)",
            all(s in texto_css for s in _selectores_riel) and not re.search(r"\.st-emotion-cache-\w+\s*\{", texto_css))
v.comprobar("La barra de filtros horizontal vive en un solo contenedor aislado (st.container(key=\"barra_filtros\")), en dashboard/_shell.py",
            'key="barra_filtros"' in _shell_src and '.st-key-barra_filtros' in texto_css)
v.comprobar("Formato usa st.segmented_control (no st.radio) y Género/País usan st.pills/st.multiselect dentro de un st.popover cada uno",
            "st.segmented_control(" in _shell_src and "st.pills(" in _shell_src and 'st.popover(f"Género' in _shell_src and 'st.popover(f"País' in _shell_src)
v.comprobar("El sidebar ya no tiene «Reiniciar filtros» ni «Contexto del análisis» (se retiraron con el Paso 2)",
            "Reiniciar filtros" not in app and "Reiniciar filtros" not in _shell_src and "Contexto del análisis" not in _shell_src)

# ---------------------------------------------------------------- Valoración: opacidades, separación y rótulos ENCIMA
_df_completo, _, _ = data_loader.load_data()
_df_defecto = _df_completo[metrics.construir_mascara(_df_completo, "Ambos", [], [], (metrics.ANIO_INICIO_DEFECTO, int(_df_completo["release_year"].max())))]
op = theme.OPACIDAD_NIVEL
v.comprobar("Opacidades de nivel: Alta 1,0 · Media 0,70 · Baja 0,40", (op["alta"], op["media"], op["baja"]) == (1.0, 0.70, 0.40), str(op))
v.comprobar("Alta > Media > Baja (los tres niveles se ordenan por intensidad)", op["alta"] > op["media"] > op["baja"])
for f, color in (("Película", theme.PELICULA), ("Serie", theme.SERIE), ("Leyenda", theme.TEXT_MUTED)):
    c = {n: theme.mezclar(color, op[n]) for n in op}
    v.info(f"{f}: contraste alta/media {theme.contraste(c['alta'], c['media']):.2f}:1 · media/baja {theme.contraste(c['media'], c['baja']):.2f}:1 · baja/fondo {theme.contraste(c['baja'], theme.BG):.2f}:1")

# Los porcentajes van SIEMPRE por encima de la barra (nunca dentro): ya no hay contraste que comprobar contra un
# relleno translúcido. Se verifica que ninguna traza de barra lleve texto propio y que cada segmento con títulos
# tenga su anotación (una por Alta/Media/Baja/Sin votos de cada formato, más el encabezado «Sin votos»).
_datos = metrics.barras_valoracion(_df_defecto)
_fig = charts.barras_valoracion(_datos)
_barras_nivel = [t for t in _fig.data if t.type == "bar" and t.name in metrics.ORDEN_VALORACION]
v.comprobar("Valoración: ninguna barra lleva texto propio (los porcentajes son anotaciones, todas por encima)",
            all(t.text is None for t in _barras_nivel), str([(t.name, t.text) for t in _barras_nivel if t.text is not None]))
_niveles_op = [t for t in _fig.data if t.type == "bar" and t.name in (metrics.NIVEL_ALTA, metrics.NIVEL_MEDIA, metrics.NIVEL_BAJA)]
v.comprobar(f"Valoración: los segmentos Alta, Media y Baja se separan con {theme.SEPARACION_SEGMENTOS_PX} px en el color BG",
            len(_niveles_op) == 3 and all(t.marker.line.color == theme.BG and t.marker.line.width == theme.SEPARACION_SEGMENTOS_PX for t in _niveles_op),
            str([(t.name, t.marker.line.color, t.marker.line.width) for t in _niveles_op]))
_con_titulos = int((_datos["Titulos"] > 0).sum())  # un segmento por (formato, nivel) con títulos, incluido «Sin votos»
v.comprobar(f"Valoración: cada uno de los {_con_titulos} segmentos con títulos tiene su rótulo de porcentaje, más el encabezado «Sin votos»",
            len(_fig.layout.annotations) == _con_titulos + 1, f"{len(_fig.layout.annotations)} anotaciones para {_con_titulos} segmentos")
_max_sin_votos = _datos[_datos["Nivel"] == metrics.NIVEL_SIN_VOTOS]["Porcentaje"].max()
v.comprobar("Valoración: el rango del eje X incluye la columna «Sin votos» más ancha (no queda cortada)",
            _fig.layout.xaxis.range[1] >= 1 + _max_sin_votos, f"rango hasta {_fig.layout.xaxis.range[1]:.3f}, «Sin votos» máximo {_max_sin_votos:.3f}")
v.comprobar("Valoración: todas las trazas y anotaciones están dentro del rango visible del eje X",
            all(a.x <= _fig.layout.xaxis.range[1] + 1e-9 for a in _fig.layout.annotations if a.xref in ("x", None)),
            str([(a.text, a.x) for a in _fig.layout.annotations if a.xref in ("x", None) and a.x > _fig.layout.xaxis.range[1]]))

# ---------------------------------------------------------------- metodología: popover y documento completo
_anio_max = int(_df_completo["release_year"].max())
_popover = metodologia.popover_html(_anio_max)
v.comprobar("El popover: 3 puntos de «Lo esencial», al menos 4 limitaciones clave y la línea final, sin tablas ni código",
            _popover.split("Limitaciones clave")[0].count("<li>") == 3 and _popover.split("Limitaciones clave")[1].count("<li>") >= 4
            and metodologia.LINEA_FINAL in _popover and not any(t in _popover for t in ("<table", "<code", "<pre", "`")))
_documento = metodologia.documento_markdown(_anio_max)
_en_disco = metodologia.RUTA_DOCUMENTO.read_text(encoding="utf-8") if metodologia.RUTA_DOCUMENTO.exists() else None
v.comprobar("docs/metodologia.md está al día con src/metodologia.py (si falla: python -m src.metodologia)", _en_disco == _documento,
            "no existe" if _en_disco is None else "el archivo difiere de lo que genera el código")
v.comprobar("docs/metodologia.md trae las 5 secciones, las tablas de métricas y de criterios de corte y las limitaciones completas",
            all(f"## {s}" in _documento for s in ("Lo esencial", "Fuente de datos", "Métricas derivadas", "Criterios de corte", "Limitaciones"))
            and _documento.count("\n| **") >= 20 and len(re.findall(r"^\d+\. \*\*", _documento.split("## Limitaciones")[1], re.M)) >= 8)

# ---------------------------------------------------------------- rediseño (Paso 1): franja de KPIs, tarjetas, listas
_franja = kpis.franja_html(_df_defecto, len(_df_completo))
v.comprobar("La franja de KPIs es UN solo contenedor `.kpi-franja` con 4 `.kpi-celda` (no 4 tarjetas sueltas)",
            _franja.count('class="kpi-franja"') == 1 and _franja.count('class="kpi-celda"') == 4)
v.comprobar("Solo la celda de «Títulos en riesgo» usa el ícono rojo `.kpi-icono--riesgo`", _franja.count("kpi-icono--riesgo") == 1)
v.comprobar("Ninguna celda de KPI lleva barra de progreso (`.bar`, eliminada del diseño)", 'class="bar"' not in _franja and "<div class=\"bar\">" not in theme.ESTILOS)
v.comprobar("N_TABLA_RIESGO (filas de la lista de riesgo de la Matriz) es 5, el mínimo pedido", metrics.N_TABLA_RIESGO == 5, metrics.N_TABLA_RIESGO)
for _fn, _nombre in ((charts.linea_evolucion, "linea_evolucion"), (charts.barras_valoracion, "barras_valoracion")):
    v.comprobar(f"charts.{_nombre} ya no tiene un parámetro `reducido` (el Resumen no usa mini-gráficos de estas figuras)",
                "reducido" not in inspect.signature(_fn).parameters)
# Paso 2: cada tarjeta de gráfico vive en la página que le corresponde (dashboard/pages/), no en app.py.
_paginas_de_grafico = {
    "grafico_generos": "generos.py", "grafico_paises": "mercados.py", "grafico_evolucion": "evolucion.py",
    "grafico_valoracion": "valoracion.py", "grafico_matriz": "matriz.py",
}
for _clave, _archivo in _paginas_de_grafico.items():
    _src = (RAIZ / "dashboard" / "pages" / _archivo).read_text(encoding="utf-8")
    v.comprobar(f"pages/{_archivo} declara la tarjeta del gráfico st.container(key=\"{_clave}\")", f'key="{_clave}"' in _src)
v.comprobar("theme.py tiene el CSS de la tarjeta del gráfico (selector `st-key-grafico_`), la leyenda y «Cómo leer este gráfico»",
            all(s in texto_css for s in ("st-key-grafico_", ".leyenda {", ".como-leer {", ".hacer-lista", ".riesgo-lista", ".mercado-lista")))

# ---------------------------------------------------------------- traducciones
crudo = pd.concat([pd.read_csv(data_loader.RUTA_DATOS / a) for a in (data_loader.ARCHIVO_PELICULAS, data_loader.ARCHIVO_SERIES)])
generos_csv = {x.strip() for f in crudo["genres"].dropna() for x in f.split(",") if x.strip()}
paises_csv = {x.strip() for f in crudo["country"].dropna() for x in f.split(",") if x.strip()}
v.comprobar(f"Los {len(generos_csv)} géneros de los CSV están traducidos", not generos_csv - set(data_loader.GENEROS_ES), str(sorted(generos_csv - set(data_loader.GENEROS_ES))))
v.comprobar(f"Los {len(paises_csv)} países de los CSV están traducidos", not paises_csv - set(data_loader.PAISES_ES), str(sorted(paises_csv - set(data_loader.PAISES_ES))))

# ---------------------------------------------------------------- imágenes
anio_max = int(_df_completo["release_year"].max())
df_defecto = _df_defecto
esperadas = {f"{n}.png" for n in exportar.figuras(df_defecto, anio_max)}
presentes = {p.name for p in (RAIZ / "images").glob("*.png")}
v.comprobar("images/ tiene exactamente los PNG que genera src/exportar.py", presentes == esperadas, f"sobran {sorted(presentes - esperadas)}, faltan {sorted(esperadas - presentes)}")

sys.exit(v.terminar())
