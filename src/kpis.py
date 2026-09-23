"""
Franja de indicadores (KPIs) de la cabecera del dashboard: el HTML de la franja, a partir del catálogo filtrado.

`franja_html(df_filt, n_catalogo)` devuelve UNA franja SURFACE con borde y radio 12, dividida en 4 celdas por líneas
verticales (no 4 tarjetas), en el orden «cuánto tengo -> qué tan atractivo -> qué tan bueno -> qué está fallando». Cada
celda: ícono en círculo de 40px a la izquierda, etiqueta/valor/detalle a la derecha. Toda cifra sale de src/metrics.py y
todo color de src/theme.py; app.py solo dibuja el HTML que esta función devuelve.
"""
from html import escape

from src import metrics, theme

# Íconos en línea (trazo, sin relleno — `currentColor` toma el color de `.kpi-icono`/`.kpi-icono--riesgo` en theme.py).
_ICONO_CATALOGO = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
    '<rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>'
)
_ICONO_POPULARIDAD = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/></svg>'
)
_ICONO_ESTRELLA = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
)
_ICONO_RIESGO = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 2 1 21h22L12 2z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
)


def _celda(icono, etiqueta, valor, detalle_html, riesgo=False):
    clase_icono = "kpi-icono kpi-icono--riesgo" if riesgo else "kpi-icono"
    return (
        f'<div class="kpi-celda"><div class="{clase_icono}">{icono}</div>'
        f'<div class="kpi-textos"><div class="kpi-etiqueta">{escape(etiqueta)}</div>'
        f'<div class="kpi-valor">{escape(valor)}</div><div class="kpi-detalle">{detalle_html}</div></div></div>'
    )


def _punto(color):
    return f'<span class="dot" style="background:{color}"></span>'


def _detalle_popularidad(pop_por_formato):
    """Detalle de la celda de popularidad: la mediana de cada formato (`pop_por_formato`, una Serie indexada por formato),
    con su punto de color (solo los presentes). No lleva delta contra otro período: `popularity` no es comparable entre años."""
    partes = [
        f'{_punto(theme.COLOR_FORMATO[f])}{plural} {theme.fmt_float(pop_por_formato[f])}'
        for f, plural in (("Serie", "Series"), ("Película", "Películas")) if f in pop_por_formato.index
    ]
    return " &nbsp;·&nbsp; ".join(partes)


def franja_html(df_filt, n_catalogo):
    """HTML de la franja de 4 KPIs globales del catálogo filtrado `df_filt`; `n_catalogo` es el tamaño del catálogo
    completo (para el % de «Títulos analizados»). Se dibuja una sola vez, arriba de las pestañas, y se ve en todas."""
    n_total = len(df_filt)
    n_riesgo = metrics.matriz_popularidad_valoracion(df_filt, metrics.MIN_VOTOS_MATRIZ_DEFECTO).get("n_riesgo")
    pct_bien_evaluado = metrics.pct_bien_evaluado(df_filt)
    celdas = [
        _celda(
            _ICONO_CATALOGO, "Títulos analizados", theme.fmt_int(n_total),
            f"{theme.fmt_pct(n_total / n_catalogo)} del catálogo completo",
        ),
        _celda(
            _ICONO_POPULARIDAD, "Popularidad mediana", theme.fmt_float(metrics.popularidad_mediana(df_filt)),
            _detalle_popularidad(metrics.popularidad_mediana_por_formato(df_filt)),
        ),
        _celda(
            _ICONO_ESTRELLA, "Bien evaluados",
            "—" if pct_bien_evaluado is None else theme.fmt_pct(pct_bien_evaluado),
            f"Del total, valoración ≥{metrics.UMBRAL_ALTA} con ≥{metrics.MIN_VOTOS_BIEN_EVALUADO} votos",
        ),
        _celda(
            _ICONO_RIESGO, "Títulos en riesgo",
            "—" if n_riesgo is None else theme.fmt_int(n_riesgo),
            f"Populares (P75) con valoración <{metrics.UMBRAL_RIESGO}" if n_riesgo is not None else "Sin títulos con votos suficientes",
            riesgo=True,
        ),
    ]
    return f'<div class="kpi-franja">{"".join(celdas)}</div>'
