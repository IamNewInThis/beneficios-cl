"""Fuente: Mach (machbank.cl) — beneficios de comercios.

La página pública solo *renderiza* unos pocos beneficios destacados, pero su
HTML trae el catálogo COMPLETO embebido como datos de Storyblok (cada beneficio
es una entrada `type:"beneficios"` con `name`, `descripcion` y `dia_de_promo`).

Extraemos esas entradas estructuradas y se las pasamos al extractor con IA, que
las normaliza al formato común (comercio, categoria, tipo, valor, dias, ...).
Ver scraper/extract.py.
"""
import re

import requests

from extract import extraer_beneficios

URL = "https://www.machbank.cl/beneficios"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def _campo(ventana: str, campo: str) -> str | None:
    """Saca el valor de "campo":"..." dentro de una ventana de texto."""
    m = re.search(r'"' + campo + r'":"((?:[^"\\]|\\.)*)"', ventana)
    return m.group(1) if m else None


def _extraer_entradas(raw: str) -> list[str]:
    """Devuelve una línea de texto limpia por cada beneficio del catálogo."""
    lineas, vistos = [], set()
    for m in re.finditer(r'"type":"beneficios"', raw):
        ventana = raw[max(0, m.start() - 400):m.start() + 1500]
        name = _campo(ventana, "name")
        if not name or name in vistos:
            continue
        vistos.add(name)

        desc = _campo(ventana, "descripcion") or _campo(ventana, "titulo") or ""
        dias_m = re.search(r'"dia_de_promo":\[([^\]]*)\]', ventana)
        dias = dias_m.group(1).replace('"', "") if dias_m else ""

        linea = name
        if dias:
            linea += f" (días: {dias})"
        if desc:
            linea += f" — {desc}"
        lineas.append(linea)
    return lineas


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    lineas = _extraer_entradas(resp.text)
    texto = "Beneficios MACH:\n" + "\n".join(lineas)

    return extraer_beneficios(
        texto,
        tarjeta="MACH",
        emisor="Mach",
        fuente=URL,
    )
