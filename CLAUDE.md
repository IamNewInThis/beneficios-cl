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
GitHub Actions (cron) -> scraper/ (Python+Playwright) -> Supabase (Postgres)
                                                              |
                                         frontend/ (Next.js) lee y muestra
```

- **scraper y web desacoplados**: solo se comunican por la base de datos.
- La web **nunca scrapea en vivo**: lee datos ya cacheados (rápido, robusto).
- web usa la **anon key** (solo lectura); el scraper usa la **service role**.

## Estructura

- `frontend/` — Next.js 15 + TypeScript + Tailwind. Pantalla "Beneficios de hoy".
- `scraper/` — Python. Cada fuente en `scraper/sources/`, registrada en `SOURCES`.
- `db/schema.sql` — esquema de Supabase/Postgres (tabla `tarjeta`, `beneficio`,
  vista `beneficio_detalle`).
- `.github/workflows/scraper.yml` — cron que ejecuta el scraper.

## Convenciones / decisiones ya tomadas (no re-litigar sin avisar)

- **Sin login** en la v1. El valor se ve sin registrarse.
- **Card por comercio**, agrupando tarjetas y distinguiendo `credito`/`debito`.
- **Orden aleatorio** de resultados en la v1 (sin señal de relevancia aún).
- **Toggle Hoy / Semana** (ventana de ~7 días) como vista temporal.
- **Categorías v1**: super, farmacia, comida, combustible.
- Scraping desde la v1; cada fuente aislada (una caída no tumba al resto).

## Modelo de datos y flujo (clave para entender el código)

- Tablas en `db/schema.sql`: `tarjeta` (id, nombre único, emisor) y `beneficio`
  (FK a tarjeta, `medio_pago` credito|debito, `comercio`, `categoria`, `tipo`
  porcentaje|monto|precio_fijo, `valor`, `dias text[]`, `condiciones`,
  `vigencia_desde/hasta`, `fuente`). La web lee de la **vista
  `beneficio_detalle`** (beneficio + nombre de tarjeta ya unidos).
- **Contrato fuente→BD**: cada `scrape()` devuelve dicts con el formato de
  `sources/example_source.py`. `main.py::normalize()` los mapea a la tabla
  `beneficio`; `db.upsert_tarjeta()` resuelve/crea la tarjeta por nombre.
- **El filtrado por día NO ocurre en SQL**: `frontend/app/page.tsx` trae *todos* los
  beneficios y filtra "aplica hoy" en el server component (`aplicaHoy`: lista de
  días vacía = siempre aplica). Los `Categoria`/`MedioPago`/`TipoBeneficio` de
  `frontend/lib/types.ts` deben mantenerse sincronizados con los `check` del schema.
- **Aislamiento de fuentes**: `main.py` envuelve cada `source.scrape()` en
  try/except; una fuente que lanza excepción se cuenta como fallida y no detiene
  al resto. Exit code 1 solo si hubo fallidas y 0 insertados.

## Estado actual vs. convenciones

Varias convenciones de abajo son el *objetivo de producto*, aún no implementadas
en código: el toggle Hoy/Semana, el filtro por categoría/comercio/banco y el
orden aleatorio **no existen todavía** en `page.tsx` (hoy solo muestra
"beneficios de hoy" agrupados por comercio). La única fuente registrada es
`example_source` (datos hardcodeados); no hay scraping real aún. No hay tests.

## Comandos

```bash
# frontend (Next.js 16, React 19, Tailwind 3)
cd frontend
cp .env.example .env.local                # NEXT_PUBLIC_SUPABASE_URL + ANON_KEY
npm install
npm run dev                               # http://localhost:3000
npm run build                             # build de producción
# Nota: `next lint` fue removido en Next 16; aún no hay ESLint configurado.

# scraper (Python 3.13)
cd scraper
cp .env.example .env                      # SUPABASE_URL + SUPABASE_SERVICE_KEY
pip install -r requirements.txt && playwright install chromium
python main.py                            # scrapea y puebla la BD
```

No hay suite de tests ni linter de Python configurados todavía.

## Para agregar una fuente de scraping

1. Crear `scraper/sources/<nombre>.py` con una función `scrape() -> list[dict]`
   en el formato documentado en `sources/example_source.py`.
2. Registrar el módulo en la lista `SOURCES` de `scraper/sources/__init__.py`.
