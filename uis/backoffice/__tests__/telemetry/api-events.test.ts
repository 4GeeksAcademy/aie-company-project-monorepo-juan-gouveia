// Eventos de cada llamada a la API (lib/telemetry/api-events.ts): latencia muestreada, errores 4xx,
// caídas de conexión y validación de órdenes. track() está simulado.
import { ApiError } from "@/lib/api-client";
import { reportApiCall, reportApiError, resetApiEventThrottle, sampleRate, type ApiCall } from "@/lib/telemetry/api-events";

const track = jest.fn();
jest.mock("@/lib/telemetry", () => ({ track: (...args: unknown[]) => track(...args) }));
jest.mock("@/lib/auth/token", () => ({ getToken: () => null, readTokenClaims: () => null }));
jest.mock("@/lib/telemetry/session", () => ({ currentUserRole: () => "user" }));

// requestId cuya muestra sale (últimos 4 hex = 0x000a → 10 % 10 = 0) y otro que no (0x0001).
const SAMPLED = "0f8e7d6c-5b4a-4392-8170-6e5d4c3b000a";
const NOT_SAMPLED = "0f8e7d6c-5b4a-4392-8170-6e5d4c3b0001";

function call(overrides: Partial<ApiCall> = {}): ApiCall {
  return { method: "GET", path: "/inventory/orders", requestId: NOT_SAMPLED, durationMs: 42.37, ...overrides };
}

function error(status: number, code: string, details: { field: string; message: string }[] = []): ApiError {
  return new ApiError("x", status, code, details, NOT_SAMPLED);
}

function events(name: string) {
  return track.mock.calls.filter(([eventType]) => eventType === name).map(([, properties]) => properties);
}

beforeEach(() => {
  track.mockReset();
  resetApiEventThrottle();
});

describe("api_latency_recorded", () => {
  it("emite siempre las llamadas lentas o con error, con sample_rate 1", () => {
    expect(sampleRate(NOT_SAMPLED, 300, 200)).toBe(1);
    expect(sampleRate(NOT_SAMPLED, 10, 404)).toBe(1);
  });

  it("del resto, 1 de cada 10 elegidas por el requestId", () => {
    expect(sampleRate(SAMPLED, 10, 200)).toBe(0.1);
    expect(sampleRate(NOT_SAMPLED, 10, 200)).toBeNull();
  });

  it("lleva la ruta como plantilla, la duración y el resultado de la caché", () => {
    reportApiCall(call({ path: "/inventory/products/12", durationMs: 1.44, requestId: SAMPLED }), 200, "HIT");

    expect(events("api_latency_recorded")).toEqual([
      { method: "GET", route: "/api/v1/inventory/products/{ingredient_id}", status_code: 200, duration_ms: 1.4, cache: "HIT", sample_rate: 0.1 },
    ]);
  });

  it("una llamada rápida no muestreada no emite nada", () => {
    reportApiCall(call(), 200, null);
    expect(track).not.toHaveBeenCalled();
  });
});

describe("api_error_returned", () => {
  it("emite el método, la ruta, el estado y el código de un 4xx", () => {
    reportApiError(call({ method: "POST", path: "/suppliers" }), error(409, "duplicate_supplier"), 0);

    expect(events("api_error_returned")).toEqual([{ method: "POST", route: "/api/v1/suppliers", status_code: 409, error_code: "duplicate_supplier" }]);
  });

  it("el mismo error en la misma ruta no se repite antes de 10 s", () => {
    reportApiError(call(), error(404, "not_found"), 0);
    reportApiError(call(), error(404, "not_found"), 5_000);
    reportApiError(call(), error(404, "not_found"), 11_000);

    expect(events("api_error_returned")).toHaveLength(2);
  });

  it("no emite los 5xx ni los fallos de red", () => {
    reportApiError(call(), error(500, "server_error"), 0);
    reportApiError(call(), error(0, "network_error"), 0);

    expect(events("api_error_returned")).toEqual([]);
  });
});

describe("api_connection_failed", () => {
  it.each([
    [502, "api_unavailable"],
    [504, "api_timeout"],
    [500, "api_not_configured"],
  ])("un %i %s del intermediario es una caída de conexión", (status, code) => {
    reportApiError(call({ durationMs: 3012.4 }), error(status, code), 0);

    expect(events("api_connection_failed")).toEqual([
      { method: "GET", route: "/api/v1/inventory/orders", failure: code, status_code: status, duration_ms: 3012 },
    ]);
    expect(events("api_error_returned")).toEqual([]);
  });

  it("se emite como máximo una vez cada 30 s", () => {
    reportApiError(call(), error(502, "api_unavailable"), 0);
    reportApiError(call(), error(502, "api_unavailable"), 20_000);
    reportApiError(call(), error(502, "api_unavailable"), 31_000);

    expect(events("api_connection_failed")).toHaveLength(2);
  });
});

describe("order_validation_failed", () => {
  const body = JSON.stringify({ ingredient_id: 12, quantity: 0, location_id: 3, supplier_name: "Carnes del Valle S.A." });

  it("un 422 de una orden emite los campos señalados y los identificadores del cuerpo, sin valores", () => {
    const details = [
      { field: "quantity", message: "Debe ser mayor que 0." },
      { field: "unit_cost", message: "Campo obligatorio." },
    ];
    reportApiError(call({ method: "POST", path: "/inventory/orders/inbound", body }), error(422, "invalid_request", details), 0);

    expect(events("order_validation_failed")).toEqual([
      { order_type: "inbound", product_id: 12, location_id: 3, error_code: "invalid_request", invalid_fields: ["quantity", "unit_cost"], status_code: 422 },
    ]);
    expect(JSON.stringify(track.mock.calls)).not.toContain("Carnes del Valle");
  });

  it("un 404 de ingrediente inexistente también cuenta, sin campos", () => {
    reportApiError(call({ method: "POST", path: "/inventory/orders/outbound", body: "no-json" }), error(404, "ingredient_not_found"), 0);

    expect(events("order_validation_failed")).toEqual([
      { order_type: "outbound", error_code: "ingredient_not_found", invalid_fields: [], status_code: 404 },
    ]);
  });

  it("un current_stock en el cuerpo es una edición directa, no un error de validación", () => {
    reportApiError(
      call({ method: "POST", path: "/inventory/orders/inbound", body }),
      error(422, "invalid_request", [{ field: "current_stock", message: "Campo no permitido." }]),
      0
    );

    expect(events("direct_stock_edit_rejected")).toHaveLength(1);
    expect(events("order_validation_failed")).toEqual([]);
  });

  it("otras rutas no emiten order_validation_failed", () => {
    reportApiError(call({ method: "POST", path: "/suppliers" }), error(422, "invalid_request"), 0);
    expect(events("order_validation_failed")).toEqual([]);
  });
});
