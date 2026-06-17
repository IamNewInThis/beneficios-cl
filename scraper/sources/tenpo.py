"""Fuente: Tenpo (tenpo.cl/beneficios) — beneficios de tarjetas Tenpo.

El sitio usa Webflow CMS con Finsweet CMS Load. El grid solo trae UNA página de
beneficios por request; el resto vive en páginas paginadas (`?<id>_page=N`, que
Webflow renderiza server-side). Si solo pedimos la primera, perdemos la mayoría
(eran ~40 en el sitio, traíamos 9). Recorremos todas las páginas, juntamos el
texto de cada item (deduplicado) y se lo pasamos al extractor con IA.
"""
import re

import requests
from bs4 import BeautifulSoup

from extract import extraer_beneficios

BASE = "https://www.tenpo.cl"
URL = f"{BASE}/beneficios"
MAX_PAGINAS = 15  # tope de seguridad contra loops

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def _param_paginacion(html: str) -> str | None:
    """Nombre del query param de paginación Webflow (ej. 'ca01dc3d_page')."""
    m = re.search(r"[?&]([a-z0-9]+_page)=\d+", html)
    return m.group(1) if m else None


def _items_grid(html: str) -> list[tuple[str, str | None]]:
    """(texto, url) de cada beneficio del grid (lista vacía si no hay grid).

    Tomamos los items TOP-LEVEL (no los `.w-dyn-item` anidados, que son chips de
    día y meten ruido). Cada card trae un `<a href="/beneficios/<slug>">` que es
    el deep-link al beneficio concreto.
    """
    soup = BeautifulSoup(html, "html.parser")
    grid = soup.find("div", class_="benficios-collection-list")
    if not grid:
        return []
    for tag in grid.find_all(["script", "style", "noscript"]):
        tag.decompose()
    items = []
    for it in grid.find_all("div", class_="w-dyn-item", recursive=False):
        txt = " ".join(it.get_text(separator=" ").split())
        if not txt:
            continue
        a = it.find("a", href=True)
        href = a["href"] if a else None
        url = (BASE + href) if href and href.startswith("/") else href
        items.append((txt, url))
    return items


# Frases del detalle que vale la pena rescatar: vigencia y condiciones reales.
_VIGENCIA_RE = re.compile(
    r"(v[áa]lid|vigenc|del\s+\d+\s+al\s+\d+\s+de|hasta\s+el\s+\d)", re.I
)


def _detalle_texto(html: str) -> str:
    """Contenido útil de la página de detalle: condiciones (rich-text) + vigencia.

    El grid solo trae el titular ("15% dcto, requiere cupón"); el detalle agrega
    el cupón/sitio y la VIGENCIA real ("Válida desde el 1 al 30 de junio de
    2026"), que necesitamos para `vigencia_hasta`. Evitamos el menú/footer
    apuntando al bloque `.w-richtext` y a las frases con patrón de vigencia.
    """
    soup = BeautifulSoup(html, "html.parser")
    partes: list[str] = []
    for rt in soup.select(".w-richtext"):
        t = " ".join(rt.get_text(separator=" ").split())
        if t:
            partes.append(t)
    for s in soup.find_all(string=_VIGENCIA_RE):
        t = " ".join(s.split())
        if 8 < len(t) < 200 and t not in partes:
            partes.append(t)
    # Acotar: solo necesitamos vigencia + condición corta; el párrafo entero
    # infla el prompt y la respuesta del modelo (que tiene tope de tokens).
    return " ".join(partes)[:400]


def _todas_las_paginas(primer_html: str) -> list[tuple[str, str | None]]:
    """Recorre la paginación y devuelve los items (texto, url) deduplicados."""
    param = _param_paginacion(primer_html)
    vistos: set[str] = set()
    items: list[tuple[str, str | None]] = []

    pagina, html = 1, primer_html
    while pagina <= MAX_PAGINAS:
        nuevos = 0
        for txt, url in _items_grid(html):
            if txt in vistos:
                continue
            vistos.add(txt)
            items.append((txt, url))
            nuevos += 1
        if not param or nuevos == 0:
            break
        pagina += 1
        resp = requests.get(f"{URL}?{param}={pagina}", headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            break
        html = resp.text
    return items


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    items = _todas_las_paginas(resp.text)
    if not items:
        msg = "No se encontró el grid de beneficios en el HTML"
        raise ValueError(msg)

    lineas: list[str] = []
    urls: set[str] = set()
    for txt, url in items:
        if url:
            urls.add(url)
            # Enriquecer con el detalle (vigencia + condiciones). Si falla un
            # detalle, seguimos con el titular del grid (aislamiento por item).
            try:
                detalle = _detalle_texto(
                    requests.get(url, headers=HEADERS, timeout=30).text
                )
                if detalle:
                    txt += f" — {detalle}"
            except requests.RequestException:
                pass
            txt += f" <url:{url}>"
        lineas.append(txt)

    texto = "Beneficios Tenpo:\n" + "\n".join(lineas)

    return extraer_beneficios(
        texto,
        tarjeta="Tenpo",
        emisor="Tenpo",
        fuente=URL,
        urls_validas=urls,
    )
