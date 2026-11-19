-- Almacenamiento de telemetría (docs/telemetry/telemetry-plan.md, sección 14).
--
-- Crea la tabla `telemetry_events`, donde `POST /telemetry/events` guarda los eventos válidos de cada
-- lote. La API NO crea esta tabla al arrancar (`create_all` no la conoce): hay que ejecutar este script
-- UNA vez en Supabase antes de usar el receptor. Sin la tabla, el receptor responde 503 y su log pide
-- ejecutar este archivo; el resto de la API funciona igual.
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Es idempotente: se puede volver a ejecutar sin
-- perder datos ni duplicar nada.
--
-- La tabla solo admite inserciones: los eventos son hechos inmutables. La API solo hace INSERT, y
-- además la base rechaza cualquier UPDATE, DELETE o TRUNCATE (trigger) y la API REST de Supabase no
-- tiene acceso (RLS sin políticas). La API se conecta como `postgres`, que no está sujeto a RLS.

CREATE TABLE IF NOT EXISTS telemetry_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp   timestamptz NOT NULL,
    service     text        NOT NULL,
    event_type  text        NOT NULL,
    level       text        NOT NULL DEFAULT 'info' CHECK (level IN ('info', 'warn', 'error')),
    value       numeric,
    message     text,
    tags        jsonb       NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE telemetry_events IS
    'Eventos de telemetría de Brasaland (plan de telemetría, sección 14). Solo inserciones: los eventos no se modifican ni se borran.';
COMMENT ON COLUMN telemetry_events.id IS 'eventId del envelope: un reintento del mismo evento no crea otra fila.';
COMMENT ON COLUMN telemetry_events.timestamp IS 'Momento del hecho (del envelope), no el de la recepción.';
COMMENT ON COLUMN telemetry_events.service IS 'Origen del evento: backoffice, api, bff o process (del campo source del envelope).';
COMMENT ON COLUMN telemetry_events.event_type IS 'Tipo de evento, entidad_acción en snake_case.';
COMMENT ON COLUMN telemetry_events.level IS 'info, warn o error; fijo por tipo de evento (x-level del esquema).';
COMMENT ON COLUMN telemetry_events.value IS 'Métrica principal del evento (x-value del esquema). Su unidad la da event_type: no sumar entre tipos.';
COMMENT ON COLUMN telemetry_events.message IS 'Resumen legible (x-message del esquema), sin datos personales.';
COMMENT ON COLUMN telemetry_events.tags IS 'properties del evento (solo su allowlist) más session_id, user_id, request_id, schema_version y environment.';

-- Índices: consultas por periodo, por tipo de evento y por dimensiones dentro de tags
-- (por ejemplo, tags @> '{"country": "CO"}').
CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp ON telemetry_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_event_type ON telemetry_events (event_type);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_tags ON telemetry_events USING GIN (tags);

-- Inmutabilidad: cualquier UPDATE, DELETE o TRUNCATE falla, venga de la API, de la consola de
-- Supabase o de un script. search_path vacío: la función no depende de los esquemas de quien la llama.
CREATE OR REPLACE FUNCTION telemetry_events_reject_changes()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION 'telemetry_events solo admite inserciones: % no está permitido', TG_OP
        USING HINT = 'Las purgas excepcionales se hacen a mano desactivando los triggers (ver migrations/002_telemetry_events.sql).';
END;
$$;

DROP TRIGGER IF EXISTS telemetry_events_no_update_delete ON telemetry_events;
CREATE TRIGGER telemetry_events_no_update_delete
    BEFORE UPDATE OR DELETE ON telemetry_events
    FOR EACH ROW EXECUTE FUNCTION telemetry_events_reject_changes();

DROP TRIGGER IF EXISTS telemetry_events_no_truncate ON telemetry_events;
CREATE TRIGGER telemetry_events_no_truncate
    BEFORE TRUNCATE ON telemetry_events
    FOR EACH STATEMENT EXECUTE FUNCTION telemetry_events_reject_changes();

-- La API REST de Supabase (PostgREST) publica las tablas de `public` a los roles anon y authenticated.
-- RLS sin políticas les niega todas las filas, y sin permisos no pueden ni intentarlo.
ALTER TABLE telemetry_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON telemetry_events FROM anon, authenticated;

-- Purga excepcional (retención o derecho de supresión), nunca desde la aplicación:
--
--   BEGIN;
--   ALTER TABLE telemetry_events DISABLE TRIGGER telemetry_events_no_update_delete;
--   DELETE FROM telemetry_events WHERE tags->>'user_id' = '<uuid>';
--   ALTER TABLE telemetry_events ENABLE TRIGGER telemetry_events_no_update_delete;
--   COMMIT;

-- Comprobación: deben salir las 8 columnas, los 3 índices (más la clave primaria), los 2 triggers y
-- rls_enabled = true.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'telemetry_events'
ORDER BY ordinal_position;

SELECT indexname FROM pg_indexes WHERE tablename = 'telemetry_events' ORDER BY indexname;

SELECT tgname FROM pg_trigger WHERE tgrelid = 'telemetry_events'::regclass AND NOT tgisinternal ORDER BY tgname;

SELECT relrowsecurity AS rls_enabled FROM pg_class WHERE oid = 'telemetry_events'::regclass;
