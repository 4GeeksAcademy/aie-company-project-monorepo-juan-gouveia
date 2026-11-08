# Divergencias con los briefings — Brasaland

Registro de cada punto en que la implementación se aparta de un briefing o de la consigna del curso, con su motivo. Sirve para justificar las entregas y para que nadie "corrija" una divergencia que es intencionada.

## Cómo usar este documento

- **Cuándo añadir una entrada:** siempre que una carpeta, ruta, nombre, texto o comportamiento no coincida exactamente con el briefing o la consigna, aunque los valores sean correctos.
- **Qué no se registra aquí:** los valores esperados del briefing (campos, categorías, estados, métricas) deben coincidir siempre. Si no coinciden, es un error que hay que corregir, no una divergencia.
- **Cómo se escribe:** una sección por briefing, con una tabla resumen (qué, briefing o consigna, implementación, motivo) y un apartado por divergencia con sus argumentos y su coste.
- **Dónde más se menciona:** la justificación puede repetirse en el README del módulo afectado, pero este documento es la referencia completa.

## Índice

1. [Procesador de reportes de incidentes](#procesador-de-reportes-de-incidentes) (briefing "Utilidad de Análisis de Datos", Fases 1 y 2)

---

## Procesador de reportes de incidentes

Los valores del análisis coinciden exactamente con el briefing; las diferencias son de ubicación, rutas y textos, y cada una tiene un motivo. Cubre las dos fases del ejercicio: el script de análisis (Fase 1) y su integración en la plataforma con API y backoffice (Fase 2).

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Carpeta del script | `incidents-analysis/` (briefing) | `scripts/incident-report/` | La consigna pide `/scripts` |
| Carpeta del backend | `/services/api` | `services/brasaland-api/` | Propuesta de arquitectura del CTO |
| Rutas de la API | `/api/incidents/...` | `/api/v1/incidents/...` | Versión única de la API (propuesta) |
| Lógica compartida | Extraída a módulos compartidos | `service.py` en la API, importado por el script | El backend es la fuente de verdad |
| Pregunta de exportación | `Export results to CSV? [y / n]` | `¿Deseas exportar los resultados a CSV? [s / n]` | La consigna la pide en español |
| Detalle de inválidos | Solo conteos por regla | Conteos + ID, fila y motivo de cada uno | Criterio "muestra los registros inválidos" |
| Regla de estado | No existe | `invalid_status` | Un estado desconocido no debe contar como válido |

### 1. Ubicación del script: `scripts/incident-report/`

El script está en `scripts/incident-report/` y no en `incidents-analysis/`, como indica el briefing.

- **La consigna manda:** pide "Script de análisis (`/scripts`)", y es lo que se evalúa.
- **Encaja en el monorepo:** la carpeta `scripts/` ya existía y el README raíz la reserva para scripts puntuales y CLIs internos. Una carpeta nueva en la raíz incumpliría la regla de no dejar implementación suelta ahí.
- **Queda registrado:** `scripts/README.md` y `scripts/README.es.md` listan `incident-report/`, que tiene su propio README en los dos idiomas.

El CSV fuente se conserva sin modificar en `data/raw/incidents-brasaland.csv`, y la exportación se escribe en `data/process/results.csv`, ignorado en Git. Si la ruta recibida no existe desde la carpeta actual, el script busca el mismo nombre en `data/raw/`, para que `python analyze.py incidents-brasaland.csv` funcione desde la carpeta del script.

### 2. Backend: `services/brasaland-api/` y rutas bajo `/api/v1`

La consigna pide `/services/api` y las rutas `/api/incidents/...`; se siguió la propuesta de arquitectura del CTO ([`ARCHITECTURE_PROPOSAL.md`](./ARCHITECTURE_PROPOSAL.md)).

- **Es el contrato acordado para todo el backend:** una carpeta por servicio con nombre propio y una sola versión de la API bajo `/api/v1` (secciones 2.2 y 3.1 de la propuesta). `incidents` es el primer dominio implementado; desviarse en él rompería esa coherencia desde el principio.
- **Desde el navegador se ve igual que en la consigna:** el backoffice expone `/api/incidents/analyze` y `/api/incidents/results/export`, y su intermediario (BFF) las reenvía a `/api/v1/incidents/...`.
- **Los criterios de evaluación no mencionan rutas ni carpetas,** solo el comportamiento: que el endpoint devuelva el resumen en JSON, que el export sea un CSV descargable y que los errores usen códigos HTTP apropiados.

La propuesta incorpora el dominio `incidents` al árbol de carpetas (2.3), a las dependencias entre dominios (2.5) y al mapa de rutas (3.3). La justificación también está en `services/brasaland-api/README.md` y `README.es.md`.

### 3. Lógica compartida en `service.py`

La validación y el análisis existen una sola vez, en `services/brasaland-api/app/domains/incidents/service.py`; el script y la API la importan.

- **Qué se extrajo:** las constantes (campos, sedes, categorías, estados, reglas, etiquetas de puntaje y límites) y las funciones `validate_record`, `split_records`, `analyze`, `percentage`, `rounded_average`, `build_export_rows` y `export_csv_text`.
- **Qué queda en el script:** solo la consola (formato del reporte, pregunta de exportación y escritura del archivo).
- **Qué queda en la API:** solo HTTP (lectura del archivo subido, traducción de errores a códigos y formato JSON).
- **El frontend no calcula nada:** muestra lo que devuelve la API y solo tiene los textos de presentación.

**Por qué dentro de la API y no en `packages/`:** la propuesta del CTO establece que el backend es la fuente de verdad de las reglas de negocio. `packages/brasa-core` es un paquete transitorio que no admite reglas nuevas y se retirará cuando sus reglas pasen al backend. Poner la lógica de incidentes ahí iría contra esa decisión.

**Cómo lo usa el script:** añade `services/brasaland-api` a `sys.path` e importa `app.domains.incidents.service`. `service.py` solo usa la librería estándar de Python, así que el script sigue sin necesitar instalación. El coste es que `analyze.py` funciona dentro del repositorio, pero no copiado fuera de él; está documentado en su README.

**Prueba de que la extracción no cambió el comportamiento:** las pruebas del script siguieron pasando sin cambios (hoy son 32), y el CSV que exporta la API es idéntico byte a byte al `results.csv` del script.

### 4. Diferencias con la salida esperada del briefing

Todos los valores numéricos coinciden; el briefing acepta "diferencias menores de formato", y estas son las tres que hay.

**Pregunta de exportación en español.** El bloque del briefing termina en `Export results to CSV? [y / n]:`, y el script pregunta `¿Deseas exportar los resultados a CSV? [s / n]:` porque la consigna la pide en español. Acepta `s`, `si`, `sí`, `y` y `yes`, así que quien responda en inglés también exporta; sin entrada disponible no exporta.

**Sección `INVALID RECORDS DETAIL`.** Bajo el desglose por regla, el script lista cada registro inválido con su ID, su fila y su motivo (por ejemplo `BRS-000044 (row 45): Missing location_id`). El criterio de evaluación pide que el script "detecta, clasifica y muestra los registros inválidos con su tipo de problema", y los conteos solos no muestran cuáles son. Los totales y el CSV exportado no cambian; la API y el backoffice muestran el mismo detalle.

**Regla adicional `invalid_status`.** El briefing define seis reglas, pero ninguna cubre un `status` vacío o distinto de `OPEN`, `CLOSED` y `DISCARDED`, aunque la estructura lo marca como requerido. Sin esta regla, un registro así contaría como válido sin aparecer en ningún estado. Con el CSV del briefing queda en 0, así que la consola y el backoffice no la muestran y la salida coincide; en el CSV exportado aparece con valor 0, como todas las reglas, para que la estructura no cambie entre archivos.

En el backoffice se muestran los códigos exactos del briefing (`CUSTOMER_COMPLAINT`, `OPEN`…), acompañados solo de las descripciones de categoría que trae el propio briefing, y los números con punto decimal (`30.2%`, `3.46 / 5.00`).

### 5. Decisiones de funcionamiento

Estas decisiones no se apartan de la consigna, pero cambian cómo se comporta el sistema y conviene conocerlas.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| El último análisis se guarda en la memoria de la API, detrás de `repository.py` | Aún no hay base de datos y los criterios no piden persistencia; el repositorio se sustituirá por la base de datos sin tocar los endpoints | Si la API se reinicia, el export responde 404 y hay que volver a subir el archivo; si dos personas analizan a la vez, se descarga el más reciente |
| El backoffice llama a la API a través de un intermediario (BFF), `app/api/[...path]/route.ts` | Propuesta 5.2: la URL de la API queda en el servidor (`API_BASE_URL`), no hace falta CORS y el intermediario no aplica lógica | Si la API no responde, devuelve 502 con un mensaje claro |
| El tipo de archivo se valida por la extensión `.csv`, no por el `Content-Type` | Windows envía los CSV como `application/vnd.ms-excel` | Un archivo mal nombrado se rechaza después, por no estar en UTF-8 o no tener las columnas esperadas (422) |
| Tamaño máximo de 5 MB | Un mes de incidentes de las 14 sedes ocupa decenas de KB | Archivos mayores reciben 413 |
| Un registro que rompe varias reglas suma en cada una y una sola vez en el total de inválidos | El briefing pide contar cuántos registros caen en cada regla | Los conteos por regla pueden sumar más que el total; la consola y el backoffice lo advierten |
| Las categorías, estados y puntajes se calculan solo con registros válidos | Es lo que muestra la salida esperada (96 válidos, porcentajes sobre 96) | — |
| Entorno virtual propio de la API (`services/brasaland-api/.venv`) | Aísla FastAPI y sus dependencias del Python global | Hay que crearlo antes de arrancar la API (README del servicio) |
| Sin autenticación todavía | No es parte de este ejercicio | El backoffice no debe publicarse hasta que exista el login |

### 6. Cómo verificarlo

Todo lo de esta tabla se ejecutó el 3 de noviembre de 2026 con el CSV del briefing, `data/raw/incidents-brasaland.csv`.

| Qué se comprueba | Comando o acción | Resultado |
| --- | --- | --- |
| Pruebas del script | `cd scripts/incident-report && python -m unittest` | 32 pruebas pasan |
| Pruebas de la API | `cd services/brasaland-api && .venv\Scripts\python -m pytest` | 24 pruebas pasan |
| Script con la ruta como argumento | `python scripts/incident-report/analyze.py data/raw/incidents-brasaland.csv` (también desde otra carpeta, con ruta absoluta) | 100 / 96 / 4; categorías 29, 17, 22, 19, 9; estados 32, 50, 14; puntajes 4, 6, 12, 19, 9; promedio 3.46 |
| Exportación del script | Responder `s` a la pregunta final | `data/process/results.csv` con 26 métricas y las columnas `metric`, `value`, `percentage` |
| Misma lógica en script y API | Comparar el export de la API con el del script | Idénticos byte a byte |
| Errores de la API | Subir un archivo inválido a `POST /api/v1/incidents/analyze` | Sin archivo 400, `.txt` 415, vacío 400, más de 5 MB 413, no UTF-8 422, faltan columnas 422, solo encabezado 422; export sin análisis 404 |
| Backoffice | Arrancar la API (puerto 8000) y `npm run dev` en `uis/backoffice` (puerto 3001); abrir `http://localhost:3001/incidencias` | Carga del CSV, resumen, aviso de los 4 inválidos con su detalle y descarga de `results.csv`; con la API apagada, aviso de servicio no disponible. Revisado y aprobado en el navegador |
