import type { Category, Country, Currency, SupplierStatus } from "@/types/supplier";

// Se muestran los valores exactos del briefing; el texto de cada opción es el propio código.
export const COUNTRY_OPTIONS: Record<Country, string> = {
  Colombia: "Colombia",
  USA: "USA",
};

export const CATEGORY_OPTIONS: Record<Category, string> = {
  carne: "carne",
  verduras_y_hortalizas: "verduras_y_hortalizas",
  salsas_y_condimentos: "salsas_y_condimentos",
  bebidas: "bebidas",
  packaging: "packaging",
  productos_limpieza: "productos_limpieza",
  lacteos: "lacteos",
  carbon_y_combustible: "carbon_y_combustible",
};

export const CATEGORIES = Object.keys(CATEGORY_OPTIONS) as Category[];

export const STATUS_OPTIONS: Record<SupplierStatus, string> = {
  active: "active",
  suspended: "suspended",
};

// Restricción del briefing: Colombia factura en COP y USA en USD. La API también lo valida.
export const CURRENCY_BY_COUNTRY: Record<Country, Currency> = {
  Colombia: "COP",
  USA: "USD",
};

// Punto decimal, como el resto del backoffice. COP sin decimales salvo que los tenga; USD con 2.
// Ej.: "28,500 COP", "6.80 USD".
export function formatRate(rate: number, currency: Currency): string {
  const digits = currency === "USD" ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : { maximumFractionDigits: 2 };
  return `${rate.toLocaleString("en-US", digits)} ${currency}`;
}
