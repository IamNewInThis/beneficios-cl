"""Fuente: Banco BCI (bci.cl/beneficios/beneficios-bci).

El sitio consume una API JSON privada de bciplus.cl que expone todas las
ofertas estructuradas. Llamamos directamente a esa API (sin Playwright) y
le pasamos el texto de cada oferta al extractor con IA.
"""
import os

import requests
from dotenv import load_dotenv

from extract import extraer_beneficios, limpiar_condiciones

load_dotenv()

API_URL = "https://api.bciplus.cl/bff-loyalty-beneficios/v1/offers"
DOMINIO = "https://www.bci.cl"
FUENTE = f"{DOMINIO}/beneficios/beneficios-bci"
EMISOR = "Banco BCI"
TARJETA = "Bci"

# Subscription key que el frontend expone a cada visitante (no es secreto).
# Se puede leer del entorno para no versionarlo, aunque no es sensible.
API_KEY = os.environ.get("BCI_API_KEY", "fa981752762743668413b68821a43840")

HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bci.cl/",
}


def _slug_url(slug: str) -> str:
    return f"{DOMINIO}/beneficios/beneficios-bci/detalle/{slug}"


def _fetch_ofertas() -> list[dict]:
    """Trae TODAS las ofertas (paginación automática)."""
    todas: list[dict] = []
    pagina = 1
    total_paginas = 1

    while pagina <= total_paginas:
        resp = requests.get(
            API_URL,
            params={"itemsPorPagina": 100, "pagina": pagina},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        ofertas = data.get("ofertas", [])
        todas.extend(ofertas)
        paginado = data.get("paginado", {})
        total_paginas = paginado.get("totalPaginas", 1)
        pagina += 1

    return todas


def _texto_oferta(o: dict) -> tuple[str, str]:
    """Convierte una oferta en (linea_texto, url).

    El texto describe el beneficio para que el extractor con IA lo estructure.
    """
    comercio = (o.get("comercio") or {}).get("nombre", "").strip()
    titulo = (o.get("titulo") or "").strip()
    descripcion = (o.get("descripcion") or "").strip()
    slug = (o.get("slug") or "").strip()
    url = _slug_url(slug) if slug else ""

    partes = [comercio] if comercio else []
    if titulo:
        partes.append(titulo)
    if descripcion:
        # Acotar descripción para no inflar tokens
        partes.append(descripcion[:1500])

    # Categorías
    cats = [c["titulo"] for c in (o.get("categorias") or []) if c.get("titulo")]
    if cats:
        partes.append(f"(categorías: {', '.join(cats)})")

    # Tags (medio de pago, modalidad)
    tags = [t["nombre"] for t in (o.get("tags") or []) if t.get("nombre")]
    if tags:
        partes.append(f"(tags: {', '.join(tags)})")

    # Días de recurrencia
    scheduling = o.get("scheduling") or {}
    dias = scheduling.get("dayRecurrence") or []
    if dias:
        partes.append(f"(días: {', '.join(dias)})")

    # Fechas de vigencia
    fecha_desde = (o.get("fechaInicio") or "").strip()
    fecha_hasta = (o.get("fechaTermino") or "").strip()
    if fecha_desde:
        partes.append(f"(vigencia desde: {fecha_desde[:10]})")
    if fecha_hasta:
        partes.append(f"(vigencia hasta: {fecha_hasta[:10]})")

    # Condiciones legales (acotadas)
    legal = (o.get("legal") or "").strip()
    if legal:
        cond = limpiar_condiciones(legal[:500])
        if cond:
            partes.append(f"(condiciones: {cond})")

    return " ".join(partes), url


def scrape() -> list[dict]:
    ofertas = _fetch_ofertas()

    lineas: list[str] = []
    urls_validas: set[str] = set()

    for o in ofertas:
        texto, url = _texto_oferta(o)
        if not texto:
            continue
        if url:
            urls_validas.add(url)
            lineas.append(f"{texto} <url:{url}>")
        else:
            lineas.append(texto)

    if not lineas:
        return []

    texto_completo = "Beneficios BCI:\n" + "\n".join(lineas)

    return extraer_beneficios(
        texto_completo,
        tarjeta=TARJETA,
        emisor=EMISOR,
        fuente=FUENTE,
        urls_validas=urls_validas,
    )
