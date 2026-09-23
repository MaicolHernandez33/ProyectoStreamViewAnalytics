<!-- Documento generado por `python -m src.metodologia` a partir de src/metodologia.py y src/metrics.py. No se edita a mano: se regenera. -->

# Metodología y limitaciones

Cómo se calculó cada cifra del dashboard y qué no permite concluir. Describe el catálogo completo, no una selección de filtros. En el dashboard solo se muestra un resumen (botón «Datos»); este documento es el texto completo.

## Lo esencial

1. **Datos.** Dos archivos CSV del proyecto, uno de películas y otro de series, con 32.000 títulos estrenados entre 2010 y 2025 (detalle en «Fuente de datos»).
2. **Qué controla el análisis.** Los filtros de la barra lateral: toda cifra se recalcula sobre la selección. Géneros y mercados se comparan con la popularidad relativa a la mediana de su formato, y la valoración usa los cortes 4 y 7.
3. **Qué no permite concluir.** Ni tendencias de volumen de producción (el reparto por año y formato es exacto, lo que sugiere generación sintética) ni la popularidad como audiencia absoluta ni comparable entre años (es un índice relativo de TMDB) ni el año 2025 (está incompleto).

## Fuente de datos

El dashboard integra dos archivos CSV: `netflix_movies_detailed_up_to_2025.csv` (16.000 películas) y `netflix_tv_shows_detailed_up_to_2025.csv` (16.000 series). En total son 32.000 títulos estrenados entre 2010 y 2025.

Los gráficos usan las columnas `title`, `type`, `release_year`, `popularity`, `vote_count`, `vote_average`, `genres` y `country`. Géneros y países vienen como texto separado por comas: se convierten en una lista por título, se traducen al español al cargar (el nombre original se conserva en el tooltip de géneros) y se respeta el orden de origen, de modo que el primer país listado se toma como país principal.

`date_added`, `duration`, `language`, `budget` y `revenue` se conservan al cargar pero no se usan todavía; `budget` y `revenue` existen solo en el archivo de películas. La columna `rating` se descartó (ver Limitaciones).

## Métricas derivadas

| Métrica | Cómo se calcula | Dónde aparece |
|---|---|---|
| **Popularidad mediana** | Mediana de `popularity` de los títulos de la selección, por formato, por año o por género según el gráfico. Se usa la mediana y no el promedio porque la distribución es asimétrica. El indicador global muestra la de cada formato. | Indicador, Evolución |
| **Popularidad relativa a su formato** | Popularidad de cada título ÷ mediana de popularidad de SU formato en la selección (1,0 = igual a esa mediana). Por género y por país se resume con la mediana de esos valores. Sin ella, los géneros que existen en un solo formato heredarían la diferencia entre formatos. Solo entran géneros y países con al menos 150 títulos. | Géneros, Mercados, Resumen |
| **Razón series / películas por año** | Popularidad mediana de las series ÷ la de las películas en cada año. Los extremos son el primer y el último año COMPLETO (se excluye el año parcial). Un formato «supera» al otro desde 1,2×. | Evolución, Resumen |
| **Ventaja en valoración alta** | % de títulos con valoración alta de las series − % de las películas, en puntos porcentuales, por año y sobre todos los títulos de cada formato (la misma definición de la pestaña Valoración). A diferencia de `popularity`, no depende del índice relativo de TMDB. | Evolución, Resumen |
| **Valoración mediana** | Mediana de `vote_average` por año y formato, solo con títulos de al menos 10 votos. | Evolución |
| **Nivel de valoración** | Según `vote_average`: baja `[0, 4)`, media `[4, 7)` y alta `[7, 10]`. «Sin votos» agrupa los títulos con `vote_count` = 0 o `vote_average` = 0: es dato faltante, no un nivel de valoración. | Valoración, Resumen |
| **Catálogo bien evaluado** | % de los títulos de la selección con `vote_average` ≥ 7 y al menos 50 votos. El denominador incluye a los títulos sin votos suficientes, por eso es menor que la proporción de valoraciones altas de la pestaña Valoración. | Indicador |
| **Popularidad alta (P75)** | Percentil 75 de `popularity` entre los títulos con al menos N votos (N = 50 por defecto; se ajusta con el control de la Matriz). | Matriz |
| **Títulos en riesgo** | Popularidad ≥ P75 y `vote_average` < 6. El indicador global siempre usa N = 50; la Matriz usa el N que elijas, así que ambas cifras coinciden solo con el valor por defecto. | Indicador, Matriz |
| **Activos a retener** | Popularidad ≥ P75 y `vote_average` ≥ 7. | Matriz |
| **Cuadrantes de género** | Con los géneros más frecuentes (hasta 15): volumen = títulos del género y rendimiento = su popularidad relativa a su formato. La mediana de títulos de los géneros graficados y 1,0 dividen el plano en cuatro cuadrantes. Un género a menos de 10% de 1,0 «rinde como su formato» y no se clasifica. El color indica en qué formato existe el género. | Géneros |
| **Concentración geográfica** | % de los títulos con país registrado cuyo primer país listado es uno de los 3 primeros mercados (modo por defecto), o que incluyen al menos uno de ellos (modo «Coproducciones»). | Mercados, Resumen |
| **Mercados destino** | Hasta 2 países con la mayor popularidad relativa (mayor que 1,0) entre los que tienen al menos 150 títulos, sin contar los mercados que hoy concentran el catálogo. | Mercados, Resumen |

