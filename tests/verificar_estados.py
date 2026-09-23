"""
Prueba del dashboard COMPLETO en varios estados de filtros, con streamlit.testing.v1.AppTest (sin navegador).

    python tests/verificar_estados.py                      # verifica
    python tests/verificar_estados.py --guardar ruta.json  # además guarda lo renderizado (para comparar después de un refactor)
    python tests/verificar_estados.py --comparar ruta.json # compara lo renderizado con una copia guardada

Estados: por defecto · solo Película · solo Serie · género = Drama · país = México · año 2024 · filtros que dejan 0 títulos,
cada uno con los dos modos de conteo de países (primer país / coproducciones) y, en Evolución, con las dos métricas.

Paso 2 (st.navigation, páginas de archivo bajo dashboard/pages/): `AppTest.switch_page` es la única forma de multipágina
que sabe manejar, y solo funciona con páginas de ARCHIVO (no con `st.Page(función)`) — por eso dashboard/app.py declara
`st.Page("pages/….py", …)`. Un descubrimiento clave de esta migración: tras un `switch_page()`, `at.markdown`/`at.get(…)`
reflejan SOLO los elementos propios de la página a la que se cambió — NO el header, la barra de filtros, la franja de
KPIs ni el popover «Datos» que `dashboard/_shell.py` dibuja en app.py ANTES de `pg.run()` (el «router» común a las 6
páginas). Por eso ese contenido común se comprueba una sola vez, leyendo el PRIMER `at.run()` (que carga la página
default, Resumen, y de paso incluye todo el router); el contenido propio de cada página se lee por separado, después
de cada `switch_page()`.

Por cada estado comprueba: que la app no lance excepciones; las 6 páginas (sin «Metodología»); que el popover «Datos»
exista (incluso con 0 títulos) con sus tres puntos, sus limitaciones clave y la línea final; la franja de 4 KPIs (y el
subtexto del denominador); la tesis y las 3 líneas de «Qué hacer» del Resumen (ninguna empieza con «Mantener», ninguna
dice «retorno»); que NINGUNA oración del Resumen se repita en otra página; que ninguna recomendación pida frenar,
reducir o recortar un género o mercado con popularidad relativa > 1; que el TÍTULO-MENSAJE de cada página analítica sea
VERDADERO (recalculado desde el CSV crudo); y, del rediseño: que cada panel tenga su etiqueta «Recomendación», que el
enlace a los títulos en riesgo coincida con el KPI, la lista de Mercados, la lista de riesgo de la Matriz (máximo
N_TABLA_RIESGO filas, sin tabla+expander) y que «Cómo leer este gráfico» esté abierto o en expander según la página; y
que NINGÚN gráfico de NINGUNA página, en NINGÚN estado, quede vacío (≥1 traza con datos) ni con un eje fuera de su
dominio esperado (años, cantidad de títulos, valoración, países, proporciones…) — streamlit.testing.v1 por sí solo solo
detecta excepciones, no figuras vacías.
"""
import argparse
import base64
import html
import json
import re
import struct
import sys

import pandas as pd
from streamlit.testing.v1 import AppTest

from _comun import RAIZ, Verificador

# Solo para traducir géneros/países (su cobertura la verifica verificar_reglas.py) y para reusar el formateador de
# fracciones del título de Valoración (theme.fmt_fraccion es una regla de FORMATO determinista, no de análisis: se
# reutiliza en vez de reescribirla, igual que el resto del archivo reutiliza `cl`/`pct` propios para todo lo demás).
from src import data_loader, metrics, theme  # noqa: E402

RUTA_APP = str(RAIZ / "dashboard" / "app.py")
ANIO_PARCIAL = 2025
OPCIONES_CONTEO = {"primero": "Primer país", "todos": "Coproducciones"}  # mismas etiquetas cortas que dashboard/_shell.py
ESTADOS = {
    "por defecto": {},
    "solo Película": {"f_tipo": "Película"},
    "solo Serie": {"f_tipo": "Serie"},
    "género = Drama": {"f_generos": ["Drama"]},
    "país = México": {"f_paises": ["México"]},
    "año 2024": {"f_anios": (2024, 2024)},
    "filtros vacíos (0 títulos)": {"f_tipo": "Serie", "f_generos": ["Película para TV"]},
}
# nombre de página -> archivo (el orden es el de la navegación; Resumen es la default, no necesita switch_page)
PAGINAS = {
    "Resumen": "pages/resumen.py", "Géneros": "pages/generos.py", "Mercados": "pages/mercados.py",
    "Evolución": "pages/evolucion.py", "Valoración": "pages/valoracion.py", "Matriz": "pages/matriz.py",
}
NOMBRES_PAGINAS = list(PAGINAS)

