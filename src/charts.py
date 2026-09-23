"""
Construcción de los gráficos Plotly del dashboard.

Cada función recibe los datos YA calculados por src/metrics.py (nunca recalcula) y devuelve una figura estilizada con
theme.aplicar_layout, lista para st.plotly_chart. Ninguna figura dibuja su propia leyenda de Plotly (`showlegend=False`
en todas las trazas): la leyenda es HTML y vive en la cabecera de la tarjeta que envuelve al gráfico (narrative.leyenda_html),
para que quede junto al control de la pestaña y no floté sobre el trazado.

Regla de color: en todo gráfico que desagrega por formato, Película es rojo y Serie gris. Ningún tamaño de
texto ni color se escribe aquí: todo viene de theme.py.
"""
import math

import numpy as np
import plotly.graph_objects as go

from src import metrics, theme
from src.data_loader import GENERO_ORIGINAL
from src.narrative import unir_es

FORMATOS = ["Película", "Serie"]


def _rotulo_formato(nombre):
    """Etiqueta de eje con un punto del color del formato, para que la identidad rojo=Película /
    gris=Serie siga visible aun cuando el color de las barras codifica otra cosa (niveles)."""
    return f'<span style="color:{theme.COLOR_FORMATO[nombre]}">●</span> {nombre}'


def _log10(x):
    return math.log10(x)


# ----------------- Composición del catálogo (géneros) -----------------
# Tamaño aproximado del área de trazado de las burbujas, solo para estimar dónde chocarían las etiquetas
# (el ancho real depende de la pantalla; con menos ancho hay más choques, con más ancho menos).
_ANCHO_BURBUJAS, _ALTO_BURBUJAS = 900, 360
_DIAMETRO_BURBUJA = 16  # círculos de tamaño UNIFORME: el volumen ya lo dice el eje X, el círculo no necesita codificarlo también


# Dirección -> (ux, uy, ancla x, ancla y) en pantalla (y crece hacia abajo): dónde queda la etiqueta respecto de su burbuja
_DIRECCIONES = {
    "E": (1, 0, "left", "middle"), "N": (0, -1, "center", "bottom"), "S": (0, 1, "center", "top"), "W": (-1, 0, "right", "middle"),
    "NE": (.7071, -.7071, "left", "bottom"), "SE": (.7071, .7071, "left", "top"),
    "NW": (-.7071, -.7071, "right", "bottom"), "SW": (-.7071, .7071, "right", "top"),
}
_HOLGURAS = (4, 26, 50, 76)  # px entre el borde de la burbuja y su etiqueta; desde la segunda la etiqueta lleva línea guía
_UMBRAL_ETIQUETA_DOBLE = 17  # nombres de género de más letras que esto (con un espacio) se parten en 2 líneas


def _texto_etiqueta(nombre):
    """(texto a mostrar, letras para estimar el ancho, líneas) de la etiqueta de un género. Los nombres largos y con más
    de una palabra («Ciencia ficción y fantasía») se parten en 2 líneas cerca del medio: la etiqueta queda más angosta
    y cabe más cerca de su burbuja, con menos choques y sin necesitar línea guía tan seguido."""
    if len(nombre) > _UMBRAL_ETIQUETA_DOBLE and " " in nombre:
        palabras = nombre.split(" ")
        corte = min(range(1, len(palabras)), key=lambda i: abs(len(" ".join(palabras[:i])) - len(" ".join(palabras[i:]))))
        linea1, linea2 = " ".join(palabras[:corte]), " ".join(palabras[corte:])
        return f"{linea1}<br>{linea2}", max(len(linea1), len(linea2)), 2
    return nombre, len(nombre), 1


def _colocar_etiquetas(px, py, radios, textos, anchos_medida, alturas):
    """Elige, para cada burbuja, dónde poner su etiqueta: primero pegada a la burbuja (8 direcciones) y, si ahí choca con otra
    etiqueta, otra burbuja o un rótulo de cuadrante, más lejos con una línea guía hacia su burbuja (así nunca queda ambiguo cuál
    etiqueta es de cuál). Trabaja en píxeles estimados (a 12 px una letra mide ~6,6 px, `anchos_medida` en letras y `alturas` en
    px — una etiqueta de 2 líneas mide el doble de alto) y va de la burbuja más grande a la más chica: las grandes ocupan más y
    eligen primero. Devuelve, por burbuja, {ax, ay (desplazamiento en px, y hacia abajo), xanchor, yanchor, guia}."""
    w_area, h_area = _ANCHO_BURBUJAS, _ALTO_BURBUJAS
    anchos = [6.6 * a + 4 for a in anchos_medida]
    fijos = [(0, 0, 175, 34), (w_area - 150, 0, w_area, 34), (w_area - 100, h_area - 34, w_area, h_area), (0, h_area - 20, 70, h_area)]

    def solape(a, b):
        dx, dy = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
        return dx * dy if dx > 0 and dy > 0 else 0

    def candidata(i, direccion, holgura):
        ux, uy, xa, ya = _DIRECCIONES[direccion]
        d = radios[i] + holgura
        x, y, w, alto_t = px[i] + ux * d, py[i] + uy * d, anchos[i], alturas[i]
        x0 = x if xa == "left" else x - w if xa == "right" else x - w / 2
        y0 = y if ya == "top" else y - alto_t if ya == "bottom" else y - alto_t / 2
        return (x0, y0, x0 + w, y0 + alto_t), (ux * d, uy * d, xa, ya)

    colocadas, resultado = [], [None] * len(textos)
    for i in sorted(range(len(textos)), key=lambda k: -radios[k]):
        mejor = None
        for nivel, holgura in enumerate(_HOLGURAS):
            for direccion in _DIRECCIONES:
                caja, (dx, dy, xa, ya) = candidata(i, direccion, holgura)
                penal = sum(solape(caja, o) for o in colocadas) + sum(solape(caja, f) for f in fijos)
                penal += sum(solape(caja, (px[j] - radios[j], py[j] - radios[j], px[j] + radios[j], py[j] + radios[j]))
                             for j in range(len(textos)) if j != i)
                penal += 40 * (max(0, -caja[0]) + max(0, caja[2] - w_area) + max(0, -caja[1]) + max(0, caja[3] - h_area))
                if nivel:  # la línea guía no debe cruzar otras burbujas ni etiquetas ya colocadas
                    for t in (0.3, 0.5, 0.7, 0.9):
                        gx, gy = px[i] + dx * t, py[i] + dy * t
                        penal += 400 * sum(math.hypot(gx - px[j], gy - py[j]) < radios[j] for j in range(len(textos)) if j != i)
                        penal += 400 * sum(o[0] < gx < o[2] and o[1] < gy < o[3] for o in colocadas)
                    penal += 30 * nivel
                if mejor is None or penal < mejor[0] - 1e-9:  # en empate gana el primero que se probó
                    mejor = (penal, caja, dict(ax=dx, ay=dy, xanchor=xa, yanchor=ya, guia=nivel > 0))
        colocadas.append(mejor[1])
        resultado[i] = mejor[2]
    return resultado


