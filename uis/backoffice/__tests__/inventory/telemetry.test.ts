// Emisión de las métricas obligatorias desde la capa de datos (lib/inventory.ts y lib/api-client.ts):
// cada orden emite su evento al recibir el 201, con el `requestId` de su llamada, y el ajuste directo
// del stock emite `direct_stock_edit_rejected` al recibir el 405. track() y fetch están simulados.
import { ApiError, REQUEST_ID_HEADER } from "@/lib/api-client";
import { attemptDirectStockEdit, createEntry, createExit } from "@/lib/inventory";
import { currentRequestId } from "@/lib/telemetry/request-context";
import type { Ingredient } from "@/types/inventory";
import type { Location } from "@/types/locations";

const tracked: Array<{ eventType: string; properties: Record<string, unknown>; requestId: string | null }> = [];

jest.mock("@/lib/telemetry", () => ({
  track: (eventType: string, properties: Record<string, unknown>) => {
    // Los eventos de cada llamada (latencia y error genérico) tienen sus propias pruebas.
    if (eventType === "api_latency_recorded" || eventType === "api_error_returned") return;
    // El contexto real: track() lee el requestId con el que lo envuelve la capa de datos.
    const { currentRequestId: read } = jest.requireActual("@/lib/telemetry/request-context");
    tracked.push({ eventType, properties, requestId: read() });
  },
}));
jest.mock("@/lib/auth/token", () => ({ getToken: () => "jwt", clearToken: jest.fn(), readTokenClaims: () => null }));
jest.mock("@/lib/telemetry/session", () => ({ currentUserRole: () => "manager" }));

const BEEF: Ingredient = { id: 1, name: "Falda de ternera", sku: "BRS-BEEF-001", unit: "kg", category: "meat", country: "CO", current_stock: 42 };
const ENVIGADO: Location = { id: 3, code: "medellin_envigado", name: "Medellín Envigado", city: "Medellín", country: "CO", currency: "COP" };
const PROJECTION = { ingredient_id: 1, ingredient_name: "Falda de ternera", ingredient_sku: "BRS-BEEF-001", ingredient_unit: "kg" };
const fetchMock = jest.fn();

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function requestIdOf(call: number): string {
  const [, init] = fetchMock.mock.calls[call] as [string, RequestInit];
  return new Headers(init.headers).get(REQUEST_ID_HEADER) as string;
}

