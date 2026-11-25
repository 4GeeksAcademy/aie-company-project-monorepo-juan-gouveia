-- Dead Letter Queue de la cola de tareas asíncronas (ticket #DEV-55; plan en
-- docs/_private/plan-tareas-asincronas.md, decisiones T7, T8 y T9).
--
-- Crea:
--   - el rol `task_worker`, con el que se conecta el worker de Celery (`services/tasks`), sin login ni
--     contraseña;
--   - la tabla `ops.task_dead_letters`: una fila por tarea que falló de forma definitiva, ya sea por
--     agotar sus reintentos (`max_retries_exceeded`) o por un error que no se reintenta (`non_retryable`);
--   - los permisos del rol: lee `telemetry_events` (el informe de telemetría que calcula la tarea) y
--     solo lee e inserta en `ops.task_dead_letters`.
--
-- La DLQ es una cola real de Redis (`dead_letter`, decisión T8): la tarea `record_dead_letter` consume
-- sus mensajes y los guarda aquí, de forma idempotente (`task_id` único, `INSERT … ON CONFLICT DO
-- NOTHING`, que no necesita UPDATE). Ninguna fila se modifica ni se borra desde el worker.
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Necesita la migración 002 (`telemetry_events`) y la
-- 006 (esquema `ops`). Es idempotente: si ya se ejecutó, solo vuelve a dejar los permisos y las
-- políticas como están aquí, sin tocar los datos.
--
-- La contraseña del rol NO va en este archivo: después de ejecutarla, se da el login a mano con
--   ALTER ROLE task_worker WITH LOGIN PASSWORD '<contraseña>';
-- y la cadena de conexión se guarda en `TASKS_DATABASE_URL` (fuera de Git).

-- --- Requisitos -------------------------------------------------------------------------------

DO $$
BEGIN
    IF to_regclass('public.telemetry_events') IS NULL THEN
        RAISE EXCEPTION 'Falta telemetry_events: ejecuta antes la migración 002.';
    END IF;
    IF to_regnamespace('ops') IS NULL THEN
        RAISE EXCEPTION 'Falta el esquema ops: ejecuta antes la migración 006.';
    END IF;
END
$$;

-- --- Rol del worker ---------------------------------------------------------------------------

-- Sin login hasta que el desarrollador le ponga contraseña. NOINHERIT y sin atributos especiales:
-- no puede crear bases, roles ni saltarse RLS.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'task_worker') THEN
        CREATE ROLE task_worker NOLOGIN NOINHERIT;
    END IF;
END
$$;

COMMENT ON ROLE task_worker IS 'Worker de Celery (#DEV-55): lee telemetry_events y solo lee e inserta en ops.task_dead_letters.';

-- Por debajo del límite blando de la tarea (60 s, decisión T10): una consulta colgada se cancela en la
-- base antes de que Celery corte la tarea, y el error llega como fallo de la base.
ALTER ROLE task_worker SET statement_timeout = '50s';

-- --- Tabla ----------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ops.task_dead_letters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id text NOT NULL,
    task_name text NOT NULL,
    attempt integer NOT NULL CHECK (attempt >= 1),
    reason text NOT NULL CHECK (reason IN ('max_retries_exceeded', 'non_retryable')),
    error_message text NOT NULL,
    traceback text,
    task_args jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(task_args) = 'object'),
    failed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    -- Una tarea llega a la DLQ como mucho una vez: es la clave de idempotencia de record_dead_letter.
    CONSTRAINT uq_task_dead_letters_task_id UNIQUE (task_id)
);

