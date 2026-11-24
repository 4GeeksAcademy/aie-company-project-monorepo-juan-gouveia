-- Esquema `ops` del script nocturno de telemetría (ticket #DEV-53; plan en
-- docs/_private/plan-script-nocturno.md, decisiones N6, N7 y N9).
--
-- Crea:
--   - el rol `nightly_jobs`, con el que se conecta `scripts/nightly_export.py`, sin login ni contraseña;
--   - el esquema `ops` con `job_runs`: una fila por ejecución de un job programado, con su máquina de
--     estados `pending → processing → completed | failed`;
--   - los permisos del rol: lee `telemetry_events` (el export del CSV) y escribe solo en `ops.job_runs`.
--
-- `job_runs` no es `reporting.pipeline_runs`: registra la orquestación nocturna (export, disparo del
-- pipeline, lock e idempotencia); el pipeline sigue registrando su ETL en `pipeline_runs`, con su rol.
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Necesita la migración 002 (`telemetry_events`). Es
-- idempotente: si ya se ejecutó, solo vuelve a dejar los permisos y las políticas como están aquí, sin
-- tocar los datos.
--
-- La contraseña del rol NO va en este archivo: después de ejecutarla, se da el login a mano con
--   ALTER ROLE nightly_jobs WITH LOGIN PASSWORD '<contraseña>';
-- y la cadena de conexión se guarda en `JOBS_DATABASE_URL` (fuera de Git).

-- --- Requisitos -------------------------------------------------------------------------------

DO $$
BEGIN
    IF to_regclass('public.telemetry_events') IS NULL THEN
        RAISE EXCEPTION 'Falta telemetry_events: ejecuta antes la migración 002.';
    END IF;
END
$$;

-- --- Rol del script nocturno ------------------------------------------------------------------

-- Sin login hasta que el desarrollador le ponga contraseña. NOINHERIT y sin atributos especiales:
-- no puede crear bases, roles ni saltarse RLS.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nightly_jobs') THEN
        CREATE ROLE nightly_jobs NOLOGIN NOINHERIT;
    END IF;
END
$$;

COMMENT ON ROLE nightly_jobs IS 'Script nocturno (#DEV-53): lee telemetry_events y escribe solo en ops.job_runs.';

-- Una consulta colgada no debe dejar la ejecución en processing indefinidamente.
ALTER ROLE nightly_jobs SET statement_timeout = '60s';

-- --- Esquema y tabla ----------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS ops;

COMMENT ON SCHEMA ops IS 'Orquestación de jobs programados. Capa distinta de reporting (resultados de los pipelines).';

CREATE TABLE IF NOT EXISTS ops.job_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name text NOT NULL,
    target_date date NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    started_at timestamptz,
    finished_at timestamptz,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    -- Cada estado con los datos que le corresponden: ninguna fila puede decir que terminó sin cuándo, ni
    -- fallar sin el mensaje. Una fila `failed` puede no tener `started_at` (la instancia que pierde la
    -- carrera por el lock nunca llegó a processing; decisión N10).
    CONSTRAINT job_runs_processing_started CHECK (status <> 'processing' OR started_at IS NOT NULL),
    CONSTRAINT job_runs_finished_when_closed CHECK (status NOT IN ('completed', 'failed') OR finished_at IS NOT NULL),
    CONSTRAINT job_runs_completed_without_error CHECK (status <> 'completed' OR error_message IS NULL),
    CONSTRAINT job_runs_failed_with_error CHECK (status <> 'failed' OR error_message IS NOT NULL),
    CONSTRAINT job_runs_finished_after_start CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);

COMMENT ON TABLE ops.job_runs IS 'Una fila por ejecución de un job programado: pending → processing → completed | failed.';
COMMENT ON COLUMN ops.job_runs.job_name IS 'Nombre del job, p. ej. nightly_export.';
COMMENT ON COLUMN ops.job_runs.target_date IS 'Día (UTC) que procesa la ejecución: la clave de idempotencia junto a job_name.';
COMMENT ON COLUMN ops.job_runs.status IS 'processing es el lock: como mucho una fila por job (uq_job_runs_one_processing).';
COMMENT ON COLUMN ops.job_runs.error_message IS 'Mensaje de la excepción si falla; abandoned: … si se cerró por obsoleta, lock_held: … si perdió la carrera.';

-- Idempotencia por día: ¿hay una ejecución completed de este job para esta fecha?
CREATE INDEX IF NOT EXISTS idx_job_runs_job_name_target_date
    ON ops.job_runs (job_name, target_date);

-- El estado `processing` es el lock (decisión N9). Este índice no guarda nada nuevo: solo impide que dos
-- filas del mismo job estén en processing a la vez, así que la segunda transición falla de forma atómica
-- aunque dos instancias pasen la comprobación previa en el mismo instante.
CREATE UNIQUE INDEX IF NOT EXISTS uq_job_runs_one_processing
    ON ops.job_runs (job_name)
    WHERE status = 'processing';

-- --- Cerradas a la API REST de Supabase --------------------------------------------------------

-- `ops` no está entre los esquemas que publica la API REST, pero se cierra igual que el resto de las
-- tablas (migraciones 002 a 005), por si alguien lo añade.
ALTER TABLE ops.job_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA ops FROM anon, authenticated;
REVOKE ALL ON ops.job_runs FROM anon, authenticated;

-- --- Permisos del script ------------------------------------------------------------------------

-- Fuente del CSV, solo lectura. `telemetry_events` tiene RLS: sin una política de lectura, el rol vería
-- 0 filas. Ninguna política de escritura; además, el trigger de la 002 rechaza UPDATE, DELETE y TRUNCATE.
GRANT USAGE ON SCHEMA public TO nightly_jobs;
GRANT SELECT ON public.telemetry_events TO nightly_jobs;

DROP POLICY IF EXISTS nightly_jobs_read ON public.telemetry_events;
CREATE POLICY nightly_jobs_read ON public.telemetry_events
    FOR SELECT TO nightly_jobs USING (true);

-- Estado: leer, insertar y actualizar. Sin DELETE: ninguna ejecución desaparece del registro. El REVOKE
-- previo hace que volver a ejecutar la migración retire cualquier permiso concedido a mano.
GRANT USAGE ON SCHEMA ops TO nightly_jobs;
REVOKE ALL ON ops.job_runs FROM nightly_jobs;
GRANT SELECT, INSERT, UPDATE ON ops.job_runs TO nightly_jobs;

DROP POLICY IF EXISTS nightly_jobs_write ON ops.job_runs;
CREATE POLICY nightly_jobs_write ON ops.job_runs
    FOR ALL TO nightly_jobs USING (true) WITH CHECK (true);

-- --- Comprobación -------------------------------------------------------------------------------

-- 1. ops.job_runs con RLS activado.
SELECT n.nspname AS schema_name, c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'ops' AND c.relkind = 'r'
ORDER BY c.relname;

-- 2. Permisos del rol: SELECT en telemetry_events; SELECT, INSERT y UPDATE en ops.job_runs.
SELECT table_schema, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE grantee = 'nightly_jobs'
GROUP BY table_schema, table_name
ORDER BY table_schema, table_name;

-- 3. Ningún permiso para anon ni authenticated en ops (no debe devolver filas).
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'ops' AND grantee IN ('anon', 'authenticated');
