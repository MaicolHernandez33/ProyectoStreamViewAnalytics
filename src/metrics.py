"""
Cálculos derivados del catálogo filtrado.

Funciones puras (sin Streamlit, sin Plotly): reciben un DataFrame ya filtrado por
app.py y devuelven números o DataFrames pequeños. Tanto narrative.py (para los
títulos-mensaje y el panel lateral) como charts.py (para lo que se dibuja) llaman a
las mismas funciones de aquí, así el número que se muestra en texto y el que se
grafica no pueden desincronizarse — nunca se recalcula "por separado".
"""
import pandas as pd

# Niveles de valoración (vote_average, escala 0-10)
UMBRAL_MEDIA = 4    # desde aquí la valoración es "media"
UMBRAL_ALTA = 7     # desde aquí la valoración es "alta"
UMBRAL_RIESGO = 6   # bajo este valor un título popular se considera mal evaluado
MIN_VOTOS_VALORACION = 10   # votos mínimos para calcular la valoración mediana por año
MIN_VOTOS_MATRIZ_DEFECTO = 50  # mínimo de votos por defecto en la matriz Popularidad vs Valoración
# Rango y paso del control de votos mínimos de la Matriz (su valor inicial es MIN_VOTOS_MATRIZ_DEFECTO)
MIN_VOTOS_MATRIZ_MINIMO = 10
MIN_VOTOS_MATRIZ_MAXIMO = 500
MIN_VOTOS_MATRIZ_PASO = 10

# Los intervalos se escriben en notación matemática porque son los cortes reales de clasificar_valoracion:
# [0, 4) baja, [4, 7) media, [7, 10] alta. "Sin votos" NO es un nivel de valoración: es dato faltante.
NIVEL_ALTA = "Alta [7, 10]"
NIVEL_MEDIA = "Media [4, 7)"
NIVEL_BAJA = "Baja [0, 4)"
NIVEL_SIN_VOTOS = "Sin votos"
# Orden ORDINAL fijo (de mejor a peor valoración), con «Sin votos» siempre al final — no por volumen.
ORDEN_VALORACION = [NIVEL_ALTA, NIVEL_MEDIA, NIVEL_BAJA, NIVEL_SIN_VOTOS]

UMBRAL_DIFERENCIA_RELEVANTE = 1.2  # razón mínima entre formatos para hablar de "supera" (si no, "similar")
UMBRAL_CONCENTRACION = 0.30        # un top-3 de países con al menos este % se considera concentración

MIN_VOTOS_BIEN_EVALUADO = 50  # votos mínimos para que un título cuente en "Catálogo bien evaluado" (KPI 3)

# Modo de conteo de países (Mercados de origen). Por defecto cuenta cada título una sola vez, en el
# primer país listado: así los totales no suman más que el catálogo y el % de concentración es exclusivo.
MODO_PRIMER_PAIS = "primero"
MODO_TODOS_LOS_PAISES = "todos"

MIN_TITULOS_RELATIVA = 150  # títulos mínimos de un país o género para que su popularidad relativa cuente (bajo eso una mediana es ruido)
N_PAISES_RANKING = 10    # países del ranking de Mercados
N_MERCADOS_CONCENTRACION = 3  # cuántos mercados líderes entran al indicador de concentración geográfica
N_MEJOR_RENDIMIENTO_PAISES = 5  # países de la lista «Mejor rendimiento frente a su formato» (Mercados)
# Filas de la lista «Títulos en riesgo» de la Matriz. Fijo (no dinámico): Streamlit no mide en Python cuántas filas caben en el
# alto real del gráfico (eso depende del navegador), así que se aproxima con un número fijo que quepa en los ~520 px del
# gráfico de la Matriz — igual al mínimo pedido y al del mockup. Ajustable en un solo lugar si se decide otro valor.
N_TABLA_RIESGO = 5
DIFERENCIA_VALORACION_RELEVANTE = 0.3  # puntos de valoración mediana entre formatos para hablar de "supera"
N_GENEROS_BURBUJAS = 15   # géneros más frecuentes que entran al gráfico de burbujas (más y las etiquetas chocan)
MIN_GENEROS_BURBUJAS = 4  # con menos géneros distintos los cuadrantes por mediana no significan nada

