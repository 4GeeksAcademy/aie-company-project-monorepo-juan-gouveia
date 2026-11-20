-- Catálogo de los 14 locales de Brasaland (diseño del pipeline de desempeño de negocio, Fase 0b).
--
-- Hasta ahora `location_id` era un entero de 1 a 14 sin nombre ni país (regla 5 del inventario y
-- brecha B7 del plan de telemetría), y el país de una orden salía del ingrediente. Esta tabla da a cada
-- número su sede, con los nombres y los códigos del briefing del gestor de incidencias ("Sedes de
-- Brasaland"), en el orden de su tabla: 1–9 en Colombia (COP) y 10–14 en Florida (USD). `central` no es
-- un local y no está aquí. Es el mismo reparto que usan las semillas del inventario.
--
-- Solo la crea esta migración: el modelo de la API tiene un registro propio, fuera del `create_all` de
-- `init_db`, para que la tabla nunca exista sin sus filas ni sin RLS. Sin ella, `GET /api/v1/locations`
-- responde 503 y su log pide ejecutar este script.
--
-- Cómo: Supabase → SQL Editor → pegar y ejecutar. Es idempotente: si la tabla ya existe, solo vuelve a
-- dejar las 14 filas como están aquí. Las órdenes del inventario no tienen clave foránea hacia esta
-- tabla (regla 5): la API comprueba el local y su país al registrar cada orden.

CREATE TABLE IF NOT EXISTS locations (
    id integer PRIMARY KEY CHECK (id BETWEEN 1 AND 14),
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    city text NOT NULL,
    country text NOT NULL CHECK (country IN ('CO', 'US')),
    currency text NOT NULL CHECK (currency IN ('COP', 'USD')),
    CONSTRAINT locations_currency_matches_country CHECK (
        (country = 'CO' AND currency = 'COP') OR (country = 'US' AND currency = 'USD')
    )
);

COMMENT ON TABLE locations IS 'Los 14 locales de Brasaland. El id es el location_id de las órdenes y de la telemetría.';
COMMENT ON COLUMN locations.id IS 'location_id de las órdenes del inventario y de los eventos de telemetría (1–14).';
COMMENT ON COLUMN locations.code IS 'Código de la sede del briefing del gestor de incidencias (branch), p. ej. medellin_centro.';
COMMENT ON COLUMN locations.name IS 'Nombre para mostrar del briefing, p. ej. Medellín Centro.';
COMMENT ON COLUMN locations.country IS 'País del local: CO (Colombia) o US (Florida).';
COMMENT ON COLUMN locations.currency IS 'Moneda del local: COP en Colombia, USD en Florida. Sin conversión.';

INSERT INTO locations (id, code, name, city, country, currency) VALUES
    (1, 'medellin_centro', 'Medellín Centro', 'Medellín', 'CO', 'COP'),
    (2, 'medellin_laureles', 'Medellín Laureles', 'Medellín', 'CO', 'COP'),
    (3, 'medellin_envigado', 'Medellín Envigado', 'Medellín', 'CO', 'COP'),
    (4, 'medellin_bello', 'Medellín Bello', 'Medellín', 'CO', 'COP'),
    (5, 'medellin_itagui', 'Medellín Itagüí', 'Medellín', 'CO', 'COP'),
    (6, 'bogota_chapinero', 'Bogotá Chapinero', 'Bogotá', 'CO', 'COP'),
    (7, 'bogota_usaquen', 'Bogotá Usaquén', 'Bogotá', 'CO', 'COP'),
    (8, 'cali_granada', 'Cali Granada', 'Cali', 'CO', 'COP'),
    (9, 'barranquilla_norte', 'Barranquilla Norte', 'Barranquilla', 'CO', 'COP'),
    (10, 'miami_doral', 'Miami Doral', 'Miami', 'US', 'USD'),
    (11, 'miami_hialeah', 'Miami Hialeah', 'Miami', 'US', 'USD'),
    (12, 'miami_kendall', 'Miami Kendall', 'Miami', 'US', 'USD'),
    (13, 'orlando_international', 'Orlando International Drive', 'Orlando', 'US', 'USD'),
    (14, 'fort_lauderdale', 'Fort Lauderdale', 'Fort Lauderdale', 'US', 'USD')
ON CONFLICT (id) DO UPDATE SET
    code = EXCLUDED.code,
    name = EXCLUDED.name,
    city = EXCLUDED.city,
    country = EXCLUDED.country,
    currency = EXCLUDED.currency;

-- Cerrada a la API REST de Supabase, como las demás tablas de la API (migraciones 002 y 003).
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON locations FROM anon, authenticated;

-- Comprobación: 14 filas (9 CO y 5 US), RLS activado y ningún permiso para anon ni authenticated
-- (la última consulta no debe devolver filas).
SELECT country, currency, count(*) AS locations FROM locations GROUP BY country, currency ORDER BY country;

SELECT relname AS table_name, relrowsecurity AS rls_enabled FROM pg_class WHERE relname = 'locations' AND relkind = 'r';

SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'locations' AND grantee IN ('anon', 'authenticated');
