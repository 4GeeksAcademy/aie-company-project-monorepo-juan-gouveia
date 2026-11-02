---
name: update-memory-bank
description: Sincroniza el Memory Bank (memory-bank/) con el trabajo realizado en la sesión. Úsala al terminar una tarea o antes de un commit, cuando el estado del proyecto, el stack o las restricciones hayan cambiado.
---

# Skill: actualizar el Memory Bank

## Objetivo

Dejar `memory-bank/progress.md`, `memory-bank/techContext.md` y `memory-bank/projectbrief.md` fieles al estado real del repositorio tras un cambio, sin añadir información ajena a `CONTEXT.md`.

## Cuándo usarla

- Al terminar una tarea que cambie el estado del proyecto (algo se implementó, se inició o se descartó).
- Como paso 2 del flujo obligatorio previo a un commit definido en `AGENTS.md`.

## Inputs

| Input | Obligatorio | Descripción |
|---|---|---|
| Resumen del cambio | Sí | Qué se hizo, en una o dos frases. |
| Archivos afectados | Sí | Rutas creadas, modificadas o eliminadas. |
| Estado resultante | Sí | Para cada elemento: ✅ completado, ⬜️ parcial o ❌ pendiente. |
| Cambios de stack o decisiones | No | Tecnologías, versiones, decisiones de arquitectura o restricciones nuevas. |

Si falta algún input obligatorio, pídelo al desarrollador; no lo deduzcas.

## Procedimiento

1. Lee `memory-bank/progress.md` y comprueba contra el repositorio los elementos afectados (existencia de archivos, contenido real).
2. En `progress.md`, actualiza solo las filas afectadas con el estado resultante y ajusta la sección de próximos pasos: marca como hecho lo completado y añade los pasos nuevos.
3. Si cambió el stack, una decisión de arquitectura o una restricción, actualiza la sección correspondiente de `techContext.md`.
4. Modifica `projectbrief.md` solo si cambió el alcance o el enfoque del proyecto, y únicamente con información respaldada por `CONTEXT.md` o `company-choice.md`.
5. Actualiza la línea final `_Actualizado: AAAA-MM-DD_` de cada archivo modificado con la fecha de hoy.
6. Muestra al desarrollador un resumen de los cambios en el Memory Bank.

## Criterios de aceptación

- [ ] Cada elemento cambiado en la tarea aparece en `progress.md` con un estado que coincide con el contenido real del repositorio.
- [ ] No quedan elementos marcados como pendientes (❌) cuando el repositorio ya contiene su implementación, ni al revés.
- [ ] Los próximos pasos reflejan lo completado y no repiten tareas ya hechas.
- [ ] Solo cambiaron los archivos de `memory-bank/` que correspondían, y cada uno modificado tiene la fecha de actualización de hoy.
- [ ] Ninguna cifra, persona, proceso o dato del negocio nuevo carece de respaldo en `CONTEXT.md` o `company-choice.md`.
- [ ] El estilo y la estructura (tablas, emojis de estado, idioma) coinciden con los del archivo original.

## Restricciones

- No modifiques `CONTEXT.md`, `CONTEXT.es.md` ni `company-choice.md` desde esta skill.
- No reescribas secciones completas que no estén afectadas por el cambio.
