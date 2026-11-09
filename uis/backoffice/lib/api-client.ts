import { clearToken, getToken } from "@/lib/auth/token";
import { currentPath, LOGIN_PATH, loginUrl, type LoginReason } from "@/lib/auth/navigation";
import type { ApiErrorBody, ApiFieldError } from "@/types/api";

// Cliente común para la API de Brasaland. Las rutas son las del intermediario
// (app/api/[...path]/route.ts), que las reenvía a API_BASE_URL con la cabecera Authorization.
// El tracker (lib/talento/api.ts) no usa apiFetch: llama a una API de terceros que no debe recibir el
// token. Sí reutiliza errorFromStatus y readJson para que sus errores se muestren igual.
const BFF_PREFIX = "/api";

const SERVER_ERROR_MESSAGE = "El servidor tuvo un problema y no pudo completar la operación. Inténtalo de nuevo en unos minutos.";

const INVALID_RESPONSE_MESSAGE =
  "No se pudo leer la respuesta del servidor. Inténtalo de nuevo; si el problema continúa, recarga la página.";

// Error de la API con su mensaje en español y, en los 422, el detalle por campo.
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly details: ApiFieldError[] = []
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiRequestOptions extends RequestInit {
  // Qué falló, si la API no lo explica (por ejemplo, "no se pudo guardar el perfil"). Se muestra
  // con mayúscula inicial y una indicación según el tipo de error, nunca con el código de estado.
  fallback: string;
  // Si es false, un 401 o una cuenta desactivada se devuelven como error y no cierran la sesión.
  // Lo usa el login, donde un 401 significa "credenciales incorrectas".
  endSessionOnAuthError?: boolean;
}

async function toApiError(res: Response, fallback: string): Promise<ApiError> {
  try {
    const body: ApiErrorBody = await res.json();
    if (body.error?.message) {
      return new ApiError(body.error.message, res.status, body.error.code, body.error.details);
    }
  } catch {
    // El cuerpo no es JSON: se usa el mensaje genérico.
  }
  return errorFromStatus(res.status, fallback);
}

// Error legible a partir del código de estado, para respuestas sin mensaje propio. También lo usa el
// tracker (lib/talento/api.ts), cuya API de terceros no envía mensajes pensados para el usuario.
export function errorFromStatus(status: number, fallback: string): ApiError {
  if (status >= 500) {
    // Error del servidor: nunca se muestra un texto técnico al usuario.
    return new ApiError(SERVER_ERROR_MESSAGE, status, "server_error");
  }
  return new ApiError(clientErrorMessage(status, fallback), status, "unknown_error");
}

// Qué puede hacer el usuario según el tipo de error, cuando la API no envía su propio mensaje.
const CLIENT_ERROR_HINTS: Record<number, string> = {
  400: "Revisa los datos e inténtalo de nuevo.",
  401: "Inicia sesión de nuevo e inténtalo otra vez.",
  403: "No tienes permiso para realizar esta acción.",
  404: "Lo que buscas ya no existe o cambió. Recarga la página.",
  409: "Los datos cambiaron mientras tanto. Recarga la página e inténtalo de nuevo.",
  413: "El archivo o los datos son demasiado grandes.",
  415: "El formato del archivo no es compatible.",
  422: "Revisa los datos e inténtalo de nuevo.",
  429: "Hay demasiadas solicitudes. Espera un momento e inténtalo de nuevo.",
};
const DEFAULT_CLIENT_ERROR_HINT = "Inténtalo de nuevo; si el problema continúa, recarga la página.";

// Ej.: 404 + "no se pudo cambiar el estado" → "No se pudo cambiar el estado. Lo que buscas ya no existe…".
function clientErrorMessage(status: number, fallback: string): string {
  const action = fallback.charAt(0).toUpperCase() + fallback.slice(1);
  return `${action}. ${CLIENT_ERROR_HINTS[status] ?? DEFAULT_CLIENT_ERROR_HINT}`;
}

// 401: falta el token, es inválido o caducó. 403 `inactive_user`: la cuenta se desactivó.
// Los demás 403 (`forbidden`) son un error normal y no cierran la sesión.
function sessionEndReason(error: ApiError): LoginReason | null {
  if (error.status === 401) return "expired";
  if (error.status === 403 && error.code === "inactive_user") return "inactive";
  return null;
}

function endSession(reason: LoginReason) {
  clearToken();
  if (window.location.pathname === LOGIN_PATH) return;
  window.location.replace(loginUrl(currentPath(), reason));
}

// Devuelve la respuesta solo si es correcta; si no, lanza un ApiError.
export async function apiFetch(path: string, options: ApiRequestOptions): Promise<Response> {
  const { fallback, endSessionOnAuthError = true, headers, ...init } = options;

  const requestHeaders = new Headers(headers);
  const token = getToken();
  if (token) requestHeaders.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BFF_PREFIX}${path}`, { cache: "no-store", ...init, headers: requestHeaders });
  } catch {
    throw new ApiError("No se pudo conectar con el backoffice. Revisa tu conexión.", 0, "network_error");
  }

  if (res.ok) return res;

  const error = await toApiError(res, fallback);
  const reason = sessionEndReason(error);
  if (reason && endSessionOnAuthError) endSession(reason);
  throw error;
}

export async function apiJson<T>(path: string, options: ApiRequestOptions): Promise<T> {
  return readJson(await apiFetch(path, options));
}

// Lee el cuerpo JSON de una respuesta correcta; si no se puede, lanza un ApiError legible.
export async function readJson<T>(res: Response): Promise<T> {
  try {
    return await res.json();
  } catch {
    // Respuesta correcta, pero el cuerpo no es JSON (por ejemplo, una página HTML de un proxy) o la
    // conexión se cortó mientras llegaba: nunca se muestra el SyntaxError ni el TypeError al usuario.
    throw new ApiError(INVALID_RESPONSE_MESSAGE, res.status, "invalid_response");
  }
}

// Opciones de una petición con cuerpo JSON.
export function jsonBody(method: string, body: unknown): Pick<RequestInit, "method" | "headers" | "body"> {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}
