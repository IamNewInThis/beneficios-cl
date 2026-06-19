"""Fuente: Tarjeta Cencosud (tarjetacencosud.cl/publico/home).

El sitio es Next.js con los beneficios embebidos en el HTML como datos
estáticos en `window.CardsAPI.getCards()`. Los extraemos con regex y se
los pasamos al extractor con IA.
"""
import json
import re

import requests
from bs4 import BeautifulSoup

from extract import extraer_beneficios, limpiar_condiciones

URL = "https://www.tarjetacencosud.cl/publico/home"
FUENTE = "https://www.tarjetacencosud.cl/publico/beneficios/landing/inicio"
EMISOR = "Scotiabank"
TARJETA = "Cencosud"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

_CAT_MAP = {
    "mastercard": "Mastercard",
    "black": "Black",
    "platinum": "Platinum",
    "comida": None,
    "cuotas": None,
    "salud": None,
    "viajes": None,
    "educacion": None,
}


def _fetch_cards() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    # Extraer JSON embebido en window.CardsAPI = { getCards: async function() { return [...] } }
    m = re.search(
        r'window\.CardsAPI\s*=\s*\{[^}]*getCards\s*:\s*async\s*function\s*\(\)\s*\{[^}]*return\s*(\[[\s\S]*?\])\s*;?\s*\}',
        resp.text,
    )
    if not m:
        raise ValueError("No se encontró window.CardsAPI.getCards en el HTML")
    raw = m.group(1)
    # El JSON puede tener trailing commas o comentarios; intentamos parse directo
    cards = json.loads(raw)
    return cards


def _texto_beneficio(card: dict) -> str:
    title = (card.get("title") or "").strip()
    short_desc = (card.get("short_description") or "").strip()
    long_desc = (card.get("long_description") or "").strip()
    legal = (card.get("legal_text") or "").strip()
    locs = card.get("locations") or []
    cats = card.get("categories") or []
    keywords = card.get("keywords") or []

    # Limpiar HTML del legal_text
    if legal:
        soup = BeautifulSoup(legal, "html.parser")
        legal = soup.get_text(separator=" ", strip=True)

    partes = [f"comercio: {title}"]
    if short_desc:
        partes.append(f"descripción: {short_desc}")
    if long_desc and long_desc != short_desc:
        partes.append(f"detalle: {long_desc[:800]}")
    if cats:
        etiquetas = []
        for c in cats:
            label = _CAT_MAP.get(c) or c
            if label:
                etiquetas.append(label)
        if etiquetas:
            partes.append(f"categorías: {', '.join(etiquetas)}")
    if keywords:
        partes.append(f"tags: {', '.join(keywords)}")
    if locs:
        partes.append(f"ubicaciones: {', '.join(locs)}")
    if legal:
        cond = limpiar_condiciones(legal[:500])
        if cond:
            partes.append(f"condiciones: {cond}")

    return " | ".join(partes)


def scrape() -> list[dict]:
    cards = _fetch_cards()

    lineas: list[str] = []
    urls_validas: set[str] = set()

    for card in cards:
        url = (card.get("url") or "").strip()
        if not url:
            continue
        urls_validas.add(url)
        texto = _texto_beneficio(card)
        if texto:
            lineas.append(f"{texto} <url:{url}>")

    if not lineas:
        return []

    texto_completo = "Beneficios Tarjeta Cencosud:\n" + "\n".join(lineas)

    return extraer_beneficios(
        texto_completo,
        tarjeta=TARJETA,
        emisor=EMISOR,
        fuente=FUENTE,
        urls_validas=urls_validas,
    )
