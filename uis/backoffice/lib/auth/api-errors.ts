import { ApiError } from "@/lib/api-client";

// Reparte un error de la API entre los campos del formulario y un mensaje general.
// Los 422 traen `details` con el nombre del campo de la API (email, password, name…).
export interface FormApiErrors<Field extends string> {
  fields: Partial<Record<Field, string>>;
  // Mensaje general: el de la API, más los detalles que no corresponden a ningún campo.
  message: string | null;
}

export function formErrorsFromApi<Field extends string>(
  err: unknown,
  formFields: readonly Field[],
  fallback: string
): FormApiErrors<Field> {
  if (!(err instanceof ApiError)) {
    return { fields: {}, message: err instanceof Error ? err.message : fallback };
  }

  const fields: Partial<Record<Field, string>> = {};
  const unmatched: string[] = [];
  for (const detail of err.details) {
    const field = formFields.find((name) => name === detail.field);
    if (field && !fields[field]) fields[field] = detail.message;
    else if (!field) unmatched.push(detail.message);
  }

  // Email ya registrado: se muestra junto al campo email.
  const emailField = formFields.find((name) => name === "email");
  if (err.code === "duplicate_email" && emailField) {
    fields[emailField] = err.message;
    return { fields, message: null };
  }

  const hasFieldErrors = Object.keys(fields).length > 0;
  const message = hasFieldErrors && unmatched.length === 0 ? "Revisa los campos marcados." : err.message;
  return { fields, message: unmatched.length > 0 ? `${message} ${unmatched.join(" ")}` : message };
}