# ================================================================== independiente: datos crudos
_m = pd.read_csv(RAIZ / "data" / "netflix_movies_detailed_up_to_2025.csv").assign(type="Película")
_s = pd.read_csv(RAIZ / "data" / "netflix_tv_shows_detailed_up_to_2025.csv").assign(type="Serie")
CRUDO = pd.concat([_m, _s], ignore_index=True)
CRUDO["g"] = CRUDO["genres"].map(lambda t: list(dict.fromkeys(x.strip() for x in t.split(",") if x.strip())) if isinstance(t, str) else [])
CRUDO["c"] = CRUDO["country"].map(lambda t: list(dict.fromkeys(x.strip() for x in t.split(",") if x.strip())) if isinstance(t, str) else [])
ES_A_EN_GENERO = {es: en for en, es in data_loader.GENEROS_ES.items()}
ES_A_EN_PAIS = {es: en for en, es in data_loader.PAISES_ES.items()}


def cl(x, d=1):
    """Formato es-CL: 23.2 -> '23,2'; 10305 -> '10.305'."""
    entero, _, dec = f"{x:,.{d}f}".partition(".")
    entero = entero.replace(",", ".")
    return f"{entero},{dec}" if d else entero


def pct(x):
    return f"{cl(x * 100, 0)}%"


def rz(x):
    return f"{cl(x)}×"


