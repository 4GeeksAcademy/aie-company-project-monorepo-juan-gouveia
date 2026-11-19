import type { ApiError } from "@/lib/api-client";
import { getToken, readTokenClaims } from "@/lib/auth/token";
import { track } from "@/lib/telemetry";
import { withRequestId } from "@/lib/telemetry/request-context";
import { apiRouteTemplate } from "@/lib/telemetry/routes";
import { currentUserRole } from "@/lib/telemetry/session";

// Eventos que nacen de una llamada a la API. Los emite apiFetch (lib/api-client.ts) con cada llamada,
// en un solo sitio para todo el backoffice: ningún componente los instrumenta por su cuenta. Cada
// evento lleva el `requestId` de su llamada. Nunca lanzan: la telemetría no puede cambiar la
// respuesta ni el error que ve el usuario.
//
// - reportApiCall: toda llamada que recibe respuesta → `api_latency_recorded` (muestreada).
// - reportApiError: toda llamada que falla → según el caso, `api_error_returned`,
//   `api_connection_failed`, `session_expired`, `auth_token_rejected`,
//   `password_reset_link_rejected`, `direct_stock_edit_rejected` y `order_validation_failed`.

export interface ApiCall {
  method: string;
  path: string;
  requestId: string;
  durationMs: number;
  // Cuerpo enviado (texto JSON); solo se leen identificadores, nunca se emite.
  body?: BodyInit | null;
}

// Throttle por clave (§10): un mismo hecho repetido dentro de su ventana se emite una vez.
const lastEmitted = new Map<string, number>();

function firstInWindow(key: string, windowMs: number, now: number): boolean {
  const previous = lastEmitted.get(key);
  if (previous !== undefined && now - previous < windowMs) return false;
  lastEmitted.set(key, now);
  return true;
}

// Solo para las pruebas.
export function resetApiEventThrottle(): void {
  lastEmitted.clear();
}

function safely(requestId: string | null, emit: () => void): void {
  try {
    withRequestId(requestId, emit);
  } catch {
    // La telemetría nunca interfiere con la llamada.
  }
}

// --- api_latency_recorded (§5.4 y §10) ---------------------------------------------------------------
// Se emiten siempre las llamadas lentas (≥ 300 ms) o con error (≥ 400), y 1 de cada 10 del resto,
// elegidas por su requestId (determinista); `sample_rate` permite reconstruir los recuentos.

const SLOW_MS = 300;
const SAMPLE_RATE = 0.1;

export function sampleRate(requestId: string, durationMs: number, status: number): number | null {
  if (durationMs >= SLOW_MS || status >= 400) return 1;
  return parseInt(requestId.replace(/-/g, "").slice(-4), 16) % 10 === 0 ? SAMPLE_RATE : null;
}

export function reportApiCall(call: ApiCall, status: number, cacheHeader: string | null): void {
  const rate = sampleRate(call.requestId, call.durationMs, status);
  if (rate === null) return;
  safely(call.requestId, () =>
    track("api_latency_recorded", {
      method: call.method,
      route: apiRouteTemplate(call.path),
      status_code: status,
      duration_ms: Math.round(call.durationMs * 10) / 10,
      cache: cacheHeader === "HIT" || cacheHeader === "MISS" ? cacheHeader : undefined,
      sample_rate: rate,
    })
  );
}

// --- Sesión (§5.2) ---------------------------------------------------------------------------------
// Varias peticiones en paralelo con el mismo token caducado son un solo hecho: uno por token y motivo
// cada 60 s.

function trackSessionRejection(call: ApiCall, error: ApiError, now: number): void {
  if (error.status !== 401) return;
  const claims = readTokenClaims(getToken());
  const tokenKey = `${claims?.sub ?? "?"}:${claims?.iat ?? "?"}`;
  const route = apiRouteTemplate(call.path);
  if (error.code === "token_expired" && firstInWindow(`expired:${tokenKey}`, 60_000, now)) {
    track("session_expired", {
      route,
      // Antigüedad del token caducado, desde su `iat` (leído sin verificar la firma).
      token_age_minutes: claims?.iat ? Math.max(0, Math.floor((now / 1000 - claims.iat) / 60)) : undefined,
    });
  }
  if ((error.code === "invalid_token" || error.code === "session_revoked") && firstInWindow(`${error.code}:${tokenKey}`, 60_000, now)) {
    track("auth_token_rejected", { rejection_reason: error.code, route });
  }
}

// --- Enlace de recuperación de contraseña (§5.2) ---------------------------------------------------
const RESET_LINK_REJECTIONS = new Set(["invalid_reset_token", "reset_token_expired", "reset_token_used"]);

function trackResetLinkRejection(call: ApiCall, error: ApiError): void {
  if (!RESET_LINK_REJECTIONS.has(error.code)) return;
  const stage = call.path === "/auth/reset-password/validate" ? "validate" : call.path === "/auth/reset-password" ? "reset" : null;
  if (stage) track("password_reset_link_rejected", { rejection_reason: error.code, stage });
}

// --- Inventario ------------------------------------------------------------------------------------

// Campos de stock que la API no admite en el cuerpo de una orden o de un producto.
const STOCK_FIELDS = new Set(["current_stock", "stock"]);

