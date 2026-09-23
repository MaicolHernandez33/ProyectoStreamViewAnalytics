"""
Texto del dashboard: título-mensaje + subtítulo de cada gráfico, el panel de hallazgo de cada pestaña analítica, «Cómo
leer este gráfico» y el contenido del Resumen. Ninguna cifra vive escrita aquí — todas vienen de src/metrics.py a partir
del dataframe filtrado que reciba cada función.

Cada `titulo_X(df, ...)` devuelve (titulo, subtitulo): el título enuncia la conclusión que hoy sostienen los datos
filtrados, así que cambia solo si la conclusión misma deja de ser cierta. Regla de redacción: el subtítulo describe QUÉ
se está mirando; «Cómo leer este gráfico» explica CÓMO se calculó, en ítems cortos — nunca se repiten. Toda enumeración
de elementos pasa por `unir_es`.
"""
import re
from html import escape

import streamlit as st

from src import metrics, theme


def unir_es(elementos):
    """['A', 'B', 'C'] -> 'A, B y C'; dos -> 'A y B'; uno -> 'A'; ninguno -> ''. Ante una palabra que empieza con «i» o
    «hi» (India, Italia, Historia) la conjunción es «e», como pide el español. Único helper de enumeraciones del proyecto."""
    items = [str(x) for x in elementos]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    ultimo = re.sub(r"<[^>]+>", "", items[-1]).lstrip("«\"' ").lower()
    conjuncion = "e" if ultimo.startswith("i") or (ultimo.startswith("hi") and not ultimo.startswith("hie")) else "y"
    return f"{', '.join(items[:-1])} {conjuncion} {items[-1]}"


def _nombre(nombre):
    """Entrecomilla un nombre que contiene «y» («Acción y aventura», «Bosnia y Herzegovina») para que en una enumeración no se
    confunda esa «y» con la conjunción: «Telenovela y «Acción y aventura»»."""
    return f"«{nombre}»" if " y " in str(nombre) else str(nombre)


def _nombres(serie):
    return unir_es(_nombre(x) for x in serie)


MAX_GENEROS_POR_GRUPO = 3  # una recomendación con más nombres deja de leerse: se nombran los de mayor popularidad relativa


def _x(razon):
    """1.46 -> '1,46×' (dos decimales cuando es una popularidad relativa; una razón entre formatos usa un decimal)."""
    return f"{theme.fmt_float(razon, 2)}×"


def _r(razon):
    return f"{theme.fmt_float(razon)}×"


def _pts(x):
    """23.2 -> '+23' (puntos porcentuales con signo, sin decimales)."""
    return f"{'+' if x >= 0 else '-'}{theme.fmt_float(abs(x), 0)}"


def _plural_formato(formato):
    return "series" if formato == "Serie" else "películas"


def _otro_formato(formato):
    return "películas" if formato == "Serie" else "series"


# ----------------- Renderizado compartido -----------------
def render_titulo(titulo, subtitulo):
    """Las dos líneas que van encima de cada gráfico analítico."""
    st.markdown(
        f'<div class="grafico-titulo">{escape(titulo)}</div>'
        f'<div class="grafico-subtitulo">{escape(subtitulo)}</div>',
        unsafe_allow_html=True,
    )


def render_panel(numero, hallazgo, recomendacion, clave):
    """Los cuatro elementos del panel lateral de cada pestaña analítica, en este orden: número (el único elemento de 32px
    de la página), hallazgo, línea, y la recomendación bajo su propia etiqueta «Recomendación» — para que se lea como una
    instrucción, no como un dato más entre otros."""
    with st.container(key=f"panel_{clave}"):
        st.markdown(f'<div class="panel-num">{escape(numero)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="panel-desc">{escape(hallazgo)}</div><div class="panel-sep"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="panel-etiqueta">Recomendación</div><div class="panel-txt">{escape(recomendacion)}</div>',
            unsafe_allow_html=True,
        )


