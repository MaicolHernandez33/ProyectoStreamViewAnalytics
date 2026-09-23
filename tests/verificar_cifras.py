"""
Verificación de las CIFRAS de referencia (DECISIONES.md, sección 4) con un cálculo independiente.

    python tests/verificar_cifras.py

Recalcula cada cifra directamente desde los dos CSV con pandas, SIN usar src/ (lee, une, deduplica géneros y países y filtra por su
cuenta), y la compara con dos cosas: (1) el valor de referencia de DECISIONES.md y (2) lo que devuelven las funciones del dashboard
(src/metrics.py). Si el cálculo independiente y el dashboard difieren, hay un error en uno de los dos.

Filtros por defecto: ambos formatos, todos los géneros y países, estrenos 2015–2025 (22.000 títulos).
"""
import sys

import numpy as np
import pandas as pd

from _comun import RAIZ, Verificador

from src import data_loader, metrics  # noqa: E402  (solo para leer lo que calcula el dashboard, nunca para calcular el valor independiente)

v = Verificador("Cifras de referencia: cálculo independiente (pandas + CSV crudo) vs dashboard vs DECISIONES.md")

# ================================================================== cálculo independiente (sin src/)
m = pd.read_csv(RAIZ / "data" / "netflix_movies_detailed_up_to_2025.csv").assign(type="Película")
s = pd.read_csv(RAIZ / "data" / "netflix_tv_shows_detailed_up_to_2025.csv").assign(type="Serie")
crudo = pd.concat([m, s], ignore_index=True)


def lista(texto, dedup=True):
    partes = [x.strip() for x in texto.split(",") if x.strip()] if isinstance(texto, str) else []
    return list(dict.fromkeys(partes)) if dedup else partes


crudo["g"], crudo["c"] = crudo["genres"].map(lista), crudo["country"].map(lista)
sel = crudo[crudo["release_year"].between(2015, 2025)].copy()
sel["rel"] = sel["popularity"] / sel.groupby("type")["popularity"].transform("median")
alta = (sel["vote_average"] >= 7) & (sel["vote_count"] > 0)

# ================================================================== lo que calcula el dashboard
df, _, _ = data_loader.load_data()
df_def = df[metrics.construir_mascara(df, "Ambos", [], [], (metrics.ANIO_INICIO_DEFECTO, 2025))]
EN = data_loader.GENERO_ORIGINAL                       # género en español -> nombre original
PAIS_EN = {es: en for en, es in data_loader.PAISES_ES.items()}


def comparar(nombre, indep, dash, ref=None, dec=0):
    """indep = cálculo independiente; dash = dashboard; ref = cifra de DECISIONES.md (redondeada a `dec` decimales)."""
    igual = bool(np.isclose(indep, dash, rtol=0, atol=1e-9)) if isinstance(indep, (int, float, np.number)) else indep == dash
    en_ref = ref is None or round(float(indep), dec) == ref
    v.comprobar(nombre, igual and en_ref, f"independiente={indep!r} · dashboard={dash!r} · DECISIONES.md={ref!r}")


# ------------------------------------------------------------------ KPIs
n = len(sel)
comparar("Títulos analizados", n, len(df_def), 22000)
comparar("Popularidad mediana (ambos formatos)", sel["popularity"].median(), metrics.popularidad_mediana(df_def), 23.2, 1)
por_formato = sel.groupby("type")["popularity"].median()
dash_formato = metrics.popularidad_mediana_por_formato(df_def)
comparar("Popularidad mediana de las series", por_formato["Serie"], dash_formato["Serie"], 36.1, 1)
comparar("Popularidad mediana de las películas", por_formato["Película"], dash_formato["Película"], 11.9, 1)
comparar("Catálogo bien evaluado (≥7 con ≥50 votos, sobre el total)", ((sel["vote_average"] >= 7) & (sel["vote_count"] >= 50)).mean(), metrics.pct_bien_evaluado(df_def), 0.20, 2)

