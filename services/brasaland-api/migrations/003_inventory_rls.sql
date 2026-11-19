-- Cierra las tablas del inventario a la API REST de Supabase (almacenamiento de telemetría, Fase 4).
--
-- Supabase publica las tablas del esquema `public` en su API REST (PostgREST) para los roles `anon` y
-- `authenticated`. Las tablas del inventario (Hito 5) se crearon sin RLS, así que el Table Editor las
-- marca como UNRESTRICTED: cualquiera con la URL del proyecto y la clave `anon` podría leerlas y
-- modificarlas sin pasar por la API de Brasaland, saltándose la autenticación, los roles y la regla de
-- que el stock solo cambia con órdenes.
--
-- Ningún componente del proyecto usa esa API REST: la API de Brasaland se conecta como `postgres`, que
-- no está sujeto a RLS, así que este script no cambia su comportamiento. Es lo mismo que la migración
-- 002 hace con `telemetry_events`: RLS activado sin políticas (PostgREST no devuelve ninguna fila) y sin
-- permisos para `anon` ni `authenticated` (ni siquiera pueden intentarlo).
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Es idempotente y no toca los datos. Si alguna vez se
-- recrean estas tablas en una base nueva (la API las crea al arrancar con `create_all`), hay que volver a
-- ejecutarlo.

ALTER TABLE ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredient_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredient_exits ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON ingredients, ingredient_entries, ingredient_exits FROM anon, authenticated;

-- Las claves `id` son SERIAL: sus secuencias también tienen permisos para esos roles.
DO $$
DECLARE
    table_name text;
    sequence_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['ingredients', 'ingredient_entries', 'ingredient_exits'] LOOP
        sequence_name := pg_get_serial_sequence(table_name, 'id');
        IF sequence_name IS NOT NULL THEN
            EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM anon, authenticated', sequence_name);
        END IF;
    END LOOP;
END;
$$;

-- Comprobación: las cuatro tablas de la API con rls_enabled = true, y ningún permiso para anon ni
-- authenticated (la segunda consulta no debe devolver filas).
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname IN ('ingredients', 'ingredient_entries', 'ingredient_exits', 'telemetry_events') AND relkind = 'r'
ORDER BY relname;

SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name IN ('ingredients', 'ingredient_entries', 'ingredient_exits', 'telemetry_events')
  AND grantee IN ('anon', 'authenticated');
