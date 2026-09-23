"""
Mide el dashboard en un Chrome REAL sin ventana (headless): lo que AppTest no ve, porque depende del navegador y del CSS.

    python tests/verificar_pantalla.py

Necesita Chrome o Chromium instalado (variable CHROME_PATH si no está en la ruta habitual). Levanta el dashboard en un puerto
propio y lo cierra al terminar. Comprueba, con viewport de 1920×1080:
  · la franja de KPIs es un solo contenedor con 4 celdas, ninguna desborda, y el valor de cada una mide 20 px;
  · el bloque superior (título → fondo de la franja de KPIs, con la barra de filtros) se mide y se informa;
  · en el Resumen, la tesis es el ÚNICO elemento de 32 px de la página, sin recuadro, y «Qué hacer» numera sus 3 ítems sin
    números grandes; todo el Resumen se ve sin hacer scroll;
  · en una página analítica (Géneros), el número del panel es el ÚNICO elemento de 32 px de la página;
  · el RIEL de navegación (Paso 2): logo arriba, 6 páginas con ícono, la activa SIN fondo (solo ícono en PELICULA/rojo
    y texto en TEXT con peso 600; las inactivas en TEXT_MUTED), CSV y «Datos» al pie, y logo + 6 íconos + CSV + «Datos»
    compartiendo el mismo centro horizontal del riel (±1 px) — es la comprobación que fija en pantalla la nota de
    aislación de theme.py: si un testid del que depende esta CSS desapareciera en una versión de Streamlit, esto (y
    solo esto) fallaría;
  · la BARRA DE FILTROS horizontal: Formato (segmented_control con los puntos rojo/gris de Película/Serie) y los tres
    popover (Años/Género/País), y el popover «Datos» del riel: mismo contenido completo, abre y cierra;
  · 4 ajustes puntuales: la opción activa del segmented_control usa fondo BORDER y texto TEXT (sin el rojo de "Película"
    que traía por defecto el tema de Streamlit); ≥16 px entre la línea roja del header y la barra de filtros; los
    controles de la barra agrupados a la izquierda con huecos uniformes, el espacio sobrante a la derecha; ≥32 px entre
    la franja de KPIs y el título de la página; el botón nativo de colapsar el riel, oculto;
y con viewports más angostos (1600, 1440, 1366 px) que la franja de KPIs no desborde. Luego hace clic en cada una de las 6
páginas del riel: sin excepciones, con su tarjeta de gráfico (control a la izquierda, leyenda a la derecha) y «Cómo leer
este gráfico» en la forma que corresponde (abierto o en expander cerrado); y en la Matriz, la lista de riesgo (no tabla)
con su descarga, y ya no hay una tabla dentro del expander.
"""
import sys
import time

from _comun import Verificador
from _navegador import Chrome, Servidor, abrir_dashboard, buscar_chrome

v = Verificador("Dashboard en Chrome real (headless): medidas, alineación y clic en cada página")
if not buscar_chrome():
    print("  · No se encontró Chrome/Chromium: se omite (defina CHROME_PATH). Esto NO cuenta como aprobado.")
    sys.exit(0)

JS_KPIS = """(() => { const franja=document.querySelector('.kpi-franja'); const celdas=[...document.querySelectorAll('.kpi-celda')];
 const top=document.querySelector('.hdr-title').getBoundingClientRect().top;
 return {hayFranja: !!franja, nCeldas: celdas.length,
  desbordan: celdas.filter(c=>c.scrollHeight>c.clientHeight+1).length,
  fuenteValor: celdas.length ? getComputedStyle(celdas[0].querySelector('.kpi-valor')).fontSize : null,
  soloRiesgoRojo: celdas.filter(c=>c.querySelector('.kpi-icono--riesgo')).length,
  bloque: franja ? Math.round(franja.getBoundingClientRect().bottom-top) : null,
  h1: getComputedStyle(document.querySelector('.hdr-title')).fontSize,
  inter: [...document.fonts].filter(f=>f.family.includes('Inter') && f.status==='loaded').length}})()"""


