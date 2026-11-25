// Intermediario del estado de una tarea (ticket #DEV-55): /api/tasks/{taskId} → <origen de la API>/tasks/{taskId}.
// La API sirve /tasks fuera de /api/v1, así que el catch-all (que reenvía a API_BASE_URL) no llega.
// Solo GET. El token se reenvía tal cual; la API solo responde a quien encoló la tarea o a un admin.

import { apiOrigin, proxyToApi } from "@/lib/bff/proxy";

interface RouteContext {
  params: Promise<{ taskId: string }>;
}

export async function GET(request: Request, { params }: RouteContext) {
  const { taskId } = await params;
  return proxyToApi(
    request,
    (apiBaseUrl) => `${apiOrigin(apiBaseUrl)}/tasks/${encodeURIComponent(taskId)}`,
    // Sin el id en el log del servidor: solo la plantilla de la ruta.
    "GET /tasks/{task_id}",
  );
}
