---
name: new-module-scaffold
description: Crea un módulo nuevo (UI, servicio, agente, skill de producto, MCP, workflow o paquete) en la carpeta correcta del monorepo, con su README bilingüe y alineado con CONTEXT.md. Úsala cuando haya que añadir un módulo nuevo al repositorio.
---

# Skill: crear un módulo nuevo en el monorepo

## Objetivo

Crear la estructura mínima de un módulo nuevo en la carpeta que le corresponde del monorepo, documentado en español e inglés y vinculado a una necesidad real de Brasaland.

## Cuándo usarla

- Al añadir una nueva aplicación, servicio, agente, skill de producto, servidor MCP, workflow o paquete.
- No la uses para `.agents/`: esa carpeta configura al agente de código, no contiene módulos de producto.

## Inputs

| Input | Obligatorio | Descripción |
|---|---|---|
| Nombre del módulo | Sí | En minúsculas y con guiones (por ejemplo `recipe-book`). |
| Tipo | Sí | UI, servicio, agente, skill de producto, MCP, workflow, paquete, script o herramienta interna. |
| Propósito | Sí | Una frase sobre qué resuelve. |
| Necesidad de `CONTEXT.md` | Sí | Departamento o problema del briefing que atiende. |

Si falta algún input obligatorio, o si el propósito no se puede enlazar con `CONTEXT.md`, detente y pregunta al desarrollador.

## Procedimiento

1. Determina la carpeta destino con la regla de la raíz: UI → `uis/`, API o proceso en segundo plano → `services/`, agente de IA → `agents/`, capacidad reutilizable de agente → `skills/`, servidor MCP → `mcps/`, flujo de automatización → `workflows/`, código compartido → `packages/`, script → `scripts/`, herramienta interna → `internal/`.
2. Lee el `README.md` de esa carpeta y, si existe una plantilla (por ejemplo `agents/_template/` o `skills/_template/`), úsala como punto de partida.
3. Confirma con el desarrollador el nombre y la ubicación antes de crear archivos.
4. Crea la subcarpeta `<destino>/<nombre>/` con la estructura mínima que pida el README o la plantilla de esa carpeta.
5. Añade `README.md` (inglés) y `README.es.md` (español) en la subcarpeta con: propósito, necesidad de `CONTEXT.md` que atiende, estructura, cómo ejecutarlo y enlace a la versión en el otro idioma.
6. Si el alcance del proyecto cambia con el módulo, aplica la skill `update-memory-bank`.

## Criterios de aceptación

- [ ] El módulo está en la carpeta que corresponde a su tipo según el `README.md` raíz.
- [ ] La subcarpeta contiene `README.md` y `README.es.md`, y ambos se enlazan entre sí.
- [ ] El README indica qué departamento o problema de `CONTEXT.md` atiende y no contiene texto de plantilla sin reemplazar.
- [ ] No se crearon archivos fuera de la subcarpeta nueva, salvo el Memory Bank cuando se aplicó `update-memory-bank`.
- [ ] No se inventaron datos del negocio: los ejemplos están marcados como ilustrativos.
- [ ] El desarrollador confirmó el nombre y la ubicación antes de crear los archivos.

## Restricciones

- Respeta las áreas protegidas de `AGENTS.md`: no crees ni modifiques archivos en `infra/` ni `workflows/` sin confirmación explícita.
- No dejes archivos de implementación en la raíz del repositorio.