// Métrica obligatoria `direct_stock_edit_rejected` (plan, §3.2): la API rechaza un intento de cambiar
// el stock fuera de una orden. Dos formas:
// - 405 a un PUT, PATCH o DELETE sobre una ruta del inventario (la acción "Ajustar stock");
// - 422 a un POST del inventario cuyo cuerpo trae `current_stock` o `stock` (error `extra_forbidden`).
function directStockEditRejection(call: ApiCall, error: ApiError) {
  if (!call.path.startsWith("/inventory/")) return null;
  if (error.status === 405 && ["PUT", "PATCH", "DELETE"].includes(call.method)) {
    return { rejection_type: "method_not_allowed", status_code: 405 } as const;
  }
  if (error.status === 422 && call.method === "POST" && error.details.some((detail) => STOCK_FIELDS.has(detail.field))) {
    return { rejection_type: "forbidden_field", status_code: 422 } as const;
  }
  return null;
}

// /inventory/products/12 → 12. Solo una edición sobre un producto identifica el producto.
function productIdFromPath(path: string): number | undefined {
  const match = /^\/inventory\/products\/(\d+)/.exec(path);
  return match ? Number(match[1]) : undefined;
}

// Identificadores del cuerpo de una orden (si son válidos); nada más se lee de él.
function orderIdentifiers(body: ApiCall["body"]): { product_id?: number; location_id?: number } {
  if (typeof body !== "string") return {};
  try {
    const parsed = JSON.parse(body) as { ingredient_id?: unknown; location_id?: unknown };
    const productId = Number.isInteger(parsed.ingredient_id) && (parsed.ingredient_id as number) >= 1 ? (parsed.ingredient_id as number) : undefined;
    const locationId =
      Number.isInteger(parsed.location_id) && (parsed.location_id as number) >= 1 && (parsed.location_id as number) <= 14
        ? (parsed.location_id as number)
        : undefined;
    return { product_id: productId, location_id: locationId };
  } catch {
    return {};
  }
}

const ORDER_PATHS: Record<string, "inbound" | "outbound"> = {
  "/inventory/orders/inbound": "inbound",
  "/inventory/orders/outbound": "outbound",
};
const FIELD_NAME = /^[a-z_]+$/;

// `order_validation_failed` (§5.1): la API rechaza una orden por datos inválidos (422) o por un
// ingrediente que no existe (404). Solo los nombres de los campos, nunca sus valores.
function trackOrderValidation(call: ApiCall, error: ApiError): boolean {
  const orderType = ORDER_PATHS[call.path];
  if (!orderType || call.method !== "POST") return false;
  const isValidation = error.status === 422 && error.code === "invalid_request";
  const isMissingIngredient = error.status === 404 && error.code === "ingredient_not_found";
  if (!isValidation && !isMissingIngredient) return false;
  const fields = [...new Set(error.details.map((detail) => detail.field).filter((field) => FIELD_NAME.test(field) && field.length <= 40))];
  track("order_validation_failed", {
    order_type: orderType,
    ...orderIdentifiers(call.body),
    error_code: error.code,
    invalid_fields: fields.slice(0, 20),
    status_code: error.status,
  });
  return true;
}

// --- Errores y disponibilidad (§5.5) -----------------------------------------------------------------

// Respuestas del intermediario (BFF) cuando no llega a la API.
const CONNECTION_FAILURES: Record<string, { status: number }> = {
  api_unavailable: { status: 502 },
  api_timeout: { status: 504 },
  api_not_configured: { status: 500 },
};
const ERROR_CODE = /^[a-z0-9_]{1,40}$/;

function trackConnectionOrApiError(call: ApiCall, error: ApiError, now: number): void {
  const failure = CONNECTION_FAILURES[error.code];
  if (failure && failure.status === error.status) {
    // Una vez por sesión cada 30 s mientras la API no responde.
    if (firstInWindow("connection", 30_000, now)) {
      track("api_connection_failed", {
        method: call.method,
        route: apiRouteTemplate(call.path),
        failure: error.code,
        status_code: error.status,
        duration_ms: Math.round(call.durationMs),
      });
    }
    return;
  }
  if (error.status >= 400 && error.status < 500 && ERROR_CODE.test(error.code)) {
    // Un mismo (ruta, código, usuario) como máximo una vez cada 10 s.
    const route = apiRouteTemplate(call.path);
    const user = readTokenClaims(getToken())?.sub ?? "";
    if (firstInWindow(`error:${route}:${error.code}:${user}`, 10_000, now)) {
      track("api_error_returned", { method: call.method, route, status_code: error.status, error_code: error.code });
    }
  }
}

export function reportApiError(call: ApiCall, error: ApiError, now: number = Date.now()): void {
  safely(error.requestId, () => {
    trackConnectionOrApiError(call, error, now);
    trackSessionRejection(call, error, now);
    trackResetLinkRejection(call, error);
    const rejection = directStockEditRejection(call, error);
    if (rejection) {
      track("direct_stock_edit_rejected", {
        // El local no se conoce: las cuentas no tienen local asignado (brecha B10).
        product_id: productIdFromPath(call.path),
        method: call.method,
        route: apiRouteTemplate(call.path),
        ...rejection,
        user_role: currentUserRole() ?? undefined,
      });
      return;
    }
    trackOrderValidation(call, error);
  });
}
