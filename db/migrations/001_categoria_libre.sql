-- Migración 001 — categoría libre
-- Quita el CHECK que limitaba `categoria` a 4 valores, para poder capturar
-- beneficios de cualquier rubro (bebidas, perfumería, tienda, etc.).
-- Ejecutar una vez en el SQL Editor de Supabase.

alter table beneficio drop constraint if exists beneficio_categoria_check;
