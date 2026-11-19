import { apiJson, jsonBody } from "@/lib/api-client";
import type {
  Country,
  Ingredient,
  IngredientEntry,
  IngredientEntryInput,
  IngredientExit,
  IngredientExitInput,
  OrdersResponse,
} from "@/types/inventory";

// Capa de integración con la API de inventario (decisión F1): el único sitio del backoffice que
// llama a /inventory. Ningún componente usa fetch: todo pasa por apiJson (lib/api-client.ts), que
// - añade `Authorization: Bearer <token>` con el token de la sesión (localStorage);
// - convierte cualquier 4xx/5xx en un ApiError con el mensaje de la API en español (o uno legible
//   si la API no lo da), y cierra la sesión ante un 401.
// Las rutas son las del intermediario (/api/inventory/…), que las reenvía a /api/v1/inventory/….
const INVENTORY_PATH = "/inventory";

// GET /inventory/products: ingredientes con current_stock; `country` filtra por mercado.
export function listIngredients(country?: Country): Promise<Ingredient[]> {
  const query = country ? `?country=${country}` : "";
  return apiJson(`${INVENTORY_PATH}/products${query}`, {
    fallback: "no se pudieron cargar los ingredientes",
  });
}

// GET /inventory/products/{id}: un ingrediente con su stock actual (404 si no existe).
export function getIngredient(id: number): Promise<Ingredient> {
  return apiJson(`${INVENTORY_PATH}/products/${id}`, {
    fallback: "no se pudo cargar el stock del ingrediente",
  });
}

// POST /inventory/orders/inbound: registra una entrega de proveedor. 201 con la entrada creada.
export function createEntry(input: IngredientEntryInput): Promise<IngredientEntry> {
  return apiJson(`${INVENTORY_PATH}/orders/inbound`, {
    fallback: "no se pudo registrar la entrada",
    ...jsonBody("POST", input),
  });
}

// POST /inventory/orders/outbound: registra un consumo o una merma. 400 `insufficient_stock` si
// dejaría el stock en negativo (la API no escribe nada).
export function createExit(input: IngredientExitInput): Promise<IngredientExit> {
  return apiJson(`${INVENTORY_PATH}/orders/outbound`, {
    fallback: "no se pudo registrar la salida",
    ...jsonBody("POST", input),
  });
}

// Intento de cambiar el stock directamente, desde la acción "Ajustar stock" (brecha B4 del plan de
// telemetría, decisión C3). El stock solo cambia con órdenes, así que la API lo rechaza siempre (405):
// la petición es real para que el rechazo lo decida el sistema y quede medido. Lanza el ApiError.
export function attemptDirectStockEdit(ingredientId: number, currentStock: number): Promise<never> {
  return apiJson<never>(`${INVENTORY_PATH}/products/${ingredientId}`, {
    fallback: "no se pudo ajustar el stock",
    ...jsonBody("PATCH", { current_stock: currentStock }),
  });
}

// GET /inventory/orders: entradas y salidas con los datos de su ingrediente y su user_uuid.
export function listOrders(): Promise<OrdersResponse> {
  return apiJson(`${INVENTORY_PATH}/orders`, { fallback: "no se pudieron cargar las órdenes" });
}