class Esperado:
    """Los títulos-mensaje que DEBERÍA mostrar el dashboard para una selección, calculados aquí desde el CSV crudo."""

    def __init__(self, tipo="Ambos", anios=(2015, 2025), generos=(), paises=()):
        sel = CRUDO[CRUDO["release_year"].between(*anios)]
        if tipo != "Ambos":
            sel = sel[sel["type"] == tipo]
        if generos:
            en = {ES_A_EN_GENERO[x] for x in generos}
            sel = sel[sel["g"].map(lambda ls: bool(en & set(ls)))]
        if paises:
            en = {ES_A_EN_PAIS[x] for x in paises}
            sel = sel[sel["c"].map(lambda ls: bool(en & set(ls)))]
        self.sel = sel.copy()
        self.sel["rel"] = self.sel["popularity"] / self.sel.groupby("type")["popularity"].transform("median")
        self.alta = (self.sel["vote_average"] >= 7) & (self.sel["vote_count"] > 0)

    # ------------------------------------------------------------ Valoración
    def valoracion(self):
        """Título en prosa: «La mitad de las X tiene valoración alta; en Y, solo un cuarto» (theme.fmt_fraccion redondea a
        la fracción común más cercana, dentro de 3 pp; si ninguna está cerca, usa el porcentaje exacto)."""
        a = self.alta.groupby(self.sel["type"]).mean()
        if not {"Película", "Serie"} <= set(a.index):
            return "Valoración de la audiencia por nivel"
        if a["Serie"] == a["Película"]:
            return "Series y películas tienen la misma proporción de valoraciones altas"
        lider, otro = ("Serie", "Película") if a["Serie"] > a["Película"] else ("Película", "Serie")
        plural = {"Serie": "series", "Película": "películas"}
        en_prosa = lambda x: theme.fmt_fraccion(x) or pct(x)  # noqa: E731
        solo = "solo " if a[otro] < a[lider] * 0.7 else ""
        prosa_lider = en_prosa(a[lider])
        return f"{prosa_lider[0].upper()}{prosa_lider[1:]} de las {plural[lider]} tiene valoración alta; en {plural[otro]}, {solo}{en_prosa(a[otro])}"

    # ------------------------------------------------------------ Mercados
    def mercados(self, modo):
        con = self.sel[self.sel["c"].map(len) > 0]
        if con.empty:
            return "Mercados de origen del catálogo"
        if modo == "primero":
            conteo = con["c"].map(lambda ps: ps[0]).value_counts()
        else:
            conteo = con[["c"]].explode("c")["c"].value_counts()
        top = set(conteo.head(3).index)
        cubiertos = con["c"].map(lambda ps: ps[0] in top).mean() if modo == "primero" else con["c"].map(lambda ps: bool(top & set(ps))).mean()
        titulo = f"{data_loader.PAISES_ES.get(conteo.index[0], conteo.index[0])} {'produce' if modo == 'primero' else 'participa en'} el {pct(conteo.iloc[0] / len(con))} de los títulos con país registrado"
        return titulo + ("; diversificación limitada" if cubiertos >= 0.30 else "")

    # ------------------------------------------------------------ Géneros
    def generos(self):
        base = self.sel[["g", "rel"]].explode("g").dropna(subset=["g"])
        if base.empty:
            return "Composición del catálogo por género"
        por = base.groupby("g").agg(n=("rel", "size"), rel=("rel", "median"))
        top = por[por["n"] >= 150].sort_values("n", ascending=False).head(15)
        if len(top) < 4:
            lider = base["g"].value_counts()
            return f"{data_loader.GENEROS_ES.get(lider.index[0], lider.index[0])} concentra el {pct(lider.iloc[0] / len(self.sel))} del catálogo filtrado"
        med_x = top["n"].median()
        d = top["rel"] - 1
        clasificado = d.abs() >= 0.10
        arriba = int((clasificado & (d > 0)).sum())
        sobre = int((clasificado & (d < 0) & (top["n"] >= med_x)).sum())
        n = len(top)
        rinden = f"{arriba} de {n} {'rinde' if arriba == 1 else 'rinden'} sobre su formato"
        if sobre == 0:
            return "Ningún género está sobreofertado" + (f"; {rinden}" if arriba else " ni rinde sobre su formato")
        return f"{sobre} de {n} géneros {'está sobreofertado' if sobre == 1 else 'están sobreofertados'}" + (f"; {rinden}" if arriba else "")

    # ------------------------------------------------------------ Evolución
    def evolucion(self, metrica):
        return self._popularidad() if metrica == "Popularidad mediana" else self._valoracion_mediana()

    def _popularidad(self):
        med = self.sel.groupby(["release_year", "type"])["popularity"].median().unstack().reindex(columns=["Película", "Serie"])
        razon = med["Serie"] / med["Película"].where(med["Película"] > 0)
        completos = razon[(razon.index != ANIO_PARCIAL) & razon.notna()].sort_index()
        if len(completos) < 2:
            mf = self.sel.groupby("type")["popularity"].median()
            if not {"Película", "Serie"} <= set(mf.index) or mf["Película"] <= 0:
                return "Evolución de la popularidad del catálogo"
            r = mf["Serie"] / mf["Película"]
            if r >= 1.2:
                return f"Las series superan {rz(r)} en popularidad a las películas"
            if r <= 1 / 1.2:
                return f"Las películas superan {rz(1 / r)} en popularidad a las series"
            return "Series y películas tienen una popularidad similar"
        ini, fin, ri, rf = completos.index[0], completos.index[-1], completos.iloc[0], completos.iloc[-1]
        lider = "Serie" if (completos > 1).all() else "Película" if (completos < 1).all() else None
        if lider is None:
            return f"Ningún formato lidera en popularidad todos los años: la razón Serie/Película pasó de {rz(ri)} ({ini}) a {rz(rf)} ({fin})"
        oi, of = (1 / ri, 1 / rf) if lider == "Película" else (ri, rf)
        plural, otro = ("series", "películas") if lider == "Serie" else ("películas", "series")
        base = f"Las {plural} superan a las {otro} todos los años"
        if not (of >= oi * 1.15 or of <= oi * 0.85):
            return f"{base}, con una ventaja estable: {rz(oi)} en {ini} y {rz(of)} en {fin}"
        verbo, conector = ("bajó", "pero") if of <= oi * 0.85 else ("subió", "y")
        return f"{base}, {conector} la ventaja {verbo} de {rz(oi)} ({ini}) a {rz(of)} ({fin})"

    def _valoracion_mediana(self):
        cv = self.sel[self.sel["vote_count"] >= 10]
        ev = cv.groupby(["release_year", "type"])["vote_average"].median().unstack().reindex(columns=["Película", "Serie"])
        completos = ev[ev.index != ANIO_PARCIAL].dropna().sort_index()
        if len(completos) < 2:
            med = cv.groupby("type")["vote_average"].median()
            if not {"Película", "Serie"} <= set(med.index):
                return "Evolución de la valoración del catálogo"
            dif = med["Serie"] - med["Película"]
            if dif >= 0.3:
                return f"Las series superan a las películas en valoración mediana ({cl(med['Serie'])} vs {cl(med['Película'])})"
            if dif <= -0.3:
                return f"Las películas superan a las series en valoración mediana ({cl(med['Película'])} vs {cl(med['Serie'])})"
            return "Series y películas tienen una valoración mediana similar"
        brecha = completos["Serie"] - completos["Película"]
        lider = "Serie" if (brecha > 0).all() else "Película" if (brecha < 0).all() else None
        signo = -1 if lider == "Película" else 1
        ini, fin = signo * brecha.iloc[0], signo * brecha.iloc[-1]
        y0, y1 = completos.index[0], completos.index[-1]
        if lider is None:
            return (f"Ningún formato lidera todos los años en valoración mediana: la brecha Serie−Película pasó de "
                    f"{'+' if ini >= 0 else ''}{cl(ini)} a {'+' if fin >= 0 else ''}{cl(fin)} puntos")
        plural, otro = ("series", "películas") if lider == "Serie" else ("películas", "series")
        base = f"Las {plural} superan a las {otro} en valoración mediana todos los años"
        if fin - ini >= 0.2:
            return f"{base}, y la ventaja creció de {cl(ini)} a {cl(fin)} puntos ({y0}–{y1})"
        if fin - ini <= -0.2:
            return f"{base}, aunque la ventaja bajó de {cl(ini)} a {cl(fin)} puntos ({y0}–{y1})"
        return f"{base}, y la ventaja se mantiene: {cl(ini)} puntos en {y0} y {cl(fin)} en {y1}"

    # ------------------------------------------------------------ Matriz
    def matriz(self, min_votos=50):
        d = self.sel[self.sel["vote_count"] >= min_votos]
        if d.empty:
            return "Popularidad vs valoración por título"
        pop = d[d["popularity"] >= d["popularity"].quantile(0.75)]
        activos, riesgo = int((pop["vote_average"] >= 7).sum()), int((pop["vote_average"] < 6).sum())
        de_cada_10 = round(activos / len(pop) * 10)
        bien = f"{de_cada_10} de cada 10" if de_cada_10 else "Menos de 1 de cada 10"
        if riesgo == 0:
            return f"{bien} títulos populares están bien evaluados; ninguno está bajo 6"
        return f"{bien} títulos populares están bien evaluados; {'solo ' if riesgo / len(pop) < 0.10 else ''}{cl(riesgo, 0)} ({pct(riesgo / len(pop))}) bajo 6"


