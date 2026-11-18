// Proveedor de la API de Brasaland (services/brasaland-api, dominio suppliers).
// Los valores son exactamente los del briefing del directorio de proveedores.

export type Country = "Colombia" | "USA";

export type Currency = "COP" | "USD";

export type SupplierStatus = "active" | "suspended";

export type Category =
  | "carne"
  | "verduras_y_hortalizas"
  | "salsas_y_condimentos"
  | "bebidas"
  | "packaging"
  | "productos_limpieza"
  | "lacteos"
  | "carbon_y_combustible";

export interface Supplier {
  id: number;
  name: string;
  country: Country;
  categories: Category[];
  rate_per_unit: number;
  currency: Currency;
  status: SupplierStatus;
  contact_email: string | null;
  notes: string | null;
  // Timestamp (UTC) de la última actualización de tarifa; lo genera la API.
  updated_at: string;
}

// Cuerpo de POST /suppliers: sin `id` ni `updated_at`, que genera el sistema.
export type SupplierInput = Omit<Supplier, "id" | "updated_at">;

export interface SupplierFilters {
  country: Country | "";
  category: Category | "";
}