def _formato_de_origen(fila):
    """'Película' si el género existe solo en películas, 'Serie' si solo en series, None (neutro) si existe en ambos."""
    if fila["Serie"] == 0 and fila["Película"] > 0:
        return "Película"
    if fila["Película"] == 0 and fila["Serie"] > 0:
        return "Serie"
    return None


def origenes_presentes_generos(datos):
    """Los orígenes (Película/Serie/None) presentes en `datos`, para la leyenda del gráfico de Géneros (narrative.leyenda_generos_html)."""
    return {_formato_de_origen(f) for _, f in datos.iterrows()}


def burbujas_generos(datos, med_x, referencia):
    """Oferta vs rendimiento por género. X = títulos (escala log: 10 de los 15 géneros caen entre 1.000 y 2.900 títulos y en
    escala lineal quedarían apilados), Y = popularidad RELATIVA a su formato (1,0 = mediana del formato). Círculos de tamaño
    UNIFORME (el volumen ya lo dice el eje X): relleno del color de su formato si el género existe solo en ese formato, anillo
    vacío (sin relleno) si existe en ambos — la leyenda de esos tres estados va en narrative.leyenda_generos_html, en la cabecera
    de la tarjeta, no en el gráfico. La banda gris son los géneros a menos de TOLERANCIA_MEDIANA de 1,0: no se clasifican."""
    origen = [_formato_de_origen(f) for _, f in datos.iterrows()]
    colores = [theme.COLOR_FORMATO.get(o, theme.TRANSPARENTE) for o in origen]
    bordes = [theme.BG if o is not None else theme.NEUTRO for o in origen]
    grosor_borde = [1 if o is not None else 2 for o in origen]
    log_x = datos["titulos"].map(_log10).tolist()
    ys = datos["pop_relativa"].tolist()
    rango_y = (max(ys + [referencia]) - min(ys + [referencia])) or 1
    x_min, x_max = min(log_x) - 0.15, max(log_x) + 0.30
    y_min, y_max = min(ys + [referencia]) - 0.18 * rango_y, max(ys + [referencia]) + 0.30 * rango_y

    px = [(x - x_min) / (x_max - x_min) * _ANCHO_BURBUJAS for x in log_x]
    py = [(1 - (y - y_min) / (y_max - y_min)) * _ALTO_BURBUJAS for y in ys]
    radios = [_DIAMETRO_BURBUJA / 2] * len(datos)
    textos_disp, anchos_medida, alturas_etq = zip(*(_texto_etiqueta(g) for g in datos["genero"])) if len(datos) else ((), (), ())
    etiquetas = _colocar_etiquetas(px, py, radios, textos_disp, anchos_medida, alturas_etq)
    disponibilidad = [{"Película": "solo en películas", "Serie": "solo en series", None: "en películas y en series"}[o] for o in origen]

    fig = go.Figure(go.Scatter(
        x=datos["titulos"], y=datos["pop_relativa"], mode="markers", text=datos["genero"],
        marker=dict(color=colores, size=_DIAMETRO_BURBUJA, line=dict(color=bordes, width=grosor_borde)),
        customdata=np.column_stack([
            datos["genero"].map(lambda g: GENERO_ORIGINAL.get(g, g)), datos["votos"], datos["cuadrante"],
            datos["popularidad"], disponibilidad,
        ]),
        hovertemplate=(
            "<b>%{text}</b> (%{customdata[0]}), %{customdata[4]}<br>Títulos: %{x:,}"
            "<br>Popularidad relativa a su formato: %{y:.2f}×<br>Popularidad bruta (mediana): %{customdata[3]:.1f}"
            "<br>Votos totales: %{customdata[1]:,}<br>%{customdata[2]}<extra></extra>"
        ),
        showlegend=False,
    ))
    # Etiquetas como anotaciones (en un eje logarítmico su x va en log10): las que no caben pegadas a su burbuja llevan línea guía
    fuente = dict(size=theme.TAM_CAPTION, color=theme.TEXT)
    for genero, x, y, r, e in zip(textos_disp, log_x, ys, radios, etiquetas):
        base = dict(x=x, y=y, xref="x", yref="y", text=genero, font=fuente, xanchor=e["xanchor"], yanchor=e["yanchor"], align="center")
        if e["guia"]:
            fig.add_annotation(ax=e["ax"], ay=e["ay"], axref="pixel", ayref="pixel", showarrow=True, arrowhead=0, arrowwidth=1,
                               arrowcolor=theme.TEXT_MUTED, standoff=r + 1, **base)
        else:
            fig.add_annotation(showarrow=False, xshift=e["ax"], yshift=-e["ay"], **base)

    fig.update_xaxes(type="log", range=[x_min, x_max], title_text="Cantidad de títulos (escala logarítmica)")
    tope = datos["titulos"].max() * 1.25
    valores_ticks = [v for v in (100, 200, 500, 1000, 2000, 5000, 10000, 20000) if 10 ** x_min <= v <= min(10 ** x_max, tope)]
    fig.update_xaxes(tickvals=valores_ticks, ticktext=[theme.fmt_abrev(v) for v in valores_ticks])
    fig.update_yaxes(range=[y_min, y_max], dtick=0.2, tickformat=".1f", tickprefix="×", title_text="Rendimiento frente a su formato")

    fig.add_shape(type="rect", xref="paper", yref="y", x0=0, x1=1, y0=referencia * (1 - metrics.TOLERANCIA_MEDIANA),
                  y1=referencia * (1 + metrics.TOLERANCIA_MEDIANA), fillcolor=theme.rgba(theme.NEUTRO, 0.12), line_width=0, layer="below")
    linea = dict(color=theme.NEUTRO, width=1, dash="dot")
    fig.add_shape(type="line", xref="x", yref="paper", x0=med_x, x1=med_x, y0=0, y1=1, line=linea)
    fig.add_shape(type="line", xref="paper", yref="y", x0=0, x1=1, y0=referencia, y1=referencia, line=linea)
    # «mediana de su formato» va en el hueco horizontal más ancho junto a la línea de 1,0 (calculado de los datos, no una
    # posición fija): con los géneros por defecto casi todo el lado izquierdo está pegado a esa línea (Reality, Ciencia
    # ficción y fantasía, Misterio…) y el derecho tiene a Comedia y Drama sobre ella — el hueco cambia con los filtros.
    y_ref_px = (1 - (referencia - y_min) / (y_max - y_min)) * _ALTO_BURBUJAS
    cerca = sorted(x for x, y in zip(px, py) if abs(y - y_ref_px) < 40)
    bordes = [0.0] + cerca + [_ANCHO_BURBUJAS]
    _, x_libre = max((bordes[i + 1] - bordes[i], (bordes[i] + bordes[i + 1]) / 2) for i in range(len(bordes) - 1))
    fig.add_annotation(x=x_libre / _ANCHO_BURBUJAS, y=referencia, xref="paper", yref="y", xanchor="center", yanchor="bottom",
                       showarrow=False, text="mediana de su formato", font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))
    # Rótulos de cuadrante en las esquinas del área de trazado (coordenadas de papel, no de datos). «Sobreofertado» dice
    # que está vacío cuando lo está: no es un hallazgo que se deba disimular, es EL hallazgo.
    n_sobreofertado = int((datos["cuadrante"] == metrics.CUAD_SOBREOFERTADO).sum())
    texto_sobreofertado = "sin géneros en esta zona" if n_sobreofertado == 0 else "revisar"
    estilo = dict(showarrow=False, font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))
    fig.add_annotation(x=0.01, y=0.99, xref="paper", yref="paper", xanchor="left", yanchor="top", align="left",
                       text=f"<b>{metrics.CUAD_NICHO}</b><br>pocos títulos, rinden más: invertir", **estilo)
    fig.add_annotation(x=0.99, y=0.99, xref="paper", yref="paper", xanchor="right", yanchor="top", align="right",
                       text=f"<b>{metrics.CUAD_MOTORES}</b><br>muchos títulos, rinden más: sostener", **estilo)
    fig.add_annotation(x=0.99, y=0.01, xref="paper", yref="paper", xanchor="right", yanchor="bottom", align="right",
                       text=f"<b>{metrics.CUAD_SOBREOFERTADO}</b><br>{texto_sobreofertado}", **estilo)
    fig.add_annotation(x=0.01, y=0.01, xref="paper", yref="paper", xanchor="left", yanchor="bottom", align="left",
                       text=f"<b>{metrics.CUAD_MARGINAL}</b>", **estilo)

    fig = theme.aplicar_layout(fig)
    fig.update_layout(height=440, margin=dict(l=60, r=20, t=20, b=50), showlegend=False)
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)  # excepción documentada: en un scatter ambos ejes son magnitudes
    return fig


