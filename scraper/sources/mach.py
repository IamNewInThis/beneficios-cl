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
DETALLE = "https://www.machbank.cl/beneficios/detalle/"  # + slug

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


def _norm_medios(medios: str) -> set[str]:
    """Normaliza "crédito,débito" -> {"credito","debito"} (sin tilde)."""
    out = set()
    for m in medios.split(","):
        m = m.strip().lower()
        if m.startswith("créd") or m.startswith("cred"):
            out.add("credito")
        elif m.startswith("déb") or m.startswith("deb"):
            out.add("debito")
    return out


def _extraer_entradas(raw: str) -> tuple[list[str], set[str], dict[str, set[str]]]:
    """Devuelve (líneas, urls válidas, medios_por_url) por cada beneficio.

    Cada entrada de Storyblok trae varios campos; usamos los RICOS, no los
    pobres. En particular `titulo`/`etiqueta_banner` llevan la CIFRA del
    descuento (ej. "Hasta 30% dcto."), que `name`/`descripcion` suelen omitir.
    También aprovechamos `nombre_de_empresa` (comercio limpio) y `medio_de_pago`
    (crédito/débito estructurado) para que el extractor no tenga que adivinar.

    El `slug` de cada entrada arma el deep-link al detalle, que se inyecta como
    marcador `<url:...>` en la línea (el extractor lo copia a cada beneficio).
    """
    lineas, vistos, urls = [], set(), set()
    medios_por_url: dict[str, set[str]] = {}
    for m in re.finditer(r'"type":"beneficios"', raw):
        # Ventana amplia: los campos ricos (nombre_de_empresa, medio_de_pago)
        # aparecen bastante después del marcador "type":"beneficios".
        ventana = raw[max(0, m.start() - 400):m.start() + 2800]
        name = _campo(ventana, "name")
        if not name or name in vistos:
            continue
        vistos.add(name)

        # Campo con la cifra del descuento; preferimos los que la incluyen.
        titulo = _campo(ventana, "titulo") or _campo(ventana, "etiqueta_banner") or name
        # Comercio limpio y descripción de contexto (topes, condiciones).
        comercio = _campo(ventana, "nombre_de_empresa")
        desc = _campo(ventana, "descripcion_banner") or _campo(ventana, "descripcion") or ""

        # Descartar beneficios de estacionamiento de malls (tag "mall-plaza").
        # La fuente solo publica el titular ("50% OFF", "Gratis 21-04") y la
        # lista de malls, sin decir sobre qué aplica: quedan ambiguos y NO se
        # muestran en la cara visible del sitio, así que confunden al usuario.
        if '"mall-plaza"' in ventana or "Mallplaza" in name or "Mallplaza" in (comercio or ""):
            continue

        medios_m = re.search(r'"medio_de_pago":\[([^\]]*)\]', ventana)
        medios = medios_m.group(1).replace('"', "") if medios_m else ""
        dias_m = re.search(r'"dia_de_promo":\[([^\]]*)\]', ventana)
        dias = dias_m.group(1).replace('"', "") if dias_m else ""

        linea = f"{comercio}: {titulo}" if comercio else titulo
        if medios:
            linea += f" (medio de pago: {medios})"
        if dias:
            linea += f" (días: {dias})"
        if desc:
            linea += f" — {desc}"

        slug = _campo(ventana, "slug")
        if slug:
            url = DETALLE + slug
            urls.add(url)
            linea += f" <url:{url}>"
            medios_set = _norm_medios(medios)
            if medios_set:
                medios_por_url[url] = medios_set

        lineas.append(linea)
    return lineas, urls, medios_por_url


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    lineas, urls, medios_por_url = _extraer_entradas(resp.text)
    texto = "Beneficios MACH:\n" + "\n".join(lineas)

    return extraer_beneficios(
        texto,
        tarjeta="MACH",
        emisor="Mach",
        fuente=URL,
        urls_validas=urls,
        medios_por_url=medios_por_url,
    )
