"""
Cabecera compartida por las 6 páginas del dashboard (Paso 2 del rediseño): carga de datos, franja de KPIs,
barra de filtros horizontal (arriba de los KPIs) y los dos botones del pie del riel de navegación (CSV, Datos).

Un app multipágina de ARCHIVOS (`st.navigation` con `st.Page("pages/…")`, la única forma que `AppTest.switch_page`
sabe manejar — ver `tests/verificar_estados.py`) no puede pasarle argumentos a una página: cada página es un script
independiente. `preparar()` se llama UNA vez desde `dashboard/app.py`, antes de `pg.run()`; deja su resultado en
`st.session_state["_ctx"]` (por sesión, nunca una variable de módulo — ver la nota de `contexto()`) y cada página lo
lee con `contexto()` al principio de su script.
"""
from html import escape
from datetime import date

import streamlit as st

from src import data_loader, kpis, metodologia, metrics, narrative, theme

EQUIPO = "Maicol Hernández · Francis Moya"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
fmt = theme.fmt_int

CLAVE_MODO_PAISES = "conteo_paises"
# Etiquetas cortas (antes "Contar solo el primer país listado" / "Contar coproducciones en cada país"): con el texto
# largo el control no cabía en una sola línea horizontal en la cabecera de la tarjeta de Mercados.
OPCIONES_CONTEO_PAISES = {"Primer país": metrics.MODO_PRIMER_PAIS, "Coproducciones": metrics.MODO_TODOS_LOS_PAISES}

AVISO_FORMATO_UNICO = "Esta vista compara ambos formatos. Selecciona 'Ambos' para verla completa."


def aviso(texto):
    """Mensaje de estado (vista vacía, comparación imposible): mismo lenguaje visual que los paneles, no el st.info azul."""
    st.markdown(f'<div class="aviso">{escape(texto)}</div>', unsafe_allow_html=True)


def contexto():
    """El contexto que preparar() calculó en ESTE rerun. Vive en st.session_state (no en una variable de módulo):
    el proceso de Streamlit puede atender varias sesiones a la vez, y una variable de módulo se compartiría entre
    todas — session_state es, en cambio, propio de cada sesión."""
    return st.session_state["_ctx"]


# ----------------- Sidebar: CSV y «Datos» (pie del riel) -----------------
def _render_csv(df_filt, n_total):
    if n_total:
        st.sidebar.download_button(
            "CSV", icon=":material/download:", data=lambda d=df_filt: narrative.csv_filtrado(d), file_name="catalogo_filtrado.csv",
            mime="text/csv", key="csv_filtrado", on_click="ignore", width="stretch",
            help=f"Descargar los {fmt(n_total)} títulos de la selección actual",
        )


def _render_datos(anio_max):
    # Se llama ANTES de la guarda de selección vacía (más abajo en preparar()) para que exista SIEMPRE, igual que
    # antes cuando vivía en la fila de filtros — tests/verificar_estados.py lo comprueba también con 0 títulos.
    with st.sidebar.popover(metodologia.ETIQUETA_POPOVER, icon=":material/info:", key="popover_datos", width="content"):
        st.markdown(metodologia.popover_html(anio_max), unsafe_allow_html=True)


# ----------------- Header -----------------
def _render_header(rango_anios, anio_max):
    hoy = date.today()
    col_titulo, col_estado = st.columns([3, 1])
    periodo_titulo = str(rango_anios[0]) if rango_anios[0] == rango_anios[1] else f"{rango_anios[0]}-{rango_anios[1]}"
    col_titulo.markdown(
        f'<div class="hdr-title">Auditoría del Catálogo {periodo_titulo}</div>'
        '<div class="hdr-sub">¿Dónde concentrar la inversión en licencias para sostener la retención de suscriptores?</div>',
        unsafe_allow_html=True,
    )
    col_estado.markdown(
        f'<div class="hdr-right"><div class="hdr-meta">Datos hasta {anio_max}<br>Generado el {hoy.day} {MESES[hoy.month - 1]} {hoy.year}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="grad-line"></div>', unsafe_allow_html=True)


