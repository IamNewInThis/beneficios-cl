"""Extracción de beneficios desde texto usando Claude (structured output).

Este helper es GENÉRICO: cualquier fuente le pasa el texto plano de una página
y recibe una lista de beneficios ya estructurados en el formato de la tabla
`beneficio` (ver sources/example_source.py). La normalización difícil
(prosa de marketing -> campos) la hace el modelo, no regex frágil.

La IA NO inventa: solo estructura lo que ya está escrito en el texto.
"""
import json
import re
import unicodedata

from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()  # lee ANTHROPIC_API_KEY desde scraper/.env

# Modelo barato y suficiente para extracción estructurada.
MODEL = "claude-haiku-4-5"

# Tope de caracteres del texto que mandamos al modelo (acota tokens/costo).
MAX_CHARS = 60_000

# Vocabulario CANÓNICO de categorías. La IA asigna texto libre y termina
# fragmentando rubros equivalentes (restaurantes/antojos/comida, salud/farmacia,
# entretención/entretenimiento). Lo colapsamos a este set fijo, en código, para
# que el filtro lateral del front sea consistente.
CATEGORIAS = (
    "comida", "salud", "entretenimiento", "viajes", "transporte",
    "mercado", "tienda", "belleza", "mascotas", "hogar",
    "servicios", "combustible", "otros",
)

# Variantes/sinónimos (sin tilde, minúscula) -> categoría canónica.
_CATEGORIA_MAP = {
    "restaurantes": "comida", "restaurante": "comida", "antojos": "comida",
    "bebidas": "comida", "comida rapida": "comida", "cafeteria": "comida",
    "gastronomia": "comida", "super": "mercado", "supermercado": "mercado",
    "farmacia": "salud", "farmacias": "salud",
    "entretencion": "entretenimiento",
    "automotriz": "transporte", "auto": "transporte",
    "tecnologia": "tienda", "perfumeria": "belleza",
    "suscripciones": "servicios", "educacion": "servicios",
    "cmr puntos": "otros", "elite": "otros",
}


def _normalizar_categoria(cat: str | None) -> str:
    """Mapea una categoría libre al vocabulario canónico (default 'otros')."""
    if not cat:
        return "otros"
    c = "".join(
        ch for ch in unicodedata.normalize("NFD", cat.strip().lower())
        if unicodedata.category(ch) != "Mn"
    )
    c = _CATEGORIA_MAP.get(c, c)
    return c if c in CATEGORIAS else "otros"


# Tope de caracteres de `condiciones`. El prompt ya pide resumir, pero el modelo
# a veces copia prosa legal larga: esta guarda en código la acota igual.
MAX_COND_CHARS = 160

# Frases de boilerplate legal que no aportan al usuario. Si una `condiciones`
# arranca con/contiene solo esto, la descartamos (la dejamos en null).
_COND_BOILERPLATE = re.compile(
    r"t[eé]rminos,?\s+condiciones|exclusiva responsabilidad del comercio|"
    r"inf[oó]rmese sobre la garant[ií]a estatal|consultar al emisor|"
    r"cmfchile\.cl|bancofalabella\.cl/descuentos",
    re.IGNORECASE,
)

# Esquema que el modelo está OBLIGADO a devolver (structured output).
# Refleja el formato de beneficio de sources/example_source.py.
BENEFICIO_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "beneficios": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "tarjeta": {"type": "string"},
                    "emisor": {"type": ["string", "null"]},
                    "medio_pago": {"type": "string", "enum": ["credito", "debito"]},
                    "comercio": {"type": "string"},
                    "categoria": {"type": "string"},
                    "tipo": {
                        "type": "string",
                        "enum": ["porcentaje", "monto", "precio_fijo"],
                    },
                    "valor": {"type": "number"},
                    "dias": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "lunes", "martes", "miercoles", "jueves",
                                "viernes", "sabado", "domingo",
                            ],
                        },
                    },
                    "condiciones": {"type": ["string", "null"]},
                    "vigencia_desde": {"type": ["string", "null"]},
                    "vigencia_hasta": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                },
                "required": [
                    "tarjeta", "emisor", "medio_pago", "comercio", "categoria",
                    "tipo", "valor", "dias", "condiciones",
                    "vigencia_desde", "vigencia_hasta", "url",
                ],
            },
        }
    },
    "required": ["beneficios"],
}

