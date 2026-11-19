/**
 * @jest-environment jsdom
 */
// TelemetryService (lib/telemetry): track() es la única entrada. Comprueba que el servicio pone el
// envelope completo (quien llama solo pasa el tipo y las propiedades), que descarta lo que no cumple
// el catálogo y que envía por lotes. fetch y sendBeacon están simulados.
const ENDPOINT = "http://localhost:8000/telemetry/events";

jest.mock("@/lib/telemetry/config", () => ({
  ...jest.requireActual("@/lib/telemetry/config"),
  TELEMETRY_ENDPOINT: "http://localhost:8000/telemetry/events",
  TELEMETRY_ENVIRONMENT: "staging",
}));

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const USER = "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2";
const OTHER_USER = "3f1c2a9e-8b7d-4c6e-9a1b-2d3e4f5a6b7c";
const PAGE_VIEW = { route: "/inventario/ordenes", navigation_type: "client" };

const fetchMock = jest.fn();
const sendBeacon = jest.fn();

function jwt(sub: string): string {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${encode({ alg: "HS256" })}.${encode({ sub, iat: 1_763_547_000, exp: 1_763_548_800 })}.firma`;
}

function login(sub: string) {
  window.localStorage.setItem("brasaland.access_token", jwt(sub));
}

type Track = (eventType: string, properties: Record<string, unknown>) => void;
type WithRequestId = <T>(requestId: string | null, fn: () => T) => T;

// Se carga de nuevo en cada prueba: la cola del servicio es un singleton. withRequestId sale de la
// misma carga, para compartir el contexto con track().
async function loadService(): Promise<{ track: Track; withRequestId: WithRequestId }> {
  jest.resetModules();
  const [{ track }, { withRequestId }] = await Promise.all([import("@/lib/telemetry"), import("@/lib/telemetry/request-context")]);
  return { track, withRequestId };
}

async function loadTrack(): Promise<Track> {
  return (await loadService()).track;
}

function sentEvents(): Array<Record<string, unknown>> {
  return fetchMock.mock.calls.flatMap(([, init]) => JSON.parse((init as RequestInit).body as string).events);
}

beforeEach(() => {
  jest.useFakeTimers({ now: new Date("2026-11-19T10:15:30.123Z") });
  fetchMock.mockReset().mockResolvedValue({ status: 200 }); // jsdom no tiene Response; la cola solo lee status.
  window.fetch = fetchMock as unknown as typeof fetch;
  sendBeacon.mockReset().mockReturnValue(true);
  Object.defineProperty(navigator, "sendBeacon", { value: sendBeacon, configurable: true });
  jest.spyOn(console, "warn").mockImplementation(() => {});
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
  Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
});

describe("envelope", () => {
  it("añade todos los campos del envelope; quien llama solo pasa el tipo y las propiedades", async () => {
    login(USER);
    const track = await loadTrack();

    track("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(10_000);

    const [event] = sentEvents();
    expect(Object.keys(event).sort()).toEqual(
      ["environment", "eventId", "event_type", "properties", "requestId", "schemaVersion", "sessionId", "source", "timestamp", "userId"].sort()
    );
    expect(event).toMatchObject({
      timestamp: "2026-11-19T10:15:30.123Z",
      userId: USER,
      event_type: "page_viewed",
      schemaVersion: "1.0.0",
      requestId: null,
      properties: PAGE_VIEW,
      source: "browser",
      environment: "staging",
    });
    expect(event.eventId).toMatch(UUID_V4);
    expect(event.sessionId).toMatch(UUID_V4);
  });

  it("el timestamp es el de la captura, no el del envío", async () => {
    const track = await loadTrack();
    track("page_viewed", PAGE_VIEW);

    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentEvents()[0].timestamp).toBe("2026-11-19T10:15:30.123Z");
  });

  it("cada evento tiene su propio eventId", async () => {
    const track = await loadTrack();
    track("page_viewed", PAGE_VIEW);
    track("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(10_000);

    const [first, second] = sentEvents();
    expect(first.eventId).not.toBe(second.eventId);
  });

  it("schemaVersion sale del catálogo de cada evento", async () => {
    const track = await loadTrack();
    track("login_failed", { failure_reason: "invalid_credentials" });
    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentEvents()[0].schemaVersion).toBe("2.0.0");
  });

  it("requestId es el de la llamada a la API que originó el evento", async () => {
    const { track, withRequestId } = await loadService();
    withRequestId("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", () => track("login_failed", { failure_reason: "invalid_credentials" }));
    track("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentEvents().map((event) => event.requestId)).toEqual(["a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", null]);
  });

  it("omite las propiedades opcionales sin valor", async () => {
    const track = await loadTrack();
    track("page_viewed", { ...PAGE_VIEW, previous_route: undefined });
    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentEvents()[0].properties).toEqual(PAGE_VIEW);
  });
});

describe("sesión", () => {
  it("sin sesión iniciada, sessionId y userId son null", async () => {
    const track = await loadTrack();
    track("page_viewed", { route: "/login", navigation_type: "initial" });
    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentEvents()[0]).toMatchObject({ sessionId: null, userId: null });
  });

  it("mantiene el mismo sessionId durante la sesión, también tras recargar", async () => {
    login(USER);
    (await loadTrack())("page_viewed", PAGE_VIEW);
    // Recarga: el módulo se carga de nuevo, sessionStorage sigue.
    (await loadTrack())("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(10_000);

    const [first, second] = sentEvents();
    expect(first.sessionId).toBe(second.sessionId);
  });

  it("al cerrar la sesión y volver a entrar empieza una sesión nueva", async () => {
    const track = await loadTrack();
    login(USER);
    track("page_viewed", PAGE_VIEW);
    window.localStorage.clear();
    track("page_viewed", { route: "/login", navigation_type: "client" });
    login(USER);
    track("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(10_000);

    const [before, loggedOut, after] = sentEvents();
    expect(loggedOut.sessionId).toBeNull();
    expect(after.sessionId).toMatch(UUID_V4);
    expect(after.sessionId).not.toBe(before.sessionId);
  });

  it("otra cuenta en la misma pestaña empieza otra sesión", async () => {
    const track = await loadTrack();
    login(USER);
    track("page_viewed", PAGE_VIEW);
    login(OTHER_USER);
    track("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(10_000);

    const [first, second] = sentEvents();
    expect(second.userId).toBe(OTHER_USER);
    expect(second.sessionId).not.toBe(first.sessionId);
  });
});

describe("validación contra el catálogo", () => {
  it("descarta un tipo de evento que no está en el catálogo del backoffice", async () => {
    const track = await loadTrack();
    track("evento_inventado", {});
    // Existe en el plan, pero lo emite la API, no el navegador.
    track("server_error_occurred", { method: "GET", route: "/x", exception_type: "E", error_fingerprint: "0123456789abcdef" });
    await jest.advanceTimersByTimeAsync(10_000);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining("evento_inventado"));
  });

  it("descarta un evento con una clave fuera del allowlist, sin recortarlo", async () => {
    const track = await loadTrack();
    track("login_failed", { failure_reason: "invalid_credentials", email: "ana@brasaland.com" });
    await jest.advanceTimersByTimeAsync(10_000);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining("email"));
  });

  it("descarta un evento sin sus propiedades obligatorias", async () => {
    const track = await loadTrack();
    track("page_viewed", { route: "/login" });
    await jest.advanceTimersByTimeAsync(10_000);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining("navigation_type"));
  });
});

describe("envío", () => {
  it("20 eventos salen en un único lote a NEXT_PUBLIC_TELEMETRY_ENDPOINT", async () => {
    const track = await loadTrack();
    for (let n = 0; n < 20; n++) track("page_viewed", PAGE_VIEW);
    await jest.advanceTimersByTimeAsync(0);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(ENDPOINT);
    expect(sentEvents()).toHaveLength(20);
  });

  it("al ocultar la pestaña, lo pendiente sale con sendBeacon", async () => {
    const track = await loadTrack();
    track("page_viewed", PAGE_VIEW);

    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon.mock.calls[0][0]).toBe(ENDPOINT);
    await jest.advanceTimersByTimeAsync(10_000);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("nunca lanza, aunque falle la red", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const track = await loadTrack();

    expect(() => track("page_viewed", PAGE_VIEW)).not.toThrow();
    await jest.advanceTimersByTimeAsync(30_000);
  });
});
