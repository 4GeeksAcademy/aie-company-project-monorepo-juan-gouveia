-- Esquema `reporting` del pipeline de desempeño de negocio (diseño en data/pipelines/PIPELINE_DESIGN.md,
-- §3.5 y §4.4).
--
-- Crea:
--   - el rol `reporting_pipeline`, con el que se conecta el pipeline, sin login ni contraseña;
--   - el esquema `reporting` con `weekly_location_performance` (el DDL literal del briefing) y
--     `pipeline_runs` (el log de corridas);
--   - los permisos del rol: lee `telemetry_events` y `locations` y escribe solo en `reporting.*`.
--
-- Solo la crea esta migración: el pipeline nunca crea tablas. La API se conecta como `postgres`,
-- que no está sujeto a RLS, y lee `reporting.*` para los endpoints de `services/reporting/`.
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Necesita las migraciones 002 (`telemetry_events`) y
-- 004 (`locations`). Es idempotente: si ya se ejecutó, solo vuelve a dejar los permisos y las
-- políticas como están aquí, sin tocar los datos.
--
-- La contraseña del rol NO va en este archivo: después de ejecutarla, se da el login a mano con
--   ALTER ROLE reporting_pipeline WITH LOGIN PASSWORD '<contraseña>';
-- y la cadena de conexión se guarda en el bloque `Secret` de Prefect `brasaland-reporting-db`.

-- --- Requisitos -------------------------------------------------------------------------------

DO $$
BEGIN
    IF to_regclass('public.telemetry_events') IS NULL OR to_regclass('public.locations') IS NULL THEN
        RAISE EXCEPTION 'Faltan telemetry_events o locations: ejecuta antes las migraciones 002 y 004.';
    END IF;
END
$$;

-- --- Rol del pipeline -------------------------------------------------------------------------

-- Sin login hasta que el desarrollador le ponga contraseña. NOINHERIT y sin atributos especiales:
-- no puede crear bases, roles ni saltarse RLS.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'reporting_pipeline') THEN
        CREATE ROLE reporting_pipeline NOLOGIN NOINHERIT;
    END IF;
END
$$;

COMMENT ON ROLE reporting_pipeline IS 'Pipeline de desempeño de negocio: lee telemetry_events y locations, escribe en reporting.*.';

-- Una consulta colgada no debe bloquear la corrida indefinidamente.
ALTER ROLE reporting_pipeline SET statement_timeout = '60s';

-- --- Esquema y tablas -------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS reporting;

COMMENT ON SCHEMA reporting IS 'Resultados de los pipelines de negocio. Nunca se escribe en telemetry_events.';

-- Tabla del briefing del pipeline (§5), sin cambios: una fila por local y semana ISO.
create table if not exists reporting.weekly_location_performance (
  id uuid primary key default gen_random_uuid(),
  location_id text not null,
  country text not null,
  week_start date not null,
  total_purchase_cost numeric not null default 0,
  total_waste_cost numeric not null default 0,
  waste_ratio numeric not null default 0,
  stockout_events_count integer not null default 0,
  price_alert_events_count integer not null default 0,
  currency text not null,
  computed_at timestamptz not null default now(),
  unique (location_id, week_start)
);

COMMENT ON TABLE reporting.weekly_location_performance IS 'Reporte Semanal de Costo y Merma por Local: una fila por local y semana ISO (UTC), en la moneda del local.';
COMMENT ON COLUMN reporting.weekly_location_performance.location_id IS 'code del local en locations, p. ej. medellin_centro.';
COMMENT ON COLUMN reporting.weekly_location_performance.week_start IS 'Lunes de la semana ISO, en UTC.';
COMMENT ON COLUMN reporting.weekly_location_performance.waste_ratio IS 'total_waste_cost / total_purchase_cost; 0 si no hubo compras.';

-- GET /reporting/weekly-location-performance pide todos los locales de una semana.
CREATE INDEX IF NOT EXISTS idx_weekly_location_performance_week_start
    ON reporting.weekly_location_performance (week_start);

