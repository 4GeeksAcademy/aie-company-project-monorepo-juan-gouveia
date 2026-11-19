-- Captura de telemetría, brechas B5 y B6 del plan (docs/telemetry/telemetry-plan.md, sección 12).
--
-- Añade a las órdenes del inventario el coste unitario de las entradas y el motivo de las mermas.
-- `create_all` crea estas columnas en una base nueva, pero no las añade a tablas que ya existen:
-- en la base de Supabase que ya tiene datos hay que ejecutar este script UNA vez, ANTES de arrancar la
-- API con este código (si no, las consultas del inventario fallan porque la columna no existe).
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Es idempotente (IF NOT EXISTS) y no toca los datos:
-- las filas anteriores quedan con NULL, que la API devuelve como `null`.

ALTER TABLE ingredient_entries ADD COLUMN IF NOT EXISTS unit_cost DOUBLE PRECISION;

ALTER TABLE ingredient_exits ADD COLUMN IF NOT EXISTS waste_reason VARCHAR(20);

-- Comprobación: deben salir las dos columnas, ambas con is_nullable = YES.
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name IN ('ingredient_entries', 'ingredient_exits')
  AND column_name IN ('unit_cost', 'waste_reason');