# ----------------- Mercados de origen (países) -----------------
def barras_paises_apiladas(datos, orden, relativa):
    """Top de países apilado por formato (rojo Película / gris Serie), de mayor a menor total, con el total al final de cada
    barra. `datos` viene en formato largo de metrics.top_paises, `orden` es la lista de países de mayor a menor total y
    `relativa` una Serie país → popularidad relativa a su formato (se muestra en el tooltip)."""
    def valores(formato, columna):
        sub = datos[datos["type"] == formato].set_index("pais")[columna]
        return [sub.get(p, 0) for p in orden]

    rel = [float(relativa.get(p, float("nan"))) for p in orden]
    fig = go.Figure()
    por_formato = {f: valores(f, "titulos") for f in FORMATOS}
    for formato in FORMATOS:
        if not any(por_formato[formato]):
            continue  # con un solo formato filtrado no se dibuja esa serie vacía
        fig.add_trace(go.Bar(
            y=orden, x=por_formato[formato], name=formato, orientation="h", marker=dict(color=theme.COLOR_FORMATO[formato]),
            showlegend=False, customdata=np.column_stack([valores(formato, "popularidad"), rel]),
            hovertemplate=(
                f"<b>%{{y}}</b><br>{formato}: %{{x:,}} títulos<br>Popularidad mediana ({formato}): %{{customdata[0]:.1f}}"
                "<br>Popularidad relativa del país: %{customdata[1]:.2f}× su formato<extra></extra>"
            ),
        ))
    totales = [sum(por_formato[f][i] for f in FORMATOS) for i in range(len(orden))]
    fig.add_trace(go.Scatter(
        y=orden, x=totales, mode="text", text=[f" {theme.fmt_int(t)}" for t in totales], textposition="middle right",
        textfont=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED), cliponaxis=False, hoverinfo="skip", showlegend=False,
    ))
    fig.update_layout(barmode="stack", bargap=0.3, showlegend=False)
    fig = theme.aplicar_layout(fig)
    fig.update_yaxes(categoryorder="array", categoryarray=list(orden), autorange="reversed", title_text=None)
    maximo = max(totales) if totales else 1
    fig.update_layout(height=max(220, 34 * len(orden) + 50), margin=dict(l=110, r=55, t=10, b=40))
    tv, tt = theme.tick_abreviado(maximo)
    fig.update_xaxes(showgrid=True, tickvals=tv, ticktext=tt, range=[0, maximo * 1.12], title_text="Cantidad de títulos")
    return fig


