# Instrucciones para agentes

## Lectura obligatoria al inicio de cada sesión

Antes de proponer o realizar cambios, lee estos archivos en este orden:

1. `memory-bank/progress.md` — estado actual y próximos pasos.
2. `memory-bank/projectbrief.md` — negocio, objetivos y alcance.
3. `memory-bank/techContext.md` — stack, arquitectura y restricciones técnicas.

`CONTEXT.md` es la fuente de verdad para los hechos del negocio; consúltalo también cuando la tarea dependa del dominio de Brasaland. Antes de trabajar en una carpeta, lee su `README.md` y sigue sus instrucciones. Revisa el estado de Git para no sobrescribir cambios preexistentes.

## Flujo obligatorio antes de cada commit

Sigue estos pasos en orden:

1. Revisa `git status` y los cambios completos, tanto preparados como no preparados.
2. Actualiza la documentación directamente relacionada; si el trabajo cambia el estado o los próximos pasos del proyecto, actualiza `memory-bank/progress.md`.
3. Ejecuta las pruebas, el linter o la comprobación más pequeña que valide los archivos modificados. Si no se puede ejecutar, indícalo; no afirmes que pasó.
4. Revisa el diff final para confirmar que solo incluya los cambios solicitados y que no exponga secretos ni incluya artefactos generados por accidente.
5. Prepara únicamente los archivos previstos y vuelve a revisar el diff preparado.
6. Crea el commit solo si el desarrollador lo ha solicitado explícitamente.

## Áreas protegidas: requieren confirmación explícita

No modifiques estos archivos o áreas sin aprobación explícita del desarrollador:

- `CONTEXT.md`, `CONTEXT.es.md` y `company-choice.md`: contienen el contexto y las decisiones de negocio que sirven como fuente de verdad.
- `data/raw/`: conserva los datos fuente originales; no los sobrescribas ni los alteres.
- `infra/` y `workflows/`: pueden cambiar despliegues, infraestructura o automatizaciones con efectos externos.
- Archivos locales de credenciales o configuración, incluidos `.env*`, claves, tokens y `.claude/settings.local.json`. Nunca incluyas valores secretos en cambios o commits.

La aprobación debe referirse claramente al archivo o área y al cambio previsto. Si no está claro si un archivo está protegido o si un cambio puede tener efectos externos, detente y pide confirmación.

## Convenciones del monorepo

- Mantén cada cambio en la carpeta correspondiente a su responsabilidad; no agregues archivos de implementación a la raíz sin necesidad.
- Sigue los patrones y convenciones locales del proyecto en el que trabajas y evita cambios no relacionados con la tarea.
- No inventes hechos del negocio: usa `CONTEXT.md` y el Memory Bank como referencia.