# Cuadrantes del gráfico de géneros (volumen en X, popularidad RELATIVA A SU FORMATO en Y; 1,0 = mediana del formato)
CUAD_NICHO = "Nicho de alto rendimiento"      # poco volumen, rinde sobre su formato (rendimiento = popularidad relativa; no se midió retorno)
CUAD_MOTORES = "Motores del catálogo"         # mucho volumen, rinde sobre su formato
CUAD_SOBREOFERTADO = "Sobreofertado"          # mucho volumen, rinde bajo su formato
CUAD_MARGINAL = "Marginal"                    # poco volumen, rinde bajo su formato
CUAD_EN_MEDIANA = "Rinde como su formato"     # popularidad relativa a menos de TOLERANCIA_MEDIANA de 1,0: no se clasifica
# Un género con popularidad relativa 0,96 o 1,04 no rinde "sobre" ni "bajo" su formato en ningún sentido útil para
# decidir. La banda es de ±10% alrededor de 1,0 y NO se ajusta para forzar que aparezca un género sobreofertado: que
# el cuadrante quede vacío es un hallazgo, y el título lo dice. Ajustable en un solo lugar.
TOLERANCIA_MEDIANA = 0.10
REFERENCIA_RELATIVA = 1.0                     # popularidad relativa = 1,0: igual a la mediana de su formato

# Tendencia de la ventaja de un formato sobre otro entre el primer y el último año COMPLETO
ANIO_INICIO_DEFECTO = 2015         # año inicial del filtro de período al cargar el dashboard (y de las imágenes de src/exportar.py)
MIN_ANIOS_TENDENCIA = 2           # años completos mínimos para hablar de tendencia
CAMBIO_RELATIVO_RAZON = 0.15      # la razón entre formatos "cambió" si varía al menos 15% entre extremos
CAMBIO_ESTABLE_PP = 2.0           # bajo estos puntos porcentuales la ventaja en valoración alta "se mantuvo"
CAMBIO_ESTABLE_VALORACION = 0.2   # bajo estos puntos la brecha de valoración mediana "se mantuvo"

ANIO_ANOTADO = 2020             # año de la caída de series que se anota en el gráfico de evolución
CAIDA_MINIMA_ANOTAR = 0.10      # solo se anota si la caída respecto del año anterior es de al menos 10%


def construir_mascara(df: pd.DataFrame, tipo, generos_sel, paises_sel, rango_anios) -> pd.Series:
    """La misma lógica de filtro (tipo / género / país / años) que arma app.py para el catálogo
    filtrado, reutilizable para construir otros subconjuntos comparables (mismo tipo/género/país, otro
    rango de años; lo usa también sugerencias_relajar_filtros)."""
    mask = df["release_year"].between(*rango_anios)
    if tipo != "Ambos":
        mask &= df["type"] == tipo
    if generos_sel:
        mask &= ~df["generos"].map(set(generos_sel).isdisjoint)
    if paises_sel:
        mask &= ~df["paises"].map(set(paises_sel).isdisjoint)
    return mask


def pct_bien_evaluado(df, umbral_valoracion=UMBRAL_ALTA, min_votos=MIN_VOTOS_BIEN_EVALUADO):
    """% de títulos con vote_average >= umbral Y vote_count >= min_votos (KPI 3)."""
    if df.empty:
        return None
    return ((df["vote_average"] >= umbral_valoracion) & (df["vote_count"] >= min_votos)).mean()


def clasificar_valoracion(d):
    """Nivel de valoración según vote_average; sin votos (vote_count == 0) o con valoración 0 quedan aparte."""
    nivel = pd.cut(
        d["vote_average"],
        bins=[-0.01, UMBRAL_MEDIA, UMBRAL_ALTA, 10.01],
        labels=[NIVEL_BAJA, NIVEL_MEDIA, NIVEL_ALTA],
        right=False,
    ).astype(object)
    return nivel.where((d["vote_count"] > 0) & (d["vote_average"] > 0), NIVEL_SIN_VOTOS)


