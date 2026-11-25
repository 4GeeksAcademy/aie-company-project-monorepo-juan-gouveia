"""Respuestas de la cola de tareas: la de encolar (`202`) y la de `GET /tasks/{task_id}` (ticket #DEV-55)."""

from typing import Any

from pydantic import BaseModel, Field

from app.domains.tasks.queue import TaskStatusValue


class TaskAccepted(BaseModel):
    """Respuesta `202 Accepted` de un endpoint que encola una tarea."""

    task_id: str = Field(description="Id de la tarea; su estado se consulta en `GET /tasks/{task_id}`")


class TaskStatus(BaseModel):
    """Estado de una tarea, con los tres campos del ticket."""

    task_id: str = Field(description="Id de la tarea")
    status: TaskStatusValue = Field(
        description=(
            "`pending` (en cola, también esperando un reintento), `started` (en curso), "
            "`success` (terminada) o `failure` (falló de forma definitiva)"
        )
    )
    result: Any = Field(
        description=(
            "Con `success`, el resultado de la tarea (el informe de telemetría: `period` y `metrics`); con "
            '`failure`, `{"error": "<tipo>: <mensaje>"}`; en otro caso, `null`'
        )
    )
