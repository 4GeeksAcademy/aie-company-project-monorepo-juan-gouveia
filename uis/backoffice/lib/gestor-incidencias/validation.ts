import type { Branch, IncidentCategory, IncidentCreateInput, IncidentOrigin } from "@/types/incident-manager";

// Validación en el cliente, antes de enviar. La API vuelve a validar todo (400 con el campo).

// Mismos límites que la API (services/brasaland-api, incidents/models.py).
export const MAX_TITLE_LENGTH = 120;
export const MAX_DESCRIPTION_LENGTH = 2000;

export interface IncidentFormValues {
  title: string;
  description: string;
  category: IncidentCategory | "";
  origin: IncidentOrigin | "";
  branch: Branch | "";
}

export type IncidentFormField = keyof IncidentFormValues;
export type IncidentFormErrors = Partial<Record<IncidentFormField, string>>;

export const INCIDENT_FORM_FIELDS: readonly IncidentFormField[] = ["title", "description", "category", "origin", "branch"];

export const EMPTY_INCIDENT_FORM: IncidentFormValues = {
  title: "",
  description: "",
  category: "",
  origin: "",
  branch: "",
};

export function validateIncidentForm(values: IncidentFormValues): IncidentFormErrors {
  const errors: IncidentFormErrors = {};
  const title = values.title.trim();
  const description = values.description.trim();

  if (!title) errors.title = "Escribe un título breve.";
  else if (title.length > MAX_TITLE_LENGTH) errors.title = `El título no puede superar ${MAX_TITLE_LENGTH} caracteres.`;

  if (!description) errors.description = "Describe la incidencia.";
  else if (description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = `La descripción no puede superar ${MAX_DESCRIPTION_LENGTH} caracteres.`;
  }

  if (!values.category) errors.category = "Elige una categoría.";
  if (!values.origin) errors.origin = "Elige el origen del reporte.";
  if (!values.branch) errors.branch = "Elige la sede. Usa Central si no corresponde a un local.";
  return errors;
}

// Cuerpo de POST /incidents. Solo se llama con un formulario sin errores.
export function toCreateInput(values: IncidentFormValues): IncidentCreateInput {
  return {
    title: values.title.trim(),
    description: values.description.trim(),
    category: values.category as IncidentCategory,
    origin: values.origin as IncidentOrigin,
    branch: values.branch as Branch,
  };
}
