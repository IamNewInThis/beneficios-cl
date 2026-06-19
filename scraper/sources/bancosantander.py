"""Fuente: Banco Santander (banco.santander.cl/beneficios).

A diferencia de Mach/Tenpo/Falabella, Santander está detrás de **Akamai Bot
Manager**: cualquier request server-side (`requests`, curl, headless) recibe 403
con la página "Revisa tu conexión a internet". Lo único que pasa el muro es un
navegador REAL en modo **headful** (visible), así que esta fuente usa Playwright
con `headless=False`. Por eso NO corre en GitHub Actions (IP de datacenter US →
geo+bot block): se ejecuta a mano/localmente sobre una IP residencial chilena.

Estructura del sitio:
- El grid `…/beneficios/promociones?page=N&segmento=s-personas` lista ~12
  beneficios por página (hay ~24 páginas). Cada card linkea al detalle
  `…/beneficios/promociones/<slug>`, que es el deep-link que guardamos.
- El grid solo trae el NOMBRE del comercio; el descuento, medio de pago, días,
  vigencia y condiciones viven en la página de detalle. Por eso visitamos cada
  detalle, recortamos su contenido útil y se lo pasamos al extractor con IA.

Rendimiento: usamos `domcontentloaded` (NUNCA `networkidle`: el sitio tiene
beacons de Akamai/analytics constantes, nunca queda idle y cada `goto` gastaría
el timeout completo). Las ~288 páginas de detalle se cargan con concurrencia
ACOTADA (`CONCURRENCIA` pestañas a la vez): suficiente para bajar el run a un par
de minutos sin parecer un ataque que dispare el rate-limit de Akamai.
"""
import asyncio
import os
import random
import re

from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from extract import extraer_beneficios

BASE = "https://banco.santander.cl"
GRID = f"{BASE}/beneficios/promociones?page={{n}}&segmento=s-personas"
FUENTE = f"{BASE}/beneficios?segmento=s-personas"
MAX_PAGINAS = 40  # tope de seguridad; el sitio ronda las 24

# Headless da 403 (Akamai). Permitimos forzar headless por env para experimentar,
# pero el default es headful porque es lo único que funciona.
HEADLESS = os.environ.get("SANTANDER_HEADLESS", "0") == "1"
# Pestañas en paralelo. 3-4 es el punto dulce: acelera ~Nx sin martillar al
# punto de gatillar el Bot Manager. Configurable por env.
CONCURRENCIA = int(os.environ.get("SANTANDER_WORKERS", "4"))
# Beneficios por llamada a la IA. Con ~288 detalles, mandar todo de una supera
# MAX_CHARS del extractor (y el max_tokens de la respuesta): procesamos por lotes.
BATCH = 35

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
# Oculta el flag de automatización que Akamai busca.
_STEALTH = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"

_DETALLE_RE = re.compile(r"/beneficios/promociones/[a-z0-9-]+$", re.I)
_BLOQUEO = "conexión a internet"  # marca de la página de Akamai


async def _nuevo_contexto(p):
    browser = await p.chromium.launch(
        headless=HEADLESS, args=["--disable-blink-features=AutomationControlled"]
    )
    ctx = await browser.new_context(
        locale="es-CL",
        timezone_id="America/Santiago",
        user_agent=UA,
        viewport={"width": 1366, "height": 900},
    )
    await ctx.add_init_script(_STEALTH)
    # Acelerar: no descargar imágenes/medios/fuentes (no aportan al texto).
    await ctx.route(
        re.compile(r"\.(png|jpe?g|gif|webp|svg|woff2?|ttf|mp4|avif)(\?|$)", re.I),
        lambda route: route.abort(),
    )
    return browser, ctx


def _urls_detalle(hrefs: list[str]) -> list[str]:
    out = []
    for h in hrefs or []:
        h = (h or "").split("?")[0].split("#")[0]
        if _DETALLE_RE.search(h):
            out.append(h)
    return out


