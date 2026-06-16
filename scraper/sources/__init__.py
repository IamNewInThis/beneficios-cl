"""Fuentes de scraping.

Cada fuente expone una función `scrape() -> list[dict]` que devuelve beneficios
en un formato común (ver `sources/example_source.py`). Para agregar una fuente
nueva: crea un módulo aquí y regístralo en la lista `SOURCES` de abajo.
"""
from . import example_source

# Lista de fuentes activas. Agregar nuevas a medida que se implementen.
SOURCES = [
    example_source,
]
