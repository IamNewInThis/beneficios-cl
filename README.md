# beneficios-cl

Webapp que **centraliza los beneficios de tarjetas en Chile** (descuentos por
comercio, día y medio de pago). El usuario entra y ve, sin registrarse, qué
beneficios aplican hoy / esta semana, y puede filtrar por categoría, comercio o
banco/tarjeta.

> Documentación de producto (problema, requerimientos, diseño, stack) en el
> vault personal de Obsidian (`Personal/Proyectos/centralizador-beneficios-*`).

## Arquitectura

```
GitHub Actions (cron)  ->  scraper/ (Python + Playwright)  ->  Supabase (Postgres)
                                                                     |
                                                  frontend/ (Next.js) lee y muestra
```

El **scraper y la web están desacoplados**: solo se comunican por la base de
datos. La web nunca scrapea en vivo, solo lee datos ya cacheados.

## Estructura

```
beneficios-cl/
├── frontend/             Next.js + TypeScript + Tailwind
├── scraper/              Python + Playwright (ingesta de beneficios)
├── db/schema.sql         Esquema de tablas para Supabase/Postgres
└── .github/workflows/    Cron que ejecuta el scraper
```

## Puesta en marcha

### 1. Base de datos (Supabase)
1. Crear un proyecto en https://supabase.com (free tier).
2. En el SQL Editor, ejecutar `db/schema.sql`.
3. Anotar `Project URL` y las API keys.

### 2. Web
```bash
cd frontend
cp .env.example .env.local   # completar con datos de Supabase
npm install
npm run dev                  # http://localhost:3000
```

### 3. Scraper
```bash
cd scraper
cp .env.example .env         # completar con la SERVICE ROLE key de Supabase
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python3 main.py               # scrapea las fuentes y puebla la BD
```

## Estado
MVP en construcción. Primer hito: una sola fuente real poblando la BD y la
pantalla "Beneficios de hoy" mostrándola.
