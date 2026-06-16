-- Esquema de la base de datos — beneficios-cl
-- Ejecutar en el SQL Editor de Supabase.
-- Basado en el modelo de datos de los requerimientos (Tarjeta + Beneficio).

-- Tarjetas / emisores
create table if not exists tarjeta (
  id        bigint generated always as identity primary key,
  nombre    text not null,                 -- ej. "CMR Falabella"
  emisor    text,                          -- ej. "Banco Falabella"
  created_at timestamptz not null default now(),
  unique (nombre)
);

-- Beneficios
create table if not exists beneficio (
  id             bigint generated always as identity primary key,
  tarjeta_id     bigint not null references tarjeta(id) on delete cascade,
  medio_pago     text not null check (medio_pago in ('credito','debito')),
  comercio       text not null,            -- ej. "Cruz Verde"
  categoria      text not null check (categoria in ('super','farmacia','comida','combustible')),
  tipo           text not null check (tipo in ('porcentaje','monto','precio_fijo')),
  valor          numeric not null,         -- 20 = 20% ; o monto/precio según tipo
  dias           text[] not null default '{}',  -- ej. {'martes','miercoles'}
  condiciones    text,                     -- tope, mínimo de compra, etc.
  vigencia_desde date,
  vigencia_hasta date,
  fuente         text,                     -- url o "manual"
  actualizado_en timestamptz not null default now(),
  created_at     timestamptz not null default now()
);

-- Índices para los filtros/consultas más comunes
create index if not exists idx_beneficio_categoria on beneficio (categoria);
create index if not exists idx_beneficio_comercio  on beneficio (comercio);
create index if not exists idx_beneficio_tarjeta    on beneficio (tarjeta_id);
create index if not exists idx_beneficio_dias       on beneficio using gin (dias);

-- Vista cómoda para la web: beneficio + nombre de tarjeta ya unidos
create or replace view beneficio_detalle as
select
  b.id, b.comercio, b.categoria, b.tipo, b.valor,
  b.medio_pago, b.dias, b.condiciones,
  b.vigencia_desde, b.vigencia_hasta, b.fuente, b.actualizado_en,
  t.id as tarjeta_id, t.nombre as tarjeta, t.emisor
from beneficio b
join tarjeta t on t.id = b.tarjeta_id;
