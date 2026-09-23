"""
Regenera las imágenes de images/ con los MISMOS constructores de src/charts.py, las mismas funciones de src/metrics.py y los
mismos títulos de src/narrative.py que usa el dashboard: una imagen PNG por gráfico principal, con los filtros por defecto
(ambos formatos, todos los géneros y países, años desde metrics.ANIO_INICIO_DEFECTO hasta el último del catálogo).

Uso, desde la raíz del proyecto:

    python -m src.exportar

Requiere kaleido (>= 1.0) y un Chrome o Chromium instalado (kaleido lo usa para dibujar). Cada ejecución reemplaza los PNG.
Las imágenes son un producto del código: no se editan a mano, se vuelven a generar.
"""
import logging
import textwrap
from pathlib import Path

import streamlit  # se importa primero para poder silenciar sus avisos antes de que data_loader use st.cache_data

# Fuera de `streamlit run`, st.cache_data avisa "No runtime found" y "missing ScriptRunContext": no es un problema, es ruido.
for _nombre in list(logging.root.manager.loggerDict):
    if _nombre.startswith(streamlit.__name__):
        logging.getLogger(_nombre).setLevel(logging.ERROR)

from src import charts, data_loader, metrics, narrative, theme  # noqa: E402  (después de silenciar los avisos a propósito)

CARPETA_IMAGENES = Path(__file__).resolve().parent.parent / "images"
ANCHO_PX = 1100
ESCALA = 2  # 2× de resolución: el texto sigue nítido al pegar la imagen en un informe o una presentación
CARACTERES_POR_LINEA_TITULO = 85  # a 20 px en negrita, ~11 px por letra: 85 letras caben en los 1.100 px de ancho
ALTO_LINEA_TITULO_PX = 26  # alto de cada línea extra del título
ALTO_TITULO_PX = 78  # aire extra arriba para el título-mensaje y su subtítulo
MARGEN_TITULO_PX = 14  # distancia del título al borde superior de la imagen
DESFASE_TITULO_PX = 14  # plotly ancla un título de dos líneas ~14 px más arriba de lo pedido (medido sobre el PNG resultante)
AIRE_ABAJO_PX = 30  # y abajo, para que el título del eje X no quede pegado al borde de la imagen


def _con_titulo(fig, titulo, subtitulo):
    """Agrega al gráfico su título-mensaje (el mismo texto que el dashboard muestra encima) para que la imagen se entienda suelta.
    Plotly no parte las líneas solo: un título largo se cortaría en el borde, así que se parte aquí y se suma alto por cada línea extra."""
    lineas = textwrap.wrap(titulo, CARACTERES_POR_LINEA_TITULO)
    texto = (
        f'<b>{"<br>".join(lineas)}</b><br><span style="font-size:{theme.TAM_CAPTION}px;color:{theme.TEXT_MUTED}">{subtitulo}</span>'
    )
    alto_titulo = ALTO_TITULO_PX + ALTO_LINEA_TITULO_PX * (len(lineas) - 1)
    alto_total = (fig.layout.height or 450) + alto_titulo + AIRE_ABAJO_PX
    fig.update_layout(
        title=dict(
            text=texto, x=0.01, xanchor="left", y=1 - (MARGEN_TITULO_PX + DESFASE_TITULO_PX) / alto_total, yanchor="top",
            font=dict(size=theme.TAM_TITULO_SECCION, color=theme.TEXT),
        ),
        height=alto_total, margin=dict(t=fig.layout.margin.t + alto_titulo, b=fig.layout.margin.b + AIRE_ABAJO_PX),
        # theme.aplicar_layout deja paper_bgcolor transparente (para fundirse con la tarjeta SURFACE del dashboard); aquí la
        # figura se guarda SUELTA, sin tarjeta detrás, así que necesita un fondo sólido o el texto claro sería invisible
        # en un visor blanco.
        paper_bgcolor=theme.BG,
    )
    return fig


def figuras(df, anio_parcial):
    """{nombre de archivo: figura} de cada gráfico principal para el catálogo `df` (con los filtros por defecto ya aplicados).
    Un gráfico que la selección no permite dibujar (p. ej. menos de metrics.MIN_GENEROS_BURBUJAS géneros) se omite."""
    salida = {}

    resumen = metrics.resumen_generos(df)
    if len(resumen) >= metrics.MIN_GENEROS_BURBUJAS:
        cuadrantes, med_x, referencia = metrics.cuadrantes_generos(resumen)
        salida["generos_burbujas"] = _con_titulo(charts.burbujas_generos(cuadrantes, med_x, referencia), *narrative.titulo_generos(df))

    datos_paises, orden = metrics.top_paises(df, n=metrics.N_PAISES_RANKING, modo=metrics.MODO_PRIMER_PAIS)
    if not datos_paises.empty:
        relativa = metrics.popularidad_relativa_paises(df, metrics.MODO_PRIMER_PAIS, min_titulos=1).set_index("pais")["pop_relativa"]
        salida["mercados_paises"] = _con_titulo(
            charts.barras_paises_apiladas(datos_paises, orden, relativa), *narrative.titulo_paises(df, metrics.MODO_PRIMER_PAIS)
        )

    for metrica, archivo, evolucion in (
        ("Popularidad mediana", "evolucion_popularidad", metrics.evolucion_popularidad(df)),
        ("Valoración mediana", "evolucion_valoracion", metrics.evolucion_valoracion(df)),
    ):
        if evolucion.empty:
            continue
        caida = metrics.variacion_anual(evolucion, "Serie", metrics.ANIO_ANOTADO)
        if caida is not None and caida > -metrics.CAIDA_MINIMA_ANOTAR:
            caida = None
        fig = charts.linea_evolucion(evolucion, metrica, anio_parcial=anio_parcial, caida=caida)
        salida[archivo] = _con_titulo(fig, *narrative.titulo_evolucion(df, metrica, anio_parcial))

    salida["valoracion_formato"] = _con_titulo(charts.barras_valoracion(metrics.barras_valoracion(df)), *narrative.titulo_valoracion(df))

    mvp = metrics.matriz_popularidad_valoracion(df, metrics.MIN_VOTOS_MATRIZ_DEFECTO)
    if not mvp["df_sc"].empty:
        fig = charts.matriz_dispersion(mvp["df_sc"], mvp["p75"], metrics.UMBRAL_RIESGO, metrics.UMBRAL_ALTA, metrics.conteos_cuadrantes_matriz(mvp))
        salida["matriz_popularidad_valoracion"] = _con_titulo(fig, *narrative.titulo_matriz(mvp))
    return salida


def exportar(carpeta=CARPETA_IMAGENES):
    """Escribe un PNG por gráfico en `carpeta` (que se crea si no existe) y devuelve las rutas escritas."""
    df, _, _ = data_loader.load_data()
    anio_max = int(df["release_year"].max())
    df_defecto = df[metrics.construir_mascara(df, "Ambos", [], [], (metrics.ANIO_INICIO_DEFECTO, anio_max))]
    carpeta.mkdir(exist_ok=True)
    rutas = []
    for nombre, fig in figuras(df_defecto, anio_max).items():
        ruta = carpeta / f"{nombre}.png"
        fig.write_image(ruta, width=ANCHO_PX, height=fig.layout.height, scale=ESCALA)
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    for ruta in exportar():
        print(f"{ruta.relative_to(CARPETA_IMAGENES.parent)}  ({ruta.stat().st_size / 1024:,.0f} KB)")