INSTRUCCIONES = """\
Eres un extractor de beneficios de tarjetas en Chile. Te paso el texto de una
página y devuelves TODOS los beneficios de comercios que encuentres, sin
importar el rubro.

Reglas estrictas:
- NO inventes. Extrae únicamente beneficios escritos explícitamente en el texto.
- Si un dato no está en el texto, usa null (no adivines).
- `comercio` es el local/marca donde aplica el descuento (ej. "Cruz Verde",
  "PedidosYa", "Preunic", "Coca-Cola").
- Incluí SOLO descuentos en un comercio concreto. DESCARTÁ promos genéricas que
  no sean de un comercio: cashback general, pago de cuentas, suscripciones,
  pedir/activar la tarjeta, sorteos, "kit de bienvenida", o promos de la propia
  marca del banco (MACHBANK/MACH) sin un comercio asociado.
- Si el día viene indicado en el texto (ej. "días: martes,jueves"), usalo. Si
  aplica todos los días de la semana, dejá `dias` como lista vacía.
- `categoria` es el rubro del comercio. Usá EXCLUSIVAMENTE una de estas (en
  minúscula, sin tilde): comida, salud, entretenimiento, viajes, transporte,
  mercado, tienda, belleza, mascotas, hogar, servicios, combustible, otros.
  Reglas: "comida" cubre TODO lo gastronómico (restaurantes, bares, comida
  rápida, cafés, heladerías, delivery, bebidas). "salud" incluye farmacias.
  "mercado" es supermercado/grandes tiendas. NO inventes categorías nuevas ni
  uses etiquetas de producto de tarjeta ("cmr puntos", "elite"). Si ninguna
  calza, usá "otros".
- `tipo`: "porcentaje" (valor = el %, ej. 20), "monto" (valor = pesos de
  descuento) o "precio_fijo" (valor = precio final en pesos).
- `valor` SIEMPRE debe ser un número concreto SACADO DEL TEXTO (mayor a 0).
  NUNCA inventes ni rellenes un valor (no pongas 1, ni un estimado). Si el texto
  no dice una cifra explícita de descuento/cashback (ej. solo dice "Descuento en
  X", "Ahorra en X" o "cashback" sin número), DESCARTÁ ese beneficio.
- `dias`: lista de días en que aplica (en minúscula, sin tilde). Si aplica
  todos los días o no especifica, deja la lista vacía.
- `medio_pago`: generá UNA fila por cada medio de pago que el texto liste
  EXPLÍCITAMENTE para ese beneficio. Reglas:
  · Si el texto dice "medio de pago: crédito" o "Tarjeta de Crédito", devolvé
    SOLO una fila con "credito". NO agregues "debito".
  · Si dice solo débito, devolvé SOLO "debito".
  · Si lista ambos ("crédito, débito"), devolvé DOS filas (una por medio).
  · Solo si el texto NO menciona ningún medio de pago, devolvé una sola fila
    con "debito" por defecto.
  NUNCA dupliques un beneficio en un medio que el texto no menciona.
- Fechas en formato YYYY-MM-DD o null.
- `condiciones`: SOLO la restricción práctica que afecta al usuario, en UNA
  frase breve (máximo ~120 caracteres). Ejemplos válidos: tope de descuento,
  mínimo de compra, cupón requerido, stock/cupos limitados, productos excluidos,
  "no acumulable con otras promos". Si no hay ninguna restricción accionable,
  usa null.
  PROHIBIDO copiar el boilerplate legal. NO incluyas frases como "Términos,
  condiciones y exclusiones...", "de exclusiva responsabilidad del comercio",
  "Infórmese sobre la garantía estatal", "consultar al emisor", URLs, ni
  reproducir párrafos largos. Resume, no transcribas.
- `url`: si la línea del beneficio trae un marcador `<url:...>`, copiá ESE valor
  EXACTO (sin el `<url:` ni el `>`) en TODOS los beneficios que derives de esa
  línea. Si no hay marcador, usá null. NUNCA inventes ni completes una URL.
"""


