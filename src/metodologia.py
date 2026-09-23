"""
Metodología y limitaciones: el texto que sale del dashboard y el que se exporta al informe.

La metodología dejó de ser una pestaña (la audiencia es gerencia; los límites que necesita ya están en la nota al pie de cada gráfico).
Hay dos salidas, ambas armadas con los mismos hechos:

- `popover_html(anio_parcial)`: el contenido breve del popover «ⓘ Sobre los datos» de la fila de filtros: «Lo esencial» (tres puntos),
  «Limitaciones clave» (una línea por limitación) y una línea final que remite al informe. Sin tablas ni nombres de columnas.
- `documento_markdown(anio_parcial)`: el texto COMPLETO (lo esencial, fuente de datos, métricas derivadas, criterios de corte y
  limitaciones), que `python -m src.metodologia` escribe en docs/metodologia.md para usarlo en el informe.

Cada cifra sale de una constante de src/metrics.py o de un cálculo sobre el catálogo completo (metrics.perfil_catalogo,
metrics.tendencia_formatos, data_loader.perfil_fuente): ninguna se escribe a mano. Las limitaciones que afirman una propiedad de los datos
(reparto uniforme, `rating` numérico, año parcial, estrechamiento de la ventaja) tienen una rama alternativa: si la propiedad no se
cumpliera, el texto cambia en vez de afirmarla igual. Describe el catálogo COMPLETO, no la selección de filtros actual.
"""
import logging
from html import escape
from pathlib import Path

import streamlit as st

if __name__ == "__main__":  # `python -m src.metodologia`: fuera de `streamlit run`, st.cache_data avisa «No runtime found» al importar; es ruido
    logging.disable(logging.WARNING)

from src import data_loader, metrics, theme  # noqa: E402  (después de silenciar los avisos a propósito)
from src.narrative import unir_es  # noqa: E402

fmt = theme.fmt_int

RUTA_DOCUMENTO = Path(__file__).resolve().parent.parent / "docs" / "metodologia.md"
# «Datos», no «ⓘ Sobre los datos»: desde el Paso 2 vive en el pie del riel de navegación (dashboard/_shell.py),
# angosto, con su propio ícono (`icon=":material/info:"` en el popover, ya no un carácter ⓘ dentro del texto).
ETIQUETA_POPOVER = "Datos"
LINEA_FINAL = "Metodología completa en el informe del proyecto."


def _c(texto):
    """Nombre de columna o valor literal, como código (Markdown)."""
    return f"`{texto}`"