def js_tamano_unico(tam):
    """Nombres de clase de los elementos del contenido principal (no la sidebar) cuyo texto se ve en `tam` px
    (para comprobar que solo hay uno)."""
    return (
        '(() => { const p=document.querySelector(\'[data-testid="stMain"]\');'
        f' const con=[...p.querySelectorAll("*")].filter(e=>[...e.childNodes].some(n=>n.nodeType===3 && n.textContent.trim()) && getComputedStyle(e).fontSize==="{tam}px");'
        ' return con.map(e=>e.className || e.tagName) })()'
    )


JS_RESUMEN = """(() => { const p=document.querySelector('[data-testid="stMain"]'); const r=e=>e.getBoundingClientRect();
 const tesis=p.querySelector('.tesis-titular'), lista=p.querySelector('.hacer-lista'), enlace=p.querySelector('.hacer-enlace');
 const indices=[...p.querySelectorAll('.hacer-indice')].map(e=>e.innerText.trim());
 const ultimo=[...p.querySelectorAll('*')].reduce((m,e)=>Math.max(m, r(e).bottom), 0);
 return {tesisSinCaja: tesis ? getComputedStyle(tesis.parentElement).backgroundColor : null, indices,
         fondoContenido: Math.round(ultimo), altoVentana: innerHeight, tieneLista: !!lista, tieneEnlace: !!enlace} })()"""

# ------------------------------------------------------------ Riel de navegación (Paso 2): logo, 6 páginas, activa en
# rojo, CSV + «Datos» al pie. Es la comprobación EN PANTALLA de la nota de aislación de theme.py (solo testids/ARIA).
JS_RIEL = """(() => { const rect = e => e ? e.getBoundingClientRect() : null;
 const riel = document.querySelector('[data-testid="stSidebar"]');
 const logo = document.querySelector('[data-testid="stSidebarLogo"]');
 const links = [...document.querySelectorAll('[data-testid="stSidebarNavLink"]')];
 const activo = document.querySelector('[data-testid="stSidebarNavLink"][aria-current="page"]');
 const iconoActivo = activo ? activo.querySelector('[data-testid="stIconMaterial"]') : null;
 // st.download_button (CSV) monta un botón visible y uno oculto (mecanismo interno de Streamlit); solo cuenta el visible.
 // innerText del botón trae también el ícono ("download"/"info") y, en el popover, la flecha ("expand_more"): se
 // extrae solo la etiqueta, del <p> dentro de stMarkdownContainer.
 const botonesPie = [...document.querySelectorAll('[data-testid="stSidebarUserContent"] button')].filter(b => b.offsetParent !== null);
 return {
   anchoRiel: riel ? Math.round(rect(riel).width) : null,
   logoAncho: logo ? Math.round(rect(logo).width) : 0,
   nLinks: links.length,
   etiquetas: links.map(l => l.innerText.trim().split('\\n').pop()),
   activaEtiqueta: activo ? activo.innerText.trim().split('\\n').pop() : null,
   colorIconoActivo: iconoActivo ? getComputedStyle(iconoActivo).color : null,
   colorFondoActivo: activo ? getComputedStyle(activo).backgroundColor : null,
   etiquetasPie: botonesPie.map(b => (b.querySelector('[data-testid="stMarkdownContainer"] p') || {}).innerText || b.innerText.trim()),
 } })()"""

JS_BARRA_FILTROS = """(() => { const barra = document.querySelector('.st-key-barra_filtros');
 if (!barra) return null;
 const seg = [...barra.querySelectorAll('button[data-variant="segmented_control"]')];
 const pops = [...barra.querySelectorAll('[data-testid="stPopoverButton"]')];
 return {
   nSegmentos: seg.length, etiquetasSeg: seg.map(b => b.innerText.trim()),
   colorPuntoPelicula: seg[1] ? getComputedStyle(seg[1].querySelector('p'), '::before').content : null,
   nPopovers: pops.length, etiquetasPop: pops.map(b => b.innerText.trim().replace(/\\s+/g, ' ')),
 } })()"""

