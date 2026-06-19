"""Fuentes de scraping.

Cada fuente expone una función `scrape() -> list[dict]` que devuelve beneficios
en un formato común (ver `sources/example_source.py`). Para agregar una fuente
nueva: crea un módulo aquí y regístralo en la lista `SOURCES` de abajo.
"""
from . import mach, tenpo, bancofalabella, bci, bancochile, cencosud, bancoripley

# Lista de fuentes activas. Agregar nuevas a medida que se implementen.
#
# NOTA: `bancosantander` y `bancoestado` NO están acá a propósito. Esta lista la
# corre `main.py` y el cron de GitHub Actions; ambos sitios están detrás de Akamai
# Bot Manager y solo se dejan scrapear con un navegador HEADFUL (visible) desde
# una IP residencial chilena. En el cron (IP de datacenter US, sin display) darían
# error en cada corrida. Por eso son fuentes MANUAL/LOCAL: se ejecutan a mano (ver
# los docstrings de esos módulos). Si algún día hay un proxy residencial CL +
# forma de correr headful, recién ahí tendría sentido sumarlas acá.
SOURCES = [
    mach,
    tenpo,
    bancofalabella,
    bci,
    bancochile,
    cencosud,
    bancoripley,
]