# ------------------------------------------------------------------ Matriz
d = sel[sel["vote_count"] >= 50]
p75 = d["popularity"].quantile(0.75)
pop = d[d["popularity"] >= p75]
mvp = metrics.matriz_popularidad_valoracion(df_def, 50)
comparar("Matriz: títulos con ≥50 votos", len(d), len(mvp["df_sc"]), 10456)
comparar("Matriz: P75 de popularidad", p75, mvp["p75"], 35.1, 1)
comparar("Matriz: títulos populares (≥P75)", len(pop), mvp["n_pop"], 2614)
comparar("Matriz: activos a retener (populares con valoración ≥7)", int((pop["vote_average"] >= 7).sum()), mvp["n_activos"], 1851)
comparar("Matriz: activos = 71 % de los populares", (pop["vote_average"] >= 7).mean(), mvp["pct_activos"], 0.71, 2)
comparar("Matriz: títulos en riesgo (populares con valoración <6) = KPI", int((pop["vote_average"] < 6).sum()), mvp["n_riesgo"], 132)
comparar("Matriz: en riesgo = 5 % de los populares", (pop["vote_average"] < 6).mean(), mvp["pct_riesgo"], 0.05, 2)
comparar("Matriz: populares en la zona 6–7", int(pop["vote_average"].between(6, 7, inclusive="left").sum()), int(((mvp["df_sc"]["popularity"] >= mvp["p75"]) & mvp["df_sc"]["vote_average"].between(6, 7, inclusive="left")).sum()), 631)
popular, riesgo, activo = d["popularity"] >= p75, d["vote_average"] < 6, d["vote_average"] >= 7
zonas = {"riesgo": int((popular & riesgo).sum()), "activos": int((popular & activo).sum()), "neutra": int((~riesgo & ~activo).sum()),
         "bajo": int((~popular & riesgo).sum()), "nicho": int((~popular & activo).sum())}
dash_zonas = metrics.conteos_cuadrantes_matriz(mvp)
for zona, ref in (("riesgo", 132), ("activos", 1851), ("neutra", 3980), ("bajo", 2025), ("nicho", 2468)):
    comparar(f"Matriz: zona «{zona}»", zonas[zona], dash_zonas[zona], ref)
comparar("Matriz: las cinco zonas suman los títulos graficados", sum(zonas.values()), dash_zonas["total"], 10456)

# ------------------------------------------------------------------ Popularidad relativa por género
base = sel[["g", "rel"]].explode("g").dropna(subset=["g"])
por_genero = base.groupby("g").agg(n=("rel", "size"), rel=("rel", "median"))
top15 = por_genero[por_genero["n"] >= 150].sort_values("n", ascending=False).head(15)
dash_gen = metrics.resumen_generos(df_def).assign(en=lambda t: t["genero"].map(EN)).set_index("en")
REF_GENEROS = {"Adventure": 1.46, "Action": 1.34, "Family": 1.19, "Thriller": 1.12, "Action & Adventure": 1.09, "Animation": 1.08, "Horror": 1.07,
               "Reality": 1.06, "Crime": 1.04, "Sci-Fi & Fantasy": 1.03, "Comedy": 1.00, "Mystery": 1.00, "Drama": 0.99, "Romance": 0.96, "Documentary": 0.79}
comparar("Géneros del ranking (top 15 con ≥150 títulos): mismos géneros", sorted(top15.index), sorted(dash_gen.index))
for g, ref in REF_GENEROS.items():
    comparar(f"Popularidad relativa · {data_loader.GENEROS_ES[g]}", top15.loc[g, "rel"], dash_gen.loc[g, "pop_relativa"], ref, 2)
banda = top15["rel"].sub(1).abs()
comparar("Géneros sobre la banda de ±10 % (cuatro)", int(((top15["rel"] - 1) >= 0.10).sum()), int((dash_gen["pop_relativa"] - 1 >= 0.10).sum()), 4)
comparar("Géneros bajo la banda (uno: Documental)", int(((top15["rel"] - 1) <= -0.10).sum()), int((dash_gen["pop_relativa"] - 1 <= -0.10).sum()), 1)
comparar("Géneros dentro de la banda (diez)", int((banda < 0.10).sum()), int(((dash_gen["pop_relativa"] - 1).abs() < 0.10).sum()), 10)
comparar("Drama = 10.305 (con las etiquetas repetidas deduplicadas)", int(base["g"].eq("Drama").sum()), int(df_def["generos"].explode().eq("Drama").sum()), 10305)
sin_dedup = int(sel["genres"].map(lambda t: lista(t, dedup=False).count("Drama") if isinstance(t, str) else 0).sum())
comparar("Sin deduplicar Drama sería 10.306 (por eso el loader deduplica)", sin_dedup, 10306)

# ------------------------------------------------------------------ Países
con_pais = sel[sel["c"].map(len) > 0]
comparar("Títulos con país registrado", len(con_pais), metrics.pais_lider(df_def)["n_con_pais"], 20486)
comparar("Títulos sin país registrado", n - len(con_pais), metrics.pais_lider(df_def)["n_sin_pais"], 1514)
primero = con_pais.assign(p=con_pais["c"].map(lambda ps: ps[0])).groupby("p").agg(n=("rel", "size"), rel=("rel", "median"))
paises_150 = primero[primero["n"] >= 150].sort_values("rel", ascending=False)
dash_pais = metrics.popularidad_relativa_paises(df_def, metrics.MODO_PRIMER_PAIS).assign(en=lambda t: t["pais"].map(PAIS_EN)).set_index("en")
comparar("Países con ≥150 títulos (primer país)", len(paises_150), len(dash_pais), 21)
REF_PAISES = {"Philippines": (1.41, 331), "Mexico": (1.22, 321), "United States of America": (1.11, 5459), "Turkey": (1.07, None), "Brazil": (1.06, None),
              "Canada": (1.04, None), "South Korea": (1.04, 1577), "China": (0.95, 1790), "Japan": (0.94, 1901), "France": (0.89, None)}