# ----------------- Evolución de la popularidad -----------------
def popularidad_mediana(df):
    """Mediana de `popularity` de todos los títulos de `df` (el número del KPI global)."""
    return float(df["popularity"].median())


def popularidad_mediana_por_formato(df):
    return df.groupby("type")["popularity"].median()


def razon_popularidad_series_peliculas(df):
    """(razón Serie/Película, mediana Película, mediana Serie) según popularidad mediana.
    (None, None, None) si falta un formato o la mediana de Película es 0."""
    med = popularidad_mediana_por_formato(df)
    if not {"Película", "Serie"} <= set(med.index) or med["Película"] <= 0:
        return None, None, None
    return med["Serie"] / med["Película"], med["Película"], med["Serie"]


def evolucion_popularidad(df):
    return df.groupby(["release_year", "type"])["popularity"].median().reset_index(name="valor")


def evolucion_valoracion(df, min_votos=MIN_VOTOS_VALORACION):
    """Valoración MEDIANA por año y formato (no promedio: la distribución de vote_average es asimétrica
    y unos pocos títulos extremos mueven el promedio), solo con títulos de al menos `min_votos` votos."""
    con_votos = df[df["vote_count"] >= min_votos]
    return con_votos.groupby(["release_year", "type"])["vote_average"].median().reset_index(name="valor")


def variacion_anual(evolucion, formato, anio):
    """Variación (fracción) del valor de `formato` en `anio` respecto del año anterior, o None si falta
    alguno de los dos años en `evolucion` o el valor previo es 0."""
    serie = evolucion[evolucion["type"] == formato].set_index("release_year")["valor"]
    if anio not in serie.index or (anio - 1) not in serie.index or serie[anio - 1] <= 0:
        return None
    return serie[anio] / serie[anio - 1] - 1


def popularidad_relativa(df):
    """Popularidad de cada título dividida por la mediana de popularidad de SU formato dentro de `df` (la selección
    actual): 1,0 = igual a la mediana de su formato. Sirve para comparar géneros y mercados sin que domine el hecho de
    que un formato sea más popular que el otro. Sin mediana positiva (formato ausente o todo en 0) devuelve NaN."""
    mediana = df.groupby("type")["popularity"].transform("median")
    return df["popularity"] / mediana.where(mediana > 0)


def razon_por_anio(df):
    """Una fila por año con la popularidad mediana de cada formato y la razón Serie/Película (NaN si falta un formato
    ese año o la mediana de Película es 0). Es la serie que sostiene el mensaje de tendencia de Evolución."""
    mediana = df.groupby(["release_year", "type"])["popularity"].median().unstack()
    mediana = mediana.reindex(columns=["Película", "Serie"])
    mediana["razon"] = mediana["Serie"] / mediana["Película"].where(mediana["Película"] > 0)
    return mediana.rename_axis("anio").reset_index()


def ventaja_valoracion_alta_por_anio(df):
    """Una fila por año con el % de títulos de valoración alta de cada formato (sobre TODOS los títulos del formato ese año,
    la misma definición de la pestaña Valoración) y la ventaja Serie − Película en puntos porcentuales. A diferencia de
    `popularity`, la valoración no depende del sesgo de recencia del índice de TMDB."""
    alta = clasificar_valoracion(df) == NIVEL_ALTA
    pct = alta.groupby([df["release_year"], df["type"]]).mean().unstack().reindex(columns=["Película", "Serie"])
    pct["ventaja_pp"] = (pct["Serie"] - pct["Película"]) * 100
    return pct.rename_axis("anio").reset_index()


def _direccion(inicio, fin, relativo=None, absoluto=None):
    """'sube' | 'baja' | 'estable' según el cambio entre `inicio` y `fin` (umbral relativo o absoluto)."""
    if relativo is not None:
        if fin >= inicio * (1 + relativo):
            return "sube"
        return "baja" if fin <= inicio * (1 - relativo) else "estable"
    if fin - inicio >= absoluto:
        return "sube"
    return "baja" if fin - inicio <= -absoluto else "estable"