# ----------------- Evolución -----------------
def linea_evolucion(datos, metrica_label, anio_parcial=None, caida=None, anio_caida=metrics.ANIO_ANOTADO):
    """Dos líneas por formato: Película sólida roja, Serie PUNTEADA gris (el trazo distinto es una segunda codificación además
    del color, por accesibilidad). El año parcial se dibuja aparte, con trazas separadas para no romper la leyenda: el tramo
    hacia él con opacidad 0,35 y su marcador hueco (borde del formato, relleno transparente), con la anotación «{año} parcial»
    arriba. Rótulo de valor solo en el primer y el último año COMPLETO. Con `caida` (variación negativa de las series respecto
    del año anterior) se anota la flecha en `anio_caida`. Sin leyenda propia: la leyenda es HTML, en la cabecera de la tarjeta."""
    fig = go.Figure()
    anios = sorted(datos["release_year"].unique())
    parcial = anio_parcial if anio_parcial in anios else None
    series = {f: datos[datos["type"] == f].sort_values("release_year") for f in FORMATOS}
    trazo = {"Película": "solid", "Serie": "dash"}
    grosor, marcador = 2.5, 7
    for formato in FORMATOS:
        s = series[formato]
        if s.empty:
            continue
        color = theme.COLOR_FORMATO[formato]
        completos, en_parcial = s[s["release_year"] != parcial], s[s["release_year"] == parcial]
        if not completos.empty:
            fig.add_trace(go.Scatter(
                x=completos["release_year"], y=completos["valor"], name=formato, legendgroup=formato, mode="lines+markers",
                showlegend=False, line=dict(color=color, width=grosor, dash=trazo[formato]), marker=dict(size=marcador, color=color),
            ))
        if not en_parcial.empty:
            valor_parcial = en_parcial["valor"].iloc[0]
            if not completos.empty:
                ultimo = completos.iloc[-1]
                fig.add_trace(go.Scatter(
                    x=[ultimo["release_year"], parcial], y=[ultimo["valor"], valor_parcial], mode="lines", legendgroup=formato,
                    showlegend=False, opacity=0.35, hoverinfo="skip", line=dict(color=color, width=grosor, dash=trazo[formato]),
                ))
            fig.add_trace(go.Scatter(
                x=[parcial], y=[valor_parcial], mode="markers", name=formato, legendgroup=formato, showlegend=False,
                marker=dict(size=marcador + 2, color=theme.TRANSPARENTE, line=dict(color=color, width=2)),
            ))

    # Rótulos de valor: primer año completo (a la izquierda) y último año completo (arriba del punto; a su izquierda si la otra serie
    # queda justo encima, para que no se monten). Nunca en el año parcial.
    completos_anios = [a for a in anios if a != parcial]
    y_max = max(datos["valor"].max(), 1e-9)
    px_por_unidad = 300 / y_max
    etiquetados = []
    if completos_anios:
        etiquetados.append((completos_anios[0], "izq"))
        if completos_anios[-1] != completos_anios[0]:
            etiquetados.append((completos_anios[-1], "der"))
    for anio, lado in etiquetados:
        en_anio = {f: series[f].set_index("release_year")["valor"].get(anio) for f in FORMATOS if not series[f].empty}
        en_anio = {f: v for f, v in en_anio.items() if v is not None}
        for formato, valor in en_anio.items():
            otros = [v for f, v in en_anio.items() if f != formato]
            if lado == "izq":
                corrimiento = 0
                if otros and abs(valor - otros[0]) * px_por_unidad < 16:
                    corrimiento = 8 if valor >= otros[0] else -8
                pos = dict(xanchor="right", xshift=-9, yshift=corrimiento)
            else:
                encima = any(0 < (v - valor) * px_por_unidad < 40 for v in otros)
                pos = dict(xanchor="right", xshift=-10, yshift=6) if encima else dict(xanchor="center", yshift=14)
            fig.add_annotation(x=anio, y=valor, xref="x", yref="y", text=theme.fmt_float(valor), showarrow=False,
                               font=dict(size=theme.TAM_CAPTION, color=theme.COLOR_FORMATO[formato]), **pos)

    if parcial is not None:
        fig.add_annotation(x=parcial, y=1, xref="x", yref="paper", xanchor="center", yanchor="bottom", showarrow=False,
                           text=f"{parcial} parcial", font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))
    if caida is not None and anio_caida in anios and not series["Serie"].empty:
        y_serie = series["Serie"].set_index("release_year")["valor"][anio_caida]
        fig.add_annotation(
            x=anio_caida, y=y_serie, xref="x", yref="y", ax=0, ay=52, showarrow=True, arrowhead=2, arrowwidth=1.5,
            arrowcolor=theme.TEXT_MUTED, text=f"Series: {theme.fmt_pct(caida)} en {anio_caida}<br>respecto del año anterior",
            font=dict(size=theme.TAM_CAPTION, color=theme.TEXT), align="center",
        )

    fig = theme.aplicar_layout(fig)
    fig.update_xaxes(range=[anios[0] - 0.9, anios[-1] + 0.9], dtick=1, title_text="Año de lanzamiento")
    fig.update_yaxes(showgrid=True, rangemode="tozero", title_text=metrica_label)
    fig.update_layout(hovermode="x unified", height=380, margin=dict(l=60, r=20, t=20, b=50), showlegend=False)
    return fig


