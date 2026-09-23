"""
Entrypoint del dashboard (Paso 2: `st.navigation` con un riel de íconos, en vez de `st.tabs`).

Streamlit ejecuta este archivo con CADA rerun, sea cual sea la página activa: aquí vive el «marco» común (config de
página, riel de navegación, `dashboard._shell.preparar()` — header, barra de filtros horizontal, KPIs — y el pie de
página) y `pg.run()` ejecuta el script de la página elegida (`dashboard/pages/*.py`). Las páginas son ARCHIVOS, no
funciones: es la única forma de multipágina que `streamlit.testing.v1.AppTest.switch_page` sabe manejar (ver
`tests/verificar_estados.py`), y la que permite navegar por URL (`/generos`, `/mercados`, …).
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raíz del proyecto: `from src import …`
sys.path.insert(0, str(Path(__file__).resolve().parent))  # dashboard/: `import _shell` (también desde cada página)

import streamlit as st  # noqa: E402

from src import theme  # noqa: E402

# Streamlit vuelve a ejecutar los scripts cuando cambia algo, pero los módulos que estos importan quedan en la caché
# de Python: si se edita uno sin reiniciar el servidor, un script nuevo trabaja con un módulo viejo y falla con
# "AttributeError: module 'src.metrics' has no attribute ...". Aquí se recargan los módulos cuyo archivo cambió — se
# hace UNA vez, aquí (no en cada página), porque siempre corre antes que cualquier página. Orden de dependencia
# (cada módulo solo importa a los anteriores); _shell depende de todos los de src/, por eso va al final.
_MODULOS_SRC = ("theme", "data_loader", "metrics", "kpis", "narrative", "charts", "metodologia")
_CARPETA_SRC = Path(__file__).resolve().parent.parent / "src"
_CARPETA_DASHBOARD = Path(__file__).resolve().parent


@st.cache_resource
def _sellos_de_modulos():
    return {}


def _recargar_modulos_modificados():
    archivos = {f"src.{n}": _CARPETA_SRC / f"{n}.py" for n in _MODULOS_SRC}
    archivos["_shell"] = _CARPETA_DASHBOARD / "_shell.py"
    actuales = {n: p.stat().st_mtime_ns for n, p in archivos.items()}
    vistos = _sellos_de_modulos()
    if vistos != actuales:
        for nombre in archivos:
            if nombre in sys.modules:
                importlib.reload(sys.modules[nombre])
        vistos.clear()
        vistos.update(actuales)


_recargar_modulos_modificados()

import _shell  # noqa: E402  (después de recargar módulos a propósito)

st.set_page_config(page_title="StreamView Analytics", page_icon="📊", layout="wide")
st.markdown(theme.ESTILOS, unsafe_allow_html=True)
st.logo(str(_CARPETA_DASHBOARD / "assets" / "logo_sv.svg"), size="large")

# Riel de navegación: logo (st.logo, arriba) -> las 6 páginas (icono Material + título, la activa resaltada en rojo,
# CSS aislado en theme.py — ver la nota ahí) -> CSV y «Datos» (dashboard/_shell.py, llamados desde preparar(), pie
# del riel). Nunca hay más de 6 páginas: `expanded` no aplica (no hay secciones que colapsar).
PAGINAS = [
    st.Page("pages/resumen.py", title="Resumen", icon=":material/dashboard:", url_path="resumen", default=True),
    st.Page("pages/generos.py", title="Géneros", icon=":material/sell:", url_path="generos"),
    st.Page("pages/mercados.py", title="Mercados", icon=":material/public:", url_path="mercados"),
    st.Page("pages/evolucion.py", title="Evolución", icon=":material/show_chart:", url_path="evolucion"),
    st.Page("pages/valoracion.py", title="Valoración", icon=":material/star:", url_path="valoracion"),
    st.Page("pages/matriz.py", title="Matriz", icon=":material/scatter_plot:", url_path="matriz"),
]
pg = st.navigation(PAGINAS, position="sidebar")
 
_shell.preparar()  # header + barra de filtros horizontal + KPIs + CSV/Datos del riel; deja el contexto en session_state
pg.run()
_shell.pie_de_pagina()
