"""Acceso a Supabase para el scraper (upsert de tarjetas y beneficios)."""
import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def upsert_tarjeta(client: Client, nombre: str, emisor: str | None = None) -> int:
    """Crea (o recupera) una tarjeta por nombre y devuelve su id."""
    existing = client.table("tarjeta").select("id").eq("nombre", nombre).execute()
    if existing.data:
        return existing.data[0]["id"]
    inserted = (
        client.table("tarjeta")
        .insert({"nombre": nombre, "emisor": emisor})
        .execute()
    )
    return inserted.data[0]["id"]


def replace_beneficios(client: Client, beneficios: list[dict]) -> int:
    """Reemplaza los beneficios de las fuentes presentes en `beneficios`.

    Borra los registros viejos cuya `fuente` aparece en el lote nuevo y luego
    inserta los nuevos. Así cada corrida deja un snapshot fresco sin acumular
    duplicados (idempotente). Una fuente que no corre conserva sus datos.
    """
    if not beneficios:
        return 0

    fuentes = sorted({b.get("fuente") for b in beneficios if b.get("fuente")})
    if fuentes:
        client.table("beneficio").delete().in_("fuente", fuentes).execute()

    client.table("beneficio").insert(beneficios).execute()
    return len(beneficios)
