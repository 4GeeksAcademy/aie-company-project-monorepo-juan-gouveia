import type { ApiError } from "@/lib/api-client";
import { track } from "@/lib/telemetry";
import { withRequestId } from "@/lib/telemetry/request-context";
import { apiRouteTemplate } from "@/lib/telemetry/routes";
import { currentUserRole } from "@/lib/telemetry/session";

// Eventos que nacen de un error de la API. Los emite apiFetch (lib/api-client.ts) con cada error, en
// un solo sitio para todo el backoffice: ningún componente los instrumenta por su cuenta. Cada evento
// lleva el `requestId` de la llamada que falló. Nunca lanza: un fallo de la telemetría no puede
// cambiar el error que ve el usuario.

// Campos de stock que la API no admite en el cuerpo de una orden o de un producto.
const STOCK_FIELDS = new Set(["current_stock", "stock"]);

// Métrica obligatoria `direct_stock_edit_rejected` (plan, §3.2): la API rechaza un intento de cambiar
// el stock fuera de una orden. Dos formas:
// - 405 a un PUT, PATCH o DELETE sobre una ruta del inventario (la acción "Ajustar stock");
// - 422 a un POST del inventario cuyo cuerpo trae `current_stock` o `stock` (error `extra_forbidden`).
function directStockEditRejection(method: string, path: string, error: ApiError) {
  if (!path.startsWith("/inventory/")) return null;
  if (error.status === 405 && ["PUT", "PATCH", "DELETE"].includes(method)) {
    return { rejection_type: "method_not_allowed", status_code: 405 } as const;
  }
  if (error.status === 422 && method === "POST" && error.details.some((detail) => STOCK_FIELDS.has(detail.field))) {
    return { rejection_type: "forbidden_field", status_code: 422 } as const;
  }
  return null;
}

// /inventory/products/12 → 12. Solo una edición sobre un producto identifica el producto.
function productIdFromPath(path: string): number | undefined {
  const match = /^\/inventory\/products\/(\d+)/.exec(path);
  return match ? Number(match[1]) : undefined;
}

export function reportApiError(method: string, path: string, error: ApiError): void {
  try {
    withRequestId(error.requestId, () => {
      const rejection = directStockEditRejection(method, path, error);
      if (rejection) {
        track("direct_stock_edit_rejected", {
          // El local no se conoce: las cuentas no tienen local asignado (brecha B10).
          product_id: productIdFromPath(path),
          method,
          route: apiRouteTemplate(path),
          ...rejection,
          user_role: currentUserRole() ?? undefined,
        });
      }
    });
  } catch {
    // La telemetría nunca interfiere con el error de la API.
  }
}
