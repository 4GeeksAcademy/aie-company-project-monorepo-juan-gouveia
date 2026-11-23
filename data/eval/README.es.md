# Carpeta `data/eval`

Esta carpeta está orientada a **evaluación y validación**: datasets de evaluación, “golden sets”, resultados de experimentos, métricas, y artefactos usados para medir calidad de modelos, RAG, agentes o pipelines.

- **Propósito principal**: centralizar los insumos y salidas de evaluación para asegurar mejoras medibles a lo largo de los hitos del proyecto.
- **Recomendación**: documenta cada set de evaluación (qué mide, cómo se construyó, criterios de éxito) y evita incluir datos sensibles; si es necesario, usa datos sintéticos o anonimizados.

## Conjuntos

### `weekly_location_performance/` (pipeline de negocio, fuera de Git)

- **Origen:** la task opcional `export_eval_snapshot` del [pipeline de desempeño semanal](../pipelines/README.es.md) escribe aquí `<run_id>.json` al final de cada corrida.
- **Qué mide:** cinco comprobaciones de calidad de las filas escritas en `reporting.weekly_location_performance`: 14 filas por semana, `waste_ratio` coherente con los costes, la moneda que corresponde al país, ningún valor negativo y todas las filas escritas. Incluye las filas y los conteos de la corrida (eventos leídos, rechazados y descartados por motivo).
- **Criterio de éxito:** todas las comprobaciones en `true`.
- **Versionado:** ignorada por Git (`.gitignore` raíz). Si la exportación falla, la corrida sigue y lo registra en su log (`export_eval_snapshot_failed`).
