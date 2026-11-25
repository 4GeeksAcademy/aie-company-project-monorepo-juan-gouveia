// Propiedades de las métricas obligatorias del inventario (lib/telemetry/inventory-events.ts):
// vocabulario del briefing, variación de precio con el histórico y cruce del umbral mínimo.
import {
  PRODUCT_CATEGORY,
  inboundOrderProperties,
  outboundOrderEvent,
  priceVarianceProperties,
  productFields,
  thresholdProperties,
  wasteUnitCost,
} from "@/lib/telemetry/inventory-events";
import { apiRouteTemplate } from "@/lib/telemetry/routes";
import type { Ingredient, IngredientEntry, IngredientExit } from "@/types/inventory";
import type { Location } from "@/types/locations";

const BEEF: Ingredient = { id: 12, name: "Falda de ternera", sku: "BRS-BEEF-001", unit: "kg", category: "meat", country: "CO", current_stock: 52 };
const PORK_US: Ingredient = { ...BEEF, id: 13, sku: "BRS-PORK-001", country: "US" };
const ENVIGADO: Location = { id: 3, code: "medellin_envigado", name: "Medellín Envigado", city: "Medellín", country: "CO", currency: "COP" };
const DORAL: Location = { id: 10, code: "miami_doral", name: "Miami Doral", city: "Miami", country: "US", currency: "USD" };
const USER = "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2";
const PROJECTION = { ingredient_id: 12, ingredient_name: "Falda de ternera", ingredient_sku: "BRS-BEEF-001", ingredient_unit: "kg" as const };

function entry(id: number, unitCost: number | null, createdAt = "2026-11-19T10:00:00Z", supplier = "Carnes del Valle S.A."): IngredientEntry {
  return { id, ...PROJECTION, quantity: 20, location_id: 3, created_at: createdAt, user_uuid: USER, supplier_name: supplier, unit_cost: unitCost };
}

function exit(id: number, quantity: number, reason: "consumption" | "waste" = "consumption"): IngredientExit {
  return {
    id,
    ...PROJECTION,
    quantity,
    location_id: 3,
    created_at: "2026-11-19T10:00:00Z",
    user_uuid: USER,
    reason,
    waste_reason: reason === "waste" ? "expired" : null,
  };
}

describe("vocabulario del briefing", () => {
  it("traduce las categorías del modelo a las del briefing", () => {
    expect(PRODUCT_CATEGORY).toEqual({
      meat: "proteína",
      produce: "vegetal",
      sauce: "salsa",
      beverage: "bebida",
      packaging: "empaque",
      cleaning: "limpieza",
    });
  });

  it("el local da location_id, país y moneda", () => {
    expect(productFields(BEEF, ENVIGADO)).toEqual({ location_id: 3, country: "CO", product_id: 12, product_category: "proteína", unit: "kg", currency: "COP" });
    expect(productFields(PORK_US, DORAL)).toMatchObject({ location_id: 10, country: "US", currency: "USD" });
  });

  it("país y moneda salen del local, no del ingrediente (brecha B7 cerrada)", () => {
    // La API ya no acepta esta combinación; la prueba solo fija de dónde sale cada campo.
    expect(productFields(BEEF, DORAL)).toMatchObject({ country: "US", currency: "USD" });
  });
});

describe("inbound_order_created", () => {
  it("lleva la orden, el producto, el proveedor y el coste unitario", () => {
    expect(inboundOrderProperties(entry(7824, 38500), BEEF, ENVIGADO, 2)).toEqual({
      order_id: 7824,
      location_id: 3,
      country: "CO",
      product_id: 12,
      product_category: "proteína",
      quantity: 20,
      unit: "kg",
      currency: "COP",
      supplier_id: 2,
      unit_cost: 38500,
    });
  });
});

describe("ingredient_price_variance_detected", () => {
  const history = [entry(1, 38000, "2026-10-01T10:00:00Z"), entry(2, 38200, "2026-10-20T10:00:00Z"), entry(3, 38400, "2026-11-10T10:00:00Z")];

  it("se emite si el coste se desvía más del 10 % de la media de 3 o más entradas", () => {
    const current = entry(4, 44000);
    expect(priceVarianceProperties(current, BEEF, ENVIGADO, 2, [current, ...history])).toMatchObject({
      order_id: 4,
      unit_cost: 44000,
      historical_avg_unit_cost: 38200,
      variance_pct: 15.18,
      threshold_pct: 10,
      history_window_days: 90,
      history_sample_size: 3,
    });
  });

  it("también avisa de una bajada anómala", () => {
    expect(priceVarianceProperties(entry(4, 30000), BEEF, ENVIGADO, 2, history)?.variance_pct).toBe(-21.47);
  });

  it("no se emite dentro del 10 %", () => {
    expect(priceVarianceProperties(entry(4, 42000), BEEF, ENVIGADO, 2, history)).toBeNull();
  });

  it("no se emite sin al menos 3 entradas del mismo producto y proveedor en 90 días", () => {
    const otherSupplier = entry(5, 38000, "2026-11-01T10:00:00Z", "Otro proveedor");
    const tooOld = entry(6, 38000, "2026-07-01T10:00:00Z");
    const withoutCost = entry(7, null, "2026-11-01T10:00:00Z");
    expect(priceVarianceProperties(entry(4, 60000), BEEF, ENVIGADO, 2, [history[0], history[1], otherSupplier, tooOld, withoutCost])).toBeNull();
  });

  it("no cuenta entradas posteriores ni la propia", () => {
    const later = entry(8, 38000, "2026-11-20T10:00:00Z");
    expect(priceVarianceProperties(entry(4, 60000), BEEF, ENVIGADO, 2, [history[0], history[1], later, entry(4, 60000)])).toBeNull();
  });
});

