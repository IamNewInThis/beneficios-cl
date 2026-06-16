"""Fuente: Tenpo (tenpo.cl/beneficios) — beneficios de tarjetas Tenpo.

El sitio usa Webflow CMS con Finsweet CMS Load. Los beneficios se renderizan en
elementos `w-dyn-item` dentro del grid. Extraemos el texto visible del grid y se
lo pasamos al extractor con IA para estructurarlo.
"""
import requests
from bs4 import BeautifulSoup

from extract import extraer_beneficios

URL = "https://www.tenpo.cl/beneficios"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def _extraer_texto_beneficios(html: str) -> str:
    """Extrae el texto limpio de la sección de beneficios."""
    soup = BeautifulSoup(html, "html.parser")

    grid = soup.find("div", class_="benficios-collection-list")
    if not grid:
        msg = "No se encontró el grid de beneficios en el HTML"
        raise ValueError(msg)

    for tag in grid.find_all(["script", "style", "noscript"]):
        tag.decompose()

    texto = grid.get_text(separator="\n")
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    return "\n".join(lineas)


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    texto = _extraer_texto_beneficios(resp.text)

    return extraer_beneficios(
        texto,
        tarjeta="Tenpo",
        emisor="Tenpo",
        fuente=URL,
    )
