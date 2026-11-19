// Otras áreas del negocio: directorio de proveedores, gestor de incidencias y analizador del CSV
// (lib/telemetry/business-events.ts). Nunca viajan contactos, títulos ni descripciones.
import {
  incidentCreatedProperties,
  incidentReportAnalyzedProperties,
  incidentStatusChangedProperties,
  incidentTransitionRejectedProperties,
  supplierCreatedProperties,
  supplierRateUpdatedProperties,
  supplierStatusChangedProperties,
} from "@/lib/telemetry/business-events";
import type { IncidentAnalysis } from "@/types/incident";
import type { Incident } from "@/types/incident-manager";
import type { Supplier } from "@/types/supplier";

const SUPPLIER: Supplier = {
  id: 9,
  name: "MiamiMeat Co.",
  country: "USA",
  categories: ["carne"],
  rate_per_unit: 8.5,
  currency: "USD",
  status: "active",
  contact_email: "ventas@miamimeat.com",
  notes: "Entrega los martes",
  updated_at: "2026-11-01T10:00:00Z",
};

const INCIDENT: Incident = {
  id: 10098,
  title: "Parrilla 2 sin gas",
  description: "No enciende desde la mañana",
  category: "equipment_failure",
  status: "open",
  origin: "branch",
  branch: "medellin_centro",
  created_at: "2026-11-19T08:00:00Z",
  updated_at: "2026-11-19T08:00:00Z",
};

describe("proveedores", () => {
  it("supplier_created traduce el país y no lleva contacto ni notas", () => {
    const properties = supplierCreatedProperties(SUPPLIER);
    expect(properties).toEqual({ supplier_id: 9, country: "US", categories: ["carne"], currency: "USD", status: "active" });
    expect(JSON.stringify(properties)).not.toMatch(/ventas@|martes|MiamiMeat/);
  });

  it("supplier_rate_updated lleva la tarifa anterior, la nueva y el porcentaje", () => {
    expect(supplierRateUpdatedProperties(SUPPLIER, { ...SUPPLIER, rate_per_unit: 9.35 })).toEqual({
      supplier_id: 9,
      country: "US",
      currency: "USD",
      previous_rate: 8.5,
      new_rate: 9.35,
      change_pct: 10,
    });
  });

  it("supplier_status_changed solo si el estado cambia", () => {
    expect(supplierStatusChangedProperties(SUPPLIER, { ...SUPPLIER, status: "suspended" })).toEqual({
      supplier_id: 9,
      country: "US",
      categories: ["carne"],
      previous_status: "active",
      new_status: "suspended",
    });
    expect(supplierStatusChangedProperties(SUPPLIER, SUPPLIER)).toBeNull();
  });
});

describe("incidencias", () => {
  it("incident_created no lleva el título ni la descripción", () => {
    const properties = incidentCreatedProperties(INCIDENT);
    expect(properties).toEqual({ incident_id: 10098, category: "equipment_failure", origin: "branch", branch: "medellin_centro", status: "open" });
    expect(JSON.stringify(properties)).not.toMatch(/Parrilla|enciende/);
  });

  it("incident_status_changed mide los minutos desde la creación y desde el estado anterior", () => {
    const previous = { ...INCIDENT, status: "in_progress" as const, updated_at: "2026-11-19T09:00:00Z" };
    const updated = { ...INCIDENT, status: "resolved" as const, updated_at: "2026-11-19T09:35:00Z" };

    expect(incidentStatusChangedProperties(previous, updated)).toEqual({
      incident_id: 10098,
      category: "equipment_failure",
      branch: "medellin_centro",
      previous_status: "in_progress",
      new_status: "resolved",
      minutes_since_created: 95,
      minutes_in_previous_status: 35,
    });
  });

  it("incident_transition_rejected lleva el estado actual y el pedido", () => {
    expect(incidentTransitionRejectedProperties({ ...INCIDENT, status: "resolved" }, "in_progress")).toEqual({
      incident_id: 10098,
      current_status: "resolved",
      requested_status: "in_progress",
    });
  });

  it("incident_report_analyzed da los recuentos por regla y el tamaño, sin el nombre del archivo", () => {
    const analysis = {
      source_file: "reporte-sede-3.csv",
      analyzed_at: "2026-11-19T10:00:00Z",
      total_records: 100,
      valid_records: 96,
      invalid_records: 4,
      invalid_breakdown: [
        { rule: "missing_location", label: "Missing location_id", count: 1 },
        { rule: "invalid_category", label: "Invalid or missing category", count: 2 },
        { rule: "score_out_of_range", label: "Score out of range", count: 1 },
        { rule: "empty_description", label: "Empty description", count: 0 },
      ],
    } as unknown as IncidentAnalysis;

    const properties = incidentReportAnalyzedProperties(analysis, 18_430);
    expect(properties).toEqual({
      total_rows: 100,
      valid_rows: 96,
      invalid_rows: 4,
      invalid_by_rule: { missing_location: 1, invalid_category: 2, score_out_of_range: 1 },
      file_size_bytes: 18_430,
    });
    expect(JSON.stringify(properties)).not.toContain("reporte-sede-3");
  });
});