# ================================================================== lectura de lo renderizado
def texto_plano(valores):
    return html.unescape(re.sub(r"<[^>]+>", "\n", "\n".join(valores)))


def oraciones(valores):
    """Oraciones (de 5 palabras o más) del texto renderizado de una página."""
    trozos = re.split(r"(?<=[.;:?!])\s+|\n+", texto_plano(valores))
    return {re.sub(r"\s+", " ", t).strip() for t in trozos if len(t.split()) >= 5}


def titulo_de(valores):
    for val in valores:
        encontrado = re.search(r'<div class="grafico-titulo">(.*?)</div>', val, re.S)
        if encontrado:
            return html.unescape(encontrado.group(1))
    return None


def _instantanea(at):
    """Lo que hace falta comprobar de la página actualmente activa en `at`."""
    return {
        "markdown": [m.value for m in at.markdown],
        "plotly_specs": [json.loads(c.proto.spec) for c in at.get("plotly_chart")],
        "expander_labels": [e.label for e in at.expander],
        "dataframe": len(at.dataframe),
        "exception": [str(e.value)[:160] for e in at.exception],
    }


def leer_estado(estado, modo, metrica=None):
    """Corre la app en `estado`/`modo` y visita las 6 páginas. Devuelve (comun, paginas, excepciones):
    `comun` es la instantánea del PRIMER run (incluye el router — header, barra de filtros, KPIs, popover «Datos» —
    Y la página default, Resumen, ya que ambos corren en el mismo primer `at.run()`); `paginas` es
    {nombre: instantánea} para las 6, leídas cada una con su propio switch_page (Resumen reusa `comun`, no cambia de
    página); `excepciones` acumula las de las 7 ejecuciones (1 inicial + 5 switch_page + la del cambio de métrica)."""
    at = AppTest.from_file(RUTA_APP, default_timeout=180)
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.session_state["conteo_paises"] = OPCIONES_CONTEO[modo]
    at.run()
    comun = _instantanea(at)
    excepciones = list(comun["exception"])
    paginas = {"Resumen": comun}
    for nombre, archivo in PAGINAS.items():
        if nombre == "Resumen":
            continue
        at.switch_page(archivo).run()
        if nombre == "Evolución" and metrica:
            radios = [r for r in at.radio if r.label == "Métrica"]
            if radios:
                radios[0].set_value(metrica).run()
        paginas[nombre] = _instantanea(at)
        excepciones += paginas[nombre]["exception"]
    return comun, paginas, excepciones