async def _abrir(ctx, url: str, espera_selector: str | None = None):
    """Abre una pestaña nueva en `url` (domcontentloaded) y la devuelve."""
    page = await ctx.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if espera_selector:
        try:
            await page.wait_for_selector(espera_selector, timeout=12000)
        except PWTimeout:
            pass
    await page.wait_for_timeout(400 + random.randint(0, 500))  # jitter anti-bot
    return page


async def _grid_urls(ctx) -> list[str]:
    """URLs de detalle de todas las páginas del grid (paginación concurrente)."""
    sel = "a[href*='/beneficios/promociones/']"
    page = await _abrir(ctx, GRID.format(n=1), sel)
    body = await page.inner_text("body")
    if _BLOQUEO in body.lower():
        await page.close()
        msg = "Santander devolvió la página de bloqueo (Akamai). Usá headful en IP chilena."
        raise RuntimeError(msg)
    hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e=>e.href)")
    await page.close()

    # Máxima página declarada en la paginación del grid.
    paginas = {int(m) for m in re.findall(r"[?&]page=(\d+)", " ".join(hrefs))}
    ultima = min(max(paginas) if paginas else 1, MAX_PAGINAS)

    vistos: set[str] = set(_urls_detalle(hrefs))
    orden: list[str] = list(vistos)
    sem = asyncio.Semaphore(CONCURRENCIA)

    async def _una(n: int):
        async with sem:
            try:
                pg = await _abrir(ctx, GRID.format(n=n), sel)
                hs = await pg.eval_on_selector_all(
                    sel, "els => els.map(e=>e.href)"
                )
                await pg.close()
            except PWTimeout:
                return
            for u in _urls_detalle(hs):
                if u not in vistos:
                    vistos.add(u)
                    orden.append(u)

    await asyncio.gather(*(_una(n) for n in range(2, ultima + 1)))
    return orden


# El contenido útil del detalle está entre el botón "Volver" y el bloque legal
# "Condiciones y Restricciones" (incluye el % , el medio de pago y la vigencia).
def _recortar(body: str) -> str:
    body = re.sub(r"[ \t]+", " ", body)
    ini = body.find("Volver")
    if ini != -1:
        body = body[ini + len("Volver"):]
    fin = body.find("Condiciones y Restricciones")
    if fin != -1:
        body = body[:fin]
    lineas = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return " ".join(lineas)[:700]


async def _detalles(ctx, urls: list[str]) -> list[str]:
    """Texto recortado de cada detalle, en paralelo (concurrencia acotada)."""
    sem = asyncio.Semaphore(CONCURRENCIA)
    lineas: list[str] = []

    async def _una(url: str):
        async with sem:
            try:
                pg = await _abrir(ctx, url)
                body = await pg.inner_text("body")
                await pg.close()
            except PWTimeout:
                return
            if _BLOQUEO in body.lower():
                return
            txt = _recortar(body)
            if txt:
                lineas.append(f"{txt} <url:{url}>")

    await asyncio.gather(*(_una(u) for u in urls))
    return lineas


async def _scrape_async() -> tuple[list[str], list[str]]:
    async with async_playwright() as p:
        browser, ctx = await _nuevo_contexto(p)
        try:
            urls = await _grid_urls(ctx)
            if not urls:
                raise ValueError("No se encontraron beneficios en el grid de Santander")
            lineas = await _detalles(ctx, urls)
        finally:
            await browser.close()
    return urls, lineas


def scrape() -> list[dict]:
    urls, lineas = asyncio.run(_scrape_async())

    # Extraer por lotes (ver BATCH): cada llamada a la IA recibe un texto acotado.
    urls_set = set(urls)
    beneficios: list[dict] = []
    for i in range(0, len(lineas), BATCH):
        lote = lineas[i:i + BATCH]
        texto = "Beneficios Banco Santander:\n" + "\n".join(lote)
        beneficios.extend(
            extraer_beneficios(
                texto,
                tarjeta="Santander",
                emisor="Banco Santander",
                fuente=FUENTE,
                urls_validas=urls_set,
            )
        )
    return beneficios
