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

- `frontend/` — Next.js 16 + React 19 + TypeScript + Tailwind. `app/page.tsx`
  (server, trae datos paginados) + `app/beneficios-app.tsx` (client, filtros y
  agrupado por comercio).
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
- **Categoría: texto libre en la BD, pero vocabulario CANÓNICO en código.** No
  hay `check` en Postgres (se soltó el enum en `db/migrations/001`), pero
  `extract.py::_normalizar_categoria()` colapsa lo que devuelve la IA a un set
  fijo (`comida`, `salud`, `entretenimiento`, `viajes`, `transporte`, `mercado`,
  `tienda`, `belleza`, `mascotas`, `hogar`, `servicios`, `combustible`, `otros`),
  para que el filtro lateral del front sea consistente. "comida" cubre todo lo
  gastronómico; "salud" incluye farmacias. Default `otros`.
- **Extracción con IA, no parsing a mano** (ver sección dedicada).
- Cada fuente aislada (una caída no tumba al resto).

## Modelo de datos y flujo (clave para entender el código)

- Tablas en `db/schema.sql`: `tarjeta` (id, nombre único, emisor) y `beneficio`
  (FK a tarjeta, `medio_pago` credito|debito, `comercio`, `categoria`, `tipo`
  porcentaje|monto|precio_fijo, `valor`, `dias text[]`, `condiciones`,
  `vigencia_desde/hasta`, `fuente`, `url`). La web lee de la **vista
  `beneficio_detalle`** (beneficio + nombre de tarjeta ya unidos).
- **`url` = deep-link al beneficio concreto** (no a la fuente). Se agregó en
  `db/migrations/002`. Sirve para validar y para el "Ver en el sitio" del modal.
  OJO: es distinto de `fuente` (la URL del listado, estable, que usa el dedup).
  Las fuentes lo inyectan en el texto como marcador `<url:...>` y el extractor lo
  copia (validándolo contra un set de urls reales). Ver "Extracción con IA".
- **Contrato fuente→BD**: cada `scrape()` devuelve dicts con el formato de
  `sources/example_source.py`. `main.py::normalize()` los mapea a la tabla
  `beneficio`; `db.upsert_tarjeta()` resuelve/crea la tarjeta por nombre.
- **Idempotencia / dedup**: `db.replace_beneficios()` borra los beneficios cuya
  `fuente` aparece en el lote nuevo y reinserta. Así cada corrida (y el cron, 2×
  al día) deja un snapshot fresco sin acumular duplicados. Una fuente que NO
  corre conserva sus datos. Por eso cada beneficio debe traer un `fuente` estable.
- **El filtrado NO ocurre en SQL**: `frontend/app/page.tsx` (server) trae *todos*
  los beneficios; el filtrado por día/ventana, vigencia y los filtros de
  categoría/comercio/banco ocurren en `frontend/app/beneficios-app.tsx` (client).
  Convenciones: `dias` vacío = aplica todos los días; `vigencia_hasta` NULL = se
  muestra (NULL ≠ vencido), `vigencia_hasta < hoy` = se oculta.
  `MedioPago`/`TipoBeneficio` en `frontend/lib/types.ts` deben matchear los
  `check` del schema; `Categoria` es texto libre (unión laxa con `(string & {})`),
  sin `check` en la BD (la consistencia la da el normalizador del scraper).
- **Aislamiento de fuentes**: `main.py` envuelve cada `source.scrape()` en
  try/except; una fuente que lanza excepción se cuenta como fallida y no detiene
  al resto. Exit code 1 solo si hubo fallidas y 0 insertados.

## Extracción con IA (decisión central, leer antes de tocar fuentes)

El paso difícil no es bajar la página sino convertir la prosa de marketing a
`{comercio, categoria, tipo, valor, dias, ...}`. En vez de parsers frágiles por
sitio, hay **un solo helper genérico**: `extract.py::extraer_beneficios(texto,
tarjeta, emisor, fuente, urls_validas=None, medios_por_url=None)`. Lo único que
cambia por fuente es de dónde sale el `texto`.

- Usa **Claude Haiku 4.5** (`MODEL` en `extract.py`) con **structured output**
  (`output_config={"format": {"type": "json_schema", "schema": ...}}`) →
  el modelo está obligado a devolver el `BENEFICIO_SCHEMA`. Requiere un SDK
  `anthropic` reciente (≥ ~0.46; el repo fija 0.109.2) — los viejos no tienen
  `output_config`.
- `temperature=0` para consistencia. Aun así la extracción **no es 100%
  determinista** en casos borde (valores vagos, "gratis", "hasta X%"): el conteo
  final puede fluctuar entre corridas. Los beneficios claros salen estables.
- **Defensas en código (además del prompt), porque el modelo no es 100%
  determinista — mantenelas todas:**
  - `valor <= 1` se descarta (no solo `<= 0`): `1`/`$1` es el placeholder que el
    modelo inventa cuando no hay cifra concreta (sorteos, "gratis", "hasta X%").
  - `_normalizar_categoria()` colapsa la categoría al set canónico.
  - `limpiar_condiciones()` corta el boilerplate legal y acota a ~160 chars
    (`condiciones` debe ser la restricción accionable, no la letra chica).
  - `urls_validas`: si la fuente inyecta marcadores `<url:...>`, cualquier `url`
    que el modelo devuelva y no esté en ese set se anula (anti-link inventado).
  - `medios_por_url`: si la fuente declara los medios de pago reales por url, se
    descartan filas en un medio que la fuente NO declaró (el modelo a veces
    agrega un "débito" espurio a un beneficio solo de crédito).
  - **Dedup final**: filas idénticas en todos los campos se colapsan (el modelo a
    veces repite el mismo beneficio).