def render_como_leer(items, expandible):
    """«Cómo leer este gráfico»: reemplaza las notas al pie largas. `items` es una lista de ítems cortos (una idea cada
    uno); con `expandible=False` es un recuadro fijo sin fondo, solo borde (Géneros, Evolución, Valoración); con
    `expandible=True` el mismo contenido va en un st.expander cerrado (Mercados, Matriz) — mismo componente, otro envoltorio."""
    lista = f'<ul class="como-leer-lista">{"".join(f"<li>{escape(i)}</li>" for i in items)}</ul>'
    if expandible:
        with st.expander("Cómo leer este gráfico", expanded=False):
            st.markdown(lista, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="como-leer"><div class="como-leer-titulo">Cómo leer este gráfico</div>{lista}</div>', unsafe_allow_html=True)


def leyenda_html(presentes):
    """Leyenda HTML genérica Película/Serie (reemplaza la leyenda nativa de Plotly): solo los formatos presentes en la
    selección, en el orden FORMATOS. Va en la cabecera de la tarjeta del gráfico, no sobre el trazado."""
    items = "".join(
        f'<span class="leyenda-item"><span class="dot" style="background:{theme.COLOR_FORMATO[f]}"></span>{f}</span>'
        for f in ("Película", "Serie") if f in presentes
    )
    return f'<div class="leyenda">{items}</div>'


def leyenda_generos_html(origenes_presentes):
    """Leyenda de las burbujas de Géneros: relleno rojo/gris para «solo en un formato», anillo vacío para «en ambos»."""
    partes = []
    for clave, nombre, color in (("Película", "Solo en películas", theme.PELICULA), ("Serie", "Solo en series", theme.SERIE)):
        if clave in origenes_presentes:
            partes.append(f'<span class="leyenda-item"><span class="dot" style="background:{color}"></span>{nombre}</span>')
    if None in origenes_presentes:
        partes.append('<span class="leyenda-item"><span class="leyenda-anillo"></span>En ambos formatos</span>')
    return f'<div class="leyenda">{"".join(partes)}</div>'


def leyenda_niveles_valoracion_html():
    """Leyenda de Valoración: NIVELES (Alta/Media/Baja/Sin votos), no Película/Serie — las dos filas del gráfico ya dicen
    su formato con el rótulo del eje Y (el punto de color); lo que la leyenda tiene que explicar ahí es qué significa la
    opacidad. Muestra neutra (NEUTRO) en las tres opacidades reales de theme.OPACIDAD_NIVEL, más el tramado de «Sin votos»,
    con el mismo rango de cada nivel que usa metrics.clasificar_valoracion."""
    niveles = (
        (metrics.NIVEL_ALTA, theme.OPACIDAD_NIVEL["alta"]), (metrics.NIVEL_MEDIA, theme.OPACIDAD_NIVEL["media"]),
        (metrics.NIVEL_BAJA, theme.OPACIDAD_NIVEL["baja"]),
    )
    items = "".join(
        f'<span class="leyenda-item"><span class="leyenda-nivel" style="background:{theme.rgba(theme.NEUTRO, op)}"></span>{nivel}</span>'
        for nivel, op in niveles
    )
    items += '<span class="leyenda-item"><span class="leyenda-nivel leyenda-nivel--sinvotos"></span>Sin votos</span>'
    return f'<div class="leyenda">{items}</div>'


# ----------------- Evolución -----------------
def _valoracion_mediana_por_formato(df):
    con_votos = df[df["vote_count"] >= metrics.MIN_VOTOS_VALORACION]
    return con_votos.groupby("type")["vote_average"].median()


def _titulo_evolucion_valoracion(df, anio_parcial):
    t = metrics.tendencia_valoracion_mediana(df, anio_parcial)
    if t is None:  # sin dos años completos con ambos formatos: comparación global de la selección
        med = _valoracion_mediana_por_formato(df)
        if not {"Película", "Serie"} <= set(med.index):
            return "Evolución de la valoración del catálogo"
        dif = med["Serie"] - med["Película"]
        if dif >= metrics.DIFERENCIA_VALORACION_RELEVANTE:
            return f"Las series superan a las películas en valoración mediana ({theme.fmt_float(med['Serie'])} vs {theme.fmt_float(med['Película'])})"
        if dif <= -metrics.DIFERENCIA_VALORACION_RELEVANTE:
            return f"Las películas superan a las series en valoración mediana ({theme.fmt_float(med['Película'])} vs {theme.fmt_float(med['Serie'])})"
        return "Series y películas tienen una valoración mediana similar"
    ini, fin = theme.fmt_float(t["brecha_ini"]), theme.fmt_float(t["brecha_fin"])
    if t["lider"] is None:
        return (f"Ningún formato lidera todos los años en valoración mediana: la brecha Serie−Película pasó de "
                f"{'+' if t['brecha_ini'] >= 0 else ''}{ini} a {'+' if t['brecha_fin'] >= 0 else ''}{fin} puntos")
    base = f"Las {_plural_formato(t['lider'])} superan a las {_otro_formato(t['lider'])} en valoración mediana todos los años"
    if t["direccion"] == "sube":
        return f"{base}, y la ventaja creció de {ini} a {fin} puntos ({t['anio_ini']}–{t['anio_fin']})"
    if t["direccion"] == "baja":
        return f"{base}, aunque la ventaja bajó de {ini} a {fin} puntos ({t['anio_ini']}–{t['anio_fin']})"
    return f"{base}, y la ventaja se mantiene: {ini} puntos en {t['anio_ini']} y {fin} en {t['anio_fin']}"


def _titulo_evolucion_popularidad(df, anio_parcial):
    t = metrics.tendencia_formatos(df, anio_parcial)
    if t is None:  # sin dos años completos con ambos formatos: razón global de la selección
        razon, _, _ = metrics.razon_popularidad_series_peliculas(df)
        if razon is None:
            return "Evolución de la popularidad del catálogo"
        if razon >= metrics.UMBRAL_DIFERENCIA_RELEVANTE:
            return f"Las series superan {_r(razon)} en popularidad a las películas"
        if razon <= 1 / metrics.UMBRAL_DIFERENCIA_RELEVANTE:
            return f"Las películas superan {_r(1 / razon)} en popularidad a las series"
        return "Series y películas tienen una popularidad similar"
    ini, fin = t["anio_ini"], t["anio_fin"]
    if t["lider"] is None:
        return f"Ningún formato lidera en popularidad todos los años: la razón Serie/Película pasó de {_r(t['razon_ini'])} ({ini}) a {_r(t['razon_fin'])} ({fin})"
    base = f"Las {_plural_formato(t['lider'])} superan a las {_otro_formato(t['lider'])} todos los años"
    if t["dir_razon"] == "estable":
        return f"{base}, con una ventaja estable: {_r(t['razon_ini'])} en {ini} y {_r(t['razon_fin'])} en {fin}"
    verbo, conector = ("bajó", "pero") if t["dir_razon"] == "baja" else ("subió", "y")
    return f"{base}, {conector} la ventaja {verbo} de {_r(t['razon_ini'])} ({ini}) a {_r(t['razon_fin'])} ({fin})"


def titulo_evolucion(df, metrica_label, anio_parcial):
    anios = f"{int(df['release_year'].min())}-{int(df['release_year'].max())}"
    subtitulo = f"{metrica_label} por año de lanzamiento, {anios}"
    if "aloración" in metrica_label:
        return _titulo_evolucion_valoracion(df, anio_parcial), subtitulo
    return _titulo_evolucion_popularidad(df, anio_parcial), subtitulo


def _recomendacion_tendencia(plural, direccion, que):
    """Frase de recomendación genérica según la dirección de una tendencia (`que` describe qué asciende/baja/se mantiene,
    p. ej. 'en popularidad' o 'en valoración mediana'). Usada por panel_evolucion con la métrica que está en pantalla."""
    if direccion == "sube":
        return f"Sostener la prioridad en {plural}: su ventaja {que} crece."
    if direccion == "estable":
        return f"Sostener la prioridad en {plural}: su ventaja {que} se mantiene."
    return f"Sostener la prioridad en {plural}, pero revisarla cada ciclo: su ventaja {que} se achica."


def panel_evolucion(df, metrica_label, anio_parcial):
    """El número del panel refleja la métrica QUE ESTÁ EN PANTALLA (razón × con Popularidad, brecha en puntos con
    Valoración), para que el panel y el gráfico cuenten lo mismo de un vistazo."""
    if "aloración" in metrica_label:
        t = metrics.tendencia_valoracion_mediana(df, anio_parcial)
        if t is None or t["lider"] is None:
            return (
                "—", "ningún formato lidera en valoración mediana todos los años en la selección.",
                "Ampliar el rango de años para ver si aparece una tendencia clara.",
            )
        plural = _plural_formato(t["lider"])
        numero = f"+{theme.fmt_float(t['brecha_fin'])}" if t["brecha_fin"] >= 0 else theme.fmt_float(t["brecha_fin"])
        hallazgo = (
            f"fue la brecha de valoración mediana de las {plural} en {t['anio_fin']}; en {t['anio_ini']} era "
            f"{'+' if t['brecha_ini'] >= 0 else ''}{theme.fmt_float(t['brecha_ini'])}."
        )
        return numero, hallazgo, _recomendacion_tendencia(plural, t["direccion"], "en valoración mediana")

    t = metrics.tendencia_formatos(df, anio_parcial)
    if t is None:
        razon, _, _ = metrics.razon_popularidad_series_peliculas(df)
        if razon is None:
            return "—", "no hay títulos de ambos formatos en la selección actual para comparar.", "Ampliar el filtro de formato a 'Ambos' para poder comparar series y películas."
        lider = "Serie" if razon >= 1 else "Película"
        return (
            _r(razon if lider == "Serie" else 1 / razon),
            f"es la ventaja en popularidad de las {_plural_formato(lider)} en la selección.",
            f"Ampliar el rango de años para ver cómo evoluciona la ventaja de las {_plural_formato(lider)}.",
        )
    if t["lider"] is None:
        return (
            _r(t["razon_fin"]),
            f"fue la razón Serie/Película en {t['anio_fin']}; en {t['anio_ini']} era {_r(t['razon_ini'])}.",
            "Revisar la prioridad entre formatos: ninguno lidera en popularidad todos los años.",
        )
    plural = _plural_formato(t["lider"])
    hallazgo = f"fue la ventaja de las {plural} en {t['anio_fin']}; en {t['anio_ini']} era {_r(t['razon_ini'])}."
    return _r(t["razon_fin"]), hallazgo, _recomendacion_tendencia(plural, t["dir_razon"], "en popularidad")


def como_leer_evolucion(df, metrica_label, anio_parcial):
    """«Cómo leer este gráfico» de Evolución: ítems cortos (mismos hechos que antes daba la nota al pie, uno por línea).
    Con Valoración: solo método y qué mide el panel. Con Popularidad: qué explica la tendencia (cada cifra calculada)."""
    mediana = "Se usa la mediana, no el promedio, porque la distribución es asimétrica."
    if "aloración" in metrica_label:
        return [
            f"Solo entran títulos con al menos {metrics.MIN_VOTOS_VALORACION} votos.",
            f"El número del panel es la diferencia, en puntos porcentuales, entre el % de valoración alta ({metrics.UMBRAL_ALTA} o más) de series y películas.",
            mediana,
        ]
    items = ["El índice de popularidad favorece a los estrenos recientes: no es comparable entre años."]
    t = metrics.tendencia_formatos(df, anio_parcial)
    if t is None:
        return [*items, mediana]
    ts, tp = t["tramo_series"], t["tramo_peliculas"]
    if ts:
        tramo = (
            f"La caída de {ts['anio']} viene de las series ({theme.fmt_pct(ts['var'])}); desde ahí, el alza es de las películas"
        )
        if tp:
            tramo += f" ({theme.fmt_float(tp['de'])} a {theme.fmt_float(tp['a'])})"
        items.insert(0, tramo + ".")
    else:
        items.insert(0, (
            f"En {t['anio_fin']} la mediana de las series es {theme.fmt_float(t['serie_fin'])} y la de las películas {theme.fmt_float(t['pelicula_fin'])} "
            f"({t['anio_ini']}: {theme.fmt_float(t['serie_ini'])} y {theme.fmt_float(t['pelicula_ini'])})."
        ))
    if t["anios_alza_razon"]:
        items.append(f"La razón no baja todos los años: sube en {unir_es(a['anio'] for a in t['anios_alza_razon'])}.")
    parcial = t["parcial"]
    if parcial and t["lider"] and parcial["razon"] > (t["razon_fin"] if t["lider"] == "Serie" else 1 / t["razon_fin"]):
        items.append(f"El {_r(parcial['razon'])} de {parcial['anio']} (parcial) no es una recuperación: sus títulos aún no acumulan votos.")
    items.append(mediana)
    return items


# ----------------- Composición del catálogo (géneros) -----------------
def _contexto_generos(df):
    """(resumen con cuadrante, mediana de títulos, referencia 1,0) de los géneros graficados, o None si hay muy pocos géneros
    distintos para que los cuadrantes signifiquen algo."""
    resumen = metrics.resumen_generos(df)
    if len(resumen) < metrics.MIN_GENEROS_BURBUJAS:
        return None
    return metrics.cuadrantes_generos(resumen)


def _rinden_sobre(cuad):
    """Géneros que rinden sobre su formato (por encima de la banda de ±10% de 1,0), de mayor a menor popularidad relativa."""
    return cuad[cuad["cuadrante"].isin([metrics.CUAD_MOTORES, metrics.CUAD_NICHO])].sort_values("pop_relativa", ascending=False)


def _grupos_por_formato(generos, referencia):
    """Divide `generos` en (solo películas, solo series, ambos) según los títulos de cada formato en la selección. Si la selección
    completa (`referencia`, todos los géneros graficados) tiene un solo formato, separar por formato no tiene sentido: None."""
    if referencia["Película"].sum() == 0 or referencia["Serie"].sum() == 0:
        return None
    return (
        generos[generos["Serie"] == 0], generos[generos["Película"] == 0],
        generos[(generos["Serie"] > 0) & (generos["Película"] > 0)],
    )


def titulo_generos(df):
    gl = metrics.genero_lider(df)
    ctx = _contexto_generos(df)
    if gl is None:
        return "Composición del catálogo por género", "Géneros del catálogo por cantidad de títulos"
    if ctx is None:
        return f"{gl['genero']} concentra el {theme.fmt_pct(gl['pct'])} del catálogo filtrado", "Géneros del catálogo por cantidad de títulos"
    cuad = ctx[0]
    n, arriba = len(cuad), len(_rinden_sobre(cuad))
    sobre = int((cuad["cuadrante"] == metrics.CUAD_SOBREOFERTADO).sum())
    # Subtítulo = guía de lectura de los dos ejes (no una descripción técnica): con eso alcanza para leer el gráfico
    # sin abrir «Cómo leer este gráfico». Solo aplica cuando el gráfico se dibuja (con ctx None no hay ejes que leer).
    subtitulo = "Más a la derecha, más títulos. Más arriba, mejor rendimiento frente a su formato."
    rinden = f"{arriba} de {n} {'rinde' if arriba == 1 else 'rinden'} sobre su formato"
    if sobre == 0:
        # Que el cuadrante "sobreofertado" quede vacío es un hallazgo, no algo que corregir moviendo el criterio.
        return "Ningún género está sobreofertado" + (f"; {rinden}" if arriba else " ni rinde sobre su formato"), subtitulo
    return f"{sobre} de {n} géneros {'está sobreofertado' if sobre == 1 else 'están sobreofertados'}" + (f"; {rinden}" if arriba else ""), subtitulo


def panel_generos(df):
    ctx = _contexto_generos(df)
    gl = metrics.genero_lider(df)
    if gl is None:
        return "—", "los títulos filtrados no tienen género registrado.", "Registrar el género de los títulos sin categorizar para poder analizarlos."
    if ctx is None:
        return (
            theme.fmt_pct(gl["pct"]),
            f"del catálogo filtrado es «{gl['genero']}»; hay muy pocos géneros distintos para compararlos.",
            "Quitar el filtro de género para comparar más categorías del catálogo.",
        )
    cuad = ctx[0]
    arriba = _rinden_sobre(cuad)
    n, k = len(cuad), len(arriba)
    sobre = cuad[cuad["cuadrante"] == metrics.CUAD_SOBREOFERTADO].sort_values("pop_relativa")
    marginal = cuad[cuad["cuadrante"] == metrics.CUAD_MARGINAL].sort_values("pop_relativa")
    hallazgo = (
        f"{'género rinde' if k == 1 else 'géneros rinden'} más de {theme.fmt_pct(metrics.TOLERANCIA_MEDIANA)} sobre la mediana de su formato, y "
        + ("ninguno con mucho volumen rinde bajo ella." if sobre.empty else f"{len(sobre)} con mucho volumen {'rinde' if len(sobre) == 1 else 'rinden'} bajo ella.")
    )
    partes = []
    if k:
        grupos = _grupos_por_formato(arriba, cuad)
        if grupos is None:
            partes.append(f"Priorizar {_nombres(arriba['genero'].head(MAX_GENEROS_POR_GRUPO))} en las próximas licencias")
        else:
            solo_pel, solo_ser, ambos = (g.head(MAX_GENEROS_POR_GRUPO) for g in grupos)
            destinos = []
            if len(solo_pel):
                destinos.append(f"{_nombres(solo_pel['genero'])} cuando se licencien películas")
            if len(solo_ser):
                destinos.append(f"{_nombres(solo_ser['genero'])} cuando se licencien series")
            if destinos:
                partes.append("Priorizar " + unir_es(destinos))
                if len(ambos):
                    partes.append(f"{_nombres(ambos['genero'])} {'rinde' if len(ambos) == 1 else 'rinden'} sobre su formato en ambos")
            else:
                partes.append(f"Priorizar {_nombres(ambos['genero'])} en las próximas licencias: rinden sobre su formato en películas y en series")
    else:
        partes.append("Sostener el reparto actual de licencias por género: ninguno rinde claramente sobre su formato")
    recomendacion = "; ".join(partes) + "."
    # "Frenar" solo para géneros que rinden BAJO su formato (relativa <= 0,90) y además tienen mucho volumen; nunca uno con relativa > 1.
    if not sobre.empty:
        recomendacion += f" Frenar nuevas licencias en {unir_es(f'{_nombre(g)} ({_x(r)})' for g, r in zip(sobre['genero'], sobre['pop_relativa']))}."
    if not marginal.empty:
        recomendacion += f" Revisar {unir_es(f'{_nombre(g)} ({_x(r)})' for g, r in zip(marginal['genero'], marginal['pop_relativa']))}."
    return f"{k} de {n}", hallazgo, recomendacion


def como_leer_generos(cuad_o_resumen):
    """«Cómo leer este gráfico» de Géneros: ítems cortos, uno por idea (mismos hechos que antes daba la nota al pie)."""
    n = len(cuad_o_resumen)
    exclusivos = int(((cuad_o_resumen["Película"] == 0) | (cuad_o_resumen["Serie"] == 0)).sum())
    ref = theme.fmt_float(metrics.REFERENCIA_RELATIVA)
    items = [
        f"Cada círculo es un género con al menos {metrics.MIN_TITULOS_RELATIVA} títulos.",
        f"Rendimiento: popularidad de cada título dividida por la mediana de popularidad de su formato ({ref} = igual a esa mediana), resumida por género con la mediana de esos valores.",
        f"Banda gris: a menos de {theme.fmt_pct(metrics.TOLERANCIA_MEDIANA)} de {ref}, un género no se clasifica sobre ni bajo su formato.",
        "Un título puede pertenecer a varios géneros, por lo que los totales suman más de 100%.",
    ]
    if exclusivos:
        items.append(f"{exclusivos} de los {n} géneros existen en un solo formato: las categorías de películas y series del origen no coinciden del todo.")
    return items


# ----------------- Mercados de origen (países) -----------------
def titulo_paises(df, modo):
    # El subtítulo incorpora "Analizando N títulos con país registrado": es el único lugar del dashboard donde el
    # denominador del gráfico no coincide con el KPI global de títulos analizados, así que tiene que decirse junto al
    # resto de lo que describe el gráfico (antes era una línea aparte, encima de la tarjeta).
    subtitulo = f"Top {metrics.N_PAISES_RANKING} países por cantidad de títulos, por formato. {texto_paises_registrados(df, modo)}."
    pl = metrics.pais_lider(df, modo=modo)
    if pl is None:
        return "Mercados de origen del catálogo", subtitulo
    verbo = "produce" if modo == metrics.MODO_PRIMER_PAIS else "participa en"
    titulo = f"{pl['pais']} {verbo} el {theme.fmt_pct(pl['pct_lider'])} de los títulos con país registrado"
    if pl["pct_top"] >= metrics.UMBRAL_CONCENTRACION:
        titulo += "; diversificación limitada"
    return titulo, subtitulo


def panel_paises(df, modo):
    pl = metrics.pais_lider(df, modo=modo)
    if pl is None:
        return "—", "los títulos filtrados no tienen país registrado.", "Registrar el país de origen de los títulos sin datos para poder priorizar mercados."
    # Indicador de concentración pedido: el número grande + esta frase, que continúa desde él sin repetirlo.
    if modo == metrics.MODO_PRIMER_PAIS:
        hallazgo = f"de los títulos con país registrado está en {_nombres(pl['top'])}."
    else:
        hallazgo = f"de los títulos con país registrado incluye al menos uno de {_nombres(pl['top'])}."
    destinos = metrics.destinos_mercados(df, modo)
    if destinos:
        # Solo destinos (sin recortar nada): un mercado con relativa > 1 no se recomienda reducir.
        recomendacion = (
            f"Sumar licencias de {_nombres(d['pais'] for d in destinos)} ({unir_es(_x(d['pop_relativa']) for d in destinos)} la mediana de su formato) "
            f"para diversificar el {theme.fmt_pct(pl['pct_top'])} que hoy concentran {_nombres(pl['top'])}."
        )
    else:
        recomendacion = (
            f"Revisar la concentración en {_nombres(pl['top'])}: ningún otro mercado con al menos {metrics.MIN_TITULOS_RELATIVA} títulos "
            "rinde sobre su formato."
        )
    return theme.fmt_pct(pl["pct_top"]), hallazgo, recomendacion


def mejor_rendimiento_html(df, modo):
    """Lista «Mejor rendimiento frente a su formato» (columna derecha de Mercados, entre el panel y «Cómo leer este
    gráfico»): los N países de mayor popularidad relativa entre los que tienen al menos MIN_TITULOS_RELATIVA títulos. La
    recomendación de panel_paises nombra mercados destino que el gráfico principal (top por CANTIDAD) no siempre muestra;
    esta lista los hace visibles, junto con su cantidad de títulos."""
    top = metrics.popularidad_relativa_paises(df, modo).head(metrics.N_MEJOR_RENDIMIENTO_PAISES)
    if top.empty:
        return ""
    filas = "".join(
        f'<div class="mercado-fila"><span class="mercado-pais">{escape(f.pais)}</span>'
        f'<span class="mercado-titulos">{theme.fmt_int(f.titulos)} títulos</span>'
        f'<span class="mercado-relativa">{_x(f.pop_relativa)}</span></div>'
        for f in top.itertuples()
    )
    return (
        '<div class="mercado-lista"><div class="mercado-lista-titulo">Mejor rendimiento frente a su formato</div>'
        f'<div class="mercado-lista-subtitulo">Países con {theme.fmt_int(metrics.MIN_TITULOS_RELATIVA)} títulos o más</div>{filas}</div>'
    )


def como_leer_paises(df, modo):
    """«Cómo leer este gráfico» de Mercados: qué modo de conteo está activo y qué es la popularidad relativa del tooltip."""
    pl = metrics.pais_lider(df, modo=modo)
    if pl is None:
        return []
    conteo = (
        "Cada título se cuenta una sola vez, en el primer país listado." if modo == metrics.MODO_PRIMER_PAIS
        else "Las coproducciones se cuentan en cada país participante, por lo que los totales suman más que el catálogo."
    )
    return [
        conteo,
        f"Porcentajes sobre los {theme.fmt_int(pl['n_con_pais'])} títulos con país registrado; {theme.fmt_int(pl['n_sin_pais'])} no tienen país.",
        "El tooltip muestra la popularidad relativa del país: la mediana de sus títulos, cada uno dividido por la mediana de su formato.",
        f"Las recomendaciones solo consideran países con al menos {metrics.MIN_TITULOS_RELATIVA} títulos.",
    ]


def texto_paises_registrados(df, modo):
    """Línea sobre el denominador propio de la pestaña Mercados (no coincide con el KPI global de títulos analizados)."""
    pl = metrics.pais_lider(df, modo=modo)
    if pl is None:
        return "Ningún título de la selección tiene país registrado"
    return f"Analizando {theme.fmt_int(pl['n_con_pais'])} títulos con país registrado, de {theme.fmt_int(len(df))} en la selección"


# ----------------- Valoración por formato -----------------
def _en_prosa(fraccion):
    """0.50 -> 'la mitad' ; 0.26 -> 'un cuarto' (aprox.) ; 0.41 -> '41%' (sin fracción común cerca: se usa el porcentaje)."""
    return theme.fmt_fraccion(fraccion) or theme.fmt_pct(fraccion)


def titulo_valoracion(df):
    """Título en prosa (fracciones: «la mitad», «un cuarto»…) en vez de dos porcentajes exactos — más fácil de leer de un
    vistazo; sigue siendo verdadero porque la fracción que se nombra es la que está a menos de 3 pp de la cifra real (ver
    theme.fmt_fraccion); si ninguna está cerca, se usa el porcentaje exacto."""
    por_tipo, _ = metrics.valoracion_por_formato(df)
    subtitulo = "Distribución de los títulos de cada formato según su valoración"
    ambos = {"Película", "Serie"} <= set(por_tipo.index)
    if not ambos:
        return "Valoración de la audiencia por nivel", subtitulo
    alta = {f: por_tipo.loc[f].get(metrics.NIVEL_ALTA, 0) for f in ("Serie", "Película")}
    if alta["Serie"] == alta["Película"]:
        return "Series y películas tienen la misma proporción de valoraciones altas", subtitulo
    lider = "Serie" if alta["Serie"] > alta["Película"] else "Película"
    otro = "Película" if lider == "Serie" else "Serie"
    solo = "solo " if alta[otro] < alta[lider] * 0.7 else ""
    titulo = (
        f"{_en_prosa(alta[lider]).capitalize()} de las {_plural_formato(lider)} tiene valoración alta; "
        f"en {_plural_formato(otro)}, {solo}{_en_prosa(alta[otro])}"
    )
    return titulo, subtitulo


def panel_valoracion(df):
    por_tipo, clasif = metrics.valoracion_por_formato(df)
    ambos = {"Película", "Serie"} <= set(por_tipo.index)
    if ambos:
        alta_serie = por_tipo.loc["Serie"].get(metrics.NIVEL_ALTA, 0)
        alta_pelicula = por_tipo.loc["Película"].get(metrics.NIVEL_ALTA, 0)
        numero = theme.fmt_pct(alta_serie)
        hallazgo = f"de las series tiene valoración alta, frente a {theme.fmt_pct(alta_pelicula)} de las películas."
        ganador_fmt = "Serie" if alta_serie > alta_pelicula else "Película" if alta_pelicula > alta_serie else None
        if ganador_fmt:
            plural = _plural_formato(ganador_fmt)
            pct_sin_votos_ganador = por_tipo.loc[ganador_fmt].get(metrics.NIVEL_SIN_VOTOS, 0)
            recomendacion = (
                f"Priorizar la renovación de {plural} bien evaluadas y promocionar el {theme.fmt_pct(pct_sin_votos_ganador)} de "
                f"{plural} que aún no tiene votos."
            )
        else:
            recomendacion = "Sostener el balance actual: ambos formatos valoran de forma similar."
    else:
        pct_alta = (clasif == metrics.NIVEL_ALTA).mean()
        numero = theme.fmt_pct(pct_alta)
        hallazgo = f"del contenido tiene valoración alta; {theme.fmt_pct((clasif == metrics.NIVEL_SIN_VOTOS).mean())} no tiene votos."
        recomendacion = "Promocionar el contenido sin votos para que la audiencia pueda evaluarlo."
    return numero, hallazgo, recomendacion


def como_leer_valoracion(df):
    """«Cómo leer este gráfico» de Valoración: los cortes, qué es «Sin votos» y por qué el KPI «Bien evaluados» marca menos
    que el % de valoración alta de este gráfico (exige además un mínimo de votos)."""
    pct = metrics.pct_bien_evaluado(df)
    return [
        f"Cortes de valoración: baja bajo {metrics.UMBRAL_MEDIA}, media de {metrics.UMBRAL_MEDIA} a {metrics.UMBRAL_ALTA}, alta desde {metrics.UMBRAL_ALTA}.",
        "«Sin votos» es dato faltante, no un nivel de valoración.",
        "Porcentajes sobre el total de títulos de cada formato.",
        f"El indicador «Catálogo bien evaluado» exige además {metrics.MIN_VOTOS_BIEN_EVALUADO} votos; por eso marca {'—' if pct is None else theme.fmt_pct(pct)}.",
    ]


# ----------------- Matriz popularidad vs valoración -----------------
def titulo_matriz(mvp):
    subtitulo = f"Popularidad y valoración de los títulos con al menos {theme.fmt_int(mvp['min_votos'])} votos"
    if mvp["df_sc"].empty:
        return "Popularidad vs valoración por título", subtitulo
    de_cada_10 = round(mvp["pct_activos"] * 10)
    bien = f"{de_cada_10} de cada 10" if de_cada_10 else "Menos de 1 de cada 10"
    if mvp["n_riesgo"] == 0:
        return f"{bien} títulos populares están bien evaluados; ninguno está bajo {metrics.UMBRAL_RIESGO}", subtitulo
    solo = "solo " if mvp["pct_riesgo"] < 0.10 else ""
    return (
        f"{bien} títulos populares están bien evaluados; {solo}{theme.fmt_int(mvp['n_riesgo'])} ({theme.fmt_pct(mvp['pct_riesgo'])}) "
        f"bajo {metrics.UMBRAL_RIESGO}", subtitulo,
    )


def panel_matriz(mvp):
    if mvp["df_sc"].empty:
        return "—", "ningún título alcanza el mínimo de votos elegido.", "Reducir el mínimo de votos para incluir más títulos en el análisis."
    hallazgo = (
        f"de los {theme.fmt_int(mvp['n_pop'])} títulos populares (P75, con ≥{theme.fmt_int(mvp['min_votos'])} votos) "
        f"está bien evaluado (≥{metrics.UMBRAL_ALTA}); {theme.fmt_int(mvp['n_riesgo'])} ({theme.fmt_pct(mvp['pct_riesgo'])}) "
        f"están mal evaluados (<{metrics.UMBRAL_RIESGO})."
    )
    if mvp["n_riesgo"] > 0:
        recomendacion = f"Frenar la renovación automática de los {theme.fmt_int(mvp['n_riesgo'])} títulos populares con valoración baja antes del próximo ciclo."
    else:
        recomendacion = "Sostener la estrategia de promoción actual: no hay títulos populares mal evaluados."
    return theme.fmt_pct(mvp["pct_activos"]), hallazgo, recomendacion


def como_leer_matriz(mvp):
    """«Cómo leer este gráfico» de la Matriz: criterio de umbrales y qué significan los conteos de cada zona."""
    c = metrics.conteos_cuadrantes_matriz(mvp)
    return [
        "Cada punto es un título; el eje Y usa escala logarítmica. Se destacan los títulos con popularidad sobre el P75.",
        f"Riesgo de abandono: valoración menor que {metrics.UMBRAL_RIESGO}; activos a retener: {metrics.UMBRAL_ALTA} o más.",
        f"La franja {metrics.UMBRAL_RIESGO}–{metrics.UMBRAL_ALTA} es una zona neutra que no se clasifica: se mantiene el corte de {metrics.UMBRAL_RIESGO} para que coincida con el indicador «Títulos en riesgo».",
        f"Las cinco zonas suman los {theme.fmt_int(c['total'])} títulos graficados.",
    ]
 

# ----------------- Tabla de títulos en riesgo (Matriz) -----------------
def _paises_texto(paises):
    return unir_es(paises) if len(paises) else "Sin país registrado"


def riesgo_lista_html(riesgo, anio_parcial, min_votos, es_default, n=metrics.N_TABLA_RIESGO):
    """Lista ranking «Títulos en riesgo» (columna derecha de la Matriz, reemplaza la tabla + expander): posición, título
    (recortado con puntos suspensivos por CSS, no aquí), punto de color y formato, valoración destacada, y «2025 parcial»
    bajo el título que lo tenga. Muestra los `n` más populares de `riesgo` (ya ordenado por metrics.titulos_en_riesgo);
    `n` es fijo, no dinámico (ver la nota de metrics.N_TABLA_RIESGO). Si `min_votos` no es el valor por defecto de la Matriz,
    lo dice y aclara que el KPI superior usa siempre el default, para que las dos cifras no parezcan un error."""
    t = riesgo.head(n)
    filas = "".join(
        f'<div class="riesgo-fila"><span class="riesgo-pos">{i}</span>'
        f'<div class="riesgo-info"><span class="riesgo-titulo" title="{escape(f.title)}">{escape(f.title)}</span>'
        f'<span class="riesgo-meta"><span class="dot" style="background:{theme.COLOR_FORMATO[f.type]}"></span>{f.type}'
        f'{" · " + str(anio_parcial) + " parcial" if int(f.release_year) == anio_parcial else ""}</span></div>'
        f'<span class="riesgo-valor">{theme.fmt_float(f.vote_average)}</span></div>'
        for i, f in enumerate(t.itertuples(), start=1)
    )
    aviso = "" if es_default else (
        f'<div class="riesgo-aviso">Con un mínimo de {theme.fmt_int(min_votos)} votos '
        f'(el indicador «Títulos en riesgo» de más arriba usa siempre {theme.fmt_int(metrics.MIN_VOTOS_MATRIZ_DEFECTO)}).</div>'
    )
    return (
        '<div class="riesgo-lista"><div class="riesgo-lista-titulo"><span>Títulos en riesgo</span>'
        f'<span>los {len(t)} más populares de {theme.fmt_int(len(riesgo))}</span></div>{aviso}{filas}</div>'
    )


def csv_riesgo(riesgo, anio_parcial):
    """CSV de TODOS los títulos en riesgo (no solo los de la tabla), con las mismas columnas más «Año parcial». Separador ';' y coma
    decimal, con BOM UTF-8: es lo que abre bien en Excel configurado en español de Chile."""
    import pandas as pd
    tabla = pd.DataFrame({
        "Título": riesgo["title"], "Año": riesgo["release_year"].astype(int),
        "Año parcial": ["sí" if int(a) == anio_parcial else "no" for a in riesgo["release_year"]],
        "País": riesgo["paises"].map(_paises_texto), "Formato": riesgo["type"],
        "Popularidad": riesgo["popularity"].round(1), "Valoración": riesgo["vote_average"].round(1), "Votos": riesgo["vote_count"].astype(int),
    })
    return tabla.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")


# ----------------- Filtros: etiquetas de los popover, estado vacío, CSV del conjunto filtrado -----------------
# Paso 2: la fila de chips de solo lectura (fila_filtros_html/_chip_lista) se retiró — cada filtro (Años/Género/País,
# st.popover en dashboard/_shell.py) muestra su propia selección en el texto de su botón, no hace falta repetirla aparte.
MAX_NOMBRES_EN_ETIQUETA = 3  # más nombres que estos en un mismo filtro se resumen como "y N más"


def etiqueta_filtro_anios(rango, rango_defecto):
    """Texto del botón del popover «Años»: el rango si es distinto del default, «Todos» si no."""
    return "Todos" if rango == rango_defecto else f"{rango[0]} – {rango[1]}"


def etiqueta_filtro_lista(seleccion):
    """Texto del botón del popover «Género»/«País»: «Todos» sin selección; los nombres (hasta MAX_NOMBRES_EN_ETIQUETA,
    el resto como «y N más») con selección."""
    if not seleccion:
        return "Todos"
    resto = len(seleccion) - MAX_NOMBRES_EN_ETIQUETA
    mostrados = list(seleccion[:MAX_NOMBRES_EN_ETIQUETA]) + ([f"{resto} más"] if resto > 0 else [])
    return unir_es(mostrados)


def mensaje_sin_titulos(sugerencias):
    """Texto del estado vacío: dice qué filtro relajar y cuántos títulos recuperaría, con las cifras ya calculadas."""
    base = "Ningún título cumple esta combinación de filtros."
    if not sugerencias:
        return f"{base} Quitar un solo filtro no alcanza: usa «Limpiar filtros» para volver a empezar."
    acciones = {"Formato": "Volver a «Ambos» formatos", "Años": "Ampliar el rango de años", "Género": "Quitar el filtro de género", "País": "Quitar el filtro de país"}

    def detalle(s):
        return unir_es(s["detalle"]) if isinstance(s["detalle"], list) else s["detalle"]

    opciones = "; ".join(
        f"{acciones[s['filtro']].lower() if i else acciones[s['filtro']]} ({detalle(s)}) deja {theme.fmt_int(s['n'])} títulos"
        for i, s in enumerate(sugerencias[:3])
    )
    return f"{base} Para volver a ver datos: {opciones}. También puedes usar «Limpiar filtros»."


def csv_filtrado(df):
    """CSV del conjunto filtrado completo, de más a menos popular. Mismo formato que csv_riesgo: separador ';',
    coma decimal y BOM UTF-8, que es lo que abre bien en Excel configurado en español de Chile."""
    import pandas as pd
    d = df.sort_values("popularity", ascending=False)
    tabla = pd.DataFrame({
        "Título": d["title"], "Formato": d["type"], "Año de estreno": d["release_year"].astype(int),
        "Géneros": d["generos"].map(unir_es), "Países": d["paises"].map(_paises_texto),
        "Popularidad": d["popularity"].round(1), "Valoración": d["vote_average"].round(1), "Votos": d["vote_count"].astype(int),
    })
    return tabla.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")


# ----------------- Resumen Ejecutivo -----------------
def titulo_mini_evolucion(df, anio_parcial):
    """Título del mini-gráfico de evolución del Resumen. Sintetiza (solo la razón); el de la pestaña enuncia la conclusión completa."""
    t = metrics.tendencia_formatos(df, anio_parcial)
    subtitulo = "Popularidad mediana por año y formato"
    if t is None or t["lider"] is None:
        return "Popularidad de series y películas", subtitulo
    return f"Ventaja en popularidad: de {_r(t['razon_ini'])} a {_r(t['razon_fin'])}", subtitulo


def titulo_mini_valoracion(df):
    """Título del mini-gráfico de valoración del Resumen, distinto al de la pestaña Valoración."""
    por_tipo, _ = metrics.valoracion_por_formato(df)
    if not {"Película", "Serie"} <= set(por_tipo.index):
        return "Valoración por nivel", "Título por título, según su valoración"
    return (
        f"Valoración alta: {theme.fmt_pct(por_tipo.loc['Serie'].get(metrics.NIVEL_ALTA, 0))} de las series y "
        f"{theme.fmt_pct(por_tipo.loc['Película'].get(metrics.NIVEL_ALTA, 0))} de las películas",
        f"Títulos con valoración {metrics.UMBRAL_ALTA} o más, sobre el total de cada formato",
    )


def _verbo_direccion(direccion):
    return {"baja": "bajó", "sube": "subió", "estable": "se mantuvo"}[direccion]


def _tarjeta_generos(cuad):
    """(numero, accion, respaldo) de la acción de géneros para el Resumen, o None si ningún género rinde sobre su formato.
    `respaldo` es una frase completa («Rinden 1,46×, 1,34× y 1,12× la mediana de las películas.»): si TODOS los géneros
    elegidos son exclusivos de un mismo formato nombra ese formato; si no, dice «su formato» (cada uno el propio)."""
    arriba = _rinden_sobre(cuad)
    if arriba.empty:
        return None
    grupos = _grupos_por_formato(arriba, cuad)
    if grupos is None:
        elegidos = arriba.head(MAX_GENEROS_POR_GRUPO)
        accion = f"Priorizar {_nombres(elegidos['genero'])} en las próximas licencias"
        de_su_formato = "su formato"
    else:
        solo_pel, solo_ser, ambos = (g.head(MAX_GENEROS_POR_GRUPO) for g in grupos)
        destinos = []
        if len(solo_pel):
            destinos.append(f"priorizar {_nombres(solo_pel['genero'])} al licenciar películas")
        if len(solo_ser):
            destinos.append(f"priorizar {_nombres(solo_ser['genero'])} al licenciar series")
        if destinos:
            frase = unir_es(destinos)
            accion = frase[0].upper() + frase[1:]
            elegidos = arriba[arriba["genero"].isin(list(solo_pel["genero"]) + list(solo_ser["genero"]))]
            de_su_formato = "las películas" if len(solo_ser) == 0 else "las series" if len(solo_pel) == 0 else "su formato"
        else:
            accion = f"Priorizar {_nombres(ambos['genero'])} en cualquier formato"
            elegidos, de_su_formato = ambos, "su formato"
    respaldo = f"{'Rinde' if len(elegidos) == 1 else 'Rinden'} {unir_es(_x(r) for r in elegidos['pop_relativa'])} la mediana de {de_su_formato}."
    return str(len(elegidos)), accion, respaldo


def resumen_ejecutivo(df, rango_anios, modo_paises, anio_parcial):
    """{titular, soporte, tarjetas:[{numero, accion, respaldo} × 3]} — conclusión primero.

    TESIS: si popularidad Y valoración alta favorecen al mismo formato, «las {formato} rinden más que las {otro} y deben
    priorizarse», con el soporte calculado entre el primer y el último año COMPLETO (la ventaja en popularidad puede bajar
    mientras la de valoración alta sube: se dice tal cual). Sin esa convergencia (o con un solo formato filtrado) el titular
    sale del primer hallazgo aplicable. No promete retorno financiero: no se midió.

    TRES ACCIONES, en orden de prioridad y siempre tres: formato → géneros (para cuando se licencien películas o series) →
    mercados destino → riesgo → sin votos → seguimiento. Son coherentes entre sí por construcción: la de géneros es condicional
    al formato de la licencia y la de mercados solo suma destinos, nunca pide recortar uno con popularidad relativa > 1."""
    razon, _, _ = metrics.razon_popularidad_series_peliculas(df)
    por_tipo, clasif = metrics.valoracion_por_formato(df)
    ambos = {"Película", "Serie"} <= set(por_tipo.index)
    alta = {f: por_tipo.loc[f].get(metrics.NIVEL_ALTA, 0) for f in ("Serie", "Película")} if ambos else {}
    mvp = metrics.matriz_popularidad_valoracion(df, metrics.MIN_VOTOS_MATRIZ_DEFECTO)
    pl = metrics.pais_lider(df, modo=modo_paises)
    destinos = metrics.destinos_mercados(df, modo_paises)
    ctx_generos = _contexto_generos(df)
    pct_sin_votos = (clasif == metrics.NIVEL_SIN_VOTOS).mean()
    periodo = f"en {rango_anios[0]}" if rango_anios[0] == rango_anios[1] else f"entre {rango_anios[0]} y {rango_anios[1]}"
    contexto = f"{theme.fmt_int(len(df))} títulos analizados {periodo}."

    ganador_pop = None
    if razon is not None and razon >= metrics.UMBRAL_DIFERENCIA_RELEVANTE:
        ganador_pop = "Serie"
    elif razon is not None and razon <= 1 / metrics.UMBRAL_DIFERENCIA_RELEVANTE:
        ganador_pop = "Película"
    ganador_val = None
    if ambos and alta["Serie"] != alta["Película"]:
        ganador_val = "Serie" if alta["Serie"] > alta["Película"] else "Película"
    ganador = ganador_pop if ganador_pop and ganador_pop == ganador_val else None

    tesis, candidatos = None, []
    if ganador:
        plural, otro = _plural_formato(ganador), _otro_formato(ganador)
        factor = razon if ganador == "Serie" else 1 / razon
        pp_global = (alta[ganador] - alta["Película" if ganador == "Serie" else "Serie"]) * 100
        t = metrics.tendencia_formatos(df, anio_parcial)
        if t and t["lider"] == ganador:
            pop = (f"Su ventaja en popularidad se mantuvo en torno a {_r(t['razon_fin'])}" if t["dir_razon"] == "estable"
                   else f"Su ventaja en popularidad {_verbo_direccion(t['dir_razon'])} de {_r(t['razon_ini'])} a {_r(t['razon_fin'])}")
            val = (f"su ventaja en valoración alta se mantuvo en torno a {_pts(t['pp_fin'])} puntos" if t["dir_pp"] == "estable"
                   else f"su ventaja en valoración alta {_verbo_direccion(t['dir_pp'])} de {_pts(t['pp_ini'])} a {_pts(t['pp_fin'])} puntos")
            opuestas = {t["dir_razon"], t["dir_pp"]} == {"baja", "sube"}
            soporte = f"{pop} ({t['anio_ini']}–{t['anio_fin']}){',' if opuestas else ' y'} {'pero ' if opuestas else ''}{val}."
            numero = _pts(t["pp_fin"]) + " pp"
            respaldo = f"Su ventaja en valoración alta llegó a {_pts(t['pp_fin'])} puntos en {t['anio_fin']}."
        else:
            soporte = (f"Su popularidad mediana es {_r(factor)} la de las {otro} y el {theme.fmt_pct(alta[ganador])} de sus títulos tiene "
                       f"valoración alta, frente a {theme.fmt_pct(alta['Película' if ganador == 'Serie' else 'Serie'])}.")
            numero = _pts(pp_global) + " pp"
            respaldo = f"Su ventaja en valoración alta es de {_pts(pp_global)} puntos en la selección actual."
        # El titular es el mismo enuncie o no una tendencia multi-año (eso solo cambia `soporte`, arriba): se fija UNA
        # vez aquí, fuera del if/else — antes solo se fijaba en la rama sin tendencia, y con una tendencia que coincide
        # con `ganador` (rama `if`) `tesis` se quedaba en None y el desempate de más abajo (candidatos[0][1], para
        # cuando no hay `tesis`) tronaba: esa entrada es justo la de "formato", con `None` en su lugar a propósito.
        tesis = (f"LAS {plural.upper()} RINDEN MÁS QUE LAS {otro.upper()} Y DEBEN PRIORIZARSE", soporte)
        candidatos.append(("formato", None, {"numero": numero, "accion": f"Priorizar las {plural} en las próximas licencias", "respaldo": respaldo}))

    generos = _tarjeta_generos(ctx_generos[0]) if ctx_generos is not None else None
    if generos:
        nombres = unir_es(_rinden_sobre(ctx_generos[0])["genero"].head(3))
        candidatos.append(("generos", (f"{nombres} rinden sobre la mediana de su formato", contexto),
                           {"numero": generos[0], "accion": generos[1], "respaldo": generos[2]}))
    if destinos and pl:
        nombres = _nombres(d["pais"] for d in destinos)
        candidatos.append(("mercados", (f"{nombres} rinden sobre la mediana de su formato y permiten diversificar el catálogo", contexto), {
            "numero": theme.fmt_pct(pl["pct_top"]), "accion": f"Diversificar hacia {nombres}",
            "respaldo": f"{_nombres(pl['top'])} concentran el {theme.fmt_pct(pl['pct_top'])} de los títulos con país registrado. "
                        f"{nombres} {'rinden' if len(destinos) > 1 else 'rinde'} {unir_es(_x(d['pop_relativa']) for d in destinos)} la mediana de su formato.",
        }))
    if mvp.get("pct_riesgo") is not None and mvp["n_riesgo"] > 0:
        candidatos.append(("riesgo", (f"{theme.fmt_int(mvp['n_riesgo'])} títulos populares están mal evaluados y requieren revisión", contexto), {
            "numero": theme.fmt_int(mvp["n_riesgo"]), "accion": "Auditar los títulos populares mal evaluados antes de renovar licencias",
            "respaldo": f"{theme.fmt_int(mvp['n_riesgo'])} títulos populares tienen valoración bajo {metrics.UMBRAL_RIESGO} ({theme.fmt_pct(mvp['pct_riesgo'])} de los {theme.fmt_int(mvp['n_pop'])}).",
        }))
    if pct_sin_votos > 0:
        candidatos.append(("sinvotos", (f"El {theme.fmt_pct(pct_sin_votos)} del catálogo filtrado todavía no recibe votos de la audiencia", contexto), {
            "numero": theme.fmt_pct(pct_sin_votos), "accion": "Impulsar el descubrimiento de los títulos sin votos",
            "respaldo": f"El {theme.fmt_pct(pct_sin_votos)} del catálogo filtrado aún no recibe votos: sin votos no hay valoración.",
        }))
    candidatos.append(("seguimiento", (f"El catálogo filtrado reúne {theme.fmt_int(len(df))} títulos {periodo}", contexto), {
        "numero": theme.fmt_int(len(df)), "accion": "Dar seguimiento al catálogo filtrado en el próximo corte de datos",
        "respaldo": f"Reúne {theme.fmt_int(len(df))} títulos {periodo}; el seguimiento permite detectar cambios de tendencia entre un corte y otro.",
    }))
 
    # clave_tesis: de qué candidato sale el titular mostrado — el gráfico del Resumen lo usa para elegir qué dibujar
    # (item "el gráfico del Resumen siempre respalda la tesis que se muestra"): con "generos" dibuja el ranking de
    # géneros de charts.ranking_generos_resumen; con cualquier otra clave (o sin géneros disponibles) usa un aviso.
    clave_tesis = "formato" if tesis is not None else candidatos[0][0]
    if tesis is None:
        titular_alt, soporte_alt = candidatos[0][1]
        tesis = (titular_alt, soporte_alt)
    return {
        "titular": tesis[0], "soporte": tesis[1], "tarjetas": [c[2] for c in candidatos[:3]],
        "n_riesgo": mvp.get("n_riesgo"), "clave_tesis": clave_tesis,
    }


_DIRECCION_BRECHAS = {  # (dir_razon popularidad, dir_pp valoración alta) -> titular del mini-gráfico de brechas del Resumen
    ("baja", "sube"): "Atraen menos ventaja, pero satisfacen más", ("sube", "baja"): "Atraen más ventaja, pero satisfacen menos",
    ("sube", "sube"): "Ganan ventaja en ambos frentes", ("baja", "baja"): "Pierden ventaja en ambos frentes",
    ("estable", "sube"): "Sostienen su ventaja en popularidad, y satisfacen más",
    ("estable", "baja"): "Sostienen su ventaja en popularidad, pero satisfacen menos",
    ("sube", "estable"): "Atraen más ventaja, y satisfacen igual", ("baja", "estable"): "Atraen menos ventaja, y satisfacen igual",
    ("estable", "estable"): "Sostienen su ventaja en ambos frentes",
}


def titulo_brechas_resumen(t):
    """(título, subtítulo) del gráfico de brechas del Resumen (formato «Ambos»). El título se calcula según la
    dirección real de las dos ventajas (nunca escrito a mano): «atraen» es la popularidad (el eje que se achica o
    crece), «satisfacen» es la valoración alta. El subtítulo describe lo que se grafica en términos neutros («diferencia»,
    no «ventaja»): es el mismo texto tanto si el resultado favorece a las series como si favorece a las películas."""
    subtitulo = "Razón de popularidad y diferencia de valoración alta: series frente a películas, por año"
    if t is None or t["lider"] is None:
        return "Popularidad y valoración alta por año", subtitulo
    return _DIRECCION_BRECHAS[(t["dir_razon"], t["dir_pp"])], subtitulo


def titulo_ranking_generos_resumen(cuad, formato):
    """(título, subtítulo) del gráfico del Resumen cuando el filtro deja un solo formato: la tesis pasa a hablar de
    géneros (ver resumen_ejecutivo/generos_destacados_resumen), así que el gráfico también — mismo criterio que
    narrative.titulo_generos («K de N géneros rinden sobre su formato»), acotado al formato filtrado."""
    arriba = _rinden_sobre(cuad)
    n, k = len(cuad), len(arriba)
    plural = _plural_formato(formato)
    subtitulo = f"Popularidad relativa a la mediana de {plural}, por género"
    if k == 0:
        return f"Ningún género rinde sobre la mediana de {plural}", subtitulo
    return f"{k} de {n} géneros rinden sobre la mediana de {plural}", subtitulo


def generos_destacados_resumen(cuad):
    """Los géneros que nombra la tesis de género del Resumen: mismo criterio que _tarjeta_generos (los que más rinden
    sobre su formato, acotado a MAX_GENEROS_POR_GRUPO), para que el gráfico resalte EXACTAMENTE los géneros que nombra
    el texto — nunca un color de formato en un género del que la tesis no habla."""
    return set(_rinden_sobre(cuad)["genero"].head(MAX_GENEROS_POR_GRUPO))


def render_tesis(resumen):
    """La tesis: EL único elemento de 32px de la página, SIN recuadro (una frase, no una tarjeta), con la línea de
    soporte en 14px debajo."""
    st.markdown(
        f'<div class="tesis-titular">{escape(resumen["titular"])}</div>'
        f'<div class="tesis-soporte">{escape(resumen["soporte"])}</div>',
        unsafe_allow_html=True,
    )


def render_que_hacer(resumen):
    """«Qué hacer»: lista numerada (no tarjetas), sin números grandes — índice en 12px, acción en 14px 600, respaldo en
    12px. Cierra con un enlace a los títulos en riesgo de la Matriz: visual (punto + texto), no funcional todavía — con
    st.tabs no hay forma de activar una pestaña desde código; navega de verdad recién en el Paso 2 (st.navigation)."""
    st.markdown(
        '<div class="resumen-col-titulo">Qué hacer</div>'
        '<div class="resumen-col-subtitulo">Tres decisiones para el próximo ciclo de licencias, en orden de prioridad</div>',
        unsafe_allow_html=True,
    )
    items = "".join(
        f'<div class="hacer-item"><span class="hacer-indice">{i}</span><div>'
        f'<div class="hacer-accion">{escape(t["accion"])}</div><div class="hacer-respaldo">{escape(t["respaldo"])}</div></div></div>'
        for i, t in enumerate(resumen["tarjetas"], start=1)
    )
    st.markdown(f'<div class="hacer-lista">{items}</div>', unsafe_allow_html=True)
    n_riesgo = resumen.get("n_riesgo")
    if n_riesgo:
        st.markdown(
            f'<div class="hacer-enlace"><span class="dot"></span>Revisar los {theme.fmt_int(n_riesgo)} títulos en riesgo en Matriz</div>',
            unsafe_allow_html=True,
        )
