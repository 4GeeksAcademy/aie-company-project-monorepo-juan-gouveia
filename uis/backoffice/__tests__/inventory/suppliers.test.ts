import { activeSupplierNames, supplierFiltersFor } from "@/lib/inventory-suppliers";
import type { Category } from "@/types/inventory";
import type { Supplier } from "@/types/supplier";

function supplier(name: string, status: Supplier["status"]): Supplier {
  return {
    id: 1,
    name,
    country: "Colombia",
    categories: ["carne"],
    rate_per_unit: 1,
    currency: "COP",
    status,
    contact_email: null,
    notes: null,
    updated_at: "2026-11-01T00:00:00Z",
  };
}

describe("supplierFiltersFor", () => {
  it.each<[Category, string]>([
    ["meat", "carne"],
    ["produce", "verduras_y_hortalizas"],
    ["sauce", "salsas_y_condimentos"],
    ["beverage", "bebidas"],
    ["packaging", "packaging"],
    ["cleaning", "productos_limpieza"],
  ])("la categoría %p filtra por %p", (category, expected) => {
    expect(supplierFiltersFor({ category, country: "CO" }).category).toBe(expected);
  });

  it("traduce el país del ingrediente al del directorio", () => {
    expect(supplierFiltersFor({ category: "meat", country: "CO" }).country).toBe("Colombia");
    expect(supplierFiltersFor({ category: "meat", country: "US" }).country).toBe("USA");
  });
});

describe("activeSupplierNames", () => {
  it("deja solo los activos, en orden alfabético", () => {
    const names = activeSupplierNames([
      supplier("Frigorífico Antioqueño", "active"),
      supplier("Bebidas Andinas", "suspended"),
      supplier("Carnes del Valle S.A.S.", "active"),
    ]);
    expect(names).toEqual(["Carnes del Valle S.A.S.", "Frigorífico Antioqueño"]);
  });

  it("devuelve una lista vacía si todos están suspendidos", () => {
    expect(activeSupplierNames([supplier("Limpiahogar Profesional", "suspended")])).toEqual([]);
  });
});
