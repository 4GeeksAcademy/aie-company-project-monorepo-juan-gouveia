import { ApiError } from "@/lib/api-client";
import { readTokenClaims } from "@/lib/auth/token";
import { track } from "@/lib/telemetry";
import { withRequestId } from "@/lib/telemetry/request-context";
import { pageRouteTemplate } from "@/lib/telemetry/routes";
import { currentSession, rememberUserRole } from "@/lib/telemetry/session";
import type { Role } from "@/types/auth";

// Eventos de autenticación del plan (§5.2), capturados en la capa de autenticación (lib/auth/api.ts y
// SessionProvider), nunca en cada página. Ninguno lleva el email ni la contraseña escritos.
// Los que nacen de un error de la API (sesión caducada, token rechazado, enlace de recuperación
// rechazado) están en api-events.ts, junto al resto de errores.

const PENDING_LOGIN_KEY = "brasaland.telemetry_pending_login";

function sessionStore(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

// --- login_succeeded --------------------------------------------------------------------------
// El rol no viene en la respuesta del login: lo confirma GET /auth/me, que hace SessionProvider al
// entrar en la zona protegida. El login deja una marca con su requestId y el evento se emite al
// validar la sesión, una sola vez.

export function markLoginSucceeded(requestId: string): void {
  try {
    sessionStore()?.setItem(PENDING_LOGIN_KEY, requestId);
  } catch {
    // Sin sessionStorage no se emite login_succeeded; el login funciona igual.
  }
}

// Lo llama SessionProvider cada vez que valida la sesión con /auth/me.
export function onSessionValidated(role: Role): void {
  try {
    rememberUserRole(role);
    const store = sessionStore();
    const requestId = store?.getItem(PENDING_LOGIN_KEY);
    if (!requestId) return;
    store?.removeItem(PENDING_LOGIN_KEY);
    withRequestId(requestId, () => track("login_succeeded", { user_role: role }));
  } catch {
    // La telemetría no interfiere con la sesión.
  }
}

// --- login_failed (2.0.0) -----------------------------------------------------------------------
// Motivo del fallo: credenciales incorrectas (401), cuenta desactivada (403 `inactive_user`) o una
// petición que no llegó a la API (sin conexión, o 502/504 del intermediario). Otros errores (un 422
// por un email mal formado, que ya frena el formulario) no son un intento de login fallido.

export function loginFailureReason(error: unknown): "invalid_credentials" | "inactive_user" | "network_error" | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status === 401) return "invalid_credentials";
  if (error.status === 403 && error.code === "inactive_user") return "inactive_user";
  if (error.status === 0 || error.status === 502 || error.status === 504) return "network_error";
  return null;
}

export function trackLoginFailed(error: unknown): void {
  const failureReason = loginFailureReason(error);
  if (!failureReason) return;
  withRequestId((error as ApiError).requestId, () => track("login_failed", { failure_reason: failureReason }));
}

// --- logout_completed ---------------------------------------------------------------------------
// Antes de borrar el token: después ya no hay sesión de la que medir la duración.

export function trackLogout(now: number = Date.now()): void {
  try {
    const { startedAt } = currentSession(now);
    track("logout_completed", {
      route: pageRouteTemplate(window.location.pathname),
      session_duration_seconds: startedAt === null ? undefined : Math.max(0, Math.round((now - startedAt) / 1000)),
    });
  } catch {
    // Cerrar la sesión nunca depende de la telemetría.
  }
}

// --- user_registered, password_reset_completed y password_changed ------------------------------

export function trackUserRegistered(newUserId: string, requestId: string): void {
  // El autorregistro siempre crea cuentas con rol `user`.
  withRequestId(requestId, () => track("user_registered", { new_user_id: newUserId, user_role: "user" }));
}

// La antigüedad del enlace sale del `iat` de su token, leído sin verificar la firma.
export function trackPasswordResetCompleted(resetToken: string, requestId: string, now: number = Date.now()): void {
  const iat = readTokenClaims(resetToken)?.iat;
  withRequestId(requestId, () =>
    track("password_reset_completed", {
      link_age_minutes: typeof iat === "number" ? Math.max(0, Math.floor((now / 1000 - iat) / 60)) : undefined,
    })
  );
}

export function trackPasswordChanged(requestId: string): void {
  // `days_since_last_change` necesita `password_changed_at`, que la API no envía: se omite.
  withRequestId(requestId, () => track("password_changed", { channel: "change_password" }));
}
