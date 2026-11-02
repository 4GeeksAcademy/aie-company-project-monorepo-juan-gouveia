# Regla: estructura del monorepo y diferencia entre `.agents/` y `/agents`, `/skills`

**Alcance:** por patrón de archivo. Aplica al crear o modificar contenido en:

- `uis/**`
- `services/**`
- `agents/**`
- `skills/**`
- `mcps/**`
- `workflows/**`
- `packages/**`

## Qué debe hacer el agente

- Ubicar cada cambio en la carpeta que le corresponde según el `README.md` raíz (por ejemplo: interfaz → `uis/`, API o proceso en segundo plano → `services/`, agente de IA → `agents/`).
- Respetar esta ubicación para el frontend y el backend de la empresa:

| Ruta | Qué va aquí cuando se cree |
|---|---|
| `uis/` | Proyectos frontend de la empresa. |
| `uis/website/` | Web corporativa de cara al público (ruta `/`, marca y texto alineados con `CONTEXT.md`). |
| `uis/backoffice/` | App interna de la empresa, con layout propio y separado del sitio público (vista de entrada en `/`). |
| `services/` | APIs y servicios backend. |

- El sitio público y el backoffice son proyectos independientes: no compartas layout entre ellos ni mezcles sus vistas.
- La web corporativa debe usar la marca, los textos y los datos de `CONTEXT.md`, sin contenido genérico de plantilla.
- Leer el `README.md` de la carpeta antes de trabajar en ella y seguir sus indicaciones.
- Documentar cada módulo nuevo en su propia subcarpeta con un `README.md` y su versión en español `README.es.md`, como el resto de carpetas del repositorio.
- No dejar archivos de implementación sueltos en la raíz.

## No confundir `.agents/` con `/agents` y `/skills`

- `.agents/` configura **cómo trabaja el agente de código** (Copilot, Cursor, Windsurf, Claude Code...) en este repositorio: reglas y skills de desarrollo.
- `/agents` y `/skills` contienen **código de producto**: los agentes y capacidades que se construyen para Brasaland en módulos posteriores.
- Las reglas y skills de desarrollo nunca van en `/agents` ni `/skills`, y el código de producto nunca va en `.agents/`.
