"""Página «Matriz»: popularidad vs valoración por título, con los cuatro cuadrantes contados y la lista de riesgo."""
import streamlit as st

import _shell
from src import charts, metrics, narrative, theme

ctx = _shell.contexto()
df_filt, anio_max, fmt = ctx["df_filt"], ctx["anio_max"], _shell.fmt

# El mínimo de votos se lee ANTES del título (mismo patrón que Evolución); el slider que lo fija vive en la cabecera
# de la tarjeta, más abajo, y conserva su etiqueta nativa (es la única pista de qué controla).
min_votos = st.session_state.get("votos_matriz", metrics.MIN_VOTOS_MATRIZ_DEFECTO)
mvp = metrics.matriz_popularidad_valoracion(df_filt, min_votos)
titulo, subtitulo = narrative.titulo_matriz(mvp)
narrative.render_titulo(titulo, subtitulo)
col_grafico, col_texto = st.columns([8, 4])

with col_grafico:
    with st.container(key="grafico_matriz"):
        col_ctrl, col_leg = st.columns([5, 2])
        with col_ctrl:
            col_slider, col_conteo = st.columns([3, 2])
            with col_slider:
                min_votos = st.slider(
                    "Mínimo de votos para considerar fiable la valoración",
                    min_value=metrics.MIN_VOTOS_MATRIZ_MINIMO, max_value=metrics.MIN_VOTOS_MATRIZ_MAXIMO,
                    value=metrics.MIN_VOTOS_MATRIZ_DEFECTO, step=metrics.MIN_VOTOS_MATRIZ_PASO, key="votos_matriz",
                )
            mvp = metrics.matriz_popularidad_valoracion(df_filt, min_votos)
            n_cumplen = len(mvp["df_sc"])
            with col_conteo:
                st.markdown(
                    f'<div class="conteo-criterio">{fmt(n_cumplen)} {"título cumple" if n_cumplen == 1 else "títulos cumplen"}</div>',
                    unsafe_allow_html=True,
                )
        with col_leg:
            st.markdown(f'<div style="text-align:right">{narrative.leyenda_html(set(mvp["df_sc"]["type"]))}</div>', unsafe_allow_html=True)

        if mvp["df_sc"].empty:
            _shell.aviso("Ningún título alcanza ese mínimo de votos con los filtros actuales. Reduzca el mínimo.")
        else:
            fig = charts.matriz_dispersion(
                mvp["df_sc"], mvp["p75"], metrics.UMBRAL_RIESGO, metrics.UMBRAL_ALTA, metrics.conteos_cuadrantes_matriz(mvp),
            )
            st.plotly_chart(fig, config=theme.plot_config("matriz"))

with col_texto:
    narrative.render_panel(*narrative.panel_matriz(mvp), clave="matriz")
    # La lista de riesgo reemplaza la tabla + expander, en la columna del panel (no bajo el gráfico).
    if not mvp["df_sc"].empty:
        riesgo = metrics.titulos_en_riesgo(mvp)
        if not riesgo.empty:
            es_default = min_votos == metrics.MIN_VOTOS_MATRIZ_DEFECTO
            st.markdown(narrative.riesgo_lista_html(riesgo, anio_max, min_votos, es_default), unsafe_allow_html=True)
            st.download_button(
                f"Descargar los {fmt(len(riesgo))} en CSV", narrative.csv_riesgo(riesgo, anio_max),
                file_name="titulos_en_riesgo.csv", mime="text/csv", key="descargar_riesgo",
            )
    narrative.render_como_leer(narrative.como_leer_matriz(mvp), expandible=True)
