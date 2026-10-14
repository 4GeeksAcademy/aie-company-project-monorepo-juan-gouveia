# Regla: coherencia con el dominio de Brasaland

**Alcance:** siempre activa (aplica a cualquier tarea en este repositorio).

## Qué debe hacer el agente

- Usar `CONTEXT.md` como única fuente de hechos del negocio. Si algo no aparece ahí, no lo des por cierto: pregunta al desarrollador.
- Mantener los datos, nombres y procesos coherentes con el briefing de Brasaland:
  - Cadena de 14 restaurantes propios en dos países: Colombia (sede en Medellín) y Estados Unidos (Florida, oficina en Miami).
  - Dos monedas, COP y USD. Todo valor monetario indica su moneda de forma explícita.
  - Dos idiomas, español e inglés. Parte de la documentación y la interfaz deben poder funcionar en ambos.
  - Dos marcos laborales distintos (Colombia y EE. UU.): no asumas reglas de RR. HH. iguales para ambos países.
- Preservar los tres pilares de la marca: producto consistente entre locales, servicio cálido y uniforme, y cocina eficiente.
- Priorizar el enfoque definido en `company-choice.md`: Formación y Estándares de Calidad (recetario interactivo e itinerario de incorporación), con Operaciones y Marketing como áreas secundarias.

## Restricciones

- No inventes cifras, personas, proveedores, recetas ni procesos del negocio. Los datos de ejemplo deben indicarse como ilustrativos.
- `CONTEXT.md` no define una tasa de cambio COP/USD. No la fijes como hecho del negocio: si el código necesita una, documéntala como supuesto técnico y confírmala con el desarrollador.
- No reemplaces ni reescribas `CONTEXT.md` y `company-choice.md` sin confirmación explícita (ver `AGENTS.md`).