describe("salidas", () => {
  it("un consumo emite outbound_order_created, sin reason", () => {
    expect(outboundOrderEvent(exit(13318, 4.2), BEEF, ENVIGADO, 31.6)).toEqual({
      eventType: "outbound_order_created",
      properties: { order_id: 13318, ...productFields(BEEF, ENVIGADO), quantity: 4.2, stock_after: 31.6 },
    });
  });

  it("una merma emite stock_waste_registered con su motivo, y no outbound_order_created", () => {
    const event = outboundOrderEvent(exit(13319, 1.2, "waste"), BEEF, ENVIGADO, 30.4);
    expect(event.eventType).toBe("stock_waste_registered");
    expect(event.properties).toMatchObject({ order_id: 13319, reason: "expired", stock_after: 30.4 });
  });

  it("la merma lleva su unit_cost; el consumo nunca", () => {
    expect(outboundOrderEvent(exit(13319, 1.2, "waste"), BEEF, ENVIGADO, 30.4, 38350).properties).toMatchObject({ unit_cost: 38350 });
    expect(outboundOrderEvent(exit(13318, 4.2), BEEF, ENVIGADO, 31.6, 38350).properties).not.toHaveProperty("unit_cost");
  });
});

describe("unit_cost de una merma", () => {
  const waste = exit(13319, 1.2, "waste");

  it("es la media de las entradas del producto ponderada por su cantidad", () => {
    // (10 × 36 000 + 30 × 39 000) / 40 = 38 250
    const history = [{ ...entry(1, 36000), quantity: 10 }, { ...entry(2, 39000), quantity: 30 }];
    expect(wasteUnitCost(waste, history)).toBe(38250);
  });

  it("ignora las entradas sin coste, las de otro producto y las posteriores a la merma", () => {
    const history = [
      entry(1, 38000, "2026-11-18T10:00:00Z"),
      entry(2, null, "2026-11-18T11:00:00Z"),
      { ...entry(3, 99000, "2026-11-18T12:00:00Z"), ingredient_id: 13 },
      entry(4, 99000, "2026-11-19T10:00:01Z"),
    ];
    expect(wasteUnitCost(waste, history)).toBe(38000);
  });

  it("redondea a 2 decimales", () => {
    const history = [{ ...entry(1, 10), quantity: 1 }, { ...entry(2, 11), quantity: 2 }];
    expect(wasteUnitCost(waste, history)).toBe(10.67);
  });

  it("es undefined si ninguna entrada del producto tiene coste", () => {
    expect(wasteUnitCost(waste, [])).toBeUndefined();
    expect(wasteUnitCost(waste, [entry(1, null)])).toBeUndefined();
  });
});

describe("stock_threshold_triggered", () => {
  it("se emite al cruzar el umbral de la unidad (40 kg): antes ≥ 40 y después < 40", () => {
    expect(thresholdProperties(exit(20, 5), BEEF, ENVIGADO, 38)).toEqual({
      ...productFields(BEEF, ENVIGADO),
      quantity: 38,
      threshold_quantity: 40,
      trigger_order_id: 20,
    });
  });

  it("también si la salida empieza justo en el umbral", () => {
    expect(thresholdProperties(exit(20, 0.3), BEEF, ENVIGADO, 39.7)).not.toBeNull();
  });

  it("no se repite si el stock ya estaba por debajo", () => {
    expect(thresholdProperties(exit(21, 2), BEEF, ENVIGADO, 30)).toBeNull();
  });

  it("no se emite si sigue por encima", () => {
    expect(thresholdProperties(exit(22, 2), BEEF, ENVIGADO, 45)).toBeNull();
  });
});

describe("apiRouteTemplate", () => {
  it.each([
    ["/inventory/products/12", "/api/v1/inventory/products/{ingredient_id}"],
    ["/inventory/products?country=CO", "/api/v1/inventory/products"],
    ["/inventory/orders/outbound", "/api/v1/inventory/orders/outbound"],
    ["/suppliers/9/rate", "/api/v1/suppliers/{supplier_id}/rate"],
    ["/incidents/10098/status", "/api/v1/incidents/{incident_id}/status"],
    ["/profiles/d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2", "/api/v1/profiles/{user_id}"],
    ["/telemetry/report?start_date=2026-11-14", "/telemetry/report"],
    // El id de una tarea nunca sale en un evento (#DEV-55).
    ["/tasks/8c88f901-da18-4fe1-ae9a-61e335c0be19", "/tasks/{task_id}"],
    ["/reporting/weekly-location-performance?week_start=2026-11-16", "/reporting/weekly-location-performance"],
    ["/reporting/pipeline-runs/latest", "/reporting/pipeline-runs/latest"],
  ])("%s → %s", (path, template) => {
    expect(apiRouteTemplate(path)).toBe(template);
  });
});