# ----------------- Valoración por formato -----------------
_NIVELES = [(metrics.NIVEL_ALTA, "alta"), (metrics.NIVEL_MEDIA, "media"), (metrics.NIVEL_BAJA, "baja")]
_ESPACIO_SIN_VOTOS = 0.035       # separación visual antes de «Sin votos»: es dato faltante, no un nivel
_ANCHO_NOMINAL_VALORACION = 700  # ancho de referencia del área de trazado, para estimar colisiones horizontales (igual criterio que en burbujas_generos)


def _separar_rotulos_horizontal(rotulos, rango_x, ancho_nominal=_ANCHO_NOMINAL_VALORACION, margen_px=4):
    """x de cada rótulo de `rotulos` (formato, x, texto), separados en horizontal cuando dos de la MISMA fila chocarían
    (segmentos angostos y consecutivos, p. ej. Baja junto a Sin votos). Todos los rótulos van siempre ENCIMA de su barra
    (yshift fijo en el llamador): la única forma de evitar que choquen es correrlos en X, nunca en Y."""
    px_por_unidad = ancho_nominal / rango_x
    xs = [x for _, x, _ in rotulos]
    anchos_px = [6.5 * len(t) + 6 for _, _, t in rotulos]
    por_fila = {}
    for i, (f, _, _) in enumerate(rotulos):
        por_fila.setdefault(f, []).append(i)
    for idxs in por_fila.values():
        idxs = sorted(idxs, key=lambda i: xs[i])
        for a, b in zip(idxs, idxs[1:]):
            centro_a, centro_b = xs[a] * px_por_unidad, xs[b] * px_por_unidad
            faltante = (anchos_px[a] / 2 + anchos_px[b] / 2 + margen_px) - (centro_b - centro_a)
            if faltante > 0:
                corrimiento = (faltante / 2) / px_por_unidad
                xs[a] -= corrimiento
                xs[b] += corrimiento
    return xs


