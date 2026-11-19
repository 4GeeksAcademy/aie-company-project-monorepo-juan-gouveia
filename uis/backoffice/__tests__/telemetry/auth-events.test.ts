/**
 * @jest-environment jsdom
 */
// Eventos de autenticación (actividad adicional): se capturan en lib/auth/api.ts, SessionProvider y
// apiFetch, nunca en cada página, y nunca llevan el email ni la contraseña escritos. track() y fetch
// están simulados; el token es un JWT de prueba en localStorage.
import { REQUEST_ID_HEADER } from "@/lib/api-client";
import { changePassword, getCurrentUser, login, register, resetPassword, validateResetToken } from "@/lib/auth/api";
import { loginFailureReason, onSessionValidated, trackLogout } from "@/lib/telemetry/auth-events";
import { resetApiEventThrottle } from "@/lib/telemetry/api-events";
import { ApiError } from "@/lib/api-client";

const tracked: Array<{ eventType: string; properties: Record<string, unknown>; requestId: string | null }> = [];
jest.mock("@/lib/telemetry", () => ({
  track: (eventType: string, properties: Record<string, unknown>) => {
    const { currentRequestId } = jest.requireActual("@/lib/telemetry/request-context");
    tracked.push({ eventType, properties, requestId: currentRequestId() });
  },
}));

const NOW_S = 1_763_547_000;
const fetchMock = jest.fn();

