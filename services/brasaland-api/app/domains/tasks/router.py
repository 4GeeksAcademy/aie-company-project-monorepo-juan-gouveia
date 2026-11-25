"""`GET /tasks/{task_id}`: el estado de una tarea encolada (ticket #DEV-55, decisiones T4 y T5).

En la raíz, fuera de `/api/v1`, como `/telemetry` y `/reporting`, y con token. Solo quien encoló la tarea
o un admin la consultan; para cualquier otro, y para un id desconocido o caducado (24 h), 404 sin revelar
si existe. El estado se lee de Redis en cada consulta: nada se cachea en la API.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.auth.dependencies import get_current_user
from app.domains.tasks.dependencies import get_task_queue, queue_unavailable
from app.domains.tasks.queue import TaskQueue, TaskQueueUnavailable
from app.domains.tasks.schemas import TaskStatus
from app.domains.users.models import Role, User

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = console_logger("api.tasks")


def task_not_found() -> ApiError:
    return ApiError(404, "task_not_found", "No existe ninguna tarea con ese id.")


def _is_task_id(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


@router.get(
    "/{task_id}",
    response_model=TaskStatus,
    summary="Estado de una tarea",
    description=(
        "Estado actual de una tarea encolada (`pending`, `started`, `success` o `failure`) y su resultado "
        "cuando está disponible. Solo quien la encoló o un administrador. Los ids caducan a las 24 h."
    ),
    responses={
        401: {"description": "Sin token o con un token no válido."},
        404: {"description": "Id desconocido, caducado o de una tarea de otra persona (`task_not_found`)."},
        503: {"description": "La cola de tareas no está disponible (`task_queue_unavailable`)."},
    },
)
def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskStatus:
    if not _is_task_id(task_id):
        raise task_not_found()
    try:
        owner = queue.owner_of(task_id)
        if owner is None or (owner != user.id and user.role != Role.ADMIN):
            raise task_not_found()
        snapshot = queue.snapshot(task_id)
    except TaskQueueUnavailable as error:
        logger.error(f"No se pudo leer el estado de la tarea {task_id}: {error}")
        raise queue_unavailable() from error
    return TaskStatus(task_id=snapshot.task_id, status=snapshot.status, result=snapshot.result)
