---
name: validate-domain-model
description: Comprueba que un modelo de datos, validación o dato de ejemplo nuevo o modificado respeta los hechos y restricciones de Brasaland definidos en CONTEXT.md. Úsala al añadir o cambiar entidades, tipos, validaciones o datos de ejemplo.
---

# Skill: validar un modelo de dominio contra CONTEXT.md

## Objetivo

Verificar que los modelos, validaciones y datos de ejemplo del repositorio no contradicen el briefing de Brasaland, y reportar cada discrepancia sin corregirla sin confirmación.

## Cuándo usarla

- Al crear o modificar tipos, entidades o validaciones (por ejemplo `packages/brasa-core/types/models.ts` y `packages/brasa-core/utils/validations.ts`).
- Al añadir o cambiar datos de ejemplo (por ejemplo `packages/brasa-core/utils/test-data.ts`) o campos de una API o UI.

## Inputs

| Input | Obligatorio | Descripción |
|---|---|---|
| Archivos a validar | Sí | Rutas del modelo, validación o datos de ejemplo. |
| Área del negocio | No | Departamento de `CONTEXT.md` al que pertenece (Operaciones, Compras, Marketing, Personas, Formación, Tecnología, Dirección). Si no se indica, se deduce y se confirma con el desarrollador. |

## Procedimiento

1. Lee `CONTEXT.md` y, si aplica, `company-choice.md` para identificar los hechos del área involucrada.
2. Lee solo los archivos indicados y lista los hechos del dominio que contienen: entidades, campos, monedas, países, idiomas, rangos, fechas y nombres.
3. Contrasta cada hecho con `CONTEXT.md`. Comprueba, como mínimo:
   - La cadena opera en dos países: Colombia y Estados Unidos (Florida); no aparecen otros.
   - Los valores monetarios declaran su moneda (COP o USD).
   - Los datos no contradicen las cifras del briefing: fundación en 2008, 14 locales, aproximadamente 115 empleados.
   - Los datos y procesos no asumen reglas laborales idénticas en ambos países.
   - Los datos de ejemplo no se presentan como datos reales del negocio.
4. Clasifica cada hallazgo:
   - **Contradicción:** el código dice algo opuesto a `CONTEXT.md`.
   - **Sin respaldo:** el código afirma algo que `CONTEXT.md` no define (por ejemplo, una tasa de cambio).
   - **Correcto:** coincide con `CONTEXT.md`.
5. Entrega un informe al desarrollador con la ruta, la línea o el campo, el hallazgo y la referencia de `CONTEXT.md`. No corrijas nada sin confirmación explícita.

## Criterios de aceptación

- [ ] El informe cubre todos los archivos indicados como input.
- [ ] Cada hallazgo de tipo contradicción o sin respaldo cita el archivo y el campo afectado, y la sección de `CONTEXT.md` que lo motiva.
- [ ] Ningún hecho aparece como correcto sin una referencia a `CONTEXT.md` que lo respalde.
- [ ] No se modificó ningún archivo sin confirmación del desarrollador.
- [ ] El informe distingue datos del negocio de supuestos técnicos, y los datos de ejemplo quedan marcados como ilustrativos.

## Restricciones

- `CONTEXT.md` es la única fuente de verdad: si no responde a una duda, pregunta al desarrollador en vez de suponer.
- No modifiques `CONTEXT.md`, `CONTEXT.es.md` ni `company-choice.md`.
