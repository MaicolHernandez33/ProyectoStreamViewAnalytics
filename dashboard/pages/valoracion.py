"""Página «Valoración»: composición de cada formato por nivel de valoración (alta, media, baja y sin votos)."""
import streamlit as st

import _shell
from src import charts, metrics, narrative, theme

ctx = _shell.contexto()
df_filt, tipo = ctx["df_filt"], ctx["tipo"]

if tipo != "Ambos":
    _shell.aviso(_shell.AVISO_FORMATO_UNICO)
titulo, subtitulo = narrative.titulo_valoracion(df_filt)
narrative.render_titulo(titulo, subtitulo)
col_grafico, col_texto = st.columns([8, 4])

with col_grafico:
    with st.container(key="grafico_valoracion"):
        # Leyenda de NIVELES, no Película/Serie: las filas del gráfico ya dicen su formato (rótulo del eje Y).
        st.markdown(f'<div class="tarjeta-cabecera"><span></span>{narrative.leyenda_niveles_valoracion_html()}</div>', unsafe_allow_html=True)
        st.plotly_chart(charts.barras_valoracion(metrics.barras_valoracion(df_filt)), config=theme.plot_config("valoracion"))

with col_texto:
    narrative.render_panel(*narrative.panel_valoracion(df_filt), clave="valoracion")
    narrative.render_como_leer(narrative.como_leer_valoracion(df_filt))
