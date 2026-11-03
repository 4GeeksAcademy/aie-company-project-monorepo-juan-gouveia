import type { Category, Country, SupplierStatus } from "@/types/supplier";

// Validación en el cliente, antes de enviar. La API vuelve a validar todo (422).

export interface SupplierFormValues {
  name: string;
  country: Country | "";
  categories: Category[];
  rate_per_unit: string;
  status: SupplierStatus;
  contact_email: string;
  notes: string;
}

export type SupplierFormErrors = Partial<Record<keyof SupplierFormValues, string>>;

// Comprobación básica de formato; la API usa una validación de email completa.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Tarifa: número mayor que 0. Devuelve el mensaje de error o null.
export function rateError(value: string): string | null {
  const text = value.trim();
  if (!text) return "Campo requerido";
  const rate = Number(text);
  if (!Number.isFinite(rate)) return "Ingresa un número válido";
  if (rate <= 0) return "La tarifa debe ser mayor que 0";
  return null;
}

export function validateSupplierForm(values: SupplierFormValues): SupplierFormErrors {
  const errors: SupplierFormErrors = {};
  if (!values.name.trim()) errors.name = "Campo requerido";
  if (!values.country) errors.country = "Elige un país";
  if (values.categories.length === 0) errors.categories = "Elige al menos una categoría";
  const rate = rateError(values.rate_per_unit);
  if (rate) errors.rate_per_unit = rate;
  const email = values.contact_email.trim();
  if (email && !EMAIL_PATTERN.test(email)) errors.contact_email = "El email no tiene un formato válido";
  return errors;
}