# ------------------------------------------------------------ ningún gráfico vacío (streamlit.testing.v1 solo detecta
# EXCEPCIONES, no figuras vacías: esto fue justo lo que dejó pasar, sin que ningún test lo notara, el gráfico de brechas
# del Resumen con un solo formato filtrado — metrics.razon_por_anio/ventaja_valoracion_alta_por_anio dan NaN cuando falta
# un formato, así que la figura quedaba con 0 trazas y ejes por defecto de Plotly (p. ej. "-1× a 4×").
_DTYPES_TIPADOS = {"i1": "b", "u1": "B", "i2": "h", "u2": "H", "i4": "i", "u4": "I", "i8": "q", "u8": "Q", "f4": "f", "f8": "d"}


def _decodificar_serie(valor):
    """Un eje de una traza Plotly puede venir como lista plana o, si es numérico, como un "typed array" compacto
    ({'dtype': 'i2', 'bdata': '<base64>'}) — la representación que usa streamlit al serializar la figura. Se decodifica
    aquí para poder comprobarlo igual que una lista normal."""
    if isinstance(valor, dict) and "bdata" in valor:
        crudo = base64.b64decode(valor["bdata"])
        codigo = _DTYPES_TIPADOS.get(valor.get("dtype"))
        if not codigo or not crudo:
            return []
        return list(struct.unpack(f"<{len(crudo) // struct.calcsize(codigo)}{codigo}", crudo))
    return list(valor) if valor else []


def _valores_eje(spec, eje):
    """Todos los valores no nulos de `eje` ('x' o 'y') de las trazas de una figura Plotly (dict `spec` de plotly_chart.proto.spec)."""
    return [v for tr in spec.get("data", []) for v in _decodificar_serie(tr.get(eje)) if v is not None]


def _trazas_con_datos(spec):
    """Cuántas trazas de `spec` tienen al menos un dato real en X o en Y (una traza con listas vacías, como el caso del
    bug, no cuenta)."""
    return sum(1 for tr in spec.get("data", []) if _valores_eje({"data": [tr]}, "x") or _valores_eje({"data": [tr]}, "y"))


def _dominio_esperado(nombre_pagina, spec, esp, tipo):
    """(ok, detalle) según si el eje relevante de la figura de `nombre_pagina` cae en su dominio esperado (años,
    cantidad de títulos, valoración, proporciones…) — recalculado de forma independiente, no solo "no lanzó
    excepción". None si esta página no tiene un dominio simple que comprobar así (su chequeo de título-mensaje ya
    cubre su coherencia)."""
    xs, ys = _valores_eje(spec, "x"), _valores_eje(spec, "y")
    if nombre_pagina == "Evolución":
        a0, a1 = int(esp.sel["release_year"].min()), int(esp.sel["release_year"].max())
        fuera = [v for v in xs if not (a0 <= v <= a1)]
        return not fuera, f"años fuera de [{a0}, {a1}]: {fuera[:5]}"
    if nombre_pagina == "Géneros":
        fuera = [v for v in xs if v < metrics.MIN_TITULOS_RELATIVA]
        return not fuera, f"cantidad de títulos bajo el mínimo ({metrics.MIN_TITULOS_RELATIVA}): {fuera[:5]}"
    if nombre_pagina == "Matriz":
        fuera = [v for v in xs if not (-0.01 <= v <= 10.21)]
        return not fuera, f"valoración fuera de [0, 10]: {fuera[:5]}"
    if nombre_pagina == "Valoración":
        fuera = [v for v in xs if not (-0.01 <= v <= 1.15)]
        return not fuera, f"proporción fuera de [0, 1]: {fuera[:5]}"
    if nombre_pagina == "Mercados":
        # Las 3 trazas (Película, Serie, total) comparten el mismo eje Y de países a propósito (un bar apilado + el
        # total en texto): lo que importa es que los países VISTOS (sin duplicar por traza) sean válidos, no que la
        # lista completa (con repeticiones entre trazas) no tenga duplicados.
        vistos = set(ys)
        desconocidos = vistos - set(data_loader.PAISES_ES.values())
        return bool(vistos) and not desconocidos, f"eje Y vacío o con países desconocidos: {desconocidos}"
    if nombre_pagina == "Resumen":
        if tipo == "Ambos":
            a0, a1 = int(esp.sel["release_year"].min()), int(esp.sel["release_year"].max())
            fuera = [v for v in xs if not (a0 <= v <= a1)]
            return not fuera, f"años fuera de [{a0}, {a1}]: {fuera[:5]}"
        return bool(ys), f"sin géneros en el eje Y del ranking: {ys}"
    return None