for p, (ref, titulos) in REF_PAISES.items():
    comparar(f"Popularidad relativa · {data_loader.PAISES_ES[p]}", paises_150.loc[p, "rel"], dash_pais.loc[p, "pop_relativa"], ref, 2)
    if titulos:
        comparar(f"Títulos · {data_loader.PAISES_ES[p]}", int(paises_150.loc[p, "n"]), int(dash_pais.loc[p, "titulos"]), titulos)
todos = con_pais[["c"]].explode("c").groupby("c").size().sort_values(ascending=False)
lider1, lider_t = metrics.pais_lider(df_def, modo=metrics.MODO_PRIMER_PAIS), metrics.pais_lider(df_def, modo=metrics.MODO_TODOS_LOS_PAISES)
comparar("Estados Unidos: 27 % de los títulos con país (primer país)", primero.loc["United States of America", "n"] / len(con_pais), lider1["pct_lider"], 0.27, 2)
comparar("Estados Unidos: 37 % (contando coproducciones)", todos["United States of America"] / len(con_pais), lider_t["pct_lider"], 0.37, 2)
top3_1 = set(primero["n"].nlargest(3).index)
comparar("Los 3 primeros mercados suman 45 % (primer país)", con_pais["c"].map(lambda ps: ps[0] in top3_1).mean(), lider1["pct_top"], 0.45, 2)
top3_t = set(todos.head(3).index)
comparar("Los 3 primeros mercados suman 54 % (coproducciones)", con_pais["c"].map(lambda ps: bool(top3_t & set(ps))).mean(), lider_t["pct_top"], 0.54, 2)

# ------------------------------------------------------------------ Razón y ventaja por año
med = sel.groupby(["release_year", "type"])["popularity"].median().unstack()
razon = med["Serie"] / med["Película"]
dash_razon = metrics.razon_por_anio(df_def).set_index("anio")
REF_RAZON = {2015: 4.38, 2016: 4.17, 2017: 3.86, 2018: 4.26, 2019: 4.16, 2020: 2.95, 2021: 2.79, 2022: 2.60, 2023: 2.22, 2024: 1.19, 2025: 1.47}
for anio, ref in REF_RAZON.items():
    comparar(f"Razón series/películas {anio}", razon[anio], dash_razon.loc[anio, "razon"], ref, 2)
comparar("Mediana de películas 2015", med.loc[2015, "Película"], dash_razon.loc[2015, "Película"], 9.6, 1)
comparar("Mediana de películas 2024", med.loc[2024, "Película"], dash_razon.loc[2024, "Película"], 27.7, 1)
comparar("Mediana de series 2015", med.loc[2015, "Serie"], dash_razon.loc[2015, "Serie"], 41.9, 1)
comparar("Mediana de series 2024", med.loc[2024, "Serie"], dash_razon.loc[2024, "Serie"], 32.8, 1)
pct_alta = alta.groupby([sel["release_year"], sel["type"]]).mean().unstack()
ventaja = (pct_alta["Serie"] - pct_alta["Película"]) * 100
dash_ventaja = metrics.ventaja_valoracion_alta_por_anio(df_def).set_index("anio")
REF_VENTAJA = {2015: 23.2, 2016: 21.2, 2017: 22.2, 2018: 25.9, 2019: 25.8, 2020: 25.2, 2021: 22.6, 2022: 23.6, 2023: 30.1, 2024: 34.5, 2025: 15.0}
for anio, ref in REF_VENTAJA.items():
    comparar(f"Ventaja en valoración alta {anio} (puntos)", ventaja[anio], dash_ventaja.loc[anio, "ventaja_pp"], ref, 1)
alta_formato = alta.groupby(sel["type"]).mean()
dash_alta = metrics.valoracion_por_formato(df_def)[0][metrics.NIVEL_ALTA]
comparar("Valoración ≥7: series 50 %", alta_formato["Serie"], dash_alta["Serie"], 0.50, 2)
comparar("Valoración ≥7: películas 26 %", alta_formato["Película"], dash_alta["Película"], 0.26, 2)
con_votos = sel[sel["vote_count"] >= 10]
brecha = con_votos.groupby(["release_year", "type"])["vote_average"].median().unstack()
brecha = brecha["Serie"] - brecha["Película"]
dash_brecha = metrics.tendencia_valoracion_mediana(df_def, 2025)
comparar("Brecha de valoración mediana 2015 (≥10 votos)", brecha[2015], dash_brecha["brecha_ini"], 1.0, 1)
comparar("Brecha de valoración mediana 2024 (≥10 votos)", brecha[2024], dash_brecha["brecha_fin"], 0.9, 1)

sys.exit(v.terminar())
