"""Nombres y plazos de la cola de tareas, sin efectos al importar.

`celery_app` crea la aplicación de Celery al importarse y exige `REDIS_URL`. La API necesita estos
valores (el nombre de la tarea que encola, cuánto dura un resultado) también cuando la cola no está
configurada, para arrancar y responder 503 en vez de fallar al importar. Por eso viven aquí, y
`celery_app` los reexporta.
"""

# Colas: `default` para las tareas de negocio y `dead_letter` para los fallos finales (decisión T8).
DEFAULT_QUEUE = "default"
DEAD_LETTER_QUEUE = "dead_letter"

# Nombres registrados de las tareas (`tasks.py`). La API encola por nombre (`send_task`), sin importar el
# código de las tareas: el módulo solo se carga en el worker (`include`).
TELEMETRY_REPORT_TASK = "telemetry.report"
RECORD_DEAD_LETTER_TASK = "dead_letters.record"
TASKS_MODULE = "brasaland_tasks.tasks"

# Cuánto guarda Redis el resultado de una tarea (y la API, su registro de dueño y de deduplicación).
RESULT_EXPIRES_SECONDS = 24 * 60 * 60