function jwt(claims: object): string {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${encode({ alg: "HS256" })}.${encode(claims)}.firma`;
}

function json(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function requestIdOf(call: number): string {
  const [, init] = fetchMock.mock.calls[call] as [string, RequestInit];
  return new Headers(init.headers).get(REQUEST_ID_HEADER) as string;
}

beforeEach(() => {
  tracked.length = 0;
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
  window.localStorage.clear();
  window.sessionStorage.clear();
  resetApiEventThrottle();
  jest.spyOn(Date, "now").mockReturnValue(NOW_S * 1000);
  // apiFetch redirige al login ante un 401; jsdom no navega y solo lo avisa en la consola.
  jest.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => jest.restoreAllMocks());

describe("login", () => {
  it.each([
    [new ApiError("x", 401, "invalid_credentials"), "invalid_credentials"],
    [new ApiError("x", 403, "inactive_user"), "inactive_user"],
    [new ApiError("x", 0, "network_error"), "network_error"],
    [new ApiError("x", 502, "api_unavailable"), "network_error"],
    [new ApiError("x", 504, "api_timeout"), "network_error"],
    [new ApiError("x", 422, "invalid_request"), null],
    [new Error("x"), null],
  ])("motivo del login fallido: %p → %p", (error, reason) => {
    expect(loginFailureReason(error)).toBe(reason);
  });

  it("un login fallido emite login_failed solo con el motivo, sin el email", async () => {
    fetchMock.mockResolvedValue(json({ error: { code: "invalid_credentials", message: "Credenciales incorrectas." } }, 401));

    await expect(login("ana@brasaland.com", "secreto")).rejects.toBeInstanceOf(ApiError);

    expect(tracked).toEqual([{ eventType: "login_failed", properties: { failure_reason: "invalid_credentials" }, requestId: requestIdOf(0) }]);
    expect(JSON.stringify(tracked)).not.toContain("ana@brasaland.com");
  });

  it("login_succeeded se emite al validar la sesión, una vez, con el rol y el requestId del login", async () => {
    fetchMock.mockResolvedValue(json({ access_token: "jwt", token_type: "bearer" }));
    await login("ana@brasaland.com", "secreto");
    expect(tracked).toEqual([]);

    onSessionValidated("manager");
    onSessionValidated("manager");

    expect(tracked).toEqual([{ eventType: "login_succeeded", properties: { user_role: "manager" }, requestId: requestIdOf(0) }]);
  });
});

describe("sesión", () => {
  it("un 401 token_expired emite session_expired con la antigüedad del token, una vez por token", async () => {
    window.localStorage.setItem("brasaland.access_token", jwt({ sub: "u1", iat: NOW_S - 61 * 60 }));
    fetchMock.mockResolvedValue(json({ error: { code: "token_expired", message: "La sesión caducó." } }, 401));

    await getCurrentUser().catch(() => {});
    window.localStorage.setItem("brasaland.access_token", jwt({ sub: "u1", iat: NOW_S - 61 * 60 }));
    await getCurrentUser().catch(() => {});

    expect(tracked).toEqual([
      { eventType: "session_expired", properties: { route: "/api/v1/auth/me", token_age_minutes: 61 }, requestId: requestIdOf(0) },
    ]);
  });

  it.each(["invalid_token", "session_revoked"])("un 401 %s emite auth_token_rejected", async (code) => {
    window.localStorage.setItem("brasaland.access_token", jwt({ sub: "u1", iat: NOW_S }));
    fetchMock.mockResolvedValue(json({ error: { code, message: "x" } }, 401));

    await getCurrentUser().catch(() => {});

    expect(tracked).toEqual([
      { eventType: "auth_token_rejected", properties: { rejection_reason: code, route: "/api/v1/auth/me" }, requestId: requestIdOf(0) },
    ]);
  });

  it("logout_completed lleva la ruta y la duración de la sesión", () => {
    window.localStorage.setItem("brasaland.access_token", jwt({ sub: "u1", iat: NOW_S }));
    window.sessionStorage.setItem("brasaland.telemetry_session", JSON.stringify({ id: "s", sub: "u1", startedAt: NOW_S * 1000 - 5_420_000 }));
    window.history.replaceState(null, "", "/inventario/ordenes");

    trackLogout();

    expect(tracked[0]).toMatchObject({ eventType: "logout_completed", properties: { route: "/inventario/ordenes", session_duration_seconds: 5420 } });
  });
});

describe("registro y contraseñas", () => {
  it("el registro emite user_registered con el id de la cuenta nueva y rol user", async () => {
    fetchMock.mockResolvedValue(json({ id: "3f1c2a9e-8b7d-4c6e-9a1b-2d3e4f5a6b7c", message: "Cuenta creada." }, 201));

    await register({ email: "ana@brasaland.com", password: "Secreto2026!" } as never);

    expect(tracked).toEqual([
      { eventType: "user_registered", properties: { new_user_id: "3f1c2a9e-8b7d-4c6e-9a1b-2d3e4f5a6b7c", user_role: "user" }, requestId: requestIdOf(0) },
    ]);
  });

  it("restablecer la contraseña emite password_reset_completed con la antigüedad del enlace", async () => {
    fetchMock.mockResolvedValue(json({ message: "Contraseña actualizada." }));

    await resetPassword(jwt({ sub: "u1", iat: NOW_S - 7 * 60, purpose: "password_reset" }), "Nueva2026!");

    expect(tracked[0]).toMatchObject({ eventType: "password_reset_completed", properties: { link_age_minutes: 7 } });
  });

  it.each([
    [() => validateResetToken("t"), "validate"],
    [() => resetPassword("t", "Nueva2026!"), "reset"],
  ])("un enlace caducado emite password_reset_link_rejected (%#)", async (call, stage) => {
    fetchMock.mockResolvedValue(json({ error: { code: "reset_token_expired", message: "El enlace caducó." } }, 400));

    await call().catch(() => {});

    expect(tracked).toEqual([
      { eventType: "password_reset_link_rejected", properties: { rejection_reason: "reset_token_expired", stage }, requestId: requestIdOf(0) },
    ]);
  });

  it("cambiar la contraseña emite password_changed", async () => {
    fetchMock.mockResolvedValue(json({ access_token: "nuevo", token_type: "bearer" }));

    await changePassword("Actual2026!", "Nueva2026!");

    expect(tracked).toEqual([{ eventType: "password_changed", properties: { channel: "change_password" }, requestId: requestIdOf(0) }]);
  });
});