## Criterios de corte

| Criterio | Valor | Uso |
|---|---|---|
| **Valoración alta / media / baja** | ≥ 7 / ≥ 4 / < 4 | Nivel de valoración de cada título. |
| **Valoración de riesgo** | < 6 | Un título popular con valoración menor que este corte está en riesgo de abandono. |
| **Franja neutra** | 6–7 | No se clasifica en la Matriz. Se mantiene el corte de riesgo en 6 para que la Matriz y el indicador «Títulos en riesgo» cuenten lo mismo. |
| **Votos mínimos** | 50 (ajustable) | Indicadores y Matriz. La valoración por año usa 10 votos. |
| **Popularidad alta** | ≥ P75 | Percentil 75 entre los títulos con votos suficientes. |
| **Diferencia relevante entre formatos** | 1,2× en popularidad; 0,3 puntos en valoración | Bajo esos valores los títulos hablan de resultados similares. |
| **Cambio de una tendencia** | 15% en la razón; 2 puntos en la ventaja de valoración alta; 0,2 puntos en la brecha de valoración mediana | Entre el primer y el último año completo: bajo esos valores la ventaja «se mantiene». |
| **Concentración geográfica** | ≥ 30% | Los 3 primeros mercados juntos: desde este % se habla de diversificación limitada. |
| **Banda de popularidad relativa** | ±10% de 1,0 | Géneros que rinden tan cerca de su formato que no se clasifican. No se ajusta para forzar un resultado: un cuadrante vacío es un hallazgo. |
| **Títulos mínimos para popularidad relativa** | 150 | Géneros y países con menos títulos no entran a los rankings: una mediana sobre muy pocos títulos es ruido. |
| **Cantidad de elementos** | 15 géneros, 10 países, 5 títulos de riesgo | Con más géneros las etiquetas del gráfico de burbujas se pisan. |
| **Anotación de caída** | ≥ 10% en 2020 | La flecha del gráfico de evolución solo se dibuja si las series caen al menos este % respecto del año anterior. |

## Limitaciones

1. **Distribución uniforme por año y reparto exacto entre formatos.** El catálogo tiene 16.000 películas y 16.000 series (50% y 50%) y cada formato aporta exactamente 1.000 títulos por año entre 2010 y 2025. Un reparto tan regular sugiere generación sintética y limita las conclusiones sobre tendencias de producción: por eso el dashboard no analiza cuántos títulos se estrenan por año, solo su popularidad y valoración.
2. **`popularity` es un índice relativo de TMDB, sin unidad interpretable.** Sirve para ordenar títulos, no para medir audiencia: no es comparable entre años ni interpretable en unidades absolutas. Por eso se resume con medianas y se compara entre grupos, no como valor absoluto.
3. **2025 está incompleto.** Se marca como año parcial en los gráficos de evolución y en la tabla de títulos en riesgo. Sus títulos aún no acumulan votos: 68% no tiene votos, frente a 11% de los años anteriores, y su popularidad mediana es 9,8 contra 23,0. Sus valores no deben leerse como una caída real de popularidad ni de valoración.
4. **La ventaja de las series en popularidad se estrecha.** En el catálogo completo, la razón entre formatos pasó de 4,2× (2010) a 1,2× (2024), último año completo. El estrechamiento ocurre en dos tramos: en 2020 la mediana de las series cae 34% (de 45,9 a 30,3) y entre 2020 y 2024 la de las películas sube de 10,3 a 27,7. Parte puede deberse a que el índice de TMDB favorece a los estrenos recientes de cine (mediana de películas 2024: 27,7 vs 2010: 7,7); los datos no permiten confirmarlo. Por eso la prioridad de las series se sostiene además con la valoración alta, cuya ventaja pasó de +18 a +34 puntos y no depende de ese índice.
5. **Las coproducciones se contabilizan en cada país participante.** 5.365 títulos (17%) listan más de un país. Con «Coproducciones» un título suma en todos sus países y los totales superan al catálogo; por defecto solo cuenta el primer país listado. 2.263 títulos no tienen país registrado y quedan fuera de esos gráficos.
6. **Los títulos multi-género se contabilizan en cada categoría.** 20.808 títulos (65%) tienen más de un género, por lo que las cantidades por género suman más que el catálogo y sus porcentajes, más de 100%. 1.081 títulos no tienen género registrado.
7. **La columna `rating` no es una clasificación etaria.** Contiene valores numéricos entre 0 y 10 y coincide con `vote_average` en ambos archivos, así que no permite analizar la audiencia por edad y se descartó del análisis.
8. **Los géneros de películas y series no coinciden del todo.** 20 de los 28 géneros existen en un solo formato (por ejemplo «Acción», «Acción y aventura» y «Aventura»), porque el origen usa categorías distintas para cada uno. Las comparaciones entre géneros y entre mercados se controlan por formato mediante la popularidad relativa: cada título se divide por la mediana de su formato antes de resumirse. Aun así, un género que existe en un solo formato solo se compara con los títulos de ese formato.
9. **Los umbrales son criterios de este análisis.** Los cortes de valoración, votos mínimos, percentil, bandas y mínimo de títulos (ver «Criterios de corte») están definidos para este dashboard y no vienen del origen de datos: otro criterio cambiaría qué títulos se consideran en riesgo o bien evaluados. El control de votos mínimos de la Matriz permite explorar ese efecto.
