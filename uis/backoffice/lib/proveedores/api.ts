import { apiJson, apiJsonWithRequestId, jsonBody } from "@/lib/api-client";
import { track } from "@/lib/telemetry";
import {
  supplierCreatedProperties,
  supplierRateUpdatedProperties,
  supplierStatusChangedProperties,
} from "@/lib/telemetry/business-events";
import { withRequestId } from "@/lib/telemetry/request-context";
import type { Supplier, SupplierFilters, SupplierInput, SupplierStatus } from "@/types/supplier";

// Rutas del intermediario, que las reenvía a /api/v1/suppliers.
//
// Telemetría (plan, §5.6): las escrituras emiten su evento al recibir la respuesta de la API, con el
// `requestId` de esa llamada. Para la tarifa y el estado, quien llama pasa el proveedor tal como
// estaba (`previous`): la respuesta solo trae el valor nuevo.
const SUPPLIERS_PATH = "/suppliers";

function emit(requestId: string, eventType: string, properties: Record<string, unknown> | null) {
  try {
    if (properties) withRequestId(requestId, () => track(eventType, properties));
  } catch {
    // La telemetría no interfiere con el directorio.
  }
}

export function listSuppliers(filters: SupplierFilters): Promise<Supplier[]> {
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return apiJson(`${SUPPLIERS_PATH}${query ? `?${query}` : ""}`, {
    fallback: "no se pudieron cargar los proveedores",
  });
}

// Telemetría: `supplier_created`.
export async function createSupplier(input: SupplierInput): Promise<Supplier> {
  const { data, requestId } = await apiJsonWithRequestId<Supplier>(SUPPLIERS_PATH, {
    fallback: "no se pudo registrar el proveedor",
    ...jsonBody("POST", input),
  });
  emit(requestId, "supplier_created", supplierCreatedProperties(data));
  return data;
}

// Telemetría: `supplier_rate_updated`, con la tarifa anterior de `previous`.
export async function updateRate(id: number, ratePerUnit: number, previous?: Supplier): Promise<Supplier> {
  const { data, requestId } = await apiJsonWithRequestId<Supplier>(`${SUPPLIERS_PATH}/${id}/rate`, {
    fallback: "no se pudo actualizar la tarifa",
    ...jsonBody("PATCH", { rate_per_unit: ratePerUnit }),
  });
  if (previous) emit(requestId, "supplier_rate_updated", supplierRateUpdatedProperties(previous, data));
  return data;
}

// Telemetría: `supplier_status_changed`, con el estado anterior de `previous`.
export async function updateStatus(id: number, status: SupplierStatus, previous?: Supplier): Promise<Supplier> {
  const { data, requestId } = await apiJsonWithRequestId<Supplier>(`${SUPPLIERS_PATH}/${id}/status`, {
    fallback: "no se pudo cambiar el estado",
    ...jsonBody("PATCH", { status }),
  });
  if (previous) emit(requestId, "supplier_status_changed", supplierStatusChangedProperties(previous, data));
  return data;
}
