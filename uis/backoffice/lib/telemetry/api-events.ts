import type { ApiError } from "@/lib/api-client";
import { getToken, readTokenClaims } from "@/lib/auth/token";
import { track } from "@/lib/telemetry";
import { withRequestId } from "@/lib/telemetry/request-context";
import { apiRouteTemplate } from "@/lib/telemetry/routes";
import { currentUserRole } from "@/lib/telemetry/session";

// Eventos que nacen de un error de la API. Los emite apiFetch (lib/api-client.ts) con cada error, en
// un solo sitio para todo el backoffice: ningún componente los instrumenta por su cuenta. Cada evento
// lleva el `requestId` de la llamada que falló. Nunca lanza: un fallo de la telemetría no puede
// cambiar el error que ve el usuario.

// Campos de stock que la API no admite en el cuerpo de una orden o de un producto.
const STOCK_FIELDS = new Set(["current_stock", "stock"]);

// Métrica obligatoria `direct_stock_edit_rejected` (plan, §3.2): la API rechaza un intento de cambiar
// el stock fuera de una orden. Dos formas:
// - 405 a un PUT, PATCH o DELETE sobre una ruta del inventario (la acción "Ajustar stock");
// - 422 a un POST del inventario cuyo cuerpo trae `current_stock` o `stock` (error `extra_forbidden`).
function directStockEditRejection(method: string, path: string, error: ApiError) {
  if (!path.startsWith("/inventory/")) return null;
  if (error.status === 405 && ["PUT", "PATCH", "DELETE"].includes(method)) {
    return { rejection_type: "method_not_allowed", status_code: 405 } as const;
  }
  if (error.status === 422 && method === "POST" && error.details.some((detail) => STOCK_FIELDS.has(detail.field))) {
    return { rejection_type: "forbidden_field", status_code: 422 } as const;
  }
  return null;
}

// /inventory/products/12 → 12. Solo una edición sobre un producto identifica el producto.
function productIdFromPath(path: string): number | undefined {
  const match = /^\/inventory\/products\/(\d+)/.exec(path);
  return match ? Number(match[1]) : undefined;
}

// --- Sesión (§5.2) ---------------------------------------------------------------------------------
// Varias peticiones en paralelo con el mismo token caducado (resumen y listado) son un solo hecho: un
// evento por token y motivo cada 60 s (§10).
const SESSION_REPEAT_MS = 60_000;
const lastSessionEvent = new Map<string, number>();

function firstInWindow(key: string, now: number): boolean {
  const previous = lastSessionEvent.get(key);
  if (previous !== undefined && now - previous < SESSION_REPEAT_MS) return false;
  lastSessionEvent.set(key, now);
  return true;
}

function trackSessionRejection(path: string, error: ApiError, now: number): void {
  if (error.status !== 401) return;
  const claims = readTokenClaims(getToken());
  const tokenKey = `${claims?.sub ?? "?"}:${claims?.iat ?? "?"}`;
  const route = apiRouteTemplate(path);
  if (error.code === "token_expired" && firstInWindow(`expired:${tokenKey}`, now)) {
    track("session_expired", {
      route,
      // Antigüedad del token caducado, desde su `iat` (leído sin verificar la firma).
      token_age_minutes: claims?.iat ? Math.max(0, Math.floor((now / 1000 - claims.iat) / 60)) : undefined,
    });
  }
  if ((error.code === "invalid_token" || error.code === "session_revoked") && firstInWindow(`${error.code}:${tokenKey}`, now)) {
    track("auth_token_rejected", { rejection_reason: error.code, route });
  }
}

// --- Enlace de recuperación de contraseña (§5.2) ---------------------------------------------------
const RESET_LINK_REJECTIONS = new Set(["invalid_reset_token", "reset_token_expired", "reset_token_used"]);

function trackResetLinkRejection(path: string, error: ApiError): void {
  if (!RESET_LINK_REJECTIONS.has(error.code)) return;
  const stage = path === "/auth/reset-password/validate" ? "validate" : path === "/auth/reset-password" ? "reset" : null;
  if (stage) track("password_reset_link_rejected", { rejection_reason: error.code, stage });
}

// Solo para las pruebas.
export function resetApiEventThrottle(): void {
  lastSessionEvent.clear();
}

export function reportApiError(method: string, path: string, error: ApiError, now: number = Date.now()): void {
  try {
    withRequestId(error.requestId, () => {
      trackSessionRejection(path, error, now);
      trackResetLinkRejection(path, error);
      const rejection = directStockEditRejection(method, path, error);
      if (rejection) {
        track("direct_stock_edit_rejected", {
          // El local no se conoce: las cuentas no tienen local asignado (brecha B10).
          product_id: productIdFromPath(path),
          method,
          route: apiRouteTemplate(path),
          ...rejection,
          user_role: currentUserRole() ?? undefined,
        });
      }
    });
  } catch {
    // La telemetría nunca interfiere con el error de la API.
  }
}
