import { ApiError } from "@/lib/api-client";
import { formErrorsFromApi, type FormApiErrors } from "@/lib/auth/api-errors";
import type { ExitReason, IngredientEntryInput, IngredientExitInput, WasteReason } from "@/types/inventory";

// Validación en el cliente de los formularios de entrada y salida, antes de enviar. La API vuelve a
// validar todo (422 con el campo) y aplica la regla del stock (400 `insufficient_stock`).

// Mismos límites que la API (services/brasaland-api, inventory/schemas.py).
export const MAX_SUPPLIER_NAME_LENGTH = 120;
export const MIN_LOCATION_ID = 1;
export const MAX_LOCATION_ID = 14;

// Valores tal como los da el formulario: los selects y los campos de texto devuelven texto.
export interface EntryFormValues {
  ingredient_id: string;
  quantity: string;
  supplier_name: string;
  unit_cost: string;
  location_id: string;
}

export interface ExitFormValues {
  ingredient_id: string;
  quantity: string;
  reason: ExitReason | "";
  // Solo se usa cuando `reason` es "waste".
  waste_reason: WasteReason | "";
  location_id: string;
}

export type EntryFormField = keyof EntryFormValues;
export type ExitFormField = keyof ExitFormValues;
export type EntryFormErrors = Partial<Record<EntryFormField, string>>;
export type ExitFormErrors = Partial<Record<ExitFormField, string>>;

// Nombres de campo de la API: así formErrorsFromApi coloca cada `details` junto a su campo.
export const ENTRY_FORM_FIELDS: readonly EntryFormField[] = ["ingredient_id", "quantity", "supplier_name", "unit_cost", "location_id"];
export const EXIT_FORM_FIELDS: readonly ExitFormField[] = ["ingredient_id", "quantity", "reason", "waste_reason", "location_id"];

export const EMPTY_ENTRY_FORM: EntryFormValues = { ingredient_id: "", quantity: "", supplier_name: "", unit_cost: "", location_id: "" };
export const EMPTY_EXIT_FORM: ExitFormValues = { ingredient_id: "", quantity: "", reason: "", waste_reason: "", location_id: "" };

// `?ingredient_id=` de los enlaces de la lista de ingredientes: el id en texto si es un entero
// positivo, o "" si falta o no es válido (se repite, es "abc", "0", "-3" o "1.5").
export function presetIngredientId(raw: string | string[] | undefined): string {
  if (typeof raw !== "string" || !/^[1-9]\d*$/.test(raw.trim())) return "";
  return raw.trim();
}

// Cantidad escrita por el usuario. Admite coma o punto decimal ("12,5" o "12.5"). Devuelve null si
// no es un número.
export function parseQuantity(text: string): number | null {
  const normalized = text.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$|^\.\d+$/.test(normalized)) return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

function quantityError(text: string): string | undefined {
  if (!text.trim()) return "Escribe la cantidad.";
  const value = parseQuantity(text);
  if (value === null) return "Escribe un número, por ejemplo 12 o 12.5.";
  if (value <= 0) return "La cantidad debe ser mayor que 0.";
  return undefined;
}

// Coste unitario (brecha B5): número mayor que 0, en la moneda del país del ingrediente.
function unitCostError(text: string): string | undefined {
  if (!text.trim()) return "Escribe el coste por unidad.";
  const value = parseQuantity(text);
  if (value === null) return "Escribe un número, por ejemplo 38500 o 6.8.";
  if (value <= 0) return "El coste debe ser mayor que 0.";
  return undefined;
}

function locationError(text: string): string | undefined {
  const id = Number(text);
  if (!text || !Number.isInteger(id) || id < MIN_LOCATION_ID || id > MAX_LOCATION_ID) return "Elige el local.";
  return undefined;
}

export function validateEntryForm(values: EntryFormValues): EntryFormErrors {
  const errors: EntryFormErrors = {};
  const supplier = values.supplier_name.trim();
  if (!values.ingredient_id) errors.ingredient_id = "Elige el ingrediente.";
  const quantity = quantityError(values.quantity);
  if (quantity) errors.quantity = quantity;
  if (!supplier) errors.supplier_name = "Elige el proveedor.";
  else if (supplier.length > MAX_SUPPLIER_NAME_LENGTH) {
    errors.supplier_name = `El proveedor no puede superar ${MAX_SUPPLIER_NAME_LENGTH} caracteres.`;
  }
  const unitCost = unitCostError(values.unit_cost);
  if (unitCost) errors.unit_cost = unitCost;
  const location = locationError(values.location_id);
  if (location) errors.location_id = location;
  return errors;
}

export function validateExitForm(values: ExitFormValues): ExitFormErrors {
  const errors: ExitFormErrors = {};
  if (!values.ingredient_id) errors.ingredient_id = "Elige el ingrediente.";
  const quantity = quantityError(values.quantity);
  if (quantity) errors.quantity = quantity;
  if (!values.reason) errors.reason = "Elige el motivo: consumo o merma.";
  else if (values.reason === "waste" && !values.waste_reason) errors.waste_reason = "Elige el motivo de la merma.";
  const location = locationError(values.location_id);
  if (location) errors.location_id = location;
  return errors;
}

// Advertencia de la salida: la cantidad escrita supera el stock mostrado. Es solo una ayuda: la API
// aplica la regla real con el stock del momento. Sin cantidad válida o sin stock cargado, no avisa.
export function exceedsStock(quantityText: string, stock: number | null): boolean {
  const quantity = parseQuantity(quantityText);
  return quantity !== null && stock !== null && quantity > stock;
}

// Errores de POST /inventory/orders/outbound repartidos por campo. El 400 `insufficient_stock` no
// trae `details`, pero se refiere a la cantidad: su mensaje ("Stock insuficiente para el ingrediente
// 'Yuca'. Disponible: 0, solicitado: 3.") va junto a ese campo; el aviso general remite a él, como
// hace formErrorsFromApi con los errores por campo.
export function exitErrorsFromApi(err: unknown): FormApiErrors<ExitFormField> {
  if (err instanceof ApiError && err.code === "insufficient_stock") {
    return { fields: { quantity: err.message }, message: "Revisa los campos marcados." };
  }
  return formErrorsFromApi(err, EXIT_FORM_FIELDS, "No se pudo registrar la salida.");
}

// Cuerpos de la API. Solo se llaman con un formulario sin errores.
export function toEntryInput(values: EntryFormValues): IngredientEntryInput {
  return {
    ingredient_id: Number(values.ingredient_id),
    quantity: parseQuantity(values.quantity) as number,
    supplier_name: values.supplier_name.trim(),
    unit_cost: parseQuantity(values.unit_cost) as number,
    location_id: Number(values.location_id),
  };
}

export function toExitInput(values: ExitFormValues): IngredientExitInput {
  const reason = values.reason as ExitReason;
  return {
    ingredient_id: Number(values.ingredient_id),
    quantity: parseQuantity(values.quantity) as number,
    reason,
    // Solo en las mermas: la API rechaza un consumo con motivo de merma.
    ...(reason === "waste" ? { waste_reason: values.waste_reason as WasteReason } : {}),
    location_id: Number(values.location_id),
  };
}