COMMENT ON TABLE ops.task_dead_letters IS 'Dead Letter Queue: una fila por tarea de Celery que falló de forma definitiva.';
COMMENT ON COLUMN ops.task_dead_letters.task_id IS 'Id de Celery de la tarea; el mismo que devuelve POST /telemetry/report.';
COMMENT ON COLUMN ops.task_dead_letters.task_name IS 'Nombre registrado de la tarea en Celery.';
COMMENT ON COLUMN ops.task_dead_letters.attempt IS 'Ejecución que falló por última vez, desde 1: con max_retries=3, una tarea que agota sus reintentos guarda 4.';
COMMENT ON COLUMN ops.task_dead_letters.reason IS 'max_retries_exceeded: agotó los reintentos de un error transitorio; non_retryable: error permanente, sin reintento.';
COMMENT ON COLUMN ops.task_dead_letters.error_message IS 'Mensaje completo de la excepción final.';
COMMENT ON COLUMN ops.task_dead_letters.task_args IS 'Solo referencias (fechas pedidas e id de quien la encoló); nunca datos ni el informe.';
COMMENT ON COLUMN ops.task_dead_letters.failed_at IS 'Cuándo falló la última ejecución (en el worker).';
COMMENT ON COLUMN ops.task_dead_letters.recorded_at IS 'Cuándo record_dead_letter guardó la fila; puede ir detrás de failed_at si la base no respondía.';

-- Consulta habitual: los últimos fallos.
CREATE INDEX IF NOT EXISTS idx_task_dead_letters_failed_at
    ON ops.task_dead_letters (failed_at DESC);

-- --- Cerrada a la API REST de Supabase ---------------------------------------------------------

-- `ops` no está entre los esquemas que publica la API REST, pero se cierra igual que el resto de las
-- tablas (migraciones 002 a 006), por si alguien lo añade.
ALTER TABLE ops.task_dead_letters ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA ops FROM anon, authenticated;
REVOKE ALL ON ops.task_dead_letters FROM anon, authenticated;

-- --- Permisos del worker ------------------------------------------------------------------------

-- Fuente del informe, solo lectura. `telemetry_events` tiene RLS: sin una política de lectura, el rol
-- vería 0 filas. Ninguna política de escritura; además, el trigger de la 002 rechaza UPDATE, DELETE y
-- TRUNCATE.
GRANT USAGE ON SCHEMA public TO task_worker;
GRANT SELECT ON public.telemetry_events TO task_worker;

DROP POLICY IF EXISTS task_worker_read ON public.telemetry_events;
CREATE POLICY task_worker_read ON public.telemetry_events
    FOR SELECT TO task_worker USING (true);

-- DLQ: leer e insertar. Sin UPDATE ni DELETE: ningún fallo cambia ni desaparece del registro. El REVOKE
-- previo hace que volver a ejecutar la migración retire cualquier permiso concedido a mano. El rol no
-- recibe nada sobre ops.job_runs.
GRANT USAGE ON SCHEMA ops TO task_worker;
REVOKE ALL ON ops.task_dead_letters FROM task_worker;
GRANT SELECT, INSERT ON ops.task_dead_letters TO task_worker;

DROP POLICY IF EXISTS task_worker_read ON ops.task_dead_letters;
CREATE POLICY task_worker_read ON ops.task_dead_letters
    FOR SELECT TO task_worker USING (true);

DROP POLICY IF EXISTS task_worker_insert ON ops.task_dead_letters;
CREATE POLICY task_worker_insert ON ops.task_dead_letters
    FOR INSERT TO task_worker WITH CHECK (true);

-- --- Comprobación -------------------------------------------------------------------------------

-- 1. Las tablas de ops con RLS activado (job_runs y task_dead_letters).
SELECT n.nspname AS schema_name, c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'ops' AND c.relkind = 'r'
ORDER BY c.relname;

-- 2. Permisos del rol: SELECT en telemetry_events; INSERT y SELECT en ops.task_dead_letters.
SELECT table_schema, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE grantee = 'task_worker'
GROUP BY table_schema, table_name
ORDER BY table_schema, table_name;

-- 3. Ningún permiso para anon ni authenticated en ops (no debe devolver filas).
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'ops' AND grantee IN ('anon', 'authenticated');