- `ANTHROPIC_API_KEY` se lee del entorno (`load_dotenv()` en `extract.py`).
- La IA **no inventa**: solo reordena lo que ya está escrito en el texto que le
  pasás. Para fuentes con MUCHOS beneficios, extraer **por lotes** (ver
  `sources/bancosantander.py::BATCH`): un solo texto gigante supera `MAX_CHARS` y
  el `max_tokens` de la respuesta.

### Patrón "datos embebidos" (ver `sources/mach.py`)

Muchos sitios (SPAs, CMS tipo Storyblok) **renderizan pocos beneficios** pero
traen el catálogo COMPLETO embebido en JSON dentro del HTML. `requests` + texto
visible se pierde casi todo (en Mach: 4.7 KB renderizados vs. 33 beneficios en
el blob). La fuente extrae esas entradas estructuradas del HTML crudo (regex
sobre el JSON embebido) y le pasa el texto limpio al extractor. Si una fuente
trae poco, sospechá de datos embebidos antes que de Playwright.

### Fuentes especiales (no siguen el patrón "requests → IA")

- **`bancofalabella` — Contentful, SIN IA.** El sitio usa Contentful con GraphQL
  público; la fuente consulta el API y arma las filas directo (los datos ya
  vienen estructurados, no hace falta el LLM). Aun así reusa los guards del
  extractor (`_normalizar_categoria`, `limpiar_condiciones`, `valor>1`). El
  `FALABELLA_CONTENTFUL_TOKEN` es el token **público** de Falabella (no propio,
  no se regenera). El deep-link sale del campo `cardUrl` (NO existe `slug`).
- **`bancosantander` — Akamai + Playwright HEADFUL, MANUAL.** Detrás de Akamai
  Bot Manager: `requests`/curl/headless dan **403**; solo pasa un navegador real
  **headful** (`headless=False`) desde una IP residencial chilena. Por eso **no
  está en `SOURCES`** (el cron en GitHub Actions daría 403) — se corre a mano.
  Usa `domcontentloaded` (NUNCA `networkidle`: el sitio nunca queda idle por los
  beacons de Akamai) y concurrencia acotada (`SANTANDER_WORKERS`, pestañas en
  paralelo) para los ~300 detalles.

## Estado actual vs. convenciones

- **Fuentes en `SOURCES`** (las corre `main.py`/el cron): `mach`, `tenpo`,
  `bancofalabella`, `bci`, `bancochile`, `cencosud`, `bancoripley`.
  `example_source` ya no se registra (queda como referencia del formato de salida).
  `bancoripley` usa Playwright **headless** (el cron ya hace `playwright install
  --with-deps chromium`); no tiene URL por beneficio (solo anclas de categoría).
- **`bancosantander` NO está en `SOURCES`** a propósito: es una fuente
  **manual/local** (Akamai + headful, ver "Fuentes especiales" abajo). Sus datos
  ya están en la BD, pero se refresca a mano.
- **Frontend**: `app/page.tsx` (server component) trae *todos* los beneficios
  paginando y se los pasa a `app/beneficios-app.tsx` (**client component**), que
  hace el filtrado por día/ventana, el filtro de vigencia y el agrupado por
  comercio. El toggle Hoy/Semana y los filtros **ya existen** ahí (no es backlog).
- **Límite de 1000 filas de PostgREST**: Supabase devuelve máx. 1000 filas por
  request. Con >1000 beneficios, `page.tsx` **pagina con `.range()`** (orden
  estable por `id`); sin eso, las fuentes con ids más altos quedan fuera de la web.
- **No hay tests** ni linter de Python. `next lint` fue removido en Next 16.

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
# La mayoría de fuentes usan requests; SOLO `bancosantander` necesita Chromium:
#   playwright install chromium
python main.py                            # corre las fuentes de SOURCES y puebla la BD

# Probar UNA fuente en aislamiento (sin tocar la BD):
python -c "from sources import mach; print(mach.scrape())"

# Santander (manual, NO está en SOURCES): se corre headful, en IP chilena, y se
# escribe a mano con db.replace_beneficios. Importar el módulo directo evita
# cargar SOURCES. SANTANDER_WORKERS controla la concurrencia (default 4).
```

- **Usar `python3.13` explícito** para el venv: el `python3` por defecto puede ser
  3.14, sin wheel de greenlet (rompe Playwright/Supabase).

- El scraper necesita en `scraper/.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` y
  `ANTHROPIC_API_KEY` (de pago — cada corrida llama a Claude; con Haiku son
  centavos/mes). Para Falabella además `FALABELLA_CONTENTFUL_TOKEN` (token público
  de Falabella, ver "Fuentes especiales").
- ⚠️ **Gap conocido (cron roto hasta resolverlo)**: `.github/workflows/scraper.yml`
  solo pasa los secrets de Supabase. Faltan **`ANTHROPIC_API_KEY`** (la usan
  todas las fuentes con IA) y **`FALABELLA_CONTENTFUL_TOKEN`**. Este último es
  peor: `bancofalabella` lo lee a nivel de módulo (`os.environ[...]`), así que sin
  esa var `import sources` revienta y `main.py` muere antes de correr nada (tumba
  el cron entero). Hay que agregar ambos al workflow Y a los secrets del repo.
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