def tendencia_formatos(df, anio_parcial):
    """Cómo evoluciona la ventaja de un formato sobre otro entre el primer y el último año COMPLETO de `df` (el año parcial
    se excluye de los extremos). None si hay menos de MIN_ANIOS_TENDENCIA años completos con ambos formatos. La popularidad
    de `líder` es la razón orientada hacia el formato que lidera en todos los años; si el liderazgo alterna, `lider` es None
    y la razón se deja como Serie/Película."""
    razon = razon_por_anio(df)
    completos = razon[(razon["anio"] != anio_parcial) & razon["razon"].notna()].sort_values("anio").reset_index(drop=True)
    if len(completos) < MIN_ANIOS_TENDENCIA:
        return None
    ini, fin = completos.iloc[0], completos.iloc[-1]
    todas_series = bool((completos["razon"] > 1).all())
    todas_peliculas = bool((completos["razon"] < 1).all())
    lider = "Serie" if todas_series else "Película" if todas_peliculas else None
    orientar = (lambda r: 1 / r) if lider == "Película" else (lambda r: r)

    ventaja = ventaja_valoracion_alta_por_anio(df).set_index("anio")["ventaja_pp"]
    signo = -1 if lider == "Película" else 1
    pp_ini, pp_fin = signo * ventaja.get(ini["anio"]), signo * ventaja.get(fin["anio"])

    serie, pelicula = completos.set_index("anio")["Serie"], completos.set_index("anio")["Película"]
    alzas = [
        {"anio": int(a), "de": float(completos["razon"].iloc[i - 1]), "a": float(completos["razon"].iloc[i])}
        for i, a in enumerate(completos["anio"]) if i > 0 and completos["razon"].iloc[i] > completos["razon"].iloc[i - 1]
    ]
    tramo_series = tramo_peliculas = None
    a = ANIO_ANOTADO
    if a in serie.index and (a - 1) in serie.index and serie[a - 1] > 0 and serie[a] / serie[a - 1] - 1 <= -CAIDA_MINIMA_ANOTAR:
        tramo_series = {"anio": a, "de": float(serie[a - 1]), "a": float(serie[a]), "var": float(serie[a] / serie[a - 1] - 1)}
        if int(fin["anio"]) > a and pelicula[a] > 0:
            tramo_peliculas = {"anio_ini": a, "anio_fin": int(fin["anio"]), "de": float(pelicula[a]), "a": float(pelicula[int(fin["anio"])])}
    fila_parcial = razon[razon["anio"] == anio_parcial]
    parcial = None
    if not fila_parcial.empty and pd.notna(fila_parcial["razon"].iloc[0]):
        parcial = {"anio": int(anio_parcial), "razon": float(fila_parcial["razon"].iloc[0])}
    return {
        "anio_ini": int(ini["anio"]), "anio_fin": int(fin["anio"]), "lider": lider,
        "razon_ini": float(orientar(ini["razon"])), "razon_fin": float(orientar(fin["razon"])),
        "dir_razon": _direccion(orientar(ini["razon"]), orientar(fin["razon"]), relativo=CAMBIO_RELATIVO_RAZON),
        "pp_ini": float(pp_ini), "pp_fin": float(pp_fin), "dir_pp": _direccion(pp_ini, pp_fin, absoluto=CAMBIO_ESTABLE_PP),
        "serie_ini": float(ini["Serie"]), "serie_fin": float(fin["Serie"]),
        "pelicula_ini": float(ini["Película"]), "pelicula_fin": float(fin["Película"]),
        "anios_alza_razon": alzas, "tramo_series": tramo_series, "tramo_peliculas": tramo_peliculas, "parcial": parcial,
    }


def tendencia_valoracion_mediana(df, anio_parcial):
    """Brecha de valoración MEDIANA entre formatos (con MIN_VOTOS_VALORACION votos) entre el primer y el último año completo.
    `lider` es el formato con mayor valoración en todos los años (None si alterna); la brecha se orienta hacia él."""
    ev = evolucion_valoracion(df).pivot(index="release_year", columns="type", values="valor").reindex(columns=["Película", "Serie"])
    completos = ev[ev.index != anio_parcial].dropna().sort_index()
    if len(completos) < MIN_ANIOS_TENDENCIA:
        return None
    brecha = completos["Serie"] - completos["Película"]
    lider = "Serie" if (brecha > 0).all() else "Película" if (brecha < 0).all() else None
    signo = -1 if lider == "Película" else 1
    ini, fin = float(signo * brecha.iloc[0]), float(signo * brecha.iloc[-1])
    return {
        "anio_ini": int(completos.index[0]), "anio_fin": int(completos.index[-1]), "lider": lider,
        "brecha_ini": ini, "brecha_fin": fin, "direccion": _direccion(ini, fin, absoluto=CAMBIO_ESTABLE_VALORACION),
    }


