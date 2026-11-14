import type { Unit } from "@/types/inventory";

// Niveles de stock del inventario (decisión F4). El briefing y la API no definen un mínimo por
// ingrediente, así que el backoffice usa estos umbrales propios:
//
// - "out"     — Sin stock: current_stock = 0. No se puede registrar ninguna salida.
// - "low"     — Stock bajo: mayor que 0 pero por debajo del umbral de su unidad.
// - "healthy" — Stock saludable: igual o por encima del umbral.
//
// El umbral depende de la unidad, porque las cantidades no son comparables entre sí: 20 kg de carne
// no equivalen a 20 cajas para llevar.
//   kg     < 40  → bajo (carnes y verduras: unos pocos días de consumo de un local)
//   litro  < 25  → bajo (salsas y bebidas)
//   unidad < 100 → bajo (envases: se gastan por cientos)
// Son valores iniciales para que Operaciones los ajuste: cambiarlos aquí cambia toda la herramienta.
export const LOW_STOCK_THRESHOLDS: Record<Unit, number> = {
  kg: 40,
  litro: 25,
  unidad: 100,
};

export type StockLevel = "out" | "low" | "healthy";

export function stockLevel(stock: number, unit: Unit): StockLevel {
  if (stock <= 0) return "out";
  return stock < LOW_STOCK_THRESHOLDS[unit] ? "low" : "healthy";
}

// Texto de cada nivel: el color nunca es la única señal.
export const STOCK_LEVEL_LABELS: Record<StockLevel, string> = {
  out: "Sin stock",
  low: "Stock bajo",
  healthy: "Stock saludable",
};
