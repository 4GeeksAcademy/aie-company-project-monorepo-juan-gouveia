import type { Country, ExitReason, WasteReason } from "@/types/inventory";

// Vocabulario del inventario (decisión F3): los términos del briefing del Hito 5 en español, nunca
// los genéricos de la consigna ("producto"). Los valores se muestran con su código exacto; solo se
// acompañan de la descripción que da el propio briefing.

// Etiquetas de los campos del briefing. `user_uuid` se rotula "Usuario" como el resto de columnas
// (cambio del 2026-11-16 sobre F3); el valor se sigue mostrando completo y la página nombra el campo.
export const FIELD_LABELS = {
  name: "Nombre",
  sku: "SKU",
  unit: "Unidad",
  category: "Categoría",
  country: "País",
  current_stock: "Stock actual",
  quantity: "Cantidad",
  supplier_name: "Proveedor",
  unit_cost: "Coste unitario",
  location_id: "Local",
  reason: "Motivo",
  waste_reason: "Motivo de la merma",
  created_at: "Fecha",
  user_uuid: "Usuario",
} as const;

// Briefing, tabla de IngredientExit: "consumption" (consumo) o "waste" (merma).
export const REASON_DESCRIPTIONS: Record<ExitReason, string> = {
  consumption: "consumo",
  waste: "merma",
};

// Opciones del desplegable de motivo: código exacto con su descripción.
export const REASON_OPTIONS: Record<ExitReason, string> = {
  consumption: "consumption (consumo)",
  waste: "waste (merma)",
};

// Motivos de merma del briefing de telemetría: "producto vencido, error de cocina, o pérdida/robo".
export const WASTE_REASON_DESCRIPTIONS: Record<WasteReason, string> = {
  expired: "producto vencido",
  kitchen_error: "error de cocina",
  theft_suspected: "pérdida o robo",
};

// Opciones del desplegable del motivo de la merma: código exacto con su descripción.
export const WASTE_REASON_OPTIONS: Record<WasteReason, string> = {
  expired: "expired (producto vencido)",
  kitchen_error: "kitchen_error (error de cocina)",
  theft_suspected: "theft_suspected (pérdida o robo)",
};

// Moneda de cada país: los costes unitarios van en la moneda del local, sin conversión.
export const COUNTRY_CURRENCY: Record<Country, "COP" | "USD"> = {
  CO: "COP",
  US: "USD",
};

// Briefing, tabla de Ingredient: "CO" (Colombia) o "US" (Estados Unidos).
export const COUNTRY_DESCRIPTIONS: Record<Country, string> = {
  CO: "Colombia",
  US: "Estados Unidos",
};

// Los locales (nombres y país) salen del catálogo de la API: lib/locations.ts. Los formularios y la
// API siguen usando el número (1–14).

// Número sin ceros sobrantes y con punto decimal, como el mensaje de stock insuficiente de la API
// ("Disponible: 40.5") y las métricas del backoffice: 52 → "52", 12.5 → "12.5", 0.1 + 0.2 → "0.3".
export function formatAmount(value: number): string {
  return value.toFixed(3).replace(/\.?0+$/, "");
}

// Cantidad con su unidad: 52, "kg" → "52 kg".
export function formatQuantity(value: number, unit: string): string {
  return `${formatAmount(value)} ${unit}`;
}
