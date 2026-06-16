# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# beneficios-cl — contexto para Claude Code

Webapp que centraliza los beneficios de tarjetas en Chile (descuentos por
comercio, día y medio de pago). El usuario entra y ve, **sin registrarse**, qué
beneficios aplican hoy / esta semana, y filtra por categoría, comercio o
banco/tarjeta.

## 📓 Documentación completa en el vault personal (Obsidian)

El detalle de **producto, requerimientos, diseño y decisiones de stack** vive en
el vault personal de Obsidian, NO en este repo. Para más contexto, consulta:

```
~/documents/Obsidian/Personal/Proyectos/
├── centralizador-beneficios-tarjetas.md       # idea, problema, fases (nota índice)
├── centralizador-beneficios-requerimientos.md # RF/RNF, alcance, modelo de datos
├── centralizador-beneficios-boceto.md         # wireframes baja fidelidad (móvil + PC)
└── centralizador-beneficios-stack.md          # stack elegido, arquitectura, descartes
```

> ⚠️ El vault es **local** a esta máquina y está fuera del repo. Si esos archivos
> existen, léelos antes de tomar decisiones de diseño/arquitectura — explican el
> *por qué* detrás de lo que hay en el código. Si no existen (otro equipo/clon),
> usa la info de este archivo y pregunta al usuario.

## Arquitectura (resumen)

```
GitHub Actions (cron) -> scraper/ (Python) --fetch--> sitio
                              |  texto crudo
                              v
                         Claude (Haiku 4.5) --estructura--> beneficios
                              |
                              v
                         Supabase (Postgres) <--lee-- frontend/ (Next.js)
```

- **scraper y web desacoplados**: solo se comunican por la base de datos.
- La web **nunca scrapea en vivo**: lee datos ya cacheados (rápido, robusto).
- web usa la **anon key** (solo lectura); el scraper usa la **service role**.
- **El scraper NO parsea HTML a mano**: baja el texto y usa un LLM (Claude) para
  convertir la prosa de marketing en beneficios estructurados. Ver
  "Extracción con IA" más abajo — es la decisión central de arquitectura.

## Estructura

- `frontend/` — Next.js 15 + TypeScript + Tailwind. Pantalla "Beneficios de hoy".
- `scraper/` — Python.
  - `main.py` — recorre `SOURCES`, normaliza y guarda (con dedup por fuente).
  - `extract.py` — **helper genérico de extracción con IA** (texto → beneficios
    estructurados via Claude + structured output). Lo reusa toda fuente.
  - `sources/` — una fuente por archivo, registrada en `sources/__init__.py`.
  - `db.py` — acceso a Supabase (upsert tarjeta, replace beneficios).
- `db/schema.sql` — esquema de Supabase/Postgres (tabla `tarjeta`, `beneficio`,
  vista `beneficio_detalle`). `db/migrations/` — cambios incrementales al esquema.
- `.github/workflows/scraper.yml` — cron que ejecuta el scraper.

## Convenciones / decisiones ya tomadas (no re-litigar sin avisar)

- **Sin login** en la v1. El valor se ve sin registrarse.
- **Card por comercio**, agrupando tarjetas y distinguiendo `credito`/`debito`.
- **Orden aleatorio** de resultados en la v1 (sin señal de relevancia aún).
- **Toggle Hoy / Semana** (ventana de ~7 días) como vista temporal.
- **Categoría libre** (texto): la IA asigna el rubro (`super`, `farmacia`,
  `comida`, `combustible`, `bebidas`, `perfumeria`, `tienda`, `viajes`, etc.).
  Ya NO hay enum fijo de 4 categorías — se soltó en `db/migrations/001`.
- **Extracción con IA, no parsing a mano** (ver sección dedicada).
- Cada fuente aislada (una caída no tumba al resto).

## Modelo de datos y flujo (clave para entender el código)

- Tablas en `db/schema.sql`: `tarjeta` (id, nombre único, emisor) y `beneficio`
  (FK a tarjeta, `medio_pago` credito|debito, `comercio`, `categoria`, `tipo`
  porcentaje|monto|precio_fijo, `valor`, `dias text[]`, `condiciones`,
  `vigencia_desde/hasta`, `fuente`). La web lee de la **vista
  `beneficio_detalle`** (beneficio + nombre de tarjeta ya unidos).
- **Contrato fuente→BD**: cada `scrape()` devuelve dicts con el formato de
  `sources/example_source.py`. `main.py::normalize()` los mapea a la tabla
  `beneficio`; `db.upsert_tarjeta()` resuelve/crea la tarjeta por nombre.
- **Idempotencia / dedup**: `db.replace_beneficios()` borra los beneficios cuya
  `fuente` aparece en el lote nuevo y reinserta. Así cada corrida (y el cron, 2×
  al día) deja un snapshot fresco sin acumular duplicados. Una fuente que NO
  corre conserva sus datos. Por eso cada beneficio debe traer un `fuente` estable.
- **El filtrado por día NO ocurre en SQL**: `frontend/app/page.tsx` trae *todos* los
  beneficios y filtra "aplica hoy" en el server component (`aplicaHoy`: lista de
  días vacía = siempre aplica). `MedioPago`/`TipoBeneficio` en
  `frontend/lib/types.ts` deben matchear los `check` del schema; `Categoria` es
  texto libre (unión laxa con `(string & {})`), sin `check` en la BD.