-- Log de corridas (diseño, §4.4): una fila por corrida, creada al dispararla y cerrada al terminar.
CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline text NOT NULL,
    prefect_flow_run_id uuid,
    trigger text NOT NULL CHECK (trigger IN ('scheduled', 'manual')),
    requested_by uuid,
    week_from date NOT NULL,
    week_to date NOT NULL,
    status text NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    events_read integer NOT NULL DEFAULT 0 CHECK (events_read >= 0),
    events_rejected integer NOT NULL DEFAULT 0 CHECK (events_rejected >= 0),
    events_discarded integer NOT NULL DEFAULT 0 CHECK (events_discarded >= 0),
    waste_events_without_cost integer NOT NULL DEFAULT 0 CHECK (waste_events_without_cost >= 0),
    issues jsonb NOT NULL DEFAULT '{}'::jsonb,
    rows_written integer NOT NULL DEFAULT 0 CHECK (rows_written >= 0),
    failed_task text,
    error_message text,
    CONSTRAINT pipeline_runs_week_range CHECK (week_from <= week_to),
    CONSTRAINT pipeline_runs_finished_after_start CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);

COMMENT ON TABLE reporting.pipeline_runs IS 'Log de corridas de los pipelines de negocio. GET /reporting/pipeline-runs/latest devuelve la última.';
COMMENT ON COLUMN reporting.pipeline_runs.issues IS 'Conteo de eventos excluidos por motivo (unknown_location, country_mismatch, currency_mismatch, invalid_payload, duplicate_fact, price_decrease). Nunca valores del payload.';

-- Una sola corrida activa por pipeline (diseño, §4.3): POST /reporting/pipeline-runs responde 409.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pipeline_runs_one_active
    ON reporting.pipeline_runs (pipeline)
    WHERE status IN ('pending', 'running');

-- La última corrida de un pipeline.
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_created_at
    ON reporting.pipeline_runs (pipeline, created_at DESC);

-- --- Cerradas a la API REST de Supabase --------------------------------------------------------

-- `reporting` no está entre los esquemas que publica la API REST, pero se cierra igual que las
-- tablas de `public` (migraciones 002 a 004), por si alguien lo añade.
ALTER TABLE reporting.weekly_location_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE reporting.pipeline_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA reporting FROM anon, authenticated;
REVOKE ALL ON reporting.weekly_location_performance FROM anon, authenticated;
REVOKE ALL ON reporting.pipeline_runs FROM anon, authenticated;

-- --- Permisos del pipeline ----------------------------------------------------------------------

-- Fuente, solo lectura. `telemetry_events` y `locations` tienen RLS sin políticas: sin una política
-- de lectura, el rol vería 0 filas. Ninguna política de escritura: además, el trigger de la 002
-- rechaza cualquier UPDATE, DELETE o TRUNCATE en telemetry_events.
GRANT USAGE ON SCHEMA public TO reporting_pipeline;
GRANT SELECT ON public.telemetry_events, public.locations TO reporting_pipeline;

DROP POLICY IF EXISTS reporting_pipeline_read ON public.telemetry_events;
CREATE POLICY reporting_pipeline_read ON public.telemetry_events
    FOR SELECT TO reporting_pipeline USING (true);

DROP POLICY IF EXISTS reporting_pipeline_read ON public.locations;
CREATE POLICY reporting_pipeline_read ON public.locations
    FOR SELECT TO reporting_pipeline USING (true);

-- Destino: leer, insertar y actualizar (el upsert y el log). Sin DELETE: una semana nunca se borra,
-- se recalcula.
GRANT USAGE ON SCHEMA reporting TO reporting_pipeline;
GRANT SELECT, INSERT, UPDATE ON reporting.weekly_location_performance, reporting.pipeline_runs TO reporting_pipeline;

DROP POLICY IF EXISTS reporting_pipeline_write ON reporting.weekly_location_performance;
CREATE POLICY reporting_pipeline_write ON reporting.weekly_location_performance
    FOR ALL TO reporting_pipeline USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS reporting_pipeline_write ON reporting.pipeline_runs;
CREATE POLICY reporting_pipeline_write ON reporting.pipeline_runs
    FOR ALL TO reporting_pipeline USING (true) WITH CHECK (true);

-- --- Comprobación -------------------------------------------------------------------------------

-- 1. Las dos tablas con RLS activado.
SELECT n.nspname AS schema_name, c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'reporting' AND c.relkind = 'r'
ORDER BY c.relname;

-- 2. Permisos del rol: SELECT en las dos fuentes; SELECT, INSERT y UPDATE en las dos de reporting.
SELECT table_schema, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE grantee = 'reporting_pipeline'
GROUP BY table_schema, table_name
ORDER BY table_schema, table_name;

-- 3. Ningún permiso para anon ni authenticated en reporting (no debe devolver filas).
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'reporting' AND grantee IN ('anon', 'authenticated');
