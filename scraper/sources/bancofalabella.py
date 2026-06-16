"""Fuente: Banco Falabella (bancofalabella.cl/descuentos).

El sitio usa Contentful CMS con GraphQL API pública. Consultamos directamente
el API de Contentful para obtener beneficios estructurados (sin IA ni browser).
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Token de Contentful Content Delivery (solo lectura) del espacio público de
# Banco Falabella. No es un secreto propio —es el mismo token que su sitio
# expone al navegador—, pero se lee del entorno para no versionarlo.
SPACE_ID = os.environ.get("FALABELLA_CONTENTFUL_SPACE_ID", "p6eyia4djstu")
ACCESS_TOKEN = os.environ["FALABELLA_CONTENTFUL_TOKEN"]
ENDPOINT = f"https://graphql.contentful.com/content/v1/spaces/{SPACE_ID}"

QUERY = """
query Benefits($limit: Int, $skip: Int) {
  newBenefitsCollection(limit: $limit, skip: $skip) {
    total
    items {
      commerceName
      creditCards
      discount
      discountDays
      centerDiscountText
      topDiscountText
      bottomDiscountText
      maxBenefitValue
      minBenefitValue
      legalText
      benefitsMode
      relatedCategory
      initDate
      endDate
      isNewCard
      eliteTag
      highlighted
      couponInstructions
    }
  }
}
"""

FUENTE = "https://www.bancofalabella.cl/descuentos"
EMISOR = "Banco Falabella"

DIAS_MAP = {
    "lunes": "lunes", "martes": "martes", "miercoles": "miercoles",
    "miércoles": "miercoles", "jueves": "jueves", "viernes": "viernes",
    "sabado": "sabado", "sábado": "sabado", "domingo": "domingo",
}

CATEGORIAS_SKIP = {"elite", "regiones", "cuotas sin interés"}


def _normalizar_dias(raw_days: list[str] | None) -> list[str]:
    if not raw_days:
        return []
    vistos: set[str] = set()
    resultado: list[str] = []
    for d in raw_days:
        normalizado = DIAS_MAP.get(d.lower().strip())
        if normalizado and normalizado not in vistos:
            vistos.add(normalizado)
            resultado.append(normalizado)
    return resultado


def _elegir_categoria(related: list[str] | None) -> str:
    if not related:
        return "otros"
    for cat in related:
        c = cat.lower().strip()
        if c not in CATEGORIAS_SKIP:
            return c
    return related[0].lower().strip()


def _determinar_tipo(item: dict) -> str:
    texto = (item.get("centerDiscountText") or "") + (item.get("topDiscountText") or "")
    if "%" in texto or "dcto" in texto.lower():
        return "porcentaje"
    if "$" in texto:
        return "monto"
    return "porcentaje"


def _determinar_medio(tarjeta: str) -> str:
    if "debito" in tarjeta.lower():
        return "debito"
    return "credito"


def _armar_condiciones(item: dict) -> str | None:
    partes: list[str] = []
    if item.get("legalText"):
        partes.append(item["legalText"])
    if item.get("couponInstructions"):
        partes.append(item["couponInstructions"])
    if not partes:
        return None
    return " | ".join(partes)


def _transformar(item: dict) -> list[dict]:
    rows: list[dict] = []
    tarjetas = item.get("creditCards") or ["CMR Mastercard"]
    categoria = _elegir_categoria(item.get("relatedCategory"))
    tipo = _determinar_tipo(item)
    valor = item.get("discount") or 0
    dias = _normalizar_dias(item.get("discountDays"))
    condiciones = _armar_condiciones(item)

    for tarjeta in tarjetas:
        rows.append({
            "tarjeta": tarjeta,
            "emisor": EMISOR,
            "medio_pago": _determinar_medio(tarjeta),
            "comercio": (item.get("commerceName") or "").strip(),
            "categoria": categoria,
            "tipo": tipo,
            "valor": valor,
            "dias": dias,
            "condiciones": condiciones,
            "vigencia_desde": item.get("initDate"),
            "vigencia_hasta": item.get("endDate"),
            "fuente": FUENTE,
        })
    return rows


def scrape() -> list[dict]:
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    beneficios: list[dict] = []
    skip = 0
    limit = 100
    total = None

    while total is None or skip < total:
        resp = requests.post(
            ENDPOINT,
            json={"query": QUERY, "variables": {"limit": limit, "skip": skip}},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]["newBenefitsCollection"]
        items = data["items"]
        total = data["total"]

        for item in items:
            if not item.get("commerceName"):
                continue
            rows = _transformar(item)
            rows = [r for r in rows if r["valor"] > 0]
            beneficios.extend(rows)

        skip += limit

    return beneficios