JS_CUERPO = """(() => { const b = document.querySelector('[data-testid="stPopoverBody"]'); if (!b) return null; const r = b.getBoundingClientRect();
 const ol = b.querySelector('ol.meto-lista'), ul = b.querySelector('ul.meto-lista'), t = b.innerText;
 return {esenciales: ol ? ol.querySelectorAll('li').length : 0, limitaciones: ul ? ul.querySelectorAll('li').length : 0,
   tablas: b.querySelectorAll('table').length, codigo: b.querySelectorAll('code, pre').length,
   lo_esencial: /lo esencial/i.test(t), limitaciones_clave: /limitaciones clave/i.test(t),
   cierre: t.trim().endsWith('Metodología completa en el informe del proyecto.'),
   recortado: b.scrollHeight > b.clientHeight + 1, dentro: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight} })()"""

JS_TARJETA = """(() => { const p=document.querySelector('[data-testid="stMain"]'); const card=p.querySelector('[class*="st-key-grafico_"]');
 if (!card) return null; const r=e=>e.getBoundingClientRect();
 const cab=card.querySelector('.tarjeta-cabecera'); const leyenda=card.querySelector('.leyenda');
 const ctrl=cab ? [...cab.parentElement.querySelectorAll('[data-testid="stRadio"],[data-testid="stSlider"]')][0] : null;
 return {hayTarjeta: true, tieneLeyenda: !!leyenda, leyendaTexto: leyenda ? leyenda.innerText.trim() : null,
   leyendaDerecha: leyenda ? Math.round(r(leyenda).right) : null, cardDerecha: Math.round(r(card).right),
   controlIzquierda: ctrl ? Math.round(r(ctrl).left) : null, cardIzquierda: Math.round(r(card).left),
   plot: !!card.querySelector('.js-plotly-plot'),
   fondoPlot: (() => { const bg = card.querySelector('.js-plotly-plot .bg'); return bg ? getComputedStyle(bg).fillOpacity : null })()} })()"""

JS_COMO_LEER = """(() => { const p=document.querySelector('[data-testid="stMain"]');
 return {abierto: !!p.querySelector('.como-leer'), expander: !!p.querySelector('[data-testid="stExpander"]'),
         textoExpander: (p.querySelector('[data-testid="stExpander"] summary')||{}).innerText || null} })()"""

JS_RIESGO = """(() => { const p=document.querySelector('[data-testid="stMain"]'); const filas=[...p.querySelectorAll('.riesgo-fila')];
 const descarga=p.querySelector('[class*="st-key-descargar_riesgo"] button'); const tabla=p.querySelector('[data-testid="stDataFrame"]');
 return {nFilas: filas.length, hayDescarga: !!descarga, hayTablaVieja: !!tabla,
   titulosTruncados: filas.map(f=>{const t=f.querySelector('.riesgo-titulo'); return t ? t.scrollWidth > t.clientWidth + 1 || t.title.length>0 : false})} })()"""


