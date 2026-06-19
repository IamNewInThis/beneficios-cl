"""Fuentes de scraping.

Cada fuente expone una función `scrape() -> list[dict]` que devuelve beneficios
en un formato común (ver `sources/example_source.py`). Para agregar una fuente
nueva: crea un módulo aquí y regístralo en la lista `SOURCES` de abajo.
"""
from . import mach, tenpo, bancofalabella, bci, bancochile

# Lista de fuentes activas. Agregar nuevas a medida que se implementen.
#
# NOTA: `bancosantander` NO está acá a propósito. Esta lista la corre `main.py`
# y el cron de GitHub Actions; Santander está detrás de Akamai Bot Manager y solo
# se deja scrapear con un navegador HEADFUL (visible) desde una IP residencial
# chilena. En el cron (IP de datacenter US, sin display) daría 403 en cada
# corrida. Por eso es una fuente MANUAL/LOCAL: se ejecuta a mano (ver el docstring
# de `sources/bancosantander.py`). Si algún día hay un proxy residencial CL +
# forma de correr headful, recién ahí tendría sentido sumarla acá.
SOURCES = [
    mach,
    tenpo,
    bancofalabella,
    bci,
    bancochile,
]