def barras_valoracion(datos):
    """Barras 100% apiladas, una por formato, con los cuatro segmentos en orden ordinal (Alta, Media, Baja) y «Sin votos» separado
    al final, en la MISMA posición X en ambas filas (empieza siempre en 1 + _ESPACIO_SIN_VOTOS, porque los tres niveles de cada
    fila siempre suman 1). Cada fila usa el color de SU formato (rojo Película, gris Serie) y el nivel se codifica por opacidad
    (theme.OPACIDAD_NIVEL), con un borde de theme.SEPARACION_SEGMENTOS_PX en el color de fondo entre segmentos para que el límite
    se vea sin depender de la opacidad. El porcentaje de cada segmento va SIEMPRE por ENCIMA de la barra (nunca dentro): así no
    depende del contraste contra un relleno translúcido. Sin leyenda propia (HTML, en la cabecera de la tarjeta)."""
    formatos = [f for f in FORMATOS if f in set(datos["Formato"])]
    fig = go.Figure()
    inicio = {f: 0.0 for f in formatos}   # dónde empieza el siguiente segmento de cada barra (para centrar el rótulo de encima)
    rotulos = []                          # (formato, x_centro, texto)

    for nivel in metrics.ORDEN_VALORACION:
        if nivel == metrics.NIVEL_SIN_VOTOS:
            fig.add_trace(go.Bar(  # espaciador transparente: separa «Sin votos» sin distorsionar los % de los otros niveles
                y=formatos, x=[_ESPACIO_SIN_VOTOS] * len(formatos), orientation="h", showlegend=False,
                marker=dict(color=theme.TRANSPARENTE), hoverinfo="skip",
            ))
            for f in formatos:
                inicio[f] += _ESPACIO_SIN_VOTOS
        sub = datos[datos["Nivel"] == nivel].set_index("Formato")
        pct = [float(sub.loc[f, "Porcentaje"]) for f in formatos]
        titulos = [int(sub.loc[f, "Titulos"]) for f in formatos]
        clave = dict(_NIVELES).get(nivel)
        for f, p in zip(formatos, pct):
            if p > 0:
                rotulos.append((f, inicio[f] + p / 2, "<1%" if p < 0.005 else theme.fmt_pct(p)))
            inicio[f] += p
        if clave is None:  # trama rayada, no relleno sólido, para que se lea como "dato faltante"
            marca = dict(color=theme.TRANSPARENTE, line=dict(color=theme.NEUTRO, width=1),
                         pattern=dict(shape="/", fgcolor=theme.NEUTRO, bgcolor=theme.TRANSPARENTE, size=6, solidity=0.25))
        else:
            marca = dict(color=[theme.rgba(theme.COLOR_FORMATO[f], theme.OPACIDAD_NIVEL[clave]) for f in formatos],
                         line=dict(color=theme.BG, width=theme.SEPARACION_SEGMENTOS_PX))
        fig.add_trace(go.Bar(
            y=formatos, x=pct, name=nivel, orientation="h", marker=marca, cliponaxis=False, showlegend=False,
            customdata=np.column_stack([titulos, [("<1%" if 0 < p < 0.005 else theme.fmt_pct(p)) for p in pct]]),
            hovertemplate="<b>%{y}</b> · " + nivel + "<br>%{customdata[1]} (%{customdata[0]:,} títulos)<extra></extra>",
        ))

    alto = 90 + 62 * len(formatos)
    banda = (alto - 54 - 10) / len(formatos)
    # El ancho de «Sin votos» varía mucho con los filtros (hasta 68% en el año parcial): el rango del eje X tiene que
    # incluir el más ancho de los dos formatos, si no, la columna y su encabezado quedan fuera de lo visible. Se calcula
    # ANTES de ubicar los rótulos porque también hace falta para estimar colisiones horizontales entre ellos (más abajo).
    max_sin_votos = datos[datos["Nivel"] == metrics.NIVEL_SIN_VOTOS].set_index("Formato").reindex(formatos)["Porcentaje"].max() if formatos else 0
    rango_x = 1 + _ESPACIO_SIN_VOTOS + max_sin_votos + 0.02
    desplazamiento = banda * 0.65 / 2 + 9
    xs_rotulos = _separar_rotulos_horizontal(rotulos, rango_x)
    for (f, _, texto), x in zip(rotulos, xs_rotulos):  # SIEMPRE encima de su segmento (nunca debajo de la barra)
        fig.add_annotation(x=x, y=f, xref="x", yref="y", text=texto, showarrow=False, yshift=desplazamiento,
                           font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))
    if formatos:  # encabezado de la columna «Sin votos», una vez, centrado sobre su ancho máximo entre ambas filas
        fig.add_annotation(x=1 + _ESPACIO_SIN_VOTOS + max_sin_votos / 2, y=1, xref="x", yref="paper", yanchor="bottom",
                           showarrow=False, text="Sin votos", font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))

    fig.update_layout(barmode="stack", bargap=0.35, showlegend=False)
    fig = theme.aplicar_layout(fig)
    fig.update_xaxes(range=[0, rango_x], showgrid=False, showticklabels=False, title_text=None)
    fig.update_yaxes(
        categoryorder="array", categoryarray=formatos, autorange="reversed", title_text=None,
        tickmode="array", tickvals=formatos, ticktext=[_rotulo_formato(f) for f in formatos],
    )
    fig.update_layout(height=alto, margin=dict(l=90, r=10, t=28, b=10))
    return fig


# ----------------- Resumen: brechas por año -----------------
def _ticks_con_cero_sin_signo(minimo, maximo, paso):
    """tickvals/ticktext de un eje con signo (+10, -10…) donde el cero se lee '0', no '+0' — tickformat de Plotly no
    distingue el cero al forzar el signo en el resto de las marcas."""
    ini, fin = math.floor(minimo / paso) * paso, math.ceil(maximo / paso) * paso
    valores = [ini + i * paso for i in range(int(round((fin - ini) / paso)) + 1)]
    return valores, ["0" if v == 0 else f"{v:+.0f}" for v in valores]


