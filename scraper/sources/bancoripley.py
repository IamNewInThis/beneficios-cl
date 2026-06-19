"""Fuente: Banco Ripley (bancoripley.cl/beneficios-y-promociones).

El sitio es un SPA Angular: el listado se arma en cliente llamando a
`/api/call-sp-api` por sección. NO está detrás de Akamai (a diferencia de
Santander/BancoEstado): un Chromium **headless** carga la página sin problema,
así que esta fuente SÍ es candidata a correr en el cron (necesita
`playwright install chromium`).

Estructura:
- Una sola página con categorías navegables por hash (`#nav-comidadelivery`,
  `#nav-restofans`, …). Cada categoría renderiza sus cards al navegar a su hash;
  por eso recorremos todas y juntamos las cards (si pedís una sola, te perdés el
  resto — fue el error inicial de subestimar el catálogo).
- Cada card ya trae en TEXTO todo lo necesario: día, medio de pago ("Con tus
  Tarjetas Banco Ripley Mastercard"), comercio, descuento y condición. Se lo
  pasamos tal cual al extractor con IA.
- NO hay URL de detalle por beneficio (solo anclas de categoría), así que `url`
  queda null.
"""
import asyncio
import os
import re

from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from extract import extraer_beneficios

BASE = "https://www.bancoripley.cl"
LISTADO = f"{BASE}/beneficios-y-promociones"
FUENTE = LISTADO

# Categorías navegables por hash (#nav-<cat>). Recorremos todas para juntar el
# catálogo completo.
CATEGORIAS = [
    "comidadelivery", "restofans", "viajes-y-transportes", "bienestar-belleza",
    "entretencionyotros", "oportunidades-exclusivas", "mastercardblack",
]

HEADLESS = os.environ.get("RIPLEY_HEADLESS", "1") != "0"  # default headless
BATCH = 35

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# JS que junta el texto de las cards de beneficio visibles: nodos con poco
# anidamiento, que mencionan "Banco Ripley" y traen una cifra de descuento.
_JS_CARDS = """
els => els
  .filter(e => e.children.length <= 6)
  .map(e => (e.innerText || '').replace(/\\s+/g, ' ').trim())
  .filter(t => /Banco Ripley/i.test(t) && /\\d+%|\\$\\s?\\d/.test(t)
            && t.length > 20 && t.length < 200)
"""


async def _nuevo_contexto(p):
    browser = await p.chromium.launch(
        headless=HEADLESS,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    ctx = await browser.new_context(
        locale="es-CL", timezone_id="America/Santiago",
        user_agent=UA, viewport={"width": 1366, "height": 1000},
    )
    await ctx.route(
        re.compile(r"\.(png|jpe?g|gif|webp|svg|woff2?|ttf|mp4|avif)(\?|$)", re.I),
        lambda route: route.abort(),
    )
    return browser, ctx


async def _cards_categoria(page, cat: str) -> list[str]:
    await page.goto(f"{LISTADO}#nav-{cat}", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(2500)
    for _ in range(8):
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(400)
    return await page.eval_on_selector_all("*", _JS_CARDS)


async def _scrape_async() -> list[str]:
    async with async_playwright() as p:
        browser, ctx = await _nuevo_contexto(p)
        try:
            page = await ctx.new_page()
            await page.goto(LISTADO, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            vistos: set[str] = set()
            lineas: list[str] = []
            for cat in CATEGORIAS:
                try:
                    for t in await _cards_categoria(page, cat):
                        if t not in vistos:
                            vistos.add(t)
                            lineas.append(t)
                except PWTimeout:
                    continue
        finally:
            await browser.close()
    return lineas


def scrape() -> list[dict]:
    lineas = asyncio.run(_scrape_async())
    if not lineas:
        raise ValueError("No se encontraron cards de beneficios en Banco Ripley")

    beneficios: list[dict] = []
    for i in range(0, len(lineas), BATCH):
        lote = lineas[i:i + BATCH]
        texto = "Beneficios Banco Ripley:\n" + "\n".join(lote)
        beneficios.extend(
            extraer_beneficios(
                texto,
                tarjeta="Banco Ripley",
                emisor="Banco Ripley",
                fuente=FUENTE,
            )
        )
    return beneficios
