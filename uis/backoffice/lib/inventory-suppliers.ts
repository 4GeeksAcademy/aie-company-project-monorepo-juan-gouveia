import type { Category, Country } from "@/types/inventory";
import type { Category as SupplierCategory, Country as SupplierCountry, Supplier, SupplierFilters } from "@/types/supplier";

// Proveedores que pueden entregar un ingrediente: los del directorio (dominio `suppliers`) del mismo
// país y de la categoría equivalente, y solo los activos. Los dos briefings nombran sus valores de
// forma distinta, así que esta es la única tabla de equivalencias entre ambos: si uno de los dos
// cambia sus categorías o países, hay que actualizarla aquí.

// Las 6 categorías de ingrediente tienen equivalente; `lacteos` y `carbon_y_combustible` del
// directorio no corresponden a ningún ingrediente.
export const SUPPLIER_CATEGORY_BY_INGREDIENT: Record<Category, SupplierCategory> = {
  meat: "carne",
  produce: "verduras_y_hortalizas",
  sauce: "salsas_y_condimentos",
  beverage: "bebidas",
  packaging: "packaging",
  cleaning: "productos_limpieza",
};

export const SUPPLIER_COUNTRY_BY_INGREDIENT: Record<Country, SupplierCountry> = {
  CO: "Colombia",
  US: "USA",
};

// Filtros de GET /suppliers para un ingrediente.
export function supplierFiltersFor(ingredient: { category: Category; country: Country }): SupplierFilters {
  return {
    country: SUPPLIER_COUNTRY_BY_INGREDIENT[ingredient.country],
    category: SUPPLIER_CATEGORY_BY_INGREDIENT[ingredient.category],
  };
}

// La API no filtra por estado: los suspendidos se quitan aquí. Orden alfabético para encontrarlos
// rápido en el desplegable.
export function activeSupplierNames(suppliers: Supplier[]): string[] {
  return suppliers
    .filter((supplier) => supplier.status === "active")
    .map((supplier) => supplier.name)
    .sort((a, b) => a.localeCompare(b, "es"));
}
