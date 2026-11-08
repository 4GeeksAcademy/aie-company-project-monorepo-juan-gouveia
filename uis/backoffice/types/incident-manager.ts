// Gestor de incidencias centralizado (API de Brasaland, /incidents). Los valores son exactamente
// los del briefing "Gestor de Incidencias Centralizado".

export type IncidentCategory =
  | "equipment_failure"
  | "supply_issue"
  | "customer_complaint"
  | "staff_issue"
  | "facility_issue"
  | "pos_system"
  | "delivery_issue"
  | "other";

export type IncidentStatus = "open" | "in_progress" | "resolved" | "discarded";

export type IncidentOrigin = "customer" | "branch" | "internal";

export type Branch =
  | "central"
  | "medellin_centro"
  | "medellin_laureles"
  | "medellin_envigado"
  | "medellin_bello"
  | "medellin_itagui"
  | "bogota_chapinero"
  | "bogota_usaquen"
  | "cali_granada"
  | "barranquilla_norte"
  | "miami_doral"
  | "miami_hialeah"
  | "miami_kendall"
  | "orlando_international"
  | "fort_lauderdale";

export interface Incident {
  id: number;
  title: string;
  description: string;
  category: IncidentCategory;
  status: IncidentStatus;
  origin: IncidentOrigin;
  branch: Branch;
  created_at: string;
  updated_at: string;
}

// Filtros del listado (GET /incidents). "" = sin filtro.
export interface IncidentFilters {
  status: IncidentStatus | "";
  origin: IncidentOrigin | "";
  branch: Branch | "";
}

// Respuesta de GET /incidents/summary: cada desglose trae todos los valores, también en 0.
export interface IncidentSummary {
  total: number;
  by_status: Record<IncidentStatus, number>;
  by_category: Record<IncidentCategory, number>;
  by_origin: Record<IncidentOrigin, number>;
  by_branch: Record<Branch, number>;
}

// Cuerpo de POST /incidents. `status` se omite: toda incidencia nueva empieza en `open`.
export type IncidentCreateInput = Pick<Incident, "title" | "description" | "category" | "origin" | "branch">;