# ================================================================== verificación
def verificar(v, nombre_estado, estado, modo, metrica):
    etiqueta = f"{nombre_estado} · conteo «{modo}»" + (f" · {metrica}" if metrica else "")

    # Estado de 0 títulos: un solo run alcanza (_shell.preparar llama a st.stop() antes de pg.run(), así que no hay
    # páginas que visitar — ni siquiera Resumen dibuja contenido propio).
    if "vacíos" in nombre_estado:
        at = AppTest.from_file(RUTA_APP, default_timeout=180)
        for clave, valor in estado.items():
            at.session_state[clave] = valor
        at.session_state["conteo_paises"] = OPCIONES_CONTEO[modo]
        at.run()
        comun = _instantanea(at)
        v.comprobar(f"[{etiqueta}] la app no lanza excepciones", not comun["exception"], str(comun["exception"]))
        todo = comun["markdown"]
        sobre = [t for t in todo if 'class="sobre"' in t]
        partes = sobre[0].split("Limitaciones clave") if len(sobre) == 1 else ["", ""]
        v.comprobar(f"[{etiqueta}] el popover «Datos» existe, con 3 puntos de «Lo esencial», sus limitaciones clave y la línea final, sin tablas ni código",
                    len(sobre) == 1 and partes[0].count("<li>") == 3 and partes[1].count("<li>") in (4, 5)
                    and "Metodología completa en el informe del proyecto." in sobre[0] and "<table" not in sobre[0] and "<code" not in sobre[0],
                    f"bloques={len(sobre)}, esenciales={partes[0].count('<li>')}, limitaciones={partes[1].count('<li>')}")
        v.comprobar(f"[{etiqueta}] muestra el aviso de 0 títulos y no dibuja ninguna página",
                    any("Ningún título cumple esta combinación" in t for t in todo) and not any('class="grafico-titulo"' in t for t in todo),
                    str([t[:80] for t in todo if "Ningún título" in t or 'class="grafico-titulo"' in t]))
        return {"markdown": todo, "plotly": 0, "dataframe": 0, "paginas": 0}

    comun, paginas, excepciones = leer_estado(estado, modo, metrica)
    v.comprobar(f"[{etiqueta}] la app no lanza excepciones", not excepciones, str(excepciones[:3]))
    todo = comun["markdown"]
    # Popover «Datos»: vive en el pie del riel (dashboard/_shell.py), se dibuja SIEMPRE (también con 0 títulos, comprobado arriba)
    sobre = [t for t in todo if 'class="sobre"' in t]
    partes = sobre[0].split("Limitaciones clave") if len(sobre) == 1 else ["", ""]
    v.comprobar(f"[{etiqueta}] el popover «Datos» existe, con 3 puntos de «Lo esencial», sus limitaciones clave y la línea final, sin tablas ni código",
                len(sobre) == 1 and partes[0].count("<li>") == 3 and partes[1].count("<li>") in (4, 5)
                and "Metodología completa en el informe del proyecto." in sobre[0] and "<table" not in sobre[0] and "<code" not in sobre[0],
                f"bloques={len(sobre)}, esenciales={partes[0].count('<li>')}, limitaciones={partes[1].count('<li>')}")
    franja = [t for t in todo if 'class="kpi-franja"' in t]
    v.comprobar(f"[{etiqueta}] dibuja la franja de 4 KPIs (una sola, no 4 tarjetas), con el denominador explícito en «Bien evaluados»",
                len(franja) == 1 and franja[0].count('class="kpi-celda"') == 4 and "Del total, valoración ≥7 con ≥50 votos" in franja[0],
                re.sub("<[^>]+>", " ", franja[0])[:200] if franja else "sin franja")
    firma = {"markdown": {n: p["markdown"] for n, p in paginas.items()}, "plotly": sum(len(p["plotly_specs"]) for p in paginas.values()),
             "dataframe": sum(p["dataframe"] for p in paginas.values()), "paginas": len(paginas)}
    v.comprobar(f"[{etiqueta}] dibuja las 6 páginas, sin «Metodología»", list(paginas) == NOMBRES_PAGINAS, str(list(paginas)))

    resumen = "\n".join(paginas["Resumen"]["markdown"])
    tarjetas = re.findall(r'<div class="hacer-accion">(.*?)</div>', resumen)
    v.comprobar(f"[{etiqueta}] el Resumen tiene tesis y 3 tarjetas, ninguna empieza con «Mantener»",
                'class="tesis-titular"' in resumen and len(tarjetas) == 3 and not any(t.startswith("Mantener") for t in tarjetas), str(tarjetas))
    todo_texto = texto_plano(todo + [m for p in paginas.values() for m in p["markdown"]])
    v.comprobar(f"[{etiqueta}] ningún texto dice «retorno»", "retorno" not in todo_texto.lower())
    # Ninguna oración del Resumen aparece igual en otra página. paginas["Resumen"] es el PRIMER run completo (router +
    # página), así que sus oraciones incluyen las del propio popover «Datos» — se restan antes de comparar, si no
    # cualquier estado marcaría una repetición trivial (el popover es un subconjunto de sí mismo).
    del_resumen = oraciones(paginas["Resumen"]["markdown"]) - oraciones(sobre)
    repetidas = {o for n in NOMBRES_PAGINAS[1:] for o in del_resumen & oraciones(paginas[n]["markdown"])}
    v.comprobar(f"[{etiqueta}] 0 oraciones idénticas entre el Resumen y las demás páginas ni el popover", not repetidas, str(sorted(repetidas)[:2]))
    # Recomendaciones: nunca frenar, reducir ni recortar un género o mercado con popularidad relativa > 1
    texto_reco = texto_plano(paginas["Resumen"]["markdown"] + paginas["Géneros"]["markdown"] + paginas["Mercados"]["markdown"])
    prohibido = re.findall(r"(?i)\b(reducir|recortar)\b", texto_reco)
    frenos = [float(x.replace(",", ".")) for frase in re.findall(r"Frenar nuevas licencias en ([^.]*)\.", texto_reco) for x in re.findall(r"\((\d+,\d+)×\)", frase)]
    v.comprobar(f"[{etiqueta}] ninguna recomendación pide reducir/recortar, ni frenar algo con popularidad relativa > 1", not prohibido and all(x < 1.0 for x in frenos), f"{prohibido} {frenos}")
    # Títulos-mensaje verdaderos
    esp = Esperado(estado.get("f_tipo", "Ambos"), estado.get("f_anios", (2015, 2025)), estado.get("f_generos", ()), estado.get("f_paises", ()))
    reales = {n: titulo_de(paginas[n]["markdown"]) for n in NOMBRES_PAGINAS[1:6]}
    esperados = {"Géneros": esp.generos(), "Mercados": esp.mercados(modo), "Evolución": esp.evolucion(metrica or "Popularidad mediana"),
                 "Valoración": esp.valoracion(), "Matriz": esp.matriz()}
    for n, esperado in esperados.items():
        v.comprobar(f"[{etiqueta}] título de {n} verdadero", reales[n] == esperado, f"\n      renderizado: {reales[n]!r}\n      recalculado: {esperado!r}")

    # Ningún gráfico vacío, en NINGUNA página, en NINGÚN estado (incluidos "solo Película" y "solo Serie" de ESTADOS):
    # cada plotly_chart dibujado debe tener al menos una traza con datos reales, y su eje debe caer en el dominio
    # esperado para esa página. Si una página no dibuja gráfico en este estado (p. ej. avisa "pocos datos"), no hay
    # nada que comprobar aquí — eso es correcto, no un caso vacío.
    for n in NOMBRES_PAGINAS:
        for spec in paginas[n]["plotly_specs"]:
            n_trazas = _trazas_con_datos(spec)
            v.comprobar(f"[{etiqueta}] el gráfico de {n} no está vacío (≥1 traza con datos)", n_trazas >= 1,
                        f"trazas totales={len(spec.get('data', []))}, con datos={n_trazas}")
            if n_trazas >= 1:
                resultado = _dominio_esperado(n, spec, esp, estado.get("f_tipo", "Ambos"))
                if resultado is not None:
                    ok, detalle = resultado
                    v.comprobar(f"[{etiqueta}] el eje del gráfico de {n} cae en el dominio esperado", ok, detalle)

    # ---------------------------------------------------------------- rediseño: panel, «Qué hacer», listas, «Cómo leer»
    for n in NOMBRES_PAGINAS[1:]:
        texto_n = "\n".join(paginas[n]["markdown"])
        v.comprobar(f"[{etiqueta}] el panel de {n} tiene la etiqueta «Recomendación» antes de su texto en 14px 600",
                    '<div class="panel-etiqueta">Recomendación</div>' in texto_n, texto_n.count("panel-etiqueta"))
    n_indices = len(re.findall(r'<span class="hacer-indice">(\d)</span>', resumen))
    v.comprobar(f"[{etiqueta}] «Qué hacer» numera sus 3 ítems 1, 2, 3 (sin números grandes)",
                re.findall(r'<span class="hacer-indice">(\d)</span>', resumen) == ["1", "2", "3"], n_indices)
    n_riesgo_kpi = re.search(r'<div class="kpi-valor">([\d.—]+)</div>', franja[0].split("kpi-icono--riesgo")[1]) if franja else None
    if n_riesgo_kpi and n_riesgo_kpi.group(1) not in ("—", "0"):  # 0 es falsy en Python: el enlace no se dibuja (nada que revisar)
        v.comprobar(f"[{etiqueta}] el Resumen enlaza (visual) a los títulos en riesgo de la Matriz, con el mismo número que el KPI",
                    f'Revisar los {n_riesgo_kpi.group(1)} títulos en riesgo en Matriz' in resumen, resumen.count("hacer-enlace"))
    # Mercados: lista «Mejor rendimiento frente a su formato» (cuando hay países con datos)
    if reales["Mercados"] not in (None, "Mercados de origen del catálogo"):
        v.comprobar(f"[{etiqueta}] Mercados trae la lista «Mejor rendimiento frente a su formato»", "mercado-lista-titulo" in "\n".join(paginas["Mercados"]["markdown"]))
    # Matriz: lista de riesgo (cuando hay títulos en riesgo) con como máximo N_TABLA_RIESGO filas
    texto_matriz = "\n".join(paginas["Matriz"]["markdown"])
    n_filas_riesgo = texto_matriz.count('class="riesgo-fila"')
    if "riesgo-lista-titulo" in texto_matriz:
        v.comprobar(f"[{etiqueta}] la lista de riesgo de la Matriz tiene entre 1 y 5 filas (N_TABLA_RIESGO)", 1 <= n_filas_riesgo <= 5, n_filas_riesgo)
        v.comprobar(f"[{etiqueta}] Matriz ya no tiene tabla+expander de riesgo (reemplazada por la lista)", "stDataFrame" not in texto_matriz)
    # «Cómo leer este gráfico»: abierto (Géneros/Evolución/Valoración) o en expander (Mercados/Matriz) — solo se comprueba
    # cuando la página efectivamente lo dibujó (con aviso de «pocos datos» no hay gráfico, y tampoco «Cómo leer»).
    abiertas, cerradas = ("Géneros", "Evolución", "Valoración"), ("Mercados", "Matriz")
    for n in abiertas:
        texto_n = "\n".join(paginas[n]["markdown"])
        if "Cómo leer este gráfico" in texto_n:
            v.comprobar(f"[{etiqueta}] «Cómo leer este gráfico» de {n} está ABIERTO (div fijo, no expander)", 'class="como-leer"' in texto_n)
    for n in cerradas:
        if paginas[n]["expander_labels"]:
            v.comprobar(f"[{etiqueta}] «Cómo leer este gráfico» de {n} está en un expander CERRADO",
                        paginas[n]["expander_labels"][-1] == "Cómo leer este gráfico")
    return firma


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guardar", help="guarda lo renderizado en este archivo JSON")
    ap.add_argument("--comparar", help="compara lo renderizado con este archivo JSON")
    args = ap.parse_args()
    v = Verificador("Dashboard en 7 estados × 2 modos de conteo (AppTest): sin errores, coherencia y títulos verdaderos")
    firmas = {}
    for nombre, estado in ESTADOS.items():
        for modo in OPCIONES_CONTEO:
            firmas[f"{nombre}|{modo}|"] = verificar(v, nombre, estado, modo, None)
        if "vacíos" not in nombre:
            firmas[f"{nombre}|primero|Valoración mediana"] = verificar(v, nombre, estado, "primero", "Valoración mediana")
    if args.guardar:
        with open(args.guardar, "w", encoding="utf-8") as f:
            json.dump(firmas, f, ensure_ascii=False)
        v.info(f"Renderizado guardado en {args.guardar} ({len(firmas)} estados)")
    if args.comparar:
        with open(args.comparar, encoding="utf-8") as f:
            previo = json.load(f)
        distintos = []
        for clave, firma in firmas.items():
            ant = previo.get(clave)
            if ant != json.loads(json.dumps(firma)):
                distintos.append(clave)
        v.comprobar(f"El renderizado es idéntico al guardado en {args.comparar} ({len(firmas)} estados: markdown, gráficos, tablas y páginas)",
                    not distintos and set(previo) == set(firmas), f"distintos: {distintos[:5]}")
    return v.terminar()


if __name__ == "__main__":
    sys.exit(main())
