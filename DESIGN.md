# Design System — Beneficios CL (Revolut-inspired)

## Canvas
- **Background**: `#000000` (black) — full dark canvas
- **Cards**: `#ffffff` (white) with `#e2e2e7` hairline border and `rounded-[20px]`
- **Elevated surfaces** (`#16181a`): modals, toggle bg, search input, mobile selects
- **Soft surface** (`#f4f4f4`): category badges

## Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `ink` | `#191c1f` | Primary text on white surfaces |
| `mute` | `#505a63` | Secondary text (card body) |
| `stone` | `#8d969e` | Metadata (days, conditions) |
| `on-dark-mute` | `rgba(255,255,255,0.72)` | Secondary text on dark |
| `white/60` | `rgba(255,255,255,0.60)` | Inactive nav/toggle labels |
| `white/40` | `rgba(255,255,255,0.40)` | Tertiary text, placeholders |
| `white/10` | `rgba(255,255,255,0.10)` | Dividers, borders in dark regions |
| `hairline-light` | `#e2e2e7` | Card borders on white |
| `hairline-dark` | `rgba(255,255,255,0.12)` | Borders/separators on dark |
| `cobalt` | `#494fdf` | Brand accent (selection color, sparing) |

## Radius
| Token | Value | Usage |
|-------|-------|-------|
| `rounded-full` | 9999px | Buttons, pills, inputs, badges, toggles |
| `rounded-card` | 20px | Cards, modal desktop |
| `rounded-t-card` | 20px top | Modal bottom-sheet mobile |

## Typography
- **Inter** via `next/font/google` as `--font-inter`
- `font-sans` = Inter (default)
- Headings: Inter 500–600, tracking-tight
- Body: Inter 400
- Labels (buttons, pills, sidebar): Inter 500–600

## Key Components

### Header
- Title: `text-xl font-semibold tracking-tight` white
- Search: `bg-surface-elevated rounded-full`, white text, placeholder `white/40`, focus border `white/20`
- Settings icon: `text-white/40 hover:text-white`

### Toggle (Hoy / Semana)
- Container: `bg-surface-elevated rounded-full p-0.5`
- Active tab: `bg-white text-ink rounded-full`
- Inactive tab: `text-white/60 hover:text-white`

### Mobile Filters
- `<select>` styled as `bg-surface-elevated text-white rounded-full border-hairline-dark`

### Sidebar Desktop
- Section label: `text-xs font-semibold uppercase tracking-wider text-white/40`
- Items: `text-white/60 hover:text-white`, active = `bg-white text-ink rounded-full px-3 py-1.5`

### Card
- `bg-white rounded-card border-hairline-light p-4`, `hover:border-gray-300`
- Merchant: `text-ink font-semibold truncate`
- Category badge: `bg-surface-soft text-ink rounded-full px-2 py-0.5 text-xs font-medium`
- Benefit row: tarjeta in `text-mute`, medio_pago in `text-stone`, valor in `text-ink font-semibold`
- Days/conditions: `text-stone text-xs`

### Modal (feature-card-dark style)
- Overlay: `bg-black/60`
- Sheet: `bg-surface-elevated rounded-t-card lg:rounded-card p-6`
- Title: `text-white font-semibold`
- Category badge: `bg-white/10 text-white rounded-full`
- Dividers: `border-hairline-dark`
- Benefit value: `text-white text-lg font-semibold`
- Secondary text: `text-white/50`
- Footer: `text-white/40 text-xs`

### Empty State
- `rounded-card border-hairline-dark p-8 text-center text-white/40`

## Principles
- **No drop shadows** — elevation via surface-luminance shifts (Revolut style)
- **Cobalt violet** (`#494fdf`) used only for text selection highlight (`selection:bg-cobalt/30`)
- **Hairlines** instead of shadows for card borders
- **All interactive elements pill-shaped** (rounded-full)
- **Black canvas** makes white cards pop — high contrast fintech feel
- **Mobile-first**: bottom sheet modal, horizontal scroll filters, 1/2/3 col grid

## File Reference
- `frontend/tailwind.config.ts` — token definitions
- `frontend/app/layout.tsx` — Inter font, black bg, selection color
- `frontend/app/beneficios-app.tsx` — all component implementations
- `revolut/DESIGN.md` — full Revolut token reference