# ------------------------------------------------------------ 4 ajustes pedidos sobre el riel/barra de filtros:
# botón activo sin rojo, separación bajo la línea roja, controles agrupados a la izquierda, aire KPI->título, logo
# centrado con margen superior, botón de colapsar oculto.
JS_AJUSTES = """(() => { const r = e => e.getBoundingClientRect();
 const activo = document.querySelector('.st-key-barra_filtros button[data-variant="segmented_control"][aria-checked="true"]');
 const csAct = activo ? getComputedStyle(activo) : null;
 const linea = document.querySelector('.grad-line'), barra = document.querySelector('.st-key-barra_filtros');
 const gapLineaBarra = (linea && barra) ? r(barra).top - r(linea).bottom : null;
 const hijos = barra ? [...barra.children].filter(h => r(h).width > 0) : [];
 const huecos = [];
 for (let i = 1; i < hijos.length; i++) huecos.push(Math.round(r(hijos[i]).left - r(hijos[i - 1]).right));
 const ultimoDer = hijos.length ? Math.round(r(hijos[hijos.length - 1]).right) : null;
 const barraDer = barra ? Math.round(r(barra).right) : null;
 const franja = document.querySelector('.kpi-franja');
 const titulo = document.querySelector('[data-testid="stMain"] .tesis-titular') || document.querySelector('[data-testid="stMain"] .grafico-titulo');
 const gapKpiTitulo = (franja && titulo) ? r(titulo).top - r(franja).bottom : null;
 const riel = document.querySelector('[data-testid="stSidebar"]'), logo = document.querySelector('[data-testid="stSidebarLogo"]');
 const colapsar = document.querySelector('[data-testid="stSidebarCollapseButton"]');
 const centro = e => e ? (r(e).left + r(e).right) / 2 : null;
 // Corrección «riel v1»: logo, los 6 íconos de navegación, CSV y «Datos» deben compartir el mismo eje central del
 // riel — la causa real de que antes NO coincidieran era un padding lateral de 20px que Streamlit le pone por
 // defecto a stSidebarContent (invisible con el sidebar ancho del Paso 1, devastador con el riel angosto de 84px:
 // dejaba solo 44px reales de espacio, y ni siquiera centrados). Se mide el centro de CADA elemento, no solo el CSS.
 const links = [...document.querySelectorAll('[data-testid="stSidebarNavLink"]')];
 const centroIconos = links.map(l => centro(l.querySelector('[data-testid="stIconMaterial"]')));
 const botonesPie = [...document.querySelectorAll('[data-testid="stSidebarUserContent"] button')].filter(b => b.offsetParent !== null);
 const centrosPie = botonesPie.map(centro);
 // Sección activa (corrección «riel v1»): SOLO ícono en PELICULA y texto en TEXT/600, sin cápsula de fondo; las
 // inactivas se quedan en TEXT_MUTED tanto en el ícono como en el texto.
 const activoNav = document.querySelector('[data-testid="stSidebarNavLink"][aria-current="page"]');
 const inactivoNav = links.find(l => l !== activoNav);
 const estiloNav = l => { if (!l) return null; const ic = l.querySelector('[data-testid="stIconMaterial"]');
   const p = l.querySelector('span[label] [data-testid="stMarkdownContainer"] p');
   return {bg: getComputedStyle(l).backgroundColor, iconoColor: ic ? getComputedStyle(ic).color : null,
     textoColor: p ? getComputedStyle(p).color : null, textoPeso: p ? getComputedStyle(p).fontWeight : null}; };
 return {
   activoBg: csAct ? csAct.backgroundColor : null, activoBorderColor: csAct ? csAct.borderColor : null, activoColor: csAct ? csAct.color : null,
   gapLineaBarra: gapLineaBarra === null ? null : Math.round(gapLineaBarra),
   huecos, espacioSobranteDerecha: (barraDer !== null && ultimoDer !== null) ? barraDer - ultimoDer : null,
   gapKpiTitulo: gapKpiTitulo === null ? null : Math.round(gapKpiTitulo),
   centroLogo: centro(logo), centroRiel: riel ? (r(riel).left + r(riel).right) / 2 : null,
   logoTop: logo ? Math.round(r(logo).top) : null,
   colapsarVisible: colapsar ? getComputedStyle(colapsar).display !== 'none' : false,
   centroIconos, centrosPie,
   navActivo: estiloNav(activoNav), navInactivo: estiloNav(inactivoNav),
 } })()"""


def js_clic_pagina(nombre):
    return (
        "(() => { const l = [...document.querySelectorAll('[data-testid=\"stSidebarNavLink\"]')]"
        f".find(e => e.innerText.includes({nombre!r})); if (!l) return false; l.click(); return true; }})()"
    )