# ----------------- Composición del catálogo (géneros) -----------------
def _conteo_generos(df):
    return df["generos"].explode().value_counts()


def genero_lider(df):
    """dict con el género más frecuente, su cantidad y su % sobre TODO el df filtrado
    (no solo los que se grafican)."""
    conteo = _conteo_generos(df)
    if conteo.empty:
        return None
    return {"genero": conteo.index[0], "cantidad": int(conteo.iloc[0]), "pct": conteo.iloc[0] / len(df)}


def resumen_generos(df, n=N_GENEROS_BURBUJAS, min_titulos=MIN_TITULOS_RELATIVA):
    """Una fila por género (los `n` con más títulos, y solo los que tienen al menos `min_titulos`: la popularidad relativa de
    un género con muy pocos títulos es ruido y arrastraría recomendaciones). Con los filtros por defecto todos los del top
    tienen más de 1.000 títulos, así que no cambia nada; con selecciones angostas el gráfico muestra menos géneros."""
    # pop_relativa: mediana, por género, de la popularidad de cada título relativa a la mediana de SU formato
    # (popularidad_relativa). Controla el efecto formato: las series son ~3× más populares que las películas, y un
    # género que existe en un solo formato heredaría esa diferencia si se comparara en bruto.
    filas = (
        df.assign(pop_rel=popularidad_relativa(df))[["generos", "type", "popularity", "pop_rel", "vote_count"]]
        .explode("generos").dropna(subset=["generos"])
    )
    if filas.empty:
        return pd.DataFrame(columns=["genero", "titulos", "popularidad", "pop_relativa", "votos", "Película", "Serie"])
    por_genero = filas.groupby("generos").agg(
        titulos=("popularity", "size"), popularidad=("popularity", "median"), pop_relativa=("pop_rel", "median"),
        votos=("vote_count", "sum"),
    )
    por_formato = filas.groupby(["generos", "type"]).size().unstack(fill_value=0).reindex(columns=["Película", "Serie"], fill_value=0)
    resumen = por_genero.join(por_formato)
    resumen = resumen[resumen["titulos"] >= min_titulos].sort_values("titulos", ascending=False).head(n)
    return resumen.rename_axis("genero").reset_index()


def cuadrantes_generos(resumen):
    """(resumen + columna 'cuadrante', mediana de títulos, referencia 1,0). En volumen, "mucho" es en o sobre la mediana de
    los géneros graficados. En rendimiento se usa la popularidad RELATIVA A SU FORMATO (1,0 = mediana del formato): sobre 1,0,
    bajo 1,0, o "rinde como su formato" cuando está a menos de TOLERANCIA_MEDIANA de 1,0 (esos géneros no se clasifican)."""
    med_x = resumen["titulos"].median()

    def cuadrante(fila):
        mucho_volumen = fila["titulos"] >= med_x
        if pd.isna(fila["pop_relativa"]):
            return CUAD_EN_MEDIANA
        distancia = fila["pop_relativa"] - REFERENCIA_RELATIVA
        if abs(distancia) < TOLERANCIA_MEDIANA:
            return CUAD_EN_MEDIANA
        rinde_sobre = distancia > 0
        if mucho_volumen and rinde_sobre:
            return CUAD_MOTORES
        if mucho_volumen:
            return CUAD_SOBREOFERTADO
        return CUAD_NICHO if rinde_sobre else CUAD_MARGINAL

    resultado = resumen.copy()
    resultado["cuadrante"] = resultado.apply(cuadrante, axis=1)
    return resultado, med_x, REFERENCIA_RELATIVA


# ----------------- Mercados de origen (países) -----------------
def con_pais_registrado(df):
    return df[df["paises"].map(len) > 0]


