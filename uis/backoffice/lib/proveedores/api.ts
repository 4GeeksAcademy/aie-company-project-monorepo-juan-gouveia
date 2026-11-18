import { apiJson, jsonBody } from "@/lib/api-client";
import type { Supplier, SupplierFilters, SupplierInput, SupplierStatus } from "@/types/supplier";

// Rutas del intermediario, que las reenvía a /api/v1/suppliers.
const SUPPLIERS_PATH = "/suppliers";

export function listSuppliers(filters: SupplierFilters): Promise<Supplier[]> {
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return apiJson(`${SUPPLIERS_PATH}${query ? `?${query}` : ""}`, {
    fallback: "no se pudieron cargar los proveedores",
  });
}

export function createSupplier(input: SupplierInput): Promise<Supplier> {
  return apiJson(SUPPLIERS_PATH, {
    fallback: "no se pudo registrar el proveedor",
    ...jsonBody("POST", input),
  });
}

export function updateRate(id: number, ratePerUnit: number): Promise<Supplier> {
  return apiJson(`${SUPPLIERS_PATH}/${id}/rate`, {
    fallback: "no se pudo actualizar la tarifa",
    ...jsonBody("PATCH", { rate_per_unit: ratePerUnit }),
  });
}

export function updateStatus(id: number, status: SupplierStatus): Promise<Supplier> {
  return apiJson(`${SUPPLIERS_PATH}/${id}/status`, {
    fallback: "no se pudo cambiar el estado",
    ...jsonBody("PATCH", { status }),
  });
}
