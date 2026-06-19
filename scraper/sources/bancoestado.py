"""Fuente: BancoEstado — TodoSuma (bancoestado.cl …/todos-beneficios.html).

Igual que `bancosantander`, está detrás de **Akamai Bot Manager**: cualquier
request server-side recibe la página de error ("La página que buscas no está
disponible" + referencia Akamai). Solo pasa un navegador **headful** desde una
IP residencial chilena. Por eso NO está en `SOURCES` (el cron daría error): es
una fuente **manual/local** (ver el comentario en `sources/__init__.py`).

Estructura del sitio (AEM SPA):
- El listado es UNA página (`todos-beneficios.html`) con tabs de categoría que
  filtran/cargan en cliente (rutas por `#hash`: `#viajes`, `#sabores`, …). El DOM
  por defecto trae ~29 beneficios, pero ALGUNAS categorías cargan otros que no
  están en la vista inicial → hay que clickear cada tab y unir los links.
- Cada beneficio tiene página de detalle propia
  `…/todos-beneficios/<slug>---beneficios-bancoestado.html` (el deep-link que
  guardamos en `url`). El listado solo trae el nombre; el %, medio, días,
  vigencia y condiciones viven en el detalle, así que visitamos cada uno y le
  pasamos el texto al extractor con IA.
"""
import asyncio
import os
import random
import re

from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from extract import extraer_beneficios

BASE = "https://www.bancoestado.cl"
RUTA = "/content/bancoestado-public/cl/es/home/home/todosuma---bancoestado-personas"
LISTADO = f"{BASE}{RUTA}/todos-beneficios.html"
FUENTE = LISTADO

# Tabs de categoría a recorrer para juntar TODO el catálogo (algunas cargan
# beneficios que no están en la vista por defecto). Se clickean por texto; si una
# no está, se ignora.
CATEGORIAS = [
    "Destacado", "Sabores", "Musica y Entretención", "Viajes", "Bienestar",
    "Hogar y Mascotas", "Impacto Verde", "Vestuario", "Cuotas sin interés",
    "Otros Servicios",
]

HEADLESS = os.environ.get("BANCOESTADO_HEADLESS", "0") == "1"
CONCURRENCIA = int(os.environ.get("BANCOESTADO_WORKERS", "4"))
BATCH = 35

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
_STEALTH = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"

_DETALLE_RE = re.compile(
    r"/todos-beneficios/[a-z0-9-]+---beneficios-bancoestado\.html$", re.I
)
_BLOQUEO = "no está disponible"  # marca de la página de error de Akamai


async def _nuevo_contexto(p):
    browser = await p.chromium.launch(
        headless=HEADLESS, args=["--disable-blink-features=AutomationControlled"]
    )
    ctx = await browser.new_context(
        locale="es-CL",
        timezone_id="America/Santiago",
        user_agent=UA,
        viewport={"width": 1366, "height": 1000},
    )
    await ctx.add_init_script(_STEALTH)
    await ctx.route(
        re.compile(r"\.(png|jpe?g|gif|webp|svg|woff2?|ttf|mp4|avif)(\?|$)", re.I),
        lambda route: route.abort(),
    )
    return browser, ctx


def _slug_a_comercio(url: str) -> str:
    slug = url.rsplit("/", 1)[-1]
    slug = slug.replace("---beneficios-bancoestado.html", "")
    return slug.replace("-", " ").title()


async def _links_detalle(page) -> set[str]:
    hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e=>e.href)")
    out = set()
    for h in hrefs or []:
        h = (h or "").split("#")[0]
        if _DETALLE_RE.search(h):
            out.add(h)
    return out


async def _scroll(page, vueltas: int = 8):
    for _ in range(vueltas):
        await page.mouse.wheel(0, 4000)
        await page.wait_for_timeout(400)


async def _recolectar_urls(page) -> list[str]:
    await page.goto(LISTADO, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(4000)
    body = await page.inner_text("body")
    if _BLOQUEO in body.lower():
        msg = "BancoEstado devolvió la página de error (Akamai). Usá headful en IP chilena."
        raise RuntimeError(msg)

    await _scroll(page)
    union: set[str] = await _links_detalle(page)

    # Recorrer las tabs de categoría: algunas cargan beneficios extra.
    for cat in CATEGORIAS:
        try:
            tab = page.get_by_text(cat, exact=True).first
            await tab.scroll_into_view_if_needed(timeout=4000)
            await tab.click(timeout=4000)
            await page.wait_for_timeout(1200)
            await _scroll(page, 6)
            union |= await _links_detalle(page)
        except PWTimeout:
            continue
        except Exception:
            continue
    return sorted(union)


# El contenido útil del detalle va desde el intro del beneficio ("…y obtén") y se
# corta antes del footer/legal. `limpiar_condiciones` del extractor saca lo que
# quede de letra chica.
_FIN = ("Infórmese sobre la garantía", "Mapa del sitio", "Preguntas Frecuentes",
        "Productos Cuentas", "Conoce más de BancoEstado")


def _recortar(body: str, comercio: str) -> str:
    body = re.sub(r"[ \t]+", " ", body)
    i = body.find("y obtén")
    if i != -1:
        body = body[i + len("y obtén"):]
    for fin in _FIN:
        j = body.find(fin)
        if j != -1:
            body = body[:j]
            break
    lineas = [ln.strip() for ln in body.splitlines() if ln.strip()]
    texto = " ".join(lineas)[:800]
    return f"{comercio}: {texto}"


async def _detalles(ctx, urls: list[str]) -> list[str]:
    sem = asyncio.Semaphore(CONCURRENCIA)
    lineas: list[str] = []

    async def _una(url: str):
        async with sem:
            try:
                pg = await ctx.new_page()
                await pg.goto(url, wait_until="domcontentloaded", timeout=45000)
                await pg.wait_for_timeout(900 + random.randint(0, 600))
                body = await pg.inner_text("body")
                await pg.close()
            except PWTimeout:
                return
            if _BLOQUEO in body.lower():
                return
            txt = _recortar(body, _slug_a_comercio(url))
            if txt:
                lineas.append(f"{txt} <url:{url}>")

    await asyncio.gather(*(_una(u) for u in urls))
    return lineas


async def _scrape_async() -> tuple[list[str], list[str]]:
    async with async_playwright() as p:
        browser, ctx = await _nuevo_contexto(p)
        try:
            page = await ctx.new_page()
            urls = await _recolectar_urls(page)
            await page.close()
            if not urls:
                raise ValueError("No se encontraron beneficios en el listado de BancoEstado")
            lineas = await _detalles(ctx, urls)
        finally:
            await browser.close()
    return urls, lineas


def scrape() -> list[dict]:
    urls, lineas = asyncio.run(_scrape_async())

    urls_set = set(urls)
    beneficios: list[dict] = []
    for i in range(0, len(lineas), BATCH):
        lote = lineas[i:i + BATCH]
        texto = "Beneficios BancoEstado (TodoSuma):\n" + "\n".join(lote)
        beneficios.extend(
            extraer_beneficios(
                texto,
                tarjeta="BancoEstado",
                emisor="BancoEstado",
                fuente=FUENTE,
                urls_validas=urls_set,
            )
        )
    return beneficios