def _filas_por_pais(df, modo):
    """Una fila por (título, país contado): con `MODO_PRIMER_PAIS` cada título aporta una sola fila (su
    primer país listado); con `MODO_TODOS_LOS_PAISES`, una por cada país participante."""
    con_pais = con_pais_registrado(df)[["paises", "type", "popularity"]]
    if modo == MODO_PRIMER_PAIS:
        return con_pais.assign(pais=con_pais["paises"].map(lambda ps: ps[0]))[["pais", "type", "popularity"]]
    return con_pais.explode("paises").rename(columns={"paises": "pais"})


def popularidad_relativa_paises(df, modo=MODO_PRIMER_PAIS, min_titulos=MIN_TITULOS_RELATIVA):
    """Una fila por país con al menos `min_titulos` títulos: títulos, popularidad relativa a su formato (mediana), popularidad
    bruta mediana y % de series; de mayor a menor popularidad relativa. La relativa se calcula sobre TODA la selección (no solo
    los títulos con país), y el país se cuenta según `modo`, igual que el ranking de Mercados. El umbral evita rankear países con
    muy pocos títulos, donde una mediana es puro ruido."""
    con_pais = con_pais_registrado(df).assign(pop_rel=popularidad_relativa(df))
    if con_pais.empty:
        return pd.DataFrame(columns=["pais", "titulos", "pop_relativa", "pop_bruta", "pct_series"])
    if modo == MODO_PRIMER_PAIS:
        filas = con_pais.assign(pais=con_pais["paises"].map(lambda ps: ps[0]))
    else:
        filas = con_pais.explode("paises").rename(columns={"paises": "pais"})
    por_pais = filas.groupby("pais").agg(
        titulos=("pop_rel", "size"), pop_relativa=("pop_rel", "median"), pop_bruta=("popularity", "median"),
        pct_series=("type", lambda s: (s == "Serie").mean()),
    )
    return por_pais[por_pais["titulos"] >= min_titulos].sort_values("pop_relativa", ascending=False).reset_index()


def destinos_mercados(df, modo=MODO_PRIMER_PAIS, n=2):
    """Hasta `n` mercados destino para diversificar: los de mayor popularidad relativa entre los países con al menos
    MIN_TITULOS_RELATIVA títulos, con relativa > 1 y que NO sean parte de los mercados que hoy concentran el catálogo
    (recomendar 'diversificar hacia' un mercado que es justo el concentrado sería contradictorio). Una lista de dicts."""
    relativa = popularidad_relativa_paises(df, modo)
    if relativa.empty:
        return []
    lider = pais_lider(df, modo=modo)
    concentrados = set(lider["top"]) if lider else set()
    candidatos = relativa[(relativa["pop_relativa"] > REFERENCIA_RELATIVA) & ~relativa["pais"].isin(concentrados)]
    return candidatos.head(n).to_dict("records")


def top_paises(df, n=10, modo=MODO_PRIMER_PAIS):
    """(datos, orden): `datos` en formato largo (pais, type, titulos, popularidad) para los `n` países con
    más títulos, y `orden` con esos países de mayor a menor total (para ordenar el gráfico)."""
    filas = _filas_por_pais(df, modo)
    if filas.empty:
        return pd.DataFrame(columns=["pais", "type", "titulos", "popularidad"]), []
    totales = filas.groupby("pais").size().nlargest(n)
    datos = (
        filas[filas["pais"].isin(totales.index)].groupby(["pais", "type"])
        .agg(titulos=("popularity", "size"), popularidad=("popularity", "median")).reset_index()
    )
    return datos, totales.index.tolist()


