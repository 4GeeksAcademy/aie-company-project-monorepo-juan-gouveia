import type {
  ApiFieldError,
  Supplier,
  SupplierApiErrorBody,
  SupplierFilters,
  SupplierInput,
  SupplierStatus,
} from "@/types/supplier";

// Rutas del intermediario (app/api/[...path]/route.ts), que las reenvía a /api/v1/suppliers.
const SUPPLIERS_URL = "/api/suppliers";

// Error de la API con su mensaje en español y, en los 422, el detalle por campo.
export class SupplierApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly details: ApiFieldError[] = []
  ) {
    super(message);
    this.name = "SupplierApiError";
  }
}

async function toApiError(res: Response, fallback: string): Promise<SupplierApiError> {
  try {
    const body: SupplierApiErrorBody = await res.json();
    if (body.error?.message) {
      return new SupplierApiError(body.error.message, res.status, body.error.details);
    }
  } catch {
    // El cuerpo no es JSON: se usa el mensaje genérico.
  }
  return new SupplierApiError(`Error ${res.status}: ${fallback}`, res.status);
}

async function request<T>(url: string, fallback: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store", ...init });
  } catch {
    throw new SupplierApiError("No se pudo conectar con el backoffice. Revisa tu conexión.", 0);
  }
  if (!res.ok) throw await toApiError(res, fallback);
  return res.json();
}

function jsonBody(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export function listSuppliers(filters: SupplierFilters): Promise<Supplier[]> {
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return request(`${SUPPLIERS_URL}${query ? `?${query}` : ""}`, "no se pudieron cargar los proveedores");
}

export function createSupplier(input: SupplierInput): Promise<Supplier> {
  return request(SUPPLIERS_URL, "no se pudo registrar el proveedor", jsonBody("POST", input));
}

export function updateRate(id: number, ratePerUnit: number): Promise<Supplier> {
  return request(
    `${SUPPLIERS_URL}/${id}/rate`,
    "no se pudo actualizar la tarifa",
    jsonBody("PATCH", { rate_per_unit: ratePerUnit })
  );
}

export function updateStatus(id: number, status: SupplierStatus): Promise<Supplier> {
  return request(
    `${SUPPLIERS_URL}/${id}/status`,
    "no se pudo cambiar el estado",
    jsonBody("PATCH", { status })
  );
}