ESPERA = {  # qué debe estar dibujado en cada página, y cuántos gráficos Plotly
    "Resumen": (".tesis-titular", 1), "Géneros": (".grafico-titulo", 1), "Mercados": (".grafico-titulo", 1), "Evolución": (".grafico-titulo", 1),
    "Valoración": (".grafico-titulo", 1), "Matriz": (".grafico-titulo", 1),
}
ABIERTAS, CERRADAS = ("Géneros", "Evolución", "Valoración"), ("Mercados", "Matriz")
PELICULA_RGB, SERIE_RGB = "rgb(229, 9, 20)", "rgb(179, 179, 184)"

with Servidor() as servidor:
    # ------------------------------------------------------------ 1920×1080 — Resumen
    with Chrome(1920, 1080) as ch:
        abrir_dashboard(ch, servidor.url)
        # Resumen es la página default, pero un app multipágina (Paso 2) tarda un instante más en asentar su PROPIO
        # contenido que el riel/KPIs genéricos que ya espera abrir_dashboard(): sin esto, «Qué hacer» se lee vacío
        # de forma intermitente.
        ch.esperar("document.querySelector('[data-testid=\"stMain\"] .hacer-lista')", 20)
        k = ch.evaluar(JS_KPIS)
        v.comprobar("[1920] la franja de KPIs es un solo contenedor con 4 celdas", k["hayFranja"] and k["nCeldas"] == 4, str(k))
        v.comprobar("[1920] ninguna celda de la franja desborda", k["desbordan"] == 0, k["desbordan"])
        v.comprobar("[1920] el valor de cada KPI mide 20 px", k["fuenteValor"] == "20px", k["fuenteValor"])
        v.comprobar("[1920] solo la celda «Títulos en riesgo» tiene ícono rojo", k["soloRiesgoRojo"] == 1, k["soloRiesgoRojo"])
        v.info(f"bloque superior medido: {k['bloque']} px (título → fondo de la franja de KPIs, con la barra de filtros)")
        v.comprobar("[1920] el H1 del header mide 20 px (excepción documentada)", k["h1"] == "20px", k["h1"])
        v.info("fuente Inter " + ("cargada desde Google Fonts" if k["inter"] else "NO cargada (sin internet): las medidas usan Arial"))

        con32 = ch.evaluar(js_tamano_unico(32))
        v.comprobar("[1920] en el Resumen la tesis es el ÚNICO elemento de 32 px de la página", con32 == ["tesis-titular"], str(con32))
        r = ch.evaluar(JS_RESUMEN)
        v.comprobar("[1920] la tesis NO tiene recuadro (sin fondo propio: transparente o el mismo BG de la página)",
                    r["tesisSinCaja"] in ("rgba(0, 0, 0, 0)", "rgb(14, 14, 16)", None), r["tesisSinCaja"])
        v.comprobar("[1920] «Qué hacer» numera sus 3 ítems 1, 2, 3 (sin números grandes) y cierra con el enlace a Matriz",
                    r["indices"] == ["1", "2", "3"] and r["tieneLista"] and r["tieneEnlace"], str(r))
        v.comprobar("[1920] todo el Resumen se ve sin hacer scroll (cabe en 1920×1080)", r["fondoContenido"] <= r["altoVentana"],
                    f"contenido hasta {r['fondoContenido']} px de {r['altoVentana']}")

        # ------------------------------------------------------------ Riel de navegación: logo, 6 páginas, CSV+Datos
        riel = ch.evaluar(JS_RIEL)
        v.comprobar("[1920] el riel es angosto (~84 px) y tiene el logo (st.logo) arriba",
                    riel["anchoRiel"] is not None and riel["anchoRiel"] <= 100 and riel["logoAncho"] > 0, str(riel))
        v.comprobar("[1920] el riel tiene exactamente 6 páginas: Resumen, Géneros, Mercados, Evolución, Valoración y Matriz (sin Metodología)",
                    riel["etiquetas"] == ["Resumen", "Géneros", "Mercados", "Evolución", "Valoración", "Matriz"], str(riel["etiquetas"]))
        v.comprobar("[1920] al cargar, «Resumen» es la página activa, con el ícono en PELICULA (rojo) y SIN fondo (se marca solo por color de ícono y peso del texto)",
                    riel["activaEtiqueta"] == "Resumen" and riel["colorIconoActivo"] == PELICULA_RGB and riel["colorFondoActivo"] in (None, "rgba(0, 0, 0, 0)"),
                    str(riel))
        v.comprobar("[1920] el pie del riel tiene CSV y «Datos» (en ese orden)", riel["etiquetasPie"] == ["CSV", "Datos"], str(riel["etiquetasPie"]))

        # ------------------------------------------------------------ Barra de filtros horizontal
        barra = ch.evaluar(JS_BARRA_FILTROS)
        v.comprobar("[1920] Formato es un segmented_control de 3 opciones (Ambos, Película, Serie)",
                    barra is not None and barra["etiquetasSeg"] == ["Ambos", "Película", "Serie"], str(barra))
        v.comprobar("[1920] hay 3 popover en la barra (Años, Género, País), cada uno mostrando su selección actual (Todos)",
                    barra is not None and barra["nPopovers"] == 3 and all(e.startswith(("Años", "Género", "País")) for e in barra["etiquetasPop"])
                    and all("Todos" in e for e in barra["etiquetasPop"]), str(barra and barra["etiquetasPop"]))

        # ------------------------------------------------------------ 4 ajustes pedidos sobre el riel/barra de filtros
        aj = ch.evaluar(JS_AJUSTES)
        v.comprobar("[1920] «Ambos» (opción activa del segmented_control) usa fondo BORDER sólido y texto TEXT, sin rojo ni halo",
                    aj["activoBg"] == "rgb(42, 42, 46)" and aj["activoColor"] == "rgb(242, 242, 243)" and "229, 9, 20" not in (aj["activoBorderColor"] or ""),
                    str(aj))
        v.comprobar("[1920] la barra de filtros tiene al menos 16 px de separación bajo la línea roja de arriba",
                    aj["gapLineaBarra"] is not None and aj["gapLineaBarra"] >= 16, aj["gapLineaBarra"])
        v.comprobar("[1920] los controles de la barra están agrupados a la izquierda con huecos uniformes (≤20 px) entre sí, y el espacio sobrante queda a la derecha",
                    aj["huecos"] and max(aj["huecos"]) <= 20 and aj["espacioSobranteDerecha"] is not None and aj["espacioSobranteDerecha"] > 200,
                    str(aj))
        v.comprobar("[1920] hay al menos 32 px entre la franja de KPIs y el título de la página",
                    aj["gapKpiTitulo"] is not None and aj["gapKpiTitulo"] >= 32, aj["gapKpiTitulo"])
        v.comprobar("[1920] el logo del riel no toca el borde superior (≥20 px)", aj["logoTop"] is not None and aj["logoTop"] >= 20, aj["logoTop"])
        v.comprobar("[1920] el botón nativo de colapsar el riel está oculto", aj["colapsarVisible"] is False, aj["colapsarVisible"])

        # ------------------------------------------------------------ Corrección «riel v1»: logo, los 6 íconos, CSV y
        # «Datos» comparten el mismo centro horizontal del riel (medido elemento por elemento, no solo el CSS); la
        # sección activa se marca solo con ícono PELICULA y texto TEXT/600, sin cápsula de fondo.
        v.comprobar("[1920] logo, los 6 íconos de navegación, CSV y «Datos» comparten el mismo centro horizontal del riel (±1 px)",
                    aj["centroLogo"] is not None and aj["centroRiel"] is not None
                    and abs(aj["centroLogo"] - aj["centroRiel"]) <= 1
                    and len(aj["centroIconos"]) == 6 and all(c is not None and abs(c - aj["centroRiel"]) <= 1 for c in aj["centroIconos"])
                    and len(aj["centrosPie"]) == 2 and all(c is not None and abs(c - aj["centroRiel"]) <= 1 for c in aj["centrosPie"]),
                    str(aj))
        v.comprobar("[1920] la sección activa del riel se marca SOLO con ícono en PELICULA y texto en TEXT/600, sin fondo; la inactiva queda en TEXT_MUTED (ícono y texto)",
                    aj["navActivo"] is not None and aj["navActivo"]["bg"] in ("rgba(0, 0, 0, 0)", "transparent")
                    and aj["navActivo"]["iconoColor"] == PELICULA_RGB and aj["navActivo"]["textoColor"] == "rgb(242, 242, 243)"
                    and str(aj["navActivo"]["textoPeso"]) in ("600", "bold")
                    and aj["navInactivo"] is not None and aj["navInactivo"]["iconoColor"] == "rgb(154, 154, 160)"
                    and aj["navInactivo"]["textoColor"] == "rgb(154, 154, 160)",
                    str(aj))

        # ------------------------------------------------------------ una página analítica (Géneros): único 32 px es el panel
        ch.evaluar(js_clic_pagina("Géneros"))
        ch.esperar("document.querySelector('[data-testid=\"stMain\"] .panel-num')", 20)
        con32_generos = ch.evaluar(js_tamano_unico(32))
        v.comprobar("[1920] en Géneros el número del panel es el ÚNICO elemento de 32 px de la página", con32_generos == ["panel-num"], str(con32_generos))
        tarjeta = ch.evaluar(JS_TARJETA)
        # La tarjeta tiene padding:18px 20px (theme.py): la leyenda queda a ~20px del borde EXTERNO de la tarjeta, no pegada a él.
        v.comprobar("[1920] la tarjeta del gráfico de Géneros tiene leyenda en su cabecera, dentro del padding derecho de la tarjeta",
                    tarjeta is not None and tarjeta["tieneLeyenda"] and 0 <= tarjeta["cardDerecha"] - tarjeta["leyendaDerecha"] <= 30, str(tarjeta))
        v.comprobar("[1920] el fondo del gráfico es transparente (fill-opacity 0): se funde con la tarjeta SURFACE",
                    tarjeta is not None and tarjeta["fondoPlot"] == "0", str(tarjeta and tarjeta["fondoPlot"]))
        v.comprobar("[1920] al cambiar de página, «Géneros» queda activa en el riel (rojo) y «Resumen» ya no",
                    ch.evaluar(JS_RIEL)["activaEtiqueta"] == "Géneros")

        # ------------------------------------------------------------ popover «Datos» del riel
        v.comprobar("[1920] el popover «Datos» aún no está abierto", ch.evaluar(JS_CUERPO) is None)
        ch.evaluar("document.querySelector('.st-key-popover_datos button').click()")
        try:
            ch.esperar("document.querySelector('[data-testid=\"stPopoverBody\"] .sobre-cierre')", 20)
        except TimeoutError:
            pass
        c = ch.evaluar(JS_CUERPO)
        v.comprobar("[popover Datos] abre al hacer clic", c is not None)
        if c:
            v.comprobar("[popover Datos] «Lo esencial» con sus 3 puntos y «Limitaciones clave» con una línea por limitación (4 o 5)",
                        c["lo_esencial"] and c["limitaciones_clave"] and c["esenciales"] == 3 and c["limitaciones"] in (4, 5), str(c))
            v.comprobar("[popover Datos] cierra con «Metodología completa en el informe del proyecto.», sin tablas ni nombres de columnas en formato código",
                        c["cierre"] and c["tablas"] == 0 and c["codigo"] == 0, str(c))
            v.comprobar("[popover Datos] se ve completo: sin recorte interno y dentro de la ventana", not c["recortado"] and c["dentro"], str(c))
        ch.evaluar("document.querySelector('.st-key-popover_datos button').click()")
        try:
            ch.esperar("!document.querySelector('[data-testid=\"stPopoverBody\"]')", 10)
            cerrado = True
        except TimeoutError:
            cerrado = False
        v.comprobar("[popover Datos] se cierra al volver a hacer clic en el botón", cerrado)

        # ------------------------------------------------------------ clic en cada página del riel: tarjeta, leyenda, «Cómo leer»
        for nombre in ESPERA:
            selector, graficos = ESPERA[nombre]
            # Además del título y el/los gráfico(s): esperar también el marcador de «Cómo leer este gráfico» que
            # corresponda (recuadro fijo o expander; el Resumen no tiene ninguno de los dos) — si no, se puede leer
            # el DOM a medio transicionar desde la página anterior (p. ej. el `.como-leer` de Evolución todavía
            # montado al llegar a Mercados).
            if nombre in ABIERTAS:
                extra = " && document.querySelector('[data-testid=\"stMain\"] .como-leer')"
            elif nombre in CERRADAS:
                extra = " && document.querySelector('[data-testid=\"stMain\"] [data-testid=\"stExpander\"]')"
            else:
                extra = ""
            ch.evaluar(js_clic_pagina(nombre))
            try:
                ch.esperar(
                    f"document.querySelector('[data-testid=\"stMain\"] {selector}') && "
                    f"document.querySelectorAll('[data-testid=\"stMain\"] .js-plotly-plot').length >= {graficos}{extra}", 30,
                )
                time.sleep(0.3)  # margen tras cumplirse la condición: evita leer un DOM a medio asentar (visto en Valoración)
                dibujada = True
            except TimeoutError:
                dibujada = False
            excepciones = ch.evaluar("document.querySelectorAll('[data-testid=\"stException\"]').length")
            v.comprobar(f"[clic] página «{nombre}»: dibuja su contenido{' y ' + str(graficos) + ' gráfico(s)' if graficos else ''} sin excepciones", dibujada and excepciones == 0, f"dibujada={dibujada}, excepciones={excepciones}")

            if nombre != "Resumen":
                tarjeta = ch.evaluar(JS_TARJETA)
                v.comprobar(f"[clic] {nombre}: la tarjeta del gráfico existe, con su leyenda en la cabecera", tarjeta is not None and tarjeta["hayTarjeta"] and tarjeta["tieneLeyenda"], str(tarjeta))
                como_leer = ch.evaluar(JS_COMO_LEER)
                for _reintento in range(4):  # el DOM puede tardar un instante más en asentar que la condición de espera
                    if como_leer["abierto"] or como_leer["expander"]:
                        break
                    time.sleep(0.4)
                    como_leer = ch.evaluar(JS_COMO_LEER)
                if nombre in ABIERTAS:
                    v.comprobar(f"[clic] {nombre}: «Cómo leer este gráfico» está ABIERTO (recuadro fijo, no expander)", como_leer["abierto"], str(como_leer))
                elif nombre in CERRADAS:
                    v.comprobar(f"[clic] {nombre}: «Cómo leer este gráfico» está en un expander CERRADO",
                                como_leer["expander"] and "Cómo leer este gráfico" in (como_leer["textoExpander"] or ""), str(como_leer))

            if nombre == "Matriz":
                riesgo = ch.evaluar(JS_RIESGO)
                v.comprobar("[clic] Matriz: la lista de riesgo tiene entre 1 y 5 filas y su botón de descarga (sin tabla)",
                            riesgo is not None and 1 <= riesgo["nFilas"] <= 5 and riesgo["hayDescarga"] and not riesgo["hayTablaVieja"], str(riesgo))

    # ------------------------------------------------------------ viewports angostos: la franja de KPIs no desborda y el riel se mantiene angosto
    for ancho in (1600, 1440, 1366):
        with Chrome(ancho, 1000) as ch:
            abrir_dashboard(ch, servidor.url)
            k = ch.evaluar(JS_KPIS)
            v.comprobar(f"[{ancho}] la franja de KPIs sigue siendo un solo contenedor con 4 celdas, sin desborde", k["hayFranja"] and k["nCeldas"] == 4 and k["desbordan"] == 0, str(k))
            riel = ch.evaluar(JS_RIEL)
            v.comprobar(f"[{ancho}] el riel sigue angosto (~84 px) y con sus 6 páginas", riel["anchoRiel"] <= 100 and len(riel["etiquetas"]) == 6, str(riel))

sys.exit(v.terminar())
