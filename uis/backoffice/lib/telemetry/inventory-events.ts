import { LOW_STOCK_THRESHOLDS } from "@/lib/inventory-stock-level";
import type { Category, Ingredient, IngredientEntry, IngredientExit, IngredientExitInput } from "@/types/inventory";
import type { Location } from "@/types/locations";

// Propiedades de las métricas obligatorias del inventario (plan de telemetría, sección 3). Son
// funciones puras: lib/inventory.ts las llama tras la respuesta de la API y emite con track().
//
// Los eventos usan el vocabulario del briefing, no el del modelo (plan, §12.1): `product_id` es el
// `Ingredient.id`, `product_category` es la categoría traducida, y `location_id`, `country` y `currency`
// salen del local de la orden, del catálogo `locations` (brecha B7 cerrada). La API ya exige que el
// ingrediente sea del país del local.

// Briefing: proteína, vegetal, salsa, bebida, empaque y limpieza.
export const PRODUCT_CATEGORY: Record<Category, string> = {
  meat: "proteína",
  produce: "vegetal",
  sauce: "salsa",
  beverage: "bebida",
  packaging: "empaque",
  cleaning: "limpieza",
};

// Variación de precio (plan, §3.2): media de los últimos 90 días del mismo producto y proveedor, con
// al menos 3 entradas, y un umbral del 10 % en cualquiera de los dos sentidos.
export const PRICE_VARIANCE = { thresholdPct: 10, windowDays: 90, minSamples: 3 } as const;

const DAY_MS = 24 * 60 * 60 * 1000;

function round(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

// Campos comunes de un hecho del inventario: dónde (el local), qué producto y en qué moneda (la del local).
export function productFields(ingredient: Ingredient, location: Location) {
  return {
    location_id: location.id,
    country: location.country,
    product_id: ingredient.id,
    product_category: PRODUCT_CATEGORY[ingredient.category],
    unit: ingredient.unit,
    currency: location.currency,
  };
}

// `inbound_order_created`.
export function inboundOrderProperties(
  entry: IngredientEntry,
  ingredient: Ingredient,
  location: Location,
  supplierId: number | undefined
) {
  return {
    order_id: entry.id,
    ...productFields(ingredient, location),
    quantity: entry.quantity,
    supplier_id: supplierId,
    unit_cost: entry.unit_cost ?? undefined,
  };
}

// `ingredient_price_variance_detected`, o null si no hay histórico suficiente o la variación no
// supera el umbral. `history` son las entradas que devuelve GET /inventory/orders: se usan las del
// mismo producto y proveedor de los 90 días anteriores a esta, con coste, sin contar la propia entrada.
export function priceVarianceProperties(
  entry: IngredientEntry,
  ingredient: Ingredient,
  location: Location,
  supplierId: number | undefined,
  history: readonly IngredientEntry[]
) {
  if (entry.unit_cost === null) return null;
  const createdAt = Date.parse(entry.created_at);
  const windowStart = createdAt - PRICE_VARIANCE.windowDays * DAY_MS;
  const costs = history
    .filter(
      (other) =>
        other.id !== entry.id &&
        other.ingredient_id === entry.ingredient_id &&
        other.supplier_name === entry.supplier_name &&
        other.unit_cost !== null &&
        Date.parse(other.created_at) >= windowStart &&
        Date.parse(other.created_at) <= createdAt
    )
    .map((other) => other.unit_cost as number);
  if (costs.length < PRICE_VARIANCE.minSamples) return null;

  const average = costs.reduce((sum, cost) => sum + cost, 0) / costs.length;
  const variancePct = ((entry.unit_cost - average) / average) * 100;
  if (Math.abs(variancePct) <= PRICE_VARIANCE.thresholdPct) return null;

  return {
    ...inboundOrderProperties(entry, ingredient, location, supplierId),
    historical_avg_unit_cost: round(average, 2),
    variance_pct: round(variancePct, 2),
    threshold_pct: PRICE_VARIANCE.thresholdPct,
    history_window_days: PRICE_VARIANCE.windowDays,
    history_sample_size: costs.length,
  };
}

// Una salida emite un único evento según su motivo (plan, §3.2): `outbound_order_created` si es
// consumo y `stock_waste_registered` si es merma, con el motivo en `reason`.
export function outboundOrderEvent(
  exit: IngredientExit,
  ingredient: Ingredient,
  location: Location,
  stockAfter: number | undefined
) {
  const base = {
    order_id: exit.id,
    ...productFields(ingredient, location),
    quantity: exit.quantity,
    stock_after: stockAfter,
  };
  if (exit.reason === "waste") {
    return { eventType: "stock_waste_registered", properties: { ...base, reason: exit.waste_reason ?? undefined } };
  }
  return { eventType: "outbound_order_created", properties: base };
}

// `stock_threshold_triggered`, o null si la salida no hace cruzar el mínimo: antes ≥ mínimo y
// después < mínimo (plan, §3.2). El mínimo es, mientras no haya mínimos por local (brecha B3), el
// umbral de stock bajo del backoffice para la unidad del producto, sobre el stock global.
export function thresholdProperties(exit: IngredientExit, ingredient: Ingredient, location: Location, stockAfter: number) {
  const threshold = LOW_STOCK_THRESHOLDS[ingredient.unit];
  const stockBefore = round(stockAfter + exit.quantity, 3);
  if (!(stockBefore >= threshold && stockAfter < threshold)) return null;
  return {
    ...productFields(ingredient, location),
    quantity: stockAfter,
    threshold_quantity: threshold,
    trigger_order_id: exit.id,
  };
}

// `outbound_order_rejected` (§5.1): la API rechazó una salida por superar el stock (400
// `insufficient_stock`); `available_quantity` es el stock de ese momento.
export function outboundRejectedProperties(
  input: IngredientExitInput,
  ingredient: Ingredient,
  location: Location,
  available: number
) {
  return {
    ...productFields(ingredient, location),
    quantity: input.quantity,
    available_quantity: available,
    outbound_type: input.reason,
  };
}
