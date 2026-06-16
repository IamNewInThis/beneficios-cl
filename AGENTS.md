# AGENTS.md — beneficios-cl

Arquitectura: GitHub Actions (cron) → scraper Python (Claude Haiku 4.5) → Supabase Postgres → Next.js 16 server component (sin auth).

## Comandos

```bash
# frontend
cd frontend && npm install && npm run dev   # localhost:3000
npm run build                                # producción

# scraper (Python 3.13, con venv activo)
cd scraper
python -c "from sources import mach; print(mach.scrape())"   # probar 1 fuente (sin BD)
python -c "from sources import tenpo; print(tenpo.scrape())" # probar Tenpo
python main.py                                                # scrapear todo a Supabase
```

- No hay test, lint, ni formateo configurados (en ningún lado).
- Las migraciones de BD se ejecutan a mano en el SQL Editor de Supabase (no hay runner).

## Reglas de dedup (clave)

`db.replace_beneficios()` **borra e inserta** por `fuente`: cada corrida reemplaza el snapshot completo de las fuentes que corrieron. Una fuente que NO corre conserva sus datos. El campo `fuente` debe ser estable y único por origen.

## Categorías: texto libre

Las categorías (`super`, `farmacia`, `comida`, `combustible`, `viajes`, etc.) no tienen CHECK en la BD (migración `001` eliminó el enum). La IA las asigna libremente. En TypeScript se usa `(string & {})` para tener autocompletado laxo.

## Filtro de días

`page.tsx` trae todos los beneficios de la vista `beneficio_detalle` y filtra "aplica hoy" en el server component. `dias: []` = siempre aplica. No hay filtrado en SQL.

## Agregar una fuente de scraping

1. Crear `scraper/sources/<nombre>.py` con `scrape() -> list[dict]`.
2. El dict debe seguir el formato de `sources/example_source.py` (campos: `tarjeta`, `emisor`, `medio_pago`, `comercio`, `categoria`, `tipo`, `valor`, `dias`, `condiciones`, `fuente`).
3. Pasar el texto extraído a `extract.extraer_beneficios(texto, tarjeta, emisor, fuente)` para estructurarlo con IA.
4. Registrar el módulo en `sources/__init__.py` (`SOURCES` list).

## Patrón de datos embebidos

Antes de recurrir a Playwright: muchos sitios (Storyblok, SPAs) embeben el catálogo completo en JSON dentro del HTML. Ver `sources/mach.py` — usa regex sobre el HTML crudo para extraer el blob, no texto renderizado.

Si no hay JSON embebido, los CMS como Webflow suelen renderizar los items en el HTML inicial (`w-dyn-item`). Ver `sources/tenpo.py` — usa BeautifulSoup para extraer el grid.

## Gaps conocidos

- CI (`.github/workflows/scraper.yml`) no pasa `ANTHROPIC_API_KEY` — el cron fallará hasta agregarlo.
- El scraper llama a Claude Haiku (costo ~centavos/corrida). La key se lee del entorno (`ANTHROPIC_API_KEY`).
- Frontend usa anon key (solo lectura); scraper usa service role.
- Features pendientes en `page.tsx`: toggle Hoy/Semana, filtros, orden aleatorio.

## Stack

- Frontend: Next.js 16, React 19, Tailwind 3, TypeScript strict, Supabase JS client.
- Scraper: Python 3.13, requests, BeautifulSoup, Anthropic SDK 0.109.2, Supabase Python SDK.
- BD: Supabase Postgres con tablas `tarjeta` y `beneficio`, vista `beneficio_detalle`.
