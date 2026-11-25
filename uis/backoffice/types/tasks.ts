// Cola de tareas de la API (ticket #DEV-55): la respuesta 202 al encolar y GET /tasks/{task_id}.

// `pending`: en cola (también mientras espera un reintento); `started`: en curso; `success` y `failure`: terminada.
export type TaskStatusValue = "pending" | "started" | "success" | "failure";

export interface TaskAccepted {
  task_id: string;
}

// `result` es el resultado de la tarea con `success`, `{ error }` con `failure` y `null` en otro caso.
export interface TaskStatus<T> {
  task_id: string;
  status: TaskStatusValue;
  result: T | { error: string } | null;
}
