"""Punto de entrada del scraper.

Recorre todas las fuentes registradas, normaliza los beneficios y los guarda en
Supabase. Cada fuente está aislada: si una falla, las demás siguen.

Uso:
    python main.py
"""
import sys

import db
from sources import SOURCES


def normalize(raw: dict, tarjeta_id: int) -> dict:
    """Convierte el dict de una fuente al formato de la tabla `beneficio`."""
    return {
        "tarjeta_id": tarjeta_id,
        "medio_pago": raw["medio_pago"],
        "comercio": raw["comercio"],
        "categoria": raw["categoria"],
        "tipo": raw["tipo"],
        "valor": raw["valor"],
        "dias": raw.get("dias", []),
        "condiciones": raw.get("condiciones"),
        "vigencia_desde": raw.get("vigencia_desde"),
        "vigencia_hasta": raw.get("vigencia_hasta"),
        "fuente": raw.get("fuente"),
    }


def main() -> int:
    client = db.get_client()
    total = 0
    fallidas = 0

    for source in SOURCES:
        nombre = source.__name__.split(".")[-1]
        try:
            raw_items = source.scrape()
        except Exception as e:  # una fuente caída no debe tumbar al resto
            print(f"[ERROR] fuente '{nombre}' falló: {e}", file=sys.stderr)
            fallidas += 1
            continue

        beneficios = []
        for raw in raw_items:
            tarjeta_id = db.upsert_tarjeta(client, raw["tarjeta"], raw.get("emisor"))
            beneficios.append(normalize(raw, tarjeta_id))

        n = db.insert_beneficios(client, beneficios)
        total += n
        print(f"[OK] fuente '{nombre}': {n} beneficios insertados")

    print(f"\nListo. {total} beneficios insertados. Fuentes fallidas: {fallidas}.")
    return 1 if fallidas and total == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