def brechas_resumen(razon_df, ventaja_df, anio_parcial):
    """Small multiples del Resumen: dos ejes lado a lado, un año COMPLETO por punto — el X termina en el último año
    COMPLETO (el parcial se excluye del todo, no solo del extremo: con un punto a medio año la tesis, que habla de años
    completos, se leería como un desplome que no es tal). Izquierda: razón de popularidad series/películas
    (metrics.razon_por_anio), línea SERIE (gris) — es el eje que se achica. Derecha: ventaja en valoración alta en puntos
    (metrics.ventaja_valoracion_alta_por_anio), línea ACENTO (ámbar) — es EL hallazgo que la tesis destaca y el color que
    dirige la lectura del gráfico hacia él; es el único uso de ACENTO en el dashboard (`.aviso` es neutro, ver theme.py).
    Rótulo de valor solo en el primer y el último punto, del color de su línea. Devuelve None si ningún panel tiene al
    menos un año completo con datos (nunca un gráfico vacío: quien llama debe mostrar un aviso en su lugar)."""
    fig = go.Figure().set_subplots(rows=1, cols=2, horizontal_spacing=0.12)
    paneles = (
        (1, razon_df.rename(columns={"razon": "valor"}), theme.SERIE, ".1f", "×", 1.0),
        (2, ventaja_df.rename(columns={"ventaja_pp": "valor"}), theme.ACENTO, "+.0f", "", 0.0),
    )
    algo_dibujado = False
    for col, d, color, fmt_valor, sufijo, referencia in paneles:
        completos = d.dropna(subset=["valor"]).sort_values("anio")
        completos = completos[completos["anio"] != anio_parcial]
        if completos.empty:
            continue
        algo_dibujado = True
        fig.add_trace(go.Scatter(
            x=completos["anio"], y=completos["valor"], mode="lines+markers", showlegend=False,
            line=dict(color=color, width=2.5), marker=dict(size=6, color=color),
            hovertemplate=f"%{{x}}: %{{y:{fmt_valor}}}{sufijo}<extra></extra>",
        ), row=1, col=col)
        rango_y = completos["valor"].max() - completos["valor"].min() or 1
        for anio, lado in ((completos["anio"].iloc[0], "izq"), (completos["anio"].iloc[-1], "der")):
            if lado == "der" and anio == completos["anio"].iloc[0]:
                continue
            valor = completos.set_index("anio")["valor"][anio]
            # Despeje adicional cuando el punto queda cerca de la línea de referencia (1,0× o 0 pp), para que el
            # rótulo no la toque: se aleja hacia arriba si el valor está en o sobre ella, hacia abajo si está bajo.
            cerca_de_referencia = abs(valor - referencia) < 0.12 * rango_y
            if lado == "izq":
                pos = dict(xanchor="right", xshift=-8)
            else:
                yshift = 18 if cerca_de_referencia and valor >= referencia else 14
                if cerca_de_referencia and valor < referencia:
                    yshift = -18
                pos = dict(xanchor="center", yshift=yshift)
            fig.add_annotation(x=anio, y=valor, xref=f"x{'' if col == 1 else col}", yref=f"y{'' if col == 1 else col}",
                               text=f"{valor:{fmt_valor}}{sufijo}", showarrow=False, font=dict(size=theme.TAM_CAPTION, color=color), **pos)
        eje_x, eje_y = ("xaxis", "yaxis") if col == 1 else (f"xaxis{col}", f"yaxis{col}")
        anios = sorted(completos["anio"].unique())
        fig.update_layout(**{
            eje_x: dict(range=[anios[0] - 0.6, anios[-1] + 0.6], dtick=5, tickfont=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED)),
            eje_y: dict(tickfont=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED), zeroline=False),
        })
        fig.add_shape(type="line", xref=f"x{'' if col == 1 else col} domain", yref=eje_y.replace("axis", ""),
                      x0=0, x1=1, y0=referencia, y1=referencia, line=dict(color=theme.NEUTRO, width=1, dash="dot"))
    if not algo_dibujado:
        return None
    # Eje derecho (ventaja en pp): "0" sin signo en el cero, paso calculado desde el rango real de datos (nunca fijo).
    pp_completos = ventaja_df.dropna(subset=["ventaja_pp"])
    pp_completos = pp_completos[pp_completos["anio"] != anio_parcial]["ventaja_pp"]
    if not pp_completos.empty:
        minimo, maximo = min(0.0, pp_completos.min()), max(0.0, pp_completos.max())
        paso = theme.paso_agradable(maximo - minimo, n_ticks=4)
        tickvals, ticktext = _ticks_con_cero_sin_signo(minimo, maximo, paso)
        fig.update_layout(yaxis2=dict(tickvals=tickvals, ticktext=ticktext))
    fig.update_layout(**{"yaxis": dict(ticksuffix="×", tickformat=".0f")})
    fig = theme.aplicar_layout(fig)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(height=230, margin=dict(l=36, r=10, t=10, b=30), showlegend=False)
    return fig


def ranking_generos_resumen(cuad, formato, destacados, n=8):
    """Ranking horizontal del Resumen cuando el filtro deja un solo formato: la tesis pasa a hablar de géneros (ver
    narrative.resumen_ejecutivo), así que el gráfico también, con los MISMOS datos que la pestaña Géneros
    (metrics.cuadrantes_generos). Los géneros de `destacados` (los que nombra la tesis) van en el color de `formato`;
    el resto, NEUTRO — nunca un color de formato en un género que la tesis no menciona. Línea de referencia en 1,0×
    (mediana del formato), igual que en Géneros. Los `n` géneros de mayor popularidad relativa, mayor arriba."""
    datos = cuad.sort_values("pop_relativa", ascending=False).head(n).iloc[::-1]
    colores = [theme.COLOR_FORMATO[formato] if g in destacados else theme.NEUTRO for g in datos["genero"]]
    fig = go.Figure(go.Bar(
        y=datos["genero"], x=datos["pop_relativa"], orientation="h", marker=dict(color=colores), showlegend=False,
        customdata=datos["titulos"],
        hovertemplate="<b>%{y}</b><br>Popularidad relativa a su formato: %{x:.2f}×<br>Títulos: %{customdata:,}<extra></extra>",
    ))
    fig.add_shape(type="line", xref="x", yref="paper", x0=1.0, x1=1.0, y0=0, y1=1, line=dict(color=theme.NEUTRO, width=1, dash="dot"))
    fig = theme.aplicar_layout(fig)
    fig.update_xaxes(tickformat=".1f", tickprefix="×", showgrid=True)
    fig.update_yaxes(title_text=None, tickfont=dict(size=theme.TAM_CAPTION))
    fig.update_layout(height=230, margin=dict(l=130, r=20, t=10, b=30), showlegend=False)
    return fig


# ----------------- Matriz popularidad vs valoración -----------------
def _texto_paises(paises, maximo=3):
    if not len(paises):
        return "Sin país registrado"
    return unir_es(paises[:maximo]) + (" y otros" if len(paises) > maximo else "")


