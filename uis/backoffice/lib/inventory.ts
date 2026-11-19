import { apiJson, apiJsonWithRequestId, jsonBody } from "@/lib/api-client";
import { track } from "@/lib/telemetry";
import {
  inboundOrderProperties,
  outboundOrderEvent,
  priceVarianceProperties,
  thresholdProperties,
} from "@/lib/telemetry/inventory-events";
import { withRequestId } from "@/lib/telemetry/request-context";
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
//
// Telemetría (métricas obligatorias del briefing): las órdenes emiten sus eventos aquí, al recibir el
// 201 de la API (la orden ya está guardada), con el `requestId` de esa llamada. Quien registra la orden
// pasa el contexto que la respuesta no trae (el ingrediente y el id del proveedor). Los cálculos están
// en lib/telemetry/inventory-events.ts. La telemetría nunca hace fallar el registro.
const INVENTORY_PATH = "/inventory";

export interface EntryTelemetryContext {
  ingredient: Ingredient;
  // Id del proveedor en el directorio (la entrada solo guarda su nombre; brecha B8).
  supplierId: number | undefined;
}

export interface ExitTelemetryContext {
  ingredient: Ingredient;
}

function quietly(fn: () => void | Promise<void>): void {
  try {
    void Promise.resolve(fn()).catch(() => {});
  } catch {
    // La telemetría no interfiere con el registro de la orden.
  }
}

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
// Telemetría: `inbound_order_created` y, si el coste se desvía del histórico,
// `ingredient_price_variance_detected` (lo calcula con GET /inventory/orders, sin esperar).
export async function createEntry(input: IngredientEntryInput, telemetry?: EntryTelemetryContext): Promise<IngredientEntry> {
  const { data: entry, requestId } = await apiJsonWithRequestId<IngredientEntry>(`${INVENTORY_PATH}/orders/inbound`, {
    fallback: "no se pudo registrar la entrada",
    ...jsonBody("POST", input),
  });
  if (telemetry) {
    const { ingredient, supplierId } = telemetry;
    quietly(() => withRequestId(requestId, () => track("inbound_order_created", inboundOrderProperties(entry, ingredient, supplierId))));
    quietly(async () => {
      const { inbound } = await listOrders();
      const variance = priceVarianceProperties(entry, ingredient, supplierId, inbound);
      if (variance) withRequestId(requestId, () => track("ingredient_price_variance_detected", variance));
    });
  }
  return entry;
}

// POST /inventory/orders/outbound: registra un consumo o una merma. 400 `insufficient_stock` si
// dejaría el stock en negativo (la API no escribe nada).
// Telemetría: `outbound_order_created` (consumo) o `stock_waste_registered` (merma) y, si la salida
// hace cruzar el mínimo, `stock_threshold_triggered`. El stock resultante se pide a la API.
export async function createExit(input: IngredientExitInput, telemetry?: ExitTelemetryContext): Promise<IngredientExit> {
  const { data: exit, requestId } = await apiJsonWithRequestId<IngredientExit>(`${INVENTORY_PATH}/orders/outbound`, {
    fallback: "no se pudo registrar la salida",
    ...jsonBody("POST", input),
  });
  if (telemetry) {
    const { ingredient } = telemetry;
    quietly(async () => {
      let stockAfter: number | undefined;
      try {
        stockAfter = (await getIngredient(ingredient.id)).current_stock;
      } catch {
        // Sin el stock resultante se emite la salida igualmente, sin `stock_after` ni umbral.
      }
      withRequestId(requestId, () => {
        const { eventType, properties } = outboundOrderEvent(exit, ingredient, stockAfter);
        track(eventType, properties);
        const threshold = stockAfter === undefined ? null : thresholdProperties(exit, ingredient, stockAfter);
        if (threshold) track("stock_threshold_triggered", threshold);
      });
    });
  }
  return exit;
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