def _tabla(encabezados, filas):
    """Tabla Markdown. Una barra vertical dentro de una celda se escapa para no partir la columna."""
    def celda(texto):
        return str(texto).replace("|", "\\|")
    lineas = ["| " + " | ".join(encabezados) + " |", "|" + "|".join("---" for _ in encabezados) + "|"]
    lineas += ["| " + " | ".join(celda(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def _lista_numerada(items):
    return "\n".join(f"{i}. **{titulo}** {cuerpo}" for i, (titulo, cuerpo) in enumerate(items, start=1))


@st.cache_data
def _perfil_catalogo(anio_parcial):
    """Perfil del catálogo completo; con caché porque se recalcula en cada interacción y recorre las 32.000 filas."""
    df, _, _ = data_loader.load_data()
    return metrics.perfil_catalogo(df, anio_parcial)


@st.cache_data
def _tendencia_catalogo(anio_parcial):
    """Tendencia de la ventaja de un formato sobre otro en el catálogo COMPLETO (todos los años, sin filtros)."""
    df, _, _ = data_loader.load_data()
    return metrics.tendencia_formatos(df, anio_parcial)


# ----------------- Secciones -----------------
def _esencial_items(pc, detalle=""):
    """Los tres puntos de «Lo esencial»: de dónde vienen los datos, qué controla el análisis, qué no permite concluir. `detalle` se
    agrega al primero (el documento completo remite a su sección «Fuente de datos»; el popover no, porque ahí no existe)."""
    no_permite = [
        "tendencias de volumen de producción (el reparto por año y formato es exacto, lo que sugiere generación sintética)" if pc["uniforme"]
        else "comparaciones de volumen entre años y formatos sin considerar que su reparto no es uniforme",
        "la popularidad como audiencia absoluta ni comparable entre años (es un índice relativo de TMDB)",
        f"el año {pc['parcial']['anio']} (está incompleto)",
    ]
    return [
        ("Datos.", f"Dos archivos CSV del proyecto, uno de películas y otro de series, con {fmt(pc['n_total'])} títulos estrenados entre "
                   f"{pc['anio_min']} y {pc['anio_max']}{detalle}."),
        ("Qué controla el análisis.", "Los filtros de la barra lateral: toda cifra se recalcula sobre la selección. Géneros y mercados se comparan con la "
                                      f"popularidad relativa a la mediana de su formato, y la valoración usa los cortes {metrics.UMBRAL_MEDIA} y {metrics.UMBRAL_ALTA}."),
        ("Qué no permite concluir.", f"Ni {' ni '.join(no_permite)}."),
    ]


def _fuente(pc, perfil):
    a = perfil["archivos"]
    solo_peliculas = unir_es(_c(c) for c in perfil["columnas_solo_peliculas"]) if perfil["columnas_solo_peliculas"] else None
    return [
        f'El dashboard integra dos archivos CSV: {_c(a["Película"])} ({fmt(pc["n_pelicula"])} películas) '
        f'y {_c(a["Serie"])} ({fmt(pc["n_serie"])} series). En total son {fmt(pc["n_total"])} títulos estrenados entre '
        f'{pc["anio_min"]} y {pc["anio_max"]}.',
        'Los gráficos usan las columnas '
        f'{unir_es(_c(c) for c in ("title", "type", "release_year", "popularity", "vote_count", "vote_average", "genres", "country"))}. '
        "Géneros y países vienen como texto separado por comas: se convierten en una lista por título, se traducen al español "
        "al cargar (el nombre original se conserva en el tooltip de géneros) y se respeta el orden de origen, de modo que el "
        "primer país listado se toma como país principal.",
        f'{unir_es(_c(c) for c in ("date_added", "duration", "language", "budget", "revenue"))} se conservan al '
        "cargar pero no se usan todavía"
        + (f"; {solo_peliculas} existen solo en el archivo de películas" if solo_peliculas else "")
        + f". La columna {_c('rating')} se descartó (ver Limitaciones).",
    ]


def _metricas():
    filas = [
        (
            "Popularidad mediana",
            f"Mediana de {_c('popularity')} de los títulos de la selección, por formato, por año o por género según el gráfico. "
            "Se usa la mediana y no el promedio porque la distribución es asimétrica. El indicador global muestra la de cada formato.",
            "Indicador, Evolución",
        ),
        (
            "Popularidad relativa a su formato",
            f"Popularidad de cada título ÷ mediana de popularidad de SU formato en la selección ({theme.fmt_float(metrics.REFERENCIA_RELATIVA)} = igual "
            "a esa mediana). Por género y por país se resume con la mediana de esos valores. Sin ella, los géneros que existen en un solo formato "
            f"heredarían la diferencia entre formatos. Solo entran géneros y países con al menos {fmt(metrics.MIN_TITULOS_RELATIVA)} títulos.",
            "Géneros, Mercados, Resumen",
        ),
        (
            "Razón series / películas por año",
            f"Popularidad mediana de las series ÷ la de las películas en cada año. Los extremos son el primer y el último año COMPLETO "
            f"(se excluye el año parcial). Un formato «supera» al otro desde {theme.fmt_float(metrics.UMBRAL_DIFERENCIA_RELEVANTE)}×.",
            "Evolución, Resumen",
        ),
        (
            "Ventaja en valoración alta",
            f"% de títulos con valoración alta de las series − % de las películas, en puntos porcentuales, por año y sobre todos los títulos de "
            f"cada formato (la misma definición de la pestaña Valoración). A diferencia de {_c('popularity')}, no depende del índice relativo de TMDB.",
            "Evolución, Resumen",
        ),
        (
            "Valoración mediana",
            f"Mediana de {_c('vote_average')} por año y formato, solo con títulos de al menos {fmt(metrics.MIN_VOTOS_VALORACION)} votos.",
            "Evolución",
        ),
        (
            "Nivel de valoración",
            f"Según {_c('vote_average')}: baja {_c(f'[0, {metrics.UMBRAL_MEDIA})')}, media {_c(f'[{metrics.UMBRAL_MEDIA}, {metrics.UMBRAL_ALTA})')} "
            f"y alta {_c(f'[{metrics.UMBRAL_ALTA}, 10]')}. «Sin votos» agrupa los títulos con {_c('vote_count')} = 0 o {_c('vote_average')} = 0: "
            "es dato faltante, no un nivel de valoración.",
            "Valoración, Resumen",
        ),
        (
            "Catálogo bien evaluado",
            f"% de los títulos de la selección con {_c('vote_average')} ≥ {metrics.UMBRAL_ALTA} y al menos {fmt(metrics.MIN_VOTOS_BIEN_EVALUADO)} votos. "
            "El denominador incluye a los títulos sin votos suficientes, por eso es menor que la proporción de valoraciones altas de la pestaña Valoración.",
            "Indicador",
        ),
        (
            "Popularidad alta (P75)",
            f"Percentil 75 de {_c('popularity')} entre los títulos con al menos N votos (N = {fmt(metrics.MIN_VOTOS_MATRIZ_DEFECTO)} por defecto; "
            "se ajusta con el control de la Matriz).",
            "Matriz",
        ),
        (
            "Títulos en riesgo",
            f"Popularidad ≥ P75 y {_c('vote_average')} < {metrics.UMBRAL_RIESGO}. El indicador global siempre usa N = {fmt(metrics.MIN_VOTOS_MATRIZ_DEFECTO)}; "
            "la Matriz usa el N que elijas, así que ambas cifras coinciden solo con el valor por defecto.",
            "Indicador, Matriz",
        ),
        (
            "Activos a retener",
            f"Popularidad ≥ P75 y {_c('vote_average')} ≥ {metrics.UMBRAL_ALTA}.",
            "Matriz",
        ),
        (
            "Cuadrantes de género",
            f"Con los géneros más frecuentes (hasta {fmt(metrics.N_GENEROS_BURBUJAS)}): volumen = títulos del género y rendimiento = su popularidad relativa a su "
            f"formato. La mediana de títulos de los géneros graficados y {theme.fmt_float(metrics.REFERENCIA_RELATIVA)} dividen el plano en cuatro cuadrantes. "
            f"Un género a menos de {theme.fmt_pct(metrics.TOLERANCIA_MEDIANA)} de {theme.fmt_float(metrics.REFERENCIA_RELATIVA)} «rinde como su formato» y no "
            "se clasifica. El color indica en qué formato existe el género.",
            "Géneros",
        ),
        (
            "Concentración geográfica",
            f"% de los títulos con país registrado cuyo primer país listado es uno de los {metrics.N_MERCADOS_CONCENTRACION} primeros mercados (modo por defecto), "
            "o que incluyen al menos uno de ellos (modo «Coproducciones»).",
            "Mercados, Resumen",
        ),
        (
            "Mercados destino",
            f"Hasta 2 países con la mayor popularidad relativa (mayor que {theme.fmt_float(metrics.REFERENCIA_RELATIVA)}) entre los que tienen al menos "
            f"{fmt(metrics.MIN_TITULOS_RELATIVA)} títulos, sin contar los mercados que hoy concentran el catálogo.",
            "Mercados, Resumen",
        ),
    ]
    return _tabla(["Métrica", "Cómo se calcula", "Dónde aparece"], [(f"**{n}**", d, u) for n, d, u in filas])


def _criterios():
    filas = [
        ("Valoración alta / media / baja", f"≥ {metrics.UMBRAL_ALTA} / ≥ {metrics.UMBRAL_MEDIA} / < {metrics.UMBRAL_MEDIA}", "Nivel de valoración de cada título."),
        ("Valoración de riesgo", f"< {metrics.UMBRAL_RIESGO}", "Un título popular con valoración menor que este corte está en riesgo de abandono."),
        ("Franja neutra", f"{metrics.UMBRAL_RIESGO}–{metrics.UMBRAL_ALTA}", "No se clasifica en la Matriz. Se mantiene el corte de riesgo en "
         f"{metrics.UMBRAL_RIESGO} para que la Matriz y el indicador «Títulos en riesgo» cuenten lo mismo."),
        ("Votos mínimos", f"{fmt(metrics.MIN_VOTOS_MATRIZ_DEFECTO)} (ajustable)", f"Indicadores y Matriz. La valoración por año usa {fmt(metrics.MIN_VOTOS_VALORACION)} votos."),
        ("Popularidad alta", "≥ P75", "Percentil 75 entre los títulos con votos suficientes."),
        ("Diferencia relevante entre formatos",
         f"{theme.fmt_float(metrics.UMBRAL_DIFERENCIA_RELEVANTE)}× en popularidad; {theme.fmt_float(metrics.DIFERENCIA_VALORACION_RELEVANTE)} puntos en valoración",
         "Bajo esos valores los títulos hablan de resultados similares."),
        ("Cambio de una tendencia",
         f"{theme.fmt_pct(metrics.CAMBIO_RELATIVO_RAZON)} en la razón; {theme.fmt_float(metrics.CAMBIO_ESTABLE_PP, 0)} puntos en la ventaja de valoración alta; "
         f"{theme.fmt_float(metrics.CAMBIO_ESTABLE_VALORACION)} puntos en la brecha de valoración mediana",
         "Entre el primer y el último año completo: bajo esos valores la ventaja «se mantiene»."),
        ("Concentración geográfica", f"≥ {theme.fmt_pct(metrics.UMBRAL_CONCENTRACION)}", f"Los {metrics.N_MERCADOS_CONCENTRACION} primeros mercados juntos: desde este % se habla de diversificación limitada."),
        ("Banda de popularidad relativa", f"±{theme.fmt_pct(metrics.TOLERANCIA_MEDIANA)} de {theme.fmt_float(metrics.REFERENCIA_RELATIVA)}",
         "Géneros que rinden tan cerca de su formato que no se clasifican. No se ajusta para forzar un resultado: un cuadrante vacío es un hallazgo."),
        ("Títulos mínimos para popularidad relativa", f"{fmt(metrics.MIN_TITULOS_RELATIVA)}", "Géneros y países con menos títulos no entran a los rankings: una mediana sobre muy pocos títulos es ruido."),
        ("Cantidad de elementos", f"{fmt(metrics.N_GENEROS_BURBUJAS)} géneros, {fmt(metrics.N_PAISES_RANKING)} países, {fmt(metrics.N_TABLA_RIESGO)} títulos de riesgo",
         "Con más géneros las etiquetas del gráfico de burbujas se pisan."),
        ("Anotación de caída", f"≥ {theme.fmt_pct(metrics.CAIDA_MINIMA_ANOTAR)} en {metrics.ANIO_ANOTADO}",
         "La flecha del gráfico de evolución solo se dibuja si las series caen al menos este % respecto del año anterior."),
    ]
    return _tabla(["Criterio", "Valor", "Uso"], [(f"**{c}**", v, u) for c, v, u in filas])


def _limitaciones(pc, perfil, tendencia=None):
    """Las limitaciones completas, como lista de (título, cuerpo)."""
    items = []

    # 1) Reparto uniforme (solo se afirma si se cumple)
    n_p, n_s, n_t = pc["n_pelicula"], pc["n_serie"], pc["n_total"]
    if pc["uniforme"]:
        items.append((
            "Distribución uniforme por año y reparto exacto entre formatos.",
            f"El catálogo tiene {fmt(n_p)} películas y {fmt(n_s)} series ({theme.fmt_pct(n_p / n_t)} y {theme.fmt_pct(n_s / n_t)}) y cada "
            f"formato aporta exactamente {fmt(pc['filas_por_anio_formato'])} títulos por año entre {pc['anio_min']} y {pc['anio_max']}. "
            "Un reparto tan regular sugiere generación sintética y limita las conclusiones sobre tendencias de producción: por eso el "
            "dashboard no analiza cuántos títulos se estrenan por año, solo su popularidad y valoración.",
        ))
    else:
        items.append((
            "Reparto por año y formato.",
            f"El catálogo tiene {fmt(n_p)} películas y {fmt(n_s)} series, y la cantidad de títulos por año y formato no es uniforme: "
            "las comparaciones entre formatos y años deben leerse con esa diferencia de volumen en mente.",
        ))

    # 2) popularity
    items.append((
        f"{_c('popularity')} es un índice relativo de TMDB, sin unidad interpretable.",
        "Sirve para ordenar títulos, no para medir audiencia: no es comparable entre años ni interpretable en unidades absolutas. "
        "Por eso se resume con medianas y se compara entre grupos, no como valor absoluto.",
    ))

    # 3) Año parcial (datos comprobables: votos y popularidad)
    p = pc["parcial"]
    detalle = ""
    if p["pct_sin_votos"] is not None and p["pct_sin_votos_previos"] is not None:
        detalle = (
            f" Sus títulos aún no acumulan votos: {theme.fmt_pct(p['pct_sin_votos'])} no tiene votos, frente a "
            f"{theme.fmt_pct(p['pct_sin_votos_previos'])} de los años anteriores, y su popularidad mediana es "
            f"{theme.fmt_float(p['popularidad_mediana'])} contra {theme.fmt_float(p['popularidad_mediana_previos'])}."
        )
    items.append((
        f"{p['anio']} está incompleto.",
        f"Se marca como año parcial en los gráficos de evolución y en la tabla de títulos en riesgo.{detalle} Sus valores no deben leerse como una caída real de popularidad ni de valoración.",
    ))

    # 4) La ventaja de las series en popularidad se estrecha, y parte puede ser un artefacto (solo si los datos lo muestran)
    t = tendencia
    if t and t["lider"] and t["dir_razon"] == "baja":
        tramos = ""
        if t["lider"] == "Serie" and t["tramo_series"] and t["tramo_peliculas"]:
            ts, tp = t["tramo_series"], t["tramo_peliculas"]
            tramos = (
                f" El estrechamiento ocurre en dos tramos: en {ts['anio']} la mediana de las series cae {theme.fmt_pct(abs(ts['var']))} "
                f"(de {theme.fmt_float(ts['de'])} a {theme.fmt_float(ts['a'])}) y entre {tp['anio_ini']} y {tp['anio_fin']} la de las películas sube "
                f"de {theme.fmt_float(tp['de'])} a {theme.fmt_float(tp['a'])}."
            )
        artefacto = ""
        if t["lider"] == "Serie" and t["pelicula_fin"] > t["pelicula_ini"]:
            artefacto = (
                " Parte puede deberse a que el índice de TMDB favorece a los estrenos recientes de cine (mediana de películas "
                f"{t['anio_fin']}: {theme.fmt_float(t['pelicula_fin'])} vs {t['anio_ini']}: {theme.fmt_float(t['pelicula_ini'])}); los datos no permiten confirmarlo."
            )
        respaldo = ""
        if t["pp_fin"] > t["pp_ini"]:
            respaldo = (
                f" Por eso la prioridad de las series se sostiene además con la valoración alta, cuya ventaja pasó de {'+' if t['pp_ini'] >= 0 else ''}"
                f"{theme.fmt_float(t['pp_ini'], 0)} a {'+' if t['pp_fin'] >= 0 else ''}{theme.fmt_float(t['pp_fin'], 0)} puntos y no depende de ese índice."
            )
        items.append((
            f"La ventaja de las {'series' if t['lider'] == 'Serie' else 'películas'} en popularidad se estrecha.",
            f"En el catálogo completo, la razón entre formatos pasó de {theme.fmt_float(t['razon_ini'])}× ({t['anio_ini']}) a "
            f"{theme.fmt_float(t['razon_fin'])}× ({t['anio_fin']}), último año completo.{tramos}{artefacto}{respaldo}",
        ))

    # 5) Coproducciones
    items.append((
        "Las coproducciones se contabilizan en cada país participante.",
        f"{fmt(pc['n_multipais'])} títulos ({theme.fmt_pct(pc['n_multipais'] / n_t)}) listan más de un país. Con «Coproducciones» un "
        "título suma en todos sus países y los totales superan al catálogo; por defecto solo cuenta el primer país listado. "
        f"{fmt(pc['n_sin_pais'])} títulos no tienen país registrado y quedan fuera de esos gráficos.",
    ))

    # 6) Multi-género
    items.append((
        "Los títulos multi-género se contabilizan en cada categoría.",
        f"{fmt(pc['n_multigenero'])} títulos ({theme.fmt_pct(pc['n_multigenero'] / n_t)}) tienen más de un género, por lo que las cantidades por género "
        f"suman más que el catálogo y sus porcentajes, más de 100%. {fmt(pc['n_sin_genero'])} títulos no tienen género registrado.",
    ))

    # 7) rating (solo se afirma si es numérico)
    if perfil["rating_numerico"]:
        igual = f" y coincide con {_c('vote_average')} en ambos archivos" if perfil["rating_igual_vote_average"] else ""
        items.append((
            f"La columna {_c('rating')} no es una clasificación etaria.",
            f"Contiene valores numéricos entre {theme.fmt_float(perfil['rating_min'], 0)} y {theme.fmt_float(perfil['rating_max'], 0)}{igual}, "
            "así que no permite analizar la audiencia por edad y se descartó del análisis.",
        ))
    else:
        items.append((
            f"La columna {_c('rating')} no se usa.",
            "Su contenido no es numérico y no está documentado su significado, por lo que se descartó del análisis.",
        ))

    # 8) Taxonomías de género distintas por formato: se controlan con la popularidad relativa
    if pc["generos_un_formato"]:
        ejemplos = unir_es(f"«{g}»" for g in pc["generos_un_formato"][:3])
        items.append((
            "Los géneros de películas y series no coinciden del todo.",
            f"{fmt(len(pc['generos_un_formato']))} de los {fmt(pc['n_generos'])} géneros existen en un solo formato (por ejemplo {ejemplos}), "
            "porque el origen usa categorías distintas para cada uno. Las comparaciones entre géneros y entre mercados se controlan por formato "
            "mediante la popularidad relativa: cada título se divide por la mediana de su formato antes de resumirse. Aun así, un género que existe "
            "en un solo formato solo se compara con los títulos de ese formato.",
        ))

    # 9) Umbrales propios
    items.append((
        "Los umbrales son criterios de este análisis.",
        "Los cortes de valoración, votos mínimos, percentil, bandas y mínimo de títulos (ver «Criterios de corte») están definidos para este dashboard y no "
        "vienen del origen de datos: otro criterio cambiaría qué títulos se consideran en riesgo o bien evaluados. El control de votos mínimos de la Matriz "
        "permite explorar ese efecto.",
    ))
    return items


def _limitaciones_clave(pc, perfil):
    """Una línea por limitación, para el popover: datos sintéticos, índice relativo de TMDB, año parcial, taxonomías de género distintas
    por formato y umbrales propios. Las que afirman una propiedad de los datos se comprueban y tienen rama alternativa."""
    p = pc["parcial"]
    lineas = []
    if pc["uniforme"]:
        lineas.append(
            f"Los datos parecen sintéticos: cada formato aporta exactamente {fmt(pc['filas_por_anio_formato'])} títulos por año, "
            "así que no se analiza cuántos títulos se estrenan por año."
        )
    else:
        lineas.append("El reparto de títulos por año y formato no es uniforme: las comparaciones de volumen deben leerse con esa diferencia en mente.")
    lineas.append("La popularidad es un índice relativo de TMDB: sirve para ordenar y comparar grupos, no para medir audiencia ni para comparar años.")
    if p["pct_sin_votos"] is not None and p["pct_sin_votos_previos"] is not None:
        lineas.append(
            f"{p['anio']} está incompleto: el {theme.fmt_pct(p['pct_sin_votos'])} de sus títulos aún no tiene votos (contra "
            f"{theme.fmt_pct(p['pct_sin_votos_previos'])} en los años anteriores); se marca como parcial y no entra en las tendencias."
        )
    else:
        lineas.append(f"{p['anio']} está incompleto: se marca como parcial y no entra en las tendencias.")
    if pc["generos_un_formato"]:
        lineas.append(
            f"{fmt(len(pc['generos_un_formato']))} de los {fmt(pc['n_generos'])} géneros existen en un solo formato (el origen usa categorías distintas "
            "para películas y series): por eso géneros y mercados se comparan con la popularidad relativa a su formato."
        )
    lineas.append("Los umbrales (cortes de valoración, votos mínimos, mínimo de títulos por género y país) son criterios de este análisis, no vienen de los datos.")
    return lineas


# ----------------- Salidas -----------------
def popover_html(anio_parcial):
    """HTML del popover «ⓘ Sobre los datos». Solo clases y tamaños de theme.py; sin tablas ni nombres de columnas."""
    pc = _perfil_catalogo(anio_parcial)
    perfil = data_loader.perfil_fuente()
    esencial = "".join(f"<li><b>{escape(t)}</b> {escape(d)}</li>" for t, d in _esencial_items(pc))
    claves = "".join(f"<li>{escape(x)}</li>" for x in _limitaciones_clave(pc, perfil))
    return (
        '<div class="sobre">'
        f'<div class="seccion-etiqueta">Lo esencial</div><ol class="meto-lista">{esencial}</ol>'
        f'<div class="seccion-etiqueta">Limitaciones clave</div><ul class="meto-lista">{claves}</ul>'
        f'<div class="sobre-cierre">{escape(LINEA_FINAL)}</div>'
        "</div>"
    )


def documento_markdown(anio_parcial):
    """El texto completo de metodología y limitaciones en Markdown (docs/metodologia.md): lo esencial, fuente de datos, métricas
    derivadas, criterios de corte y limitaciones. Determinista: el mismo catálogo da siempre el mismo texto."""
    pc = _perfil_catalogo(anio_parcial)
    perfil = data_loader.perfil_fuente()
    partes = [
        "<!-- Documento generado por `python -m src.metodologia` a partir de src/metodologia.py y src/metrics.py. No se edita a mano: se regenera. -->",
        "# Metodología y limitaciones",
        "Cómo se calculó cada cifra del dashboard y qué no permite concluir. Describe el catálogo completo, no una selección de filtros. "
        f"En el dashboard solo se muestra un resumen (botón «{ETIQUETA_POPOVER}»); este documento es el texto completo.",
        "## Lo esencial",
        _lista_numerada(_esencial_items(pc, " (detalle en «Fuente de datos»)")),
        "## Fuente de datos",
        *_fuente(pc, perfil),
        "## Métricas derivadas",
        _metricas(),
        "## Criterios de corte",
        _criterios(),
        "## Limitaciones",
        _lista_numerada(_limitaciones(pc, perfil, _tendencia_catalogo(anio_parcial))),
    ]
    return "\n\n".join(partes) + "\n"


def escribir_documento(anio_parcial, ruta=RUTA_DOCUMENTO):
    """Escribe el documento completo en `ruta` (docs/metodologia.md por defecto) y devuelve la ruta."""
    ruta = Path(ruta)
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text(documento_markdown(anio_parcial), encoding="utf-8", newline="\n")
    return ruta


if __name__ == "__main__":
    df, _, _ = data_loader.load_data()
    destino = escribir_documento(int(df["release_year"].max()))
    print(f"{destino.relative_to(RUTA_DOCUMENTO.parent.parent)}  ({destino.stat().st_size / 1024:,.0f} KB)")