def pais_lider(df, top_n_concentracion=N_MERCADOS_CONCENTRACION, modo=MODO_PRIMER_PAIS):
    """dict con el país líder y qué % de los títulos CON país registrado cae en los `top_n_concentracion`
    mercados líderes. Con `MODO_PRIMER_PAIS` el % es exclusivo (el primer país del título es uno de ellos);
    con `MODO_TODOS_LOS_PAISES` cuenta los títulos que incluyen al menos uno de ellos."""
    con_pais = con_pais_registrado(df)
    if con_pais.empty:
        return None
    conteo = _filas_por_pais(df, modo).groupby("pais").size().sort_values(ascending=False)
    top = conteo.head(top_n_concentracion)
    top_set = set(top.index)
    if modo == MODO_PRIMER_PAIS:
        cubiertos = con_pais["paises"].map(lambda ps: ps[0] in top_set).mean()
    else:
        cubiertos = (~con_pais["paises"].map(top_set.isdisjoint)).mean()
    return {
        "pais": conteo.index[0],
        "cantidad": int(conteo.iloc[0]),
        "pct_lider": conteo.iloc[0] / len(con_pais),
        "n_paises": len(conteo),
        "top": top.index.tolist(),
        "pct_top": cubiertos,
        "n_con_pais": len(con_pais),
        "n_sin_pais": len(df) - len(con_pais),
        "modo": modo,
    }


# ----------------- Valoración por formato -----------------
def valoracion_por_formato(df):
    """(crosstab % de títulos de cada formato por nivel, clasificación por título)."""
    clasif = clasificar_valoracion(df)
    return pd.crosstab(df["type"], clasif, normalize="index"), clasif


def barras_valoracion(df):
    """Dataframe largo (Formato × Nivel) con títulos y % sobre el total de CADA formato, en el orden
    ordinal fijo de ORDEN_VALORACION (Alta, Media, Baja y «Sin votos» al final) — nunca por volumen."""
    conteo = pd.crosstab(df["type"], clasificar_valoracion(df)).reindex(columns=ORDEN_VALORACION, fill_value=0)
    largo = conteo.rename_axis(index="Formato", columns="Nivel").stack().rename("Titulos").reset_index()
    largo["Porcentaje"] = largo["Titulos"] / largo.groupby("Formato")["Titulos"].transform("sum")
    largo["Nivel"] = pd.Categorical(largo["Nivel"], categories=ORDEN_VALORACION, ordered=True)
    return largo.sort_values(["Formato", "Nivel"]).reset_index(drop=True)


# ----------------- Matriz popularidad vs valoración -----------------
def matriz_popularidad_valoracion(df, min_votos):
    """Subconjunto con vote_count >= min_votos, más P75 de popularidad y conteos de cuadrante
    entre los títulos de popularidad alta (>= P75)."""
    df_sc = df[df["vote_count"] >= min_votos]
    resultado = {"df_sc": df_sc, "min_votos": min_votos}
    if df_sc.empty:
        return resultado
    p75 = df_sc["popularity"].quantile(0.75)
    populares = df_sc[df_sc["popularity"] >= p75]
    n_pop = len(populares)
    n_activos = int((populares["vote_average"] >= UMBRAL_ALTA).sum())
    n_riesgo = int((populares["vote_average"] < UMBRAL_RIESGO).sum())
    resultado.update(
        p75=p75, n_pop=n_pop, n_activos=n_activos, n_riesgo=n_riesgo,
        pct_activos=(n_activos / n_pop) if n_pop else None,
        pct_riesgo=(n_riesgo / n_pop) if n_pop else None,
    )
    return resultado


def titulos_en_riesgo(mvp):
    """Los títulos populares (>= P75) con valoración < UMBRAL_RIESGO, de más a menos populares: exactamente
    los que cuenta `n_riesgo`, así la tabla y las cifras del panel y del KPI nunca difieren."""
    d = mvp["df_sc"]
    if d.empty:
        return d
    return d[(d["popularity"] >= mvp["p75"]) & (d["vote_average"] < UMBRAL_RIESGO)].sort_values("popularity", ascending=False)


def conteos_cuadrantes_matriz(mvp):
    """Títulos de cada zona de la Matriz: los cuatro cuadrantes (popularidad sobre/bajo el P75 × valoración de riesgo / alta) y
    la franja neutra entre ambos cortes. Las cinco suman `total` (los títulos graficados), para que las etiquetas cierren."""
    d = mvp["df_sc"]
    popular = d["popularity"] >= mvp["p75"]
    riesgo, activo = d["vote_average"] < UMBRAL_RIESGO, d["vote_average"] >= UMBRAL_ALTA
    return {
        "riesgo": int((popular & riesgo).sum()), "activos": int((popular & activo).sum()),
        "nicho": int((~popular & activo).sum()), "bajo": int((~popular & riesgo).sum()),
        "neutra": int((~riesgo & ~activo).sum()), "total": len(d),
    }


