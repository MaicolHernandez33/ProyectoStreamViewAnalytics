"""
Carga e integración de los datos del catálogo.

Une los dos CSV (películas y series), convierte las columnas multivaluadas de género y
país en listas y TRADUCE sus nombres al español al cargar: así filtros, títulos,
recomendaciones y gráficos usan los mismos nombres sin parches pantalla por pantalla.
El nombre original (inglés) de los géneros se conserva en GENERO_ORIGINAL para mostrarlo
en el tooltip del gráfico de géneros.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

RUTA_DATOS = Path(__file__).resolve().parent.parent / "data"
ARCHIVO_PELICULAS = "netflix_movies_detailed_up_to_2025.csv"
ARCHIVO_SERIES = "netflix_tv_shows_detailed_up_to_2025.csv"

# Traducciones de los 28 géneros que trae el catálogo. Los géneros de películas y series vienen
# de taxonomías distintas del origen (p.ej. "Action" solo en películas, "Action & Adventure" solo
# en series), así que se traducen por separado y NO se fusionan.
GENEROS_ES = {
    "Drama": "Drama", "Comedy": "Comedia", "Animation": "Animación", "Thriller": "Suspenso",
    "Action": "Acción", "Crime": "Crimen", "Family": "Familiar", "Mystery": "Misterio",
    "Romance": "Romance", "Horror": "Terror", "Action & Adventure": "Acción y aventura",
    "Sci-Fi & Fantasy": "Ciencia ficción y fantasía", "Documentary": "Documental",
    "Adventure": "Aventura", "Reality": "Reality", "Science Fiction": "Ciencia ficción",
    "Fantasy": "Fantasía", "Kids": "Infantil", "History": "Historia", "Talk": "Talk show",
    "Soap": "Telenovela", "TV Movie": "Película para TV", "Music": "Música", "War": "Bélica",
    "War & Politics": "Guerra y política", "Western": "Western", "News": "Noticias",
    "Unknown": "Desconocido",
}
GENERO_ORIGINAL = {es: en for en, es in GENEROS_ES.items()}

# Traducciones de los 147 países que trae el catálogo (nombres tal como los escribe el origen).
PAISES_ES = {
    "United States of America": "Estados Unidos", "Japan": "Japón", "United Kingdom": "Reino Unido",
    "China": "China", "South Korea": "Corea del Sur", "France": "Francia", "Canada": "Canadá",
    "Germany": "Alemania", "India": "India", "Spain": "España", "Belgium": "Bélgica", "Italy": "Italia",
    "Mexico": "México", "Philippines": "Filipinas", "Hong Kong": "Hong Kong", "Australia": "Australia",
    "Brazil": "Brasil", "Russia": "Rusia", "Turkey": "Turquía", "Sweden": "Suecia", "Thailand": "Tailandia",
    "Denmark": "Dinamarca", "Netherlands": "Países Bajos", "Poland": "Polonia", "Ireland": "Irlanda",
    "Taiwan": "Taiwán", "Egypt": "Egipto", "Norway": "Noruega", "Argentina": "Argentina", "Chile": "Chile",
    "Czech Republic": "República Checa", "Switzerland": "Suiza", "Colombia": "Colombia", "Austria": "Austria",
    "South Africa": "Sudáfrica", "Finland": "Finlandia", "Portugal": "Portugal", "Indonesia": "Indonesia",
    "Israel": "Israel", "Greece": "Grecia", "New Zealand": "Nueva Zelanda", "Hungary": "Hungría",
    "Bulgaria": "Bulgaria", "Luxembourg": "Luxemburgo", "Pakistan": "Pakistán", "Malaysia": "Malasia",
    "Romania": "Rumania", "Ukraine": "Ucrania", "Singapore": "Singapur", "Serbia": "Serbia",
    "United Arab Emirates": "Emiratos Árabes Unidos", "Iceland": "Islandia", "Slovakia": "Eslovaquia",
    "Iran": "Irán", "Venezuela": "Venezuela", "Lebanon": "Líbano", "Morocco": "Marruecos", "Croatia": "Croacia",
    "Saudi Arabia": "Arabia Saudita", "Estonia": "Estonia", "Lithuania": "Lituania", "Vietnam": "Vietnam",
    "Syrian Arab Republic": "Siria", "Peru": "Perú", "Uruguay": "Uruguay", "Puerto Rico": "Puerto Rico",
    "Georgia": "Georgia", "Iraq": "Irak", "Latvia": "Letonia", "Malta": "Malta", "Slovenia": "Eslovenia",
    "Dominican Republic": "República Dominicana", "Qatar": "Catar", "Cuba": "Cuba", "Nigeria": "Nigeria",
    "Cyprus": "Chipre", "Kazakhstan": "Kazajistán", "Kuwait": "Kuwait", "Cambodia": "Camboya",
    "Tunisia": "Túnez", "Jordan": "Jordania", "Macedonia": "Macedonia del Norte",
    "Bosnia and Herzegovina": "Bosnia y Herzegovina", "Bangladesh": "Bangladés", "Sri Lanka": "Sri Lanka",
    "Mongolia": "Mongolia", "Guatemala": "Guatemala", "Algeria": "Argelia", "Kenya": "Kenia",
    "Bahamas": "Bahamas", "Cameroon": "Camerún", "Paraguay": "Paraguay",
    "Palestinian Territory": "Territorio Palestino", "Belarus": "Bielorrusia", "Afghanistan": "Afganistán",
    "Montenegro": "Montenegro", "Cote D'Ivoire": "Costa de Marfil", "Ethiopia": "Etiopía", "Bolivia": "Bolivia",
    "Albania": "Albania", "Nepal": "Nepal", "Mauritius": "Mauricio", "Kyrgyz Republic": "Kirguistán",
    "French Polynesia": "Polinesia Francesa", "New Caledonia": "Nueva Caledonia",
    "St. Kitts and Nevis": "San Cristóbal y Nieves", "Lao People's Democratic Republic": "Laos",
    "Senegal": "Senegal", "Tanzania": "Tanzania", "Congo": "Congo", "Faeroe Islands": "Islas Feroe",
    "Bhutan": "Bután", "Panama": "Panamá", "Azerbaijan": "Azerbaiyán", "Macao": "Macao", "Angola": "Angola",
    "Ecuador": "Ecuador", "Monaco": "Mónaco", "Uganda": "Uganda", "Namibia": "Namibia", "Ghana": "Ghana",
    "Vanuatu": "Vanuatu", "Malawi": "Malaui", "Guadaloupe": "Guadalupe", "Myanmar": "Myanmar", "Zambia": "Zambia",
    "Cayman Islands": "Islas Caimán", "Armenia": "Armenia", "Uzbekistan": "Uzbekistán", "Kosovo": "Kosovo",
    "Rwanda": "Ruanda", "Botswana": "Botsuana", "Mauritania": "Mauritania", "Aruba": "Aruba",
    "Netherlands Antilles": "Antillas Neerlandesas", "Liechtenstein": "Liechtenstein",
    "United States Minor Outlying Islands": "Islas Menores Alejadas de EE. UU.",
    "US Virgin Islands": "Islas Vírgenes de EE. UU.", "Greenland": "Groenlandia", "Nicaragua": "Nicaragua",
    "Central African Republic": "República Centroafricana", "St. Lucia": "Santa Lucía", "Palau": "Palaos",
    "Brunei Darussalam": "Brunéi", "Fiji": "Fiyi", "Solomon Islands": "Islas Salomón",
    "St. Pierre and Miquelon": "San Pedro y Miquelón",
}


def _a_lista(col, traduccion):
    """'A, B, A' -> ['A', 'B'] (sin repetidos, conservando el ORDEN del origen: el primero es el
    país/género principal), con cada nombre traducido. Un nombre que no esté en el diccionario
    se deja tal cual en vez de fallar (tests/verificar_reglas.py comprueba que los CSV no traigan ninguno sin traducir)."""
    def limpiar(xs):
        vistos = dict.fromkeys(x.strip() for x in xs if x.strip())
        return [traduccion.get(x, x) for x in vistos]
    return col.fillna("").str.split(",").map(limpiar)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, list, list]:
    df_m = pd.read_csv(RUTA_DATOS / ARCHIVO_PELICULAS)
    df_s = pd.read_csv(RUTA_DATOS / ARCHIVO_SERIES)
    df_m["type"] = "Película"
    df_s["type"] = "Serie"
    df = pd.concat([df_m, df_s], ignore_index=True)
    df["generos"] = _a_lista(df["genres"], GENEROS_ES)
    df["paises"] = _a_lista(df["country"], PAISES_ES)
    # date_added, duration, language, budget y revenue no las usa ningún gráfico todavía, pero se
    # conservan sin transformar (budget/revenue quedan NaN en las filas de Serie, que no las trae
    # el CSV de origen) para análisis futuros sin tener que volver a tocar el loader.
    df = df[[
        "title", "type", "release_year", "date_added", "duration", "language", "budget", "revenue",
        "popularity", "vote_count", "vote_average", "generos", "paises",
    ]]
    # Opciones de filtro ordenadas de más a menos frecuentes
    generos = df["generos"].explode().value_counts().index.tolist()
    paises = df["paises"].explode().value_counts().index.tolist()
    return df, generos, paises


@st.cache_data
def perfil_fuente():
    """Hechos de los CSV de ORIGEN que `load_data` descarta o transforma y que la metodología (popover «ⓘ Sobre los datos» y docs/metodologia.md) cita:
    qué columnas tiene cada archivo y qué contiene realmente `rating` (se descarta al cargar, así que solo
    se puede comprobar leyendo el archivo crudo)."""
    crudos = {
        "Película": pd.read_csv(RUTA_DATOS / ARCHIVO_PELICULAS),
        "Serie": pd.read_csv(RUTA_DATOS / ARCHIVO_SERIES),
    }
    rating = [d["rating"] for d in crudos.values()]
    return {
        "archivos": {"Película": ARCHIVO_PELICULAS, "Serie": ARCHIVO_SERIES},
        "columnas_solo_peliculas": sorted(set(crudos["Película"].columns) - set(crudos["Serie"].columns)),
        "rating_numerico": all(pd.api.types.is_numeric_dtype(r) for r in rating),
        "rating_igual_vote_average": all(
            bool((d["rating"].fillna(-1) == d["vote_average"].fillna(-1)).all()) for d in crudos.values()
        ),
        "rating_min": float(min(r.min() for r in rating)), "rating_max": float(max(r.max() for r in rating)),
    }
