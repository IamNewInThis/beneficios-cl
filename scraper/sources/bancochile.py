"""Fuente: Banco de Chile (sitiospublicos.bancochile.cl/personas/beneficios).

El sitio usa Modyo CMS con una API REST pública de contenido. Llamamos
directamente al API de Modyo y le pasamos el texto de cada beneficio al
extractor con IA.
"""
import requests
from bs4 import BeautifulSoup

from extract import extraer_beneficios, limpiar_condiciones

API_URL = "https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries"
DOMINIO = "https://sitiospublicos.bancochile.cl"
FUENTE = f"{DOMINIO}/personas/beneficios"
EMISOR = "Banco de Chile"
TARJETA = "Banco de Chile"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Mapeo de tipo de tarjeta Modyo -> medio de pago
_CARD_MEDIO = {
    "visa-credito-infinite": "credito",
    "visa-credito-signature": "credito",
    "visa-credito-platinum": "credito",
    "visa-credito-gold": "credito",
    "visa-fan-credito": "credito",
    "mastercard-credito-black": "credito",
    "mastercard-credito-platinum": "credito",
    "mastercard-credito-dorada": "credito",
    "visa-debito-bch": "debito",
    "visa-cuenta-fan": "debito",
    "visa-debito-infinite": "debito",
    "visa-debito-signature": "debito",
}

_DIAS_VALIDOS = {
    "lunes", "martes", "miercoles", "miércoles",
    "jueves", "viernes", "sabado", "sábado", "domingo",
}


def _slug_url(slug: str) -> str:
    return f"{DOMINIO}/personas/beneficios/detalle/{slug}"


def _extraer_dias(tags: list[str]) -> list[str]:
    dias = []
    for tag in tags:
        t = tag.lower().strip().replace("miércoles", "miercoles").replace("sábado", "sabado")
        if t in _DIAS_VALIDOS:
            dias.append(t)
    return dias


def _limpiar_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _fetch_entradas() -> list[dict]:
    todas: list[dict] = []
    pagina = 1
    total_paginas = 1

    while pagina <= total_paginas:
        resp = requests.get(
            API_URL,
            params={"per_page": 100, "page": pagina},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        todas.extend(data.get("entries", []))
        total_paginas = data.get("meta", {}).get("total_pages", 1)
        pagina += 1

    return todas


def scrape() -> list[dict]:
    entradas = _fetch_entradas()

    lineas: list[str] = []
    urls_validas: set[str] = set()
    medios_por_url: dict[str, set[str]] = {}

    for entry in entradas:
        meta = entry.get("meta", {})
        fields = entry.get("fields", {})

        slug = (meta.get("slug") or "").strip()
        url = _slug_url(slug) if slug else ""
        titulo = (fields.get("Titulo") or "").strip()
        tipo_beneficio = (fields.get("Tipo Beneficio") or "").strip()
        descripcion = _limpiar_html(fields.get("Descripcion") or "")
        extracto = (fields.get("Extracto") or "").strip()
        vigencia = (fields.get("Vigencia") or "").strip()
        condiciones = _limpiar_html(fields.get("Condiciones Comerciales") or "")
        tags = meta.get("tags", [])
        categoria = (meta.get("category") or "").replace("beneficios/", "").replace("/", " > ")

        dias = _extraer_dias(tags)
        dias_str = f"(días: {', '.join(dias)})" if dias else ""

        # Medios de pago desde Tarjetas Permitidas
        tarjetas = fields.get("Tarjetas Permitidas") or []
        medios: set[str] = set()
        for tk in tarjetas:
            medio = _CARD_MEDIO.get(tk)
            if medio:
                medios.add(medio)

        if url:
            urls_validas.add(url)
            if medios:
                medios_por_url.setdefault(url, set()).update(medios)

        partes = [f"comercio: {titulo}"]
        if tipo_beneficio:
            partes.append(f"descuento: {tipo_beneficio}")
        if extracto:
            partes.append(f"extracto: {extracto}")
        partes.append(f"descripción: {descripcion[:1200]}")
        if vigencia:
            partes.append(f"vigencia: {vigencia}")
        if condiciones:
            cond = limpiar_condiciones(condiciones[:500])
            if cond:
                partes.append(f"condiciones: {cond}")
        partes.append(f"categoría: {categoria}")
        if dias_str:
            partes.append(dias_str)

        texto = " | ".join(partes)

        if medios:
            medio_str = ", ".join(sorted(medios))
            texto += f" (medio de pago: {medio_str})"

        if url:
            lineas.append(f"{texto} <url:{url}>")
        else:
            lineas.append(texto)

    if not lineas:
        return []

    texto_completo = "Beneficios Banco de Chile:\n" + "\n".join(lineas)

    return extraer_beneficios(
        texto_completo,
        tarjeta=TARJETA,
        emisor=EMISOR,
        fuente=FUENTE,
        urls_validas=urls_validas,
        medios_por_url=medios_por_url or None,
    )