# ----------------- Perfil del catálogo COMPLETO (metodología: popover «ⓘ Sobre los datos» y docs/metodologia.md) -----------------
def perfil_catalogo(df, anio_parcial):
    """Hechos del catálogo completo (sin filtros) que la metodología cita como limitaciones. Se
    calculan aquí para que ningún texto afirme una propiedad de los datos sin haberla comprobado."""
    n_pelicula = int((df["type"] == "Película").sum())
    n_serie = int((df["type"] == "Serie").sum())
    por_anio_formato = df.groupby(["type", "release_year"]).size()
    conteos = set(int(v) for v in por_anio_formato.unique())
    parcial, previos = df[df["release_year"] == anio_parcial], df[df["release_year"] < anio_parcial]

    def pct_sin_votos(d):
        return float((clasificar_valoracion(d) == NIVEL_SIN_VOTOS).mean()) if len(d) else None

    filas_generos = df[["generos", "type"]].explode("generos").dropna(subset=["generos"])
    por_formato = filas_generos.groupby(["generos", "type"]).size().unstack(fill_value=0)
    por_formato = por_formato.reindex(columns=["Película", "Serie"], fill_value=0)
    un_formato = por_formato[(por_formato["Película"] == 0) | (por_formato["Serie"] == 0)]
    return {
        "n_total": len(df), "n_pelicula": n_pelicula, "n_serie": n_serie,
        "anio_min": int(df["release_year"].min()), "anio_max": int(df["release_year"].max()),
        # Uniforme = cada formato aporta exactamente la misma cantidad de títulos cada año, y ambos formatos suman lo mismo
        "uniforme": len(conteos) == 1 and n_pelicula == n_serie,
        "filas_por_anio_formato": next(iter(conteos)) if len(conteos) == 1 else None,
        "parcial": {
            "anio": anio_parcial, "pct_sin_votos": pct_sin_votos(parcial), "pct_sin_votos_previos": pct_sin_votos(previos),
            "popularidad_mediana": float(parcial["popularity"].median()) if len(parcial) else None,
            "popularidad_mediana_previos": float(previos["popularity"].median()) if len(previos) else None,
        },
        "n_multigenero": int((df["generos"].map(len) > 1).sum()), "n_sin_genero": int((df["generos"].map(len) == 0).sum()),
        "n_multipais": int((df["paises"].map(len) > 1).sum()), "n_sin_pais": int((df["paises"].map(len) == 0).sum()),
        "n_generos": len(por_formato), "generos_un_formato": un_formato.index.tolist(),
    }


# ----------------- Estado vacío: qué filtro relajar -----------------
def sugerencias_relajar_filtros(df, tipo, generos_sel, paises_sel, rango_anios, rango_completo):
    """Con una combinación de filtros que deja 0 títulos: para cada filtro ACTIVO, cuántos títulos quedarían si
    solo ese se relajara (tipo -> Ambos, género/país -> sin filtro, años -> rango completo). Devuelve solo los que
    recuperan al menos un título, de mayor a menor recuperación."""
    relajados = []
    if tipo != "Ambos":
        relajados.append(("Formato", tipo, (df, "Ambos", generos_sel, paises_sel, rango_anios)))
    if rango_anios != rango_completo:
        relajados.append(("Años", f"{rango_anios[0]}–{rango_anios[1]}", (df, tipo, generos_sel, paises_sel, rango_completo)))
    if generos_sel:
        relajados.append(("Género", list(generos_sel), (df, tipo, [], paises_sel, rango_anios)))
    if paises_sel:
        relajados.append(("País", list(paises_sel), (df, tipo, generos_sel, [], rango_anios)))
    sugerencias = []
    for filtro, detalle, args in relajados:
        n = int(construir_mascara(args[0], *args[1:]).sum())
        if n > 0:
            sugerencias.append({"filtro": filtro, "detalle": detalle, "n": n})
    return sorted(sugerencias, key=lambda s: -s["n"])
