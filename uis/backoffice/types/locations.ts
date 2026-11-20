import type { Country } from "@/types/inventory";

// Un local del catálogo de la API (GET /api/v1/locations). `id` es el `location_id` de las órdenes.
export interface Location {
  id: number;
  // Código de la sede del briefing del gestor de incidencias, p. ej. "medellin_centro".
  code: string;
  // Nombre para mostrar, p. ej. "Medellín Centro".
  name: string;
  city: string;
  country: Country;
  currency: "COP" | "USD";
}
