"""Página «Resumen»: conclusión primero — tesis (32px, sin recuadro) -> dos columnas (7/12 gráfico, 5/12 «Qué hacer»).

Regla: el gráfico de la izquierda SIEMPRE respalda la tesis que se muestra arriba (nunca un gráfico vacío ni un título
que no corresponda a lo que se ve). Con «Ambos» formatos, la tesis puede hablar de formato o (si ningún formato domina
en popularidad Y valoración) del primer hallazgo aplicable, y el gráfico de brechas por año sigue sirviendo de contexto
general en ambos casos. Con un solo formato filtrado no hay razón Serie/Película que calcular (falta un formato:
metrics.razon_por_anio da NaN), así que resumen_ejecutivo hace caer la tesis a géneros — y el gráfico pasa a ser el
ranking de géneros que la respalda, con los MISMOS datos que la página Géneros. Si ni eso es posible (ningún género
rinde sobre su formato en la selección), se muestra un aviso breve: nunca ejes vacíos.
"""
from html import escape

import streamlit as st

import _shell
from src import charts, metrics, narrative, theme

ctx = _shell.contexto()
df_filt, tipo, rango_anios, modo_paises, anio_max = ctx["df_filt"], ctx["tipo"], ctx["rango_anios"], ctx["modo_paises"], ctx["anio_max"]

resumen = narrative.resumen_ejecutivo(df_filt, rango_anios, modo_paises, anio_max)
narrative.render_tesis(resumen)
col_brechas, col_hacer = st.columns([7, 5])
with col_brechas:
    titulo_izq = subtitulo_izq = fig_izq = None
    if tipo == "Ambos":
        t_formatos = metrics.tendencia_formatos(df_filt, anio_max)
        titulo_izq, subtitulo_izq = narrative.titulo_brechas_resumen(t_formatos)
        fig_izq = charts.brechas_resumen(metrics.razon_por_anio(df_filt), metrics.ventaja_valoracion_alta_por_anio(df_filt), anio_max)
    elif resumen["clave_tesis"] == "generos":
        resumen_generos_resumen = metrics.resumen_generos(df_filt)
        if len(resumen_generos_resumen) >= metrics.MIN_GENEROS_BURBUJAS:
            cuad_resumen, _, _ = metrics.cuadrantes_generos(resumen_generos_resumen)
            destacados_resumen = narrative.generos_destacados_resumen(cuad_resumen)
            if destacados_resumen:
                titulo_izq, subtitulo_izq = narrative.titulo_ranking_generos_resumen(cuad_resumen, tipo)
                fig_izq = charts.ranking_generos_resumen(cuad_resumen, tipo, destacados_resumen)
    if fig_izq is not None:
        st.markdown(
            f'<div class="resumen-col-titulo">{escape(titulo_izq)}</div>'
            f'<div class="resumen-col-subtitulo">{escape(subtitulo_izq)}</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(fig_izq, config=theme.plot_config("resumen_grafico", siempre_visible=False))
    else:
        _shell.aviso(
            "Esta selección no tiene datos suficientes para un gráfico que respalde la tesis. "
            "Prueba ampliar el rango de años o quitar el filtro de género o de país."
        )
with col_hacer:
    narrative.render_que_hacer(resumen)
