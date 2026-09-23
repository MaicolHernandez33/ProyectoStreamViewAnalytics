"""Página «Géneros»: un solo gráfico (burbujas). Ya muestran volumen (eje X) y formato de origen (relleno/anillo),
así que un ranking de barras apiladas por formato sería redundante (ver DECISIONES.md, descartadas)."""
import streamlit as st

import _shell
from src import charts, metrics, narrative, theme

ctx = _shell.contexto()
df_filt = ctx["df_filt"]

titulo, subtitulo = narrative.titulo_generos(df_filt)
narrative.render_titulo(titulo, subtitulo)
col_grafico, col_texto = st.columns([8, 4])

with col_grafico:
    resumen_generos = metrics.resumen_generos(df_filt)
    if resumen_generos.empty:
        _shell.aviso(
            f"Ningún género de la selección tiene al menos {metrics.MIN_TITULOS_RELATIVA} títulos. "
            "Prueba ampliar el rango de años o quitar el filtro de país."
        )
    elif len(resumen_generos) < metrics.MIN_GENEROS_BURBUJAS:
        _shell.aviso(
            f"La selección tiene menos de {metrics.MIN_GENEROS_BURBUJAS} géneros con al menos {metrics.MIN_TITULOS_RELATIVA} títulos: "
            "las burbujas necesitan más para poder compararlos."
        )
    else:
        cuadrantes, med_x, referencia = metrics.cuadrantes_generos(resumen_generos)
        with st.container(key="grafico_generos"):
            leyenda = narrative.leyenda_generos_html(charts.origenes_presentes_generos(cuadrantes))
            st.markdown(f'<div class="tarjeta-cabecera"><span></span>{leyenda}</div>', unsafe_allow_html=True)
            st.plotly_chart(charts.burbujas_generos(cuadrantes, med_x, referencia), config=theme.plot_config("generos"))

with col_texto:
    narrative.render_panel(*narrative.panel_generos(df_filt), clave="generos")
    if not resumen_generos.empty and len(resumen_generos) >= metrics.MIN_GENEROS_BURBUJAS:
        narrative.render_como_leer(narrative.como_leer_generos(cuadrantes), expandible=False)