// Deja terminar las promesas de la telemetría, que no se esperan.
async function settle() {
  for (let i = 0; i < 5; i++) await new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(() => {
  tracked.length = 0;
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

it("una entrada emite inbound_order_created con el requestId de su POST", async () => {
  const entry = { id: 7, ...PROJECTION, quantity: 20, location_id: 3, created_at: "2026-11-19T10:00:00Z", user_uuid: "u", supplier_name: "Carnes del Valle S.A.", unit_cost: 38500 };
  fetchMock.mockResolvedValueOnce(json(entry, 201)).mockResolvedValueOnce(json({ inbound: [entry], outbound: [] }));

  await createEntry({ ingredient_id: 1, quantity: 20, supplier_name: entry.supplier_name, unit_cost: 38500, location_id: 3 }, { ingredient: BEEF, location: ENVIGADO, supplierId: 2 });
  await settle();

  expect(tracked).toEqual([
    {
      eventType: "inbound_order_created",
      properties: expect.objectContaining({ order_id: 7, product_id: 1, product_category: "proteína", supplier_id: 2, unit_cost: 38500, currency: "COP" }),
      requestId: requestIdOf(0),
    },
  ]);
  expect(currentRequestId()).toBeNull();
});

it("una entrada con un coste anómalo emite también ingredient_price_variance_detected", async () => {
  const base = { ...PROJECTION, quantity: 20, location_id: 3, user_uuid: "u", supplier_name: "Carnes del Valle S.A." };
  const entry = { id: 9, ...base, created_at: "2026-11-19T10:00:00Z", unit_cost: 50000 };
  const history = [1, 2, 3].map((id) => ({ id, ...base, created_at: `2026-11-0${id}T10:00:00Z`, unit_cost: 38000 }));
  fetchMock.mockResolvedValueOnce(json(entry, 201)).mockResolvedValueOnce(json({ inbound: [entry, ...history], outbound: [] }));

  await createEntry({ ingredient_id: 1, quantity: 20, supplier_name: base.supplier_name, unit_cost: 50000, location_id: 3 }, { ingredient: BEEF, location: ENVIGADO, supplierId: 2 });
  await settle();

  expect(tracked.map((event) => event.eventType)).toEqual(["inbound_order_created", "ingredient_price_variance_detected"]);
  expect(tracked[1]).toMatchObject({ properties: { variance_pct: 31.58, history_sample_size: 3 }, requestId: requestIdOf(0) });
});

it("una merma que cruza el mínimo emite stock_waste_registered y stock_threshold_triggered", async () => {
  const exit = { id: 30, ...PROJECTION, quantity: 5, location_id: 3, created_at: "2026-11-19T10:00:00Z", user_uuid: "u", reason: "waste", waste_reason: "kitchen_error" };
  fetchMock.mockResolvedValueOnce(json(exit, 201)).mockResolvedValueOnce(json({ ...BEEF, current_stock: 37 }));

  await createExit({ ingredient_id: 1, quantity: 5, reason: "waste", waste_reason: "kitchen_error", location_id: 3 }, { ingredient: BEEF, location: ENVIGADO });
  await settle();

  expect(tracked.map((event) => event.eventType)).toEqual(["stock_waste_registered", "stock_threshold_triggered"]);
  expect(tracked[0].properties).toMatchObject({ order_id: 30, reason: "kitchen_error", stock_after: 37 });
  expect(tracked[1].properties).toMatchObject({ quantity: 37, threshold_quantity: 40, trigger_order_id: 30 });
  expect(tracked.every((event) => event.requestId === requestIdOf(0))).toBe(true);
});

it("un consumo emite solo outbound_order_created; sin stock resultante, sin umbral", async () => {
  const exit = { id: 31, ...PROJECTION, quantity: 2, location_id: 3, created_at: "2026-11-19T10:00:00Z", user_uuid: "u", reason: "consumption", waste_reason: null };
  fetchMock.mockResolvedValueOnce(json(exit, 201)).mockRejectedValueOnce(new TypeError("Failed to fetch"));

  await createExit({ ingredient_id: 1, quantity: 2, reason: "consumption", location_id: 3 }, { ingredient: BEEF, location: ENVIGADO });
  await settle();

  expect(tracked).toHaveLength(1);
  expect(tracked[0]).toMatchObject({ eventType: "outbound_order_created", properties: { order_id: 31 } });
  // track() omite las opcionales sin valor (las que llegan como undefined).
  expect(tracked[0].properties.stock_after).toBeUndefined();
});

it("una salida sin stock suficiente (400) emite outbound_order_rejected con el stock disponible, y no la orden", async () => {
  fetchMock
    .mockResolvedValueOnce(json({ error: { code: "insufficient_stock", message: "Stock insuficiente." } }, 400))
    .mockResolvedValueOnce(json({ ...BEEF, current_stock: 52 }));

  await expect(createExit({ ingredient_id: 1, quantity: 60, reason: "waste", waste_reason: "expired", location_id: 3 }, { ingredient: BEEF, location: ENVIGADO })).rejects.toBeInstanceOf(ApiError);
  await settle();

  expect(tracked.map((event) => event.eventType)).toEqual(["outbound_order_rejected"]);
  expect(tracked[0]).toEqual({
    eventType: "outbound_order_rejected",
    properties: { location_id: 3, country: "CO", product_id: 1, product_category: "proteína", unit: "kg", currency: "COP", quantity: 60, available_quantity: 52, outbound_type: "waste" },
    requestId: requestIdOf(0),
  });
});

it("Ajustar stock: el 405 de la API emite direct_stock_edit_rejected", async () => {
  fetchMock.mockResolvedValueOnce(json({ error: { code: "http_405", message: "Esta ruta no admite el método PATCH." } }, 405));

  await attemptDirectStockEdit(1, 60).catch(() => {});

  expect(tracked).toEqual([
    {
      eventType: "direct_stock_edit_rejected",
      properties: {
        product_id: 1,
        method: "PATCH",
        route: "/api/v1/inventory/products/{ingredient_id}",
        rejection_type: "method_not_allowed",
        status_code: 405,
        user_role: "manager",
      },
      requestId: requestIdOf(0),
    },
  ]);
});

it("un POST del inventario con current_stock (422) emite direct_stock_edit_rejected", async () => {
  const details = [{ field: "current_stock", message: "Campo no permitido." }];
  fetchMock.mockResolvedValueOnce(json({ error: { code: "invalid_request", message: "La petición no es válida.", details } }, 422));

  await createEntry({ ingredient_id: 1, quantity: 1, supplier_name: "X", unit_cost: 1, location_id: 1, current_stock: 99 } as never).catch(() => {});

  expect(tracked[0]).toMatchObject({
    eventType: "direct_stock_edit_rejected",
    properties: { method: "POST", route: "/api/v1/inventory/orders/inbound", rejection_type: "forbidden_field", status_code: 422 },
  });
});

it("otros errores del inventario no se confunden con una edición directa", async () => {
  fetchMock.mockResolvedValueOnce(json({ error: { code: "invalid_request", message: "x", details: [{ field: "quantity", message: "x" }] } }, 422));

  await createEntry({ ingredient_id: 1, quantity: 0, supplier_name: "X", unit_cost: 1, location_id: 1 }).catch(() => {});

  expect(tracked.map((event) => event.eventType)).not.toContain("direct_stock_edit_rejected");
});
