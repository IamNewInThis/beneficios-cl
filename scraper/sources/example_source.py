"""Fuente de EJEMPLO — plantilla para escribir scrapers reales.

Devuelve datos hardcodeados para poder probar el flujo completo
(scraper -> BD -> web) antes de implementar el scraping real de una fuente.

Para un scraper real, reemplaza el cuerpo de `scrape()` por algo que use
Playwright/BeautifulSoup para extraer los beneficios de una web concreta.
Mantén el MISMO formato de salida.

Formato de cada beneficio:
    {
        "tarjeta": "CMR Falabella",      # nombre de la tarjeta (str)
        "emisor": "Banco Falabella",     # opcional
        "medio_pago": "credito",          # "credito" | "debito"
        "comercio": "Cruz Verde",
        "categoria": "farmacia",          # super|farmacia|comida|combustible
        "tipo": "porcentaje",             # porcentaje|monto|precio_fijo
        "valor": 20,
        "dias": ["martes"],
        "condiciones": "Tope $15.000",
        "vigencia_desde": None,           # "YYYY-MM-DD" o None
        "vigencia_hasta": "2026-07-31",
        "fuente": "manual:example",
    }
"""


def scrape() -> list[dict]:
    return [
        {
            "tarjeta": "CMR Falabella",
            "emisor": "Banco Falabella",
            "medio_pago": "credito",
            "comercio": "Cruz Verde",
            "categoria": "farmacia",
            "tipo": "porcentaje",
            "valor": 20,
            "dias": ["martes"],
            "condiciones": "Tope $15.000",
            "vigencia_desde": None,
            "vigencia_hasta": "2026-07-31",
            "fuente": "manual:example",
        },
        {
            "tarjeta": "CMR Falabella",
            "emisor": "Banco Falabella",
            "medio_pago": "debito",
            "comercio": "Cruz Verde",
            "categoria": "farmacia",
            "tipo": "porcentaje",
            "valor": 10,
            "dias": ["martes"],
            "condiciones": "Tope $15.000",
            "vigencia_desde": None,
            "vigencia_hasta": "2026-07-31",
            "fuente": "manual:example",
        },
    ]
