import { TELEMETRY_CATALOG, type CatalogEntry } from "@/lib/telemetry/catalog";

// Validación antes de emitir (plan, §7.1, y decisión C5): el tipo debe existir en el catálogo del
// backoffice, deben estar todas sus propiedades obligatorias y ninguna clave puede quedar fuera de su
// allowlist. Un evento que no cumple no se emite; nunca se recorta en silencio.
//
// Las propiedades opcionales sin valor se omiten (§7.1, regla 2): una clave con `undefined` no cuenta.

export type ValidationResult = { ok: true; entry: CatalogEntry } | { ok: false; reason: string };

export function validateEvent(eventType: string, properties: Record<string, unknown>): ValidationResult {
  const entry = TELEMETRY_CATALOG[eventType];
  if (!entry) return { ok: false, reason: `"${eventType}" no es un evento del backoffice en event-schemas.json` };

  const keys = Object.keys(properties).filter((key) => properties[key] !== undefined);
  const outside = keys.filter((key) => !entry.allowed.includes(key));
  if (outside.length > 0) return { ok: false, reason: `claves fuera del allowlist de ${eventType}: ${outside.join(", ")}` };

  const missing = entry.required.filter((key) => properties[key] === undefined || properties[key] === null);
  if (missing.length > 0) return { ok: false, reason: `faltan propiedades obligatorias de ${eventType}: ${missing.join(", ")}` };

  return { ok: true, entry };
}

// Copia de las propiedades sin las claves `undefined` (las opcionales sin valor no se envían).
export function compactProperties(properties: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(properties).filter(([, value]) => value !== undefined));
}