def matriz_dispersion(df_sc, p75, umbral_riesgo, umbral_alta, conteos):
    """Popularidad vs valoración por título con go.Scattergl (miles de puntos). Los títulos POR DEBAJO del P75 se dibujan apagados y
    pequeños (color PUNTO_APAGADO, opacidad 0,15, radio 2); los que están sobre él, por formato (opacidad 0,5, radio 4). plotly
    mide el tamaño de marcador en diámetro, de ahí size 4 y 8. `conteos` (metrics.conteos_cuadrantes_matriz) pone en cada etiqueta
    los títulos de su zona: los de los cuadrantes de abajo comunican aunque sus puntos estén atenuados."""
    df_sc = df_sc.assign(_pais=df_sc["paises"].map(_texto_paises))
    fig = go.Figure()
    for popular in (False, True):  # primero los apagados, para que los destacados queden encima
        for formato in FORMATOS:
            sub = df_sc[(df_sc["type"] == formato) & ((df_sc["popularity"] >= p75) == popular)]
            if sub.empty:
                continue
            marca = (
                dict(color=theme.COLOR_FORMATO[formato], opacity=0.5, size=8) if popular
                else dict(color=theme.PUNTO_APAGADO, opacity=0.15, size=4)
            )
            fig.add_trace(go.Scattergl(
                x=sub["vote_average"], y=sub["popularity"], mode="markers", marker=dict(**marca, line=dict(width=0)),
                showlegend=False, name=formato,
                customdata=np.column_stack([sub["title"], sub["release_year"], sub["_pais"], sub["type"], sub["vote_count"]]),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>Año: %{customdata[1]}<br>País: %{customdata[2]}<br>Formato: %{customdata[3]}"
                    "<br>Popularidad: %{y:.1f}<br>Valoración: %{x:.1f}<br>Votos: %{customdata[4]:,}<extra></extra>"
                ),
            ))
    x_min = max(0.0, df_sc["vote_average"].min() - 0.3)
    x_max = min(10.2, df_sc["vote_average"].max() + 0.3)
    log_min = _log10(df_sc["popularity"].min() / 1.3)
    log_max = _log10(df_sc["popularity"].max() * 1.3)
    y_p75 = (_log10(p75) - log_min) / (log_max - log_min)
    fig.update_xaxes(range=[x_min, x_max], title_text="Valoración (vote_average)")
    fig.update_yaxes(type="log", range=[log_min, log_max], dtick=1, title_text="Popularidad (escala log)")

    # Zona sobre el P75 sombreada, salvo la franja neutra 6-7 (queda sin sombrear para que se lea como "sin clasificar")
    tono = theme.rgba(theme.NEUTRO, 0.15)
    if x_min < umbral_riesgo:
        fig.add_shape(type="rect", xref="x", yref="paper", x0=x_min, x1=umbral_riesgo, y0=y_p75, y1=1, fillcolor=tono, line_width=0, layer="below")
    if x_max > umbral_alta:
        fig.add_shape(type="rect", xref="x", yref="paper", x0=umbral_alta, x1=x_max, y0=y_p75, y1=1, fillcolor=tono, line_width=0, layer="below")
    linea = dict(color=theme.NEUTRO, width=1, dash="dot")
    fig.add_shape(type="line", xref="paper", yref="paper", x0=0, x1=1, y0=y_p75, y1=y_p75, line=linea)
    for umbral in (umbral_riesgo, umbral_alta):
        fig.add_shape(type="line", xref="x", yref="paper", x0=umbral, x1=umbral, y0=0, y1=1, line=linea)

    # Los cuatro cuadrantes nombrados + la franja neutra, cada uno con su conteo. Los de abajo llevan fondo para leerse sobre los puntos.
    base = dict(showarrow=False, font=dict(size=theme.TAM_CAPTION, color=theme.TEXT))
    fondo = theme.rgba(theme.BG, 0.8)
    n = theme.fmt_int
    if x_min < umbral_riesgo:
        fig.add_annotation(x=umbral_riesgo, xanchor="right", xref="x", y=0.98, yanchor="top", yref="paper", align="right",
                           text=f"<b>Riesgo de abandono · {n(conteos['riesgo'])}</b><br>populares y mal evaluados", **base)
        fig.add_annotation(x=x_min, xanchor="left", xref="x", y=0.01, yanchor="bottom", yref="paper", align="left", bgcolor=fondo,
                           text=f"<b>Bajo rendimiento · {n(conteos['bajo'])}</b><br>candidatos a no renovar", **base)
    if x_max > umbral_alta:
        fig.add_annotation(x=umbral_alta, xanchor="left", xref="x", y=0.98, yanchor="top", yref="paper", align="left",
                           text=f"<b>Activos a retener · {n(conteos['activos'])}</b><br>populares y bien evaluados", **base)
        fig.add_annotation(x=x_max, xanchor="right", xref="x", y=0.01, yanchor="bottom", yref="paper", align="right", bgcolor=fondo,
                           text=f"<b>Nicho de calidad · {n(conteos['nicho'])}</b><br>promocionar", **base)
    if x_min < umbral_alta and x_max > umbral_riesgo:
        fig.add_annotation(x=(umbral_riesgo + umbral_alta) / 2, xanchor="center", xref="x", y=0.98, yanchor="top", yref="paper",
                           align="center", text=f"Zona neutra<br>{umbral_riesgo}–{umbral_alta} · {n(conteos['neutra'])}",
                           showarrow=False, font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))
    fig.add_annotation(x=0.005, xanchor="left", xref="paper", y=y_p75, yanchor="bottom", yref="paper",
                       text=f"Popularidad alta (P75 = {theme.fmt_float(p75)})", showarrow=False,
                       font=dict(size=theme.TAM_CAPTION, color=theme.TEXT_MUTED))

    fig = theme.aplicar_layout(fig)
    # Excepción documentada (igual que en Fase 1): en un scatter ambos ejes son magnitudes continuas, sin eje
    # categórico, así que aquí se activa la grilla en los dos.
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)
    fig.update_layout(height=theme.ALTO_TARJETA_GRAFICO, margin=dict(l=60, r=20, t=40, b=60), showlegend=False)
    return fig
