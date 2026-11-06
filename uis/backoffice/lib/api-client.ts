import { clearToken, getToken } from "@/lib/auth/token";
import { currentPath, LOGIN_PATH, loginUrl, type LoginReason } from "@/lib/auth/navigation";
import type { ApiErrorBody, ApiFieldError } from "@/types/api";

// Cliente común para la API de Brasaland. Las rutas son las del intermediario
// (app/api/[...path]/route.ts), que las reenvía a API_BASE_URL con la cabecera Authorization.
// El tracker (lib/talento/api.ts) no lo usa: llama a una API de terceros que no debe recibir el token.
const BFF_PREFIX = "/api";

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
  // Mensaje si la API no explica el error: "Error <status>: <fallback>".
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
  return new ApiError(`Error ${res.status}: ${fallback}`, res.status, "unknown_error");
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
  const res = await apiFetch(path, options);
  return res.json();
}

// Opciones de una petición con cuerpo JSON.
export function jsonBody(method: string, body: unknown): Pick<RequestInit, "method" | "headers" | "body"> {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}
