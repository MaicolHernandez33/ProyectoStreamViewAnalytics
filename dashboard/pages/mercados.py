"""Página «Mercados»: países de origen por formato, con el ranking siguiendo el modo de conteo activo
(Primer país / Coproducciones — el control vive aquí, pero el Resumen también lee su valor desde session_state)."""
import streamlit as st

import _shell
from src import charts, metrics, narrative, theme

ctx = _shell.contexto()
df_filt, modo_paises = ctx["df_filt"], ctx["modo_paises"]

# "Analizando N títulos con país registrado" (único lugar donde el denominador del gráfico no coincide con el
# indicador global de títulos analizados) va dentro del subtítulo que arma narrative.titulo_paises, no en una línea aparte.
titulo, subtitulo = narrative.titulo_paises(df_filt, modo_paises)
narrative.render_titulo(titulo, subtitulo)
col_grafico, col_texto = st.columns([8, 4])

with col_grafico:
    datos_paises, orden_paises = metrics.top_paises(df_filt, n=metrics.N_PAISES_RANKING, modo=modo_paises)
    if datos_paises.empty:
        _shell.aviso("Los títulos filtrados no tienen país registrado. Prueba ampliar el rango de años o quitar el filtro de género.")
    else:
        relativa_paises = metrics.popularidad_relativa_paises(df_filt, modo_paises, min_titulos=1).set_index("pais")["pop_relativa"]
        with st.container(key="grafico_paises"):
            col_ctrl, col_leg = st.columns([3, 2])
            with col_ctrl:
                # El modo se lee ANTES en _shell.preparar() (desde session_state) para que el Resumen y esta página
                # siempre usen el mismo conteo; este widget es quien lo escribe.
                st.radio("Conteo", list(_shell.OPCIONES_CONTEO_PAISES), index=0, key=_shell.CLAVE_MODO_PAISES, horizontal=True)
            with col_leg:
                st.markdown(f'<div style="text-align:right">{narrative.leyenda_html(set(datos_paises["type"]))}</div>', unsafe_allow_html=True)
            st.plotly_chart(charts.barras_paises_apiladas(datos_paises, orden_paises, relativa_paises), config=theme.plot_config("mercados"))

with col_texto:
    narrative.render_panel(*narrative.panel_paises(df_filt, modo_paises), clave="paises")
    if not datos_paises.empty:
        st.markdown(narrative.mejor_rendimiento_html(df_filt, modo_paises), unsafe_allow_html=True)
        narrative.render_como_leer(narrative.como_leer_paises(df_filt, modo_paises), expandible=True)
