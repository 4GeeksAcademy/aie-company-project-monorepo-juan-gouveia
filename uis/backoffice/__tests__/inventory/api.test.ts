// Capa de integración del inventario (lib/inventory.ts, decisión F1): cada llamada va al
// intermediario con su método, su cuerpo y `Authorization: Bearer <token>`, y los errores de la
// API llegan como ApiError con el mensaje en español. `fetch` está simulado: no hay red.
import { ApiError } from "@/lib/api-client";
import { createEntry, createExit, getIngredient, listIngredients, listOrders } from "@/lib/inventory";

jest.mock("@/lib/auth/token", () => ({
  getToken: () => "jwt-de-la-sesion",
  clearToken: jest.fn(),
}));

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function lastRequest(): { url: string; method: string; headers: Headers; body: unknown } {
  const [url, init] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
  return {
    url,
    method: init.method ?? "GET",
    headers: new Headers(init.headers),
    body: init.body ? JSON.parse(init.body as string) : undefined,
  };
}

const INGREDIENT = {
  id: 1,
  name: "Falda de ternera",
  sku: "BRS-BEEF-001",
  unit: "kg",
  category: "meat",
  country: "CO",
  current_stock: 52,
};

describe("lecturas", () => {
  it("listIngredients pide GET /api/inventory/products con el token", async () => {
    fetchMock.mockResolvedValue(jsonResponse([INGREDIENT]));

    await expect(listIngredients()).resolves.toEqual([INGREDIENT]);
    const request = lastRequest();
    expect([request.method, request.url]).toEqual(["GET", "/api/inventory/products"]);
    expect(request.headers.get("Authorization")).toBe("Bearer jwt-de-la-sesion");
  });

  it("listIngredients con país añade el filtro ?country=", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));

    await listIngredients("US");
    expect(lastRequest().url).toBe("/api/inventory/products?country=US");
  });

  it("getIngredient pide el ingrediente por su id", async () => {
    fetchMock.mockResolvedValue(jsonResponse(INGREDIENT));

    await expect(getIngredient(1)).resolves.toMatchObject({ current_stock: 52 });
    expect(lastRequest().url).toBe("/api/inventory/products/1");
  });

  it("listOrders pide GET /api/inventory/orders", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ inbound: [], outbound: [] }));

    await expect(listOrders()).resolves.toEqual({ inbound: [], outbound: [] });
    expect(lastRequest().url).toBe("/api/inventory/orders");
    expect(lastRequest().headers.get("Authorization")).toBe("Bearer jwt-de-la-sesion");
  });
});

describe("escrituras", () => {
  it("createEntry envía POST /api/inventory/orders/inbound en JSON, sin user_uuid", async () => {
    const input = { ingredient_id: 1, quantity: 50, supplier_name: "Carnes del Valle S.A.", location_id: 1 };
    fetchMock.mockResolvedValue(jsonResponse({ id: 5, ...input }, 201));

    await createEntry(input);
    const request = lastRequest();
    expect([request.method, request.url]).toEqual(["POST", "/api/inventory/orders/inbound"]);
    expect(request.headers.get("Content-Type")).toBe("application/json");
    expect(request.headers.get("Authorization")).toBe("Bearer jwt-de-la-sesion");
    expect(request.body).toEqual(input);
  });

  it("createExit envía POST /api/inventory/orders/outbound con el motivo", async () => {
    const input = { ingredient_id: 1, quantity: 3, reason: "waste" as const, location_id: 2 };
    fetchMock.mockResolvedValue(jsonResponse({ id: 9, ...input }, 201));

    await createExit(input);
    expect(lastRequest()).toMatchObject({ method: "POST", url: "/api/inventory/orders/outbound", body: input });
  });
});

describe("errores de la API", () => {
  it("el 400 de stock insuficiente llega como ApiError con el mensaje de la API", async () => {
    const message = "Stock insuficiente para el ingrediente 'Falda de ternera'. Disponible: 52, solicitado: 60.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "insufficient_stock", message } }, 400));

    const error = await createExit({ ingredient_id: 1, quantity: 60, reason: "consumption", location_id: 1 }).catch(
      (err: unknown) => err
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 400, code: "insufficient_stock", message });
  });

  it("un 422 conserva el detalle por campo", async () => {
    const details = [{ field: "location_id", message: "Debe ser menor o igual que 14." }];
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "invalid_request", message: "La petición no es válida.", details } }, 422)
    );

    await expect(
      createEntry({ ingredient_id: 1, quantity: 1, supplier_name: "X", location_id: 15 })
    ).rejects.toMatchObject({ status: 422, details });
  });

  it("un 500 sin mensaje propio se muestra con un texto legible, nunca técnico", async () => {
    fetchMock.mockResolvedValue(new Response("Internal Server Error", { status: 500 }));

    await expect(listIngredients()).rejects.toMatchObject({
      status: 500,
      message: expect.stringMatching(/^El servidor tuvo un problema/),
    });
  });

  it("si la red falla, el error es legible", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(listOrders()).rejects.toMatchObject({ status: 0, code: "network_error" });
  });
});
