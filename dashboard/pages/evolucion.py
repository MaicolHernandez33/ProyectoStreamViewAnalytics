"""Página «Evolución»: popularidad o valoración mediana por año, Película vs Serie."""
import streamlit as st

import _shell
from src import charts, metrics, narrative, theme

ctx = _shell.contexto()
df_filt, tipo, anio_max = ctx["df_filt"], ctx["tipo"], ctx["anio_max"]

if tipo != "Ambos":
    _shell.aviso(_shell.AVISO_FORMATO_UNICO)
# La métrica se lee ANTES del título (que la necesita); el widget que la fija vive más abajo, en la cabecera de la
# tarjeta (mismo patrón que el modo de conteo de Mercados: se lee el valor del run anterior, el widget lo actualiza).
metrica = st.session_state.get("metrica_evolucion", "Popularidad mediana")
titulo, subtitulo = narrative.titulo_evolucion(df_filt, metrica, anio_max)
narrative.render_titulo(titulo, subtitulo)
col_grafico, col_texto = st.columns([8, 4])

with col_grafico:
    with st.container(key="grafico_evolucion"):
        col_ctrl, col_leg = st.columns([3, 2])
        with col_ctrl:
            metrica = st.radio("Métrica", ["Popularidad mediana", "Valoración mediana"], horizontal=True, key="metrica_evolucion")
        evolucion = metrics.evolucion_popularidad(df_filt) if metrica == "Popularidad mediana" else metrics.evolucion_valoracion(df_filt)
        with col_leg:
            st.markdown(f'<div style="text-align:right">{narrative.leyenda_html(set(evolucion.get("type", [])))}</div>', unsafe_allow_html=True)
        if evolucion.empty:
            _shell.aviso(f"No hay títulos con al menos {metrics.MIN_VOTOS_VALORACION} votos para calcular la valoración mediana. "
                         "Amplía el rango de años o cambia a «Popularidad mediana».")
        else:
            # La flecha de la caída de series solo se dibuja si la caída existe en los datos mostrados
            # y es de al menos CAIDA_MINIMA_ANOTAR (en popularidad es -34%; en valoración no llega a -1%).
            caida = metrics.variacion_anual(evolucion, "Serie", metrics.ANIO_ANOTADO)
            if caida is not None and caida > -metrics.CAIDA_MINIMA_ANOTAR:
                caida = None
            fig = charts.linea_evolucion(evolucion, metrica, anio_parcial=anio_max, caida=caida)
            fig.update_yaxes(hoverformat=".2f" if metrica == "Valoración mediana" else ",.1f")
            st.plotly_chart(fig, config=theme.plot_config("evolucion"))

with col_texto:
    narrative.render_panel(*narrative.panel_evolucion(df_filt, metrica, anio_max), clave="evolucion")
    if not evolucion.empty:
        narrative.render_como_leer(narrative.como_leer_evolucion(df_filt, metrica, anio_max), expandible=False)