- **Aislamiento de fuentes**: `main.py` envuelve cada `source.scrape()` en
  try/except; una fuente que lanza excepción se cuenta como fallida y no detiene
  al resto. Exit code 1 solo si hubo fallidas y 0 insertados.

## Extracción con IA (decisión central, leer antes de tocar fuentes)

El paso difícil no es bajar la página sino convertir la prosa de marketing a
`{comercio, categoria, tipo, valor, dias, ...}`. En vez de parsers frágiles por
sitio, hay **un solo helper genérico**: `extract.py::extraer_beneficios(texto,
tarjeta, emisor, fuente)`. Lo único que cambia por fuente es de dónde sale el
`texto`.

- Usa **Claude Haiku 4.5** (`MODEL` en `extract.py`) con **structured output**
  (`output_config={"format": {"type": "json_schema", "schema": ...}}`) →
  el modelo está obligado a devolver el `BENEFICIO_SCHEMA`. Requiere un SDK
  `anthropic` reciente (≥ ~0.46; el repo fija 0.109.2) — los viejos no tienen
  `output_config`.
- `temperature=0` para consistencia. Aun así la extracción **no es 100%
  determinista** en casos borde (valores vagos, "gratis", "hasta X%"): el conteo
  final puede fluctuar entre corridas. Los beneficios claros salen estables.
- **Reglas anti-invención**: el prompt (`INSTRUCCIONES`) le prohíbe inventar y le
  pide descartar beneficios sin cifra concreta; además hay un **filtro en código**
  que tira cualquier `valor <= 0`. Mantené ambas defensas.
- `ANTHROPIC_API_KEY` se lee del entorno (`load_dotenv()` en `extract.py`).
- La IA **no inventa**: solo reordena lo que ya está escrito en el texto que le
  pasás.

### Patrón "datos embebidos" (ver `sources/mach.py`)

Muchos sitios (SPAs, CMS tipo Storyblok) **renderizan pocos beneficios** pero
traen el catálogo COMPLETO embebido en JSON dentro del HTML. `requests` + texto
visible se pierde casi todo (en Mach: 4.7 KB renderizados vs. 33 beneficios en
el blob). La fuente extrae esas entradas estructuradas del HTML crudo (regex
sobre el JSON embebido) y le pasa el texto limpio al extractor. Si una fuente
trae poco, sospechá de datos embebidos antes que de Playwright.

## Estado actual vs. convenciones

- **Fuentes reales**: `mach` (machbank.cl) ya scrapea de verdad vía IA, además
  de `example_source` (datos de juguete, sirve para probar la tubería).
- **Frontend**: aún solo muestra "beneficios de hoy" agrupados por comercio. El
  toggle Hoy/Semana, los filtros y el orden aleatorio son *objetivo de producto*,
  **no implementados todavía** en `page.tsx`.
- **No hay tests** ni linter de Python.

## Comandos

```bash
# frontend (Next.js 16, React 19, Tailwind 3)
cd frontend
cp .env.example .env.local                # NEXT_PUBLIC_SUPABASE_URL + ANON_KEY
npm install
npm run dev                               # http://localhost:3000
npm run build                             # build de producción
# Nota: `next lint` fue removido en Next 16; aún no hay ESLint configurado.

# scraper (Python 3.13) — usar venv
cd scraper
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env       # SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
pip install -r requirements.txt
# Playwright NO es necesario para las fuentes actuales (Mach usa requests).
# Solo si agregás una fuente que requiera renderizar JS:
#   playwright install chromium
python main.py                            # scrapea (llama a la IA) y puebla la BD

# Probar UNA fuente en aislamiento (sin tocar la BD):
python -c "from sources import mach; print(mach.scrape())"
```

- El scraper necesita **3 secretos** en `scraper/.env`: `SUPABASE_URL`,
  `SUPABASE_SERVICE_KEY` y `ANTHROPIC_API_KEY` (esta última es de pago — cada
  corrida llama a Claude; con Haiku el costo es de centavos/mes).
- ⚠️ **Gap conocido**: `.github/workflows/scraper.yml` aún NO pasa
  `ANTHROPIC_API_KEY` (solo los secrets de Supabase). El cron fallará hasta
  agregar ese secret al workflow y al repo de GitHub.
- Migraciones de BD: ejecutar los `.sql` de `db/migrations/` en el SQL Editor de
  Supabase (no hay runner automático).
- No hay suite de tests ni linter de Python configurados todavía.

## Para agregar una fuente de scraping

1. Crear `scraper/sources/<nombre>.py` con `scrape() -> list[dict]`. Patrón:
   bajar el contenido → pasar el texto a `extract.extraer_beneficios(...)`. Ver
   `sources/mach.py` (caso real con datos embebidos) y `sources/example_source.py`
   (formato de salida documentado). Cada beneficio debe traer un `fuente` estable
   (lo usa el dedup).
2. Registrar el módulo en la lista `SOURCES` de `scraper/sources/__init__.py`.
