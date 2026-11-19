import type { Incident, IncidentListItem } from "@/types/incident-manager";
import type { IncidentAnalysis } from "@/types/incident";
import type { Supplier } from "@/types/supplier";

// Propiedades de los eventos de las otras áreas del negocio (plan, §5.6): directorio de proveedores,
// gestor de incidencias y analizador del CSV. Funciones puras; las llaman lib/proveedores/api.ts,
// lib/gestor-incidencias/api.ts y lib/incidencias/api.ts tras la respuesta de la API. Nunca viajan
// los datos de contacto de un proveedor ni el título o la descripción de una incidencia (§8.1).

const MINUTE_MS = 60_000;

function round(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

// El directorio usa "Colombia"/"USA"; los eventos, el código del país del local (§12.1).
const SUPPLIER_COUNTRY = { Colombia: "CO", USA: "US" } as const;

export function supplierCreatedProperties(supplier: Supplier) {
  return {
    supplier_id: supplier.id,
    country: SUPPLIER_COUNTRY[supplier.country],
    categories: supplier.categories,
    currency: supplier.currency,
    status: supplier.status,
  };
}

export function supplierRateUpdatedProperties(previous: Supplier, updated: Supplier) {
  return {
    supplier_id: updated.id,
    country: SUPPLIER_COUNTRY[updated.country],
    currency: updated.currency,
    previous_rate: previous.rate_per_unit,
    new_rate: updated.rate_per_unit,
    change_pct: round(((updated.rate_per_unit - previous.rate_per_unit) / previous.rate_per_unit) * 100, 2),
  };
}

// null si el estado no cambió (la API acepta el mismo estado, pero no es un cambio).
export function supplierStatusChangedProperties(previous: Supplier, updated: Supplier) {
  if (previous.status === updated.status) return null;
  return {
    supplier_id: updated.id,
    country: SUPPLIER_COUNTRY[updated.country],
    categories: updated.categories,
    previous_status: previous.status,
    new_status: updated.status,
  };
}

export function incidentCreatedProperties(incident: Incident) {
  return {
    incident_id: incident.id,
    category: incident.category,
    origin: incident.origin,
    branch: incident.branch,
    status: incident.status,
  };
}

// Tiempos de respuesta por sede (§5.6): desde la creación y desde el cambio de estado anterior
// (`updated_at` del listado, antes del cambio).
export function incidentStatusChangedProperties(previous: IncidentListItem, updated: Incident) {
  const changedAt = Date.parse(updated.updated_at);
  const minutesSince = (from: string) => Math.max(0, Math.floor((changedAt - Date.parse(from)) / MINUTE_MS));
  return {
    incident_id: updated.id,
    category: updated.category,
    branch: updated.branch,
    previous_status: previous.status,
    new_status: updated.status,
    minutes_since_created: minutesSince(updated.created_at),
    minutes_in_previous_status: minutesSince(previous.updated_at),
  };
}

export function incidentTransitionRejectedProperties(previous: IncidentListItem, requested: string) {
  return { incident_id: previous.id, current_status: previous.status, requested_status: requested };
}

// Reglas del analizador (packages/shared): las que admite el esquema de `invalid_by_rule`.
const ANALYZER_RULES = new Set([
  "missing_location",
  "invalid_category",
  "empty_description",
  "missing_reporter",
  "invalid_status",
  "closed_without_score",
  "score_out_of_range",
]);

// Sin el nombre ni el contenido del archivo: solo los recuentos y el tamaño.
export function incidentReportAnalyzedProperties(analysis: IncidentAnalysis, fileSizeBytes: number) {
  const invalidByRule = Object.fromEntries(
    analysis.invalid_breakdown.filter((item) => ANALYZER_RULES.has(item.rule) && item.count > 0).map((item) => [item.rule, item.count])
  );
  return {
    total_rows: analysis.total_records,
    valid_rows: analysis.valid_records,
    invalid_rows: analysis.invalid_records,
    invalid_by_rule: invalidByRule,
    file_size_bytes: fileSizeBytes,
  };
}
