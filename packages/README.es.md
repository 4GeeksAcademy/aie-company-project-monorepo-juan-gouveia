# Carpeta `packages`

Esta carpeta contiene **paquetes compartidos** del monorepo: librerías internas, utilidades, tipos, componentes comunes, SDKs, clientes y cualquier código reutilizable por varias aplicaciones/agentes/pipelines.

Cada subcarpeta dentro de `packages/` debería representar **un paquete versionable** (por ejemplo `shared-types`, `ui`, `analytics-sdk`) con su README propio.

- **Propósito principal**: fomentar reutilización y consistencia entre todos los desarrollos de la compañía.
- **Recomendación**: documenta los paquetes que vayas añadiendo, su API pública y cómo se consumen desde `uis/`, `services/`, `agents/` y `workflows/`.

## Paquetes disponibles

| Paquete | Carpeta | Propósito | Lo consume |
|---|---|---|---|
| [`@repo/brasa-core`](./brasa-core/README.es.md) | `brasa-core/` | Transitorio: modelos de dominio y utilidades de negocio de Brasaland, que el backend sustituirá | `uis/backoffice` |
| [`brasaland-shared`](./shared/README.es.md) (Python) y `@repo/shared-types` (TypeScript) | `shared/` | Reglas del CSV de incidentes compartidas entre scripts y API; tipos base (`Id`, `BaseEntity`) | `scripts/incident-report`, `scripts/seed_incidents.py` y `services/brasaland-api`; los tipos, aún sin consumidores |
