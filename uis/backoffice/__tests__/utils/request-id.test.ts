// Correlación de la telemetría (decisión C9): cada llamada de apiFetch lleva su propio X-Request-Id,
// y un error de la API conserva el de su llamada. `fetch` está simulado: no hay red.
import { ApiError, apiFetch, REQUEST_ID_HEADER } from "@/lib/api-client";

jest.mock("@/lib/auth/token", () => ({
  getToken: () => null,
  clearToken: jest.fn(),
}));

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

function sentRequestId(call = 0): string | null {
  const [, init] = fetchMock.mock.calls[call] as [string, RequestInit];
  return new Headers(init.headers).get(REQUEST_ID_HEADER);
}

it("envía un UUID v4 distinto en X-Request-Id en cada llamada", async () => {
  fetchMock.mockImplementation(() => Promise.resolve(new Response("{}", { status: 200 })));

  await apiFetch("/inventory/products", { fallback: "no se pudo cargar" });
  await apiFetch("/inventory/products", { fallback: "no se pudo cargar" });

  expect(sentRequestId(0)).toMatch(UUID_V4);
  expect(sentRequestId(1)).toMatch(UUID_V4);
  expect(sentRequestId(0)).not.toBe(sentRequestId(1));
});

it("conserva las cabeceras de quien llama", async () => {
  fetchMock.mockResolvedValue(new Response("{}", { status: 200 }));

  await apiFetch("/inventory/orders/inbound", { fallback: "x", method: "POST", headers: { "Content-Type": "application/json" } });

  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
});

it("un error de la API lleva el X-Request-Id de su llamada", async () => {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ error: { code: "insufficient_stock", message: "No hay stock suficiente." } }), { status: 400 })
  );

  const error = await apiFetch("/inventory/orders/outbound", { fallback: "x" }).catch((err: unknown) => err);

  expect(error).toBeInstanceOf(ApiError);
  expect((error as ApiError).code).toBe("insufficient_stock");
  expect((error as ApiError).requestId).toBe(sentRequestId());
});

it("un fallo de red también lleva el X-Request-Id", async () => {
  fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

  const error = (await apiFetch("/inventory/products", { fallback: "x" }).catch((err: unknown) => err)) as ApiError;

  expect(error.code).toBe("network_error");
  expect(error.requestId).toBe(sentRequestId());
});