def limpiar_condiciones(cond: str | None) -> str | None:
    """Normaliza `condiciones`: quita boilerplate legal y acota el largo.

    Defensa en código (el prompt ya pide resumir, pero el modelo no es 100%
    determinista). Devuelve null si lo que queda es solo prosa legal.
    """
    if not cond:
        return None
    texto = " ".join(cond.split())  # colapsa espacios/saltos de línea

    # Si arranca con boilerplate, cortá en la primera frase legal conocida para
    # quedarte con la restricción real (si la hay antes).
    m = _COND_BOILERPLATE.search(texto)
    if m:
        texto = texto[: m.start()].rstrip(" .,;–-")

    if not texto:
        return None

    if len(texto) > MAX_COND_CHARS:
        # Cortá en el último límite de palabra dentro del tope.
        texto = texto[:MAX_COND_CHARS].rsplit(" ", 1)[0].rstrip(" .,;–-") + "…"
    return texto or None


def limpiar_html(html: str) -> str:
    """Extrae el texto visible de un HTML, descartando scripts/estilos."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    texto = soup.get_text(separator="\n")
    # Colapsar líneas en blanco repetidas.
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    return "\n".join(lineas)


def extraer_beneficios(
    texto: str,
    tarjeta: str,
    emisor: str,
    fuente: str,
    urls_validas: set[str] | None = None,
    medios_por_url: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Convierte texto de una página en beneficios estructurados via Claude.

    `tarjeta`/`emisor` son el default si el texto no nombra la tarjeta.
    `fuente` queda registrado en cada beneficio (trazabilidad).
    `urls_validas`: si la fuente inyecta marcadores `<url:...>` por beneficio,
    pasá acá el set de URLs reales. Cualquier `url` que el modelo devuelva y que
    no esté en el set se descarta (defensa anti-alucinación).
    `medios_por_url`: mapa url -> {"credito","debito"} con los medios de pago que
    la FUENTE declara para ese beneficio. El modelo a veces inventa una fila en
    un medio que el texto no menciona (ej. agrega débito a un beneficio solo de
    crédito); si la fuente lo declara, se descartan esas filas espurias.
    """
    client = Anthropic()  # lee ANTHROPIC_API_KEY del entorno

    contenido = texto[:MAX_CHARS]
    prompt = (
        f"La tarjeta por defecto es '{tarjeta}' (emisor '{emisor}').\n\n"
        f"TEXTO DE LA PÁGINA:\n{contenido}"
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        temperature=0,  # determinismo: misma página -> mismos beneficios
        system=INSTRUCCIONES,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": BENEFICIO_SCHEMA}},
    )

    raw = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(raw)

    beneficios = []
    for b in data.get("beneficios", []):
        # Filtro de calidad: descartar beneficios sin valor cuantificable.
        # (El prompt ya lo pide, pero el modelo no es 100% determinista.)
        # `valor <= 1` es el placeholder que el modelo inventa cuando el texto
        # no trae cifra concreta (sorteos, preventas, "gratis", canjes): ningún
        # descuento real promocionado es de 1% ni $1. Si el comercio sí tiene
        # cifra real, sale > 1 (ej. Buho $5.000, Coca-Cola 30%).
        if not b.get("valor") or b["valor"] <= 1:
            continue
        # Defaults de tarjeta si el modelo no la identificó en el texto.
        b["tarjeta"] = b.get("tarjeta") or tarjeta
        b["emisor"] = b.get("emisor") or emisor
        b["categoria"] = _normalizar_categoria(b.get("categoria"))
        b["condiciones"] = limpiar_condiciones(b.get("condiciones"))
        # URL exacta del beneficio: solo se acepta si coincide con una real
        # inyectada por la fuente (evita que el modelo invente links).
        url = b.get("url")
        if url and urls_validas is not None and url not in urls_validas:
            url = None
        b["url"] = url or None

        # Medio de pago: si la fuente declaró los medios para esta url, descartar
        # filas en un medio que NO declaró (el modelo a veces inventa débito).
        if url and medios_por_url:
            declarados = medios_por_url.get(url)
            if declarados and b["medio_pago"] not in declarados:
                continue

        b["fuente"] = fuente
        beneficios.append(b)

    # Dedup de filas idénticas: el modelo a veces emite el mismo beneficio dos
    # veces. Dos filas con TODOS los campos iguales (incl. tarjeta, medio, url y
    # días) son duplicados reales; las distintas por tarjeta/medio se conservan.
    vistos: set[tuple] = set()
    unicos = []
    for b in beneficios:
        clave = (
            b["tarjeta"], b["medio_pago"], b["comercio"], b["categoria"],
            b["tipo"], b["valor"], tuple(b.get("dias") or []),
            b.get("vigencia_desde"), b.get("vigencia_hasta"),
            b.get("url"), b.get("condiciones"),
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(b)
    return unicos
