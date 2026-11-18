import type { Country, ExitReason } from "@/types/inventory";

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
  location_id: "Local",
  reason: "Motivo",
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

// Briefing, tabla de Ingredient: "CO" (Colombia) o "US" (Estados Unidos).
export const COUNTRY_DESCRIPTIONS: Record<Country, string> = {
  CO: "Colombia",
  US: "Estados Unidos",
};

// Locales de Brasaland (decisión F5). El briefing solo dice que van del 1 al 14 y que sus datos se
// gestionan por separado, así que no se inventan nombres. Es la única lista de locales del
// inventario: para mostrar los nombres reales basta con cambiar aquí las etiquetas (o construir la
// lista desde el futuro dominio `locations`); los formularios y la API siempre usan el número.
export const LOCATIONS: { id: number; label: string }[] = Array.from({ length: 14 }, (_, index) => ({
  id: index + 1,
  label: `Local ${index + 1}`,
}));

// Opciones para LabeledSelect: el valor es el id en texto ("1"…"14").
export const LOCATION_OPTIONS: Record<string, string> = Object.fromEntries(
  LOCATIONS.map((location) => [String(location.id), location.label])
);

export function locationLabel(id: number): string {
  return LOCATIONS.find((location) => location.id === id)?.label ?? `Local ${id}`;
}

// Número sin ceros sobrantes y con punto decimal, como el mensaje de stock insuficiente de la API
// ("Disponible: 40.5") y las métricas del backoffice: 52 → "52", 12.5 → "12.5", 0.1 + 0.2 → "0.3".
export function formatAmount(value: number): string {
  return value.toFixed(3).replace(/\.?0+$/, "");
}

// Cantidad con su unidad: 52, "kg" → "52 kg".
export function formatQuantity(value: number, unit: string): string {
  return `${formatAmount(value)} ${unit}`;
}
