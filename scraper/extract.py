"""Extracción de beneficios desde texto usando Claude (structured output).

Este helper es GENÉRICO: cualquier fuente le pasa el texto plano de una página
y recibe una lista de beneficios ya estructurados en el formato de la tabla
`beneficio` (ver sources/example_source.py). La normalización difícil
(prosa de marketing -> campos) la hace el modelo, no regex frágil.

La IA NO inventa: solo estructura lo que ya está escrito en el texto.
"""
import json

from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()  # lee ANTHROPIC_API_KEY desde scraper/.env

# Modelo barato y suficiente para extracción estructurada.
MODEL = "claude-haiku-4-5"

# Tope de caracteres del texto que mandamos al modelo (acota tokens/costo).
MAX_CHARS = 60_000

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
                },
                "required": [
                    "tarjeta", "emisor", "medio_pago", "comercio", "categoria",
                    "tipo", "valor", "dias", "condiciones",
                    "vigencia_desde", "vigencia_hasta",
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
- `categoria` es el rubro del comercio, en una sola palabra en minúscula y sin
  tilde. Usa estas cuando apliquen: super, farmacia, comida, combustible,
  bebidas, perfumeria, tienda, tecnologia, viajes, entretenimiento, salud,
  belleza, mascotas. Si ninguna calza, elige la más cercana o usa "otros".
- `tipo`: "porcentaje" (valor = el %, ej. 20), "monto" (valor = pesos de
  descuento) o "precio_fijo" (valor = precio final en pesos).
- `valor` SIEMPRE debe ser un número concreto SACADO DEL TEXTO (mayor a 0).
  NUNCA inventes ni rellenes un valor (no pongas 1, ni un estimado). Si el texto
  no dice una cifra explícita de descuento/cashback (ej. solo dice "Descuento en
  X", "Ahorra en X" o "cashback" sin número), DESCARTÁ ese beneficio.
- `dias`: lista de días en que aplica (en minúscula, sin tilde). Si aplica
  todos los días o no especifica, deja la lista vacía.
- `medio_pago`: "credito" o "debito" según lo que diga el texto. Si no lo
  aclara, usa "debito".
- Fechas en formato YYYY-MM-DD o null.
- `condiciones`: topes, cupones, mínimos de compra, etc. (texto corto) o null.
"""


def limpiar_html(html: str) -> str:
    """Extrae el texto visible de un HTML, descartando scripts/estilos."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    texto = soup.get_text(separator="\n")
    # Colapsar líneas en blanco repetidas.
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    return "\n".join(lineas)


def extraer_beneficios(texto: str, tarjeta: str, emisor: str, fuente: str) -> list[dict]:
    """Convierte texto de una página en beneficios estructurados via Claude.

    `tarjeta`/`emisor` son el default si el texto no nombra la tarjeta.
    `fuente` queda registrado en cada beneficio (trazabilidad).
    """
    client = Anthropic()  # lee ANTHROPIC_API_KEY del entorno

    contenido = texto[:MAX_CHARS]
    prompt = (
        f"La tarjeta por defecto es '{tarjeta}' (emisor '{emisor}').\n\n"
        f"TEXTO DE LA PÁGINA:\n{contenido}"
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
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
        if not b.get("valor") or b["valor"] <= 0:
            continue
        # Defaults de tarjeta si el modelo no la identificó en el texto.
        b["tarjeta"] = b.get("tarjeta") or tarjeta
        b["emisor"] = b.get("emisor") or emisor
        b["fuente"] = fuente
        beneficios.append(b)
    return beneficios