# ----------------- Barra de filtros horizontal -----------------
def _render_barra_filtros(generos_disp, paises_disp, anio_min, anio_max, rango_defecto):
    """Formato (st.segmented_control) + Años/Género/País (st.popover, cada uno mostrando su selección en el botón
    y resaltado cuando tiene un valor distinto del default) + «Limpiar filtros»/«Vista completa». Todo dentro de
    `st.container(key="barra_filtros")`: es el ÚNICO selector propio (`.st-key-barra_filtros`) del que depende el
    CSS de esta barra en theme.py — ver la nota de aislación ahí."""
    rango_actual = tuple(st.session_state["f_anios"])
    generos_sel, paises_sel = st.session_state["f_generos"], st.session_state["f_paises"]
    activos = {
        "anios": rango_actual != rango_defecto,
        "genero": bool(generos_sel),
        "pais": bool(paises_sel),
    }
    en_defecto = st.session_state["f_tipo"] == "Ambos" and not any(activos.values())

    with st.container(key="barra_filtros", horizontal=True, gap="small", vertical_alignment="center"):
        st.segmented_control(
            "Formato", ["Ambos", "Película", "Serie"], key="f_tipo", required=True, label_visibility="collapsed",
        )
        with st.container(key=f"filtro_anios{'_activo' if activos['anios'] else ''}"):
            with st.popover(f"Años  {narrative.etiqueta_filtro_anios(rango_actual, rango_defecto)}", key="pop_anios"):
                st.markdown(
                    '<div class="filtro-pop-titulo">Años</div>'
                    '<div class="filtro-pop-ayuda">Rango de años de lanzamiento. Se aplica a todas las vistas.</div>',
                    unsafe_allow_html=True,
                )
                st.slider("Años", min_value=anio_min, max_value=anio_max, key="f_anios", label_visibility="collapsed")
                if activos["anios"]:
                    st.button("Quitar selección", key="quitar_anios", on_click=lambda: st.session_state.update(f_anios=rango_defecto))
        with st.container(key=f"filtro_genero{'_activo' if activos['genero'] else ''}"):
            with st.popover(f"Género  {narrative.etiqueta_filtro_lista(generos_sel)}", key="pop_genero"):
                st.markdown(
                    '<div class="filtro-pop-titulo">Género</div>'
                    '<div class="filtro-pop-ayuda">Elige uno o varios. Se aplica a todas las vistas.</div>',
                    unsafe_allow_html=True,
                )
                st.pills("Género", generos_disp, selection_mode="multi", key="f_generos", label_visibility="collapsed")
                if activos["genero"]:
                    st.button("Quitar selección", key="quitar_genero", on_click=lambda: st.session_state.update(f_generos=[]))
        with st.container(key=f"filtro_pais{'_activo' if activos['pais'] else ''}"):
            with st.popover(f"País  {narrative.etiqueta_filtro_lista(paises_sel)}", key="pop_pais"):
                st.markdown(
                    '<div class="filtro-pop-titulo">País</div>'
                    '<div class="filtro-pop-ayuda">Elige uno o varios. Se aplica a todas las vistas.</div>',
                    unsafe_allow_html=True,
                )
                st.multiselect("País", paises_disp, key="f_paises", label_visibility="collapsed", placeholder="Buscar país…")
                if activos["pais"]:
                    st.button("Quitar selección", key="quitar_pais", on_click=lambda: st.session_state.update(f_paises=[]))
        if en_defecto:
            st.markdown('<div class="vista-completa">Vista completa, sin filtros</div>', unsafe_allow_html=True)
        else:
            st.button(
                "Limpiar filtros", icon=":material/close:", key="btn_limpiar", kwargs=dict(rango_defecto=rango_defecto),
                on_click=lambda rango_defecto: st.session_state.update(f_tipo="Ambos", f_anios=rango_defecto, f_generos=[], f_paises=[]),
            )


# ----------------- Orquestación -----------------
def preparar():
    """Se llama UNA vez desde app.py, antes de pg.run(). Carga los datos, dibuja CSV y «Datos» en el riel, el
    header, la barra de filtros y la franja de KPIs, y deja el contexto listo para que cada página lo lea."""
    df, generos_disp, paises_disp = data_loader.load_data()
    anio_min, anio_max = int(df["release_year"].min()), int(df["release_year"].max())
    rango_defecto = (metrics.ANIO_INICIO_DEFECTO, anio_max)

    st.session_state.setdefault("f_tipo", "Ambos")
    st.session_state.setdefault("f_anios", rango_defecto)
    st.session_state.setdefault("f_generos", [])
    st.session_state.setdefault("f_paises", [])

    # Los filtros se leen de session_state directamente (no del valor que devuelve el widget, que recién se dibuja
    # más abajo): Streamlit ya actualiza session_state con la interacción del usuario ANTES de re-ejecutar el script,
    # así que esta lectura ya es la del rerun actual (mismo patrón que modo_paises/metrica/min_votos en las páginas).
    tipo = st.session_state["f_tipo"]
    rango_anios = tuple(st.session_state["f_anios"])
    generos_sel, paises_sel = st.session_state["f_generos"], st.session_state["f_paises"]
    df_filt = df[metrics.construir_mascara(df, tipo, generos_sel, paises_sel, rango_anios)]
    n_total = len(df_filt)

    # Orden del pie del riel (arriba hacia abajo): CSV, luego Datos — ninguno de los dos necesita que la barra de
    # filtros ya se haya dibujado, así que van antes; «Datos» sobrevive a la guarda de selección vacía de abajo.
    _render_csv(df_filt, n_total)
    _render_datos(anio_max)

    _render_header(rango_anios, anio_max)
    _render_barra_filtros(generos_disp, paises_disp, anio_min, anio_max, rango_defecto)

    if n_total == 0:
        aviso(narrative.mensaje_sin_titulos(
            metrics.sugerencias_relajar_filtros(df, tipo, generos_sel, paises_sel, rango_anios, (anio_min, anio_max))
        ))
        st.stop()

    st.markdown(kpis.franja_html(df_filt, len(df)), unsafe_allow_html=True)

    # Conteo de países: el widget vive en la página Mercados, pero el Resumen también usa la cifra de concentración
    # geográfica — se lee aquí desde session_state para que ambas páginas usen siempre el mismo modo.
    modo_paises = OPCIONES_CONTEO_PAISES.get(st.session_state.get(CLAVE_MODO_PAISES, "Primer país"), metrics.MODO_PRIMER_PAIS)

    ctx = dict(
        df=df, df_filt=df_filt, n_total=n_total, tipo=tipo, rango_anios=rango_anios, generos_sel=generos_sel,
        paises_sel=paises_sel, anio_min=anio_min, anio_max=anio_max, modo_paises=modo_paises,
        generos_disp=generos_disp, paises_disp=paises_disp,
    )
    st.session_state["_ctx"] = ctx
    return ctx


def pie_de_pagina():
    st.divider()
    st.markdown(
        '<div class="footer">'
        f'<span title="Fuente: {data_loader.ARCHIVO_PELICULAS} y {data_loader.ARCHIVO_SERIES}">'
        "StreamView Analytics</span>"
        f"<span>{escape(EQUIPO)}</span>"
        "<span>ADY1104 · DUOC UC</span></div>",
        unsafe_allow_html=True,
    )
