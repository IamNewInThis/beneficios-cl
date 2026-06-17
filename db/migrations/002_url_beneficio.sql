-- 002 — URL exacta por beneficio
-- `fuente` se mantiene como la página de listado (clave de dedup en
-- db.replace_beneficios). `url` guarda el deep-link al beneficio concreto
-- (ej. https://www.machbank.cl/beneficios/detalle/<slug>) para validación:
-- el usuario puede abrir y verificar el beneficio en el sitio original.

alter table beneficio add column if not exists url text;

-- Recrear la vista incluyendo `url`. Se hace drop+create porque
-- `create or replace view` solo permite agregar columnas al final.
drop view if exists beneficio_detalle;
create view beneficio_detalle as
select
  b.id, b.comercio, b.categoria, b.tipo, b.valor,
  b.medio_pago, b.dias, b.condiciones,
  b.vigencia_desde, b.vigencia_hasta, b.fuente, b.url, b.actualizado_en,
  t.id as tarjeta_id, t.nombre as tarjeta, t.emisor
from beneficio b
join tarjeta t on t.id = b.tarjeta_id;
