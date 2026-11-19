// Navegación y abandono de flujos (plan, §5.3): lógica pura de `form_validation_failed`,
// `form_abandoned` y `list_filter_applied`. Los hooks (useFormTelemetry, useListFilterTelemetry y
// useShowMore) la envuelven y emiten con track(); así ningún formulario ni lista instrumenta nada por
// su cuenta. Solo viajan nombres de campos y de filtros, nunca lo escrito (§8.1).

export type FormId =
  | "login"
  | "register"
  | "forgot_password"
  | "reset_password"
  | "change_password"
  | "profile"
  | "inbound_order"
  | "outbound_order"
  | "supplier"
  | "supplier_rate"
  | "incident"
  | "incident_upload"
  | "candidate"
  | "candidate_note";

export type FormExit = "navigation" | "modal_closed" | "tab_closed";

const FIELD_NAME = /^[a-z_]+$/;
// Throttle (§10): un `form_validation_failed` por formulario cada 2 s (doble clic en enviar).
export const VALIDATION_REPEAT_MS = 2_000;

export interface FormSession {
  // Un campo cambió: el formulario se considera empezado.
  change(field: string, now: number): void;
  // El envío se bloqueó por errores de validación del navegador.
  invalid(errors: Record<string, unknown>, now: number): Record<string, unknown> | null;
  // Envío correcto: el formulario termina (los cambios siguientes empiezan otro).
  succeed(): void;
  // Salida sin enviar: el evento, o null si no se llegó a cambiar ningún campo. Se emite una sola vez.
  abandon(exit: FormExit, now: number): Record<string, unknown> | null;
}

export function createFormSession(formId: FormId): FormSession {
  let startedAt: number | null = null;
  let lastField: string | null = null;
  let changed = new Set<string>();
  let lastInvalidAt: number | null = null;

  function reset() {
    startedAt = null;
    lastField = null;
    changed = new Set();
  }

  return {
    change(field, now) {
      if (!FIELD_NAME.test(field)) return;
      startedAt ??= now;
      lastField = field;
      changed.add(field);
    },
    invalid(errors, now) {
      const fields = Object.keys(errors).filter((field) => errors[field] && FIELD_NAME.test(field));
      if (fields.length === 0) return null;
      if (lastInvalidAt !== null && now - lastInvalidAt < VALIDATION_REPEAT_MS) return null;
      lastInvalidAt = now;
      return { form_id: formId, invalid_fields: fields.slice(0, 20), error_count: fields.length };
    },
    succeed: reset,
    abandon(exit, now) {
      if (startedAt === null || lastField === null || changed.size === 0) return null;
      const event = {
        form_id: formId,
        last_field: lastField,
        filled_field_count: changed.size,
        time_in_form_seconds: Math.max(0, Math.round((now - startedAt) / 1000)),
        exit,
      };
      reset();
      return event;
    },
  };
}

// --- Listas ---------------------------------------------------------------------------------------

export type ListId = "order_history" | "incident_manager" | "supplier_directory";
export type FilterName = "kind" | "ingredient" | "status" | "origin" | "branch" | "country" | "category";

const FILTER_VALUE = /^[a-z_A-Z]+$/;

// Un `list_filter_applied` por cada filtro que cambió respecto al último estado emitido. Los filtros
// de texto (`textFilters`) solo dan la longitud del texto; los de lista cerrada dan el valor elegido
// (si es un código del dominio) y nada al quitarlos.
export function changedFilterEvents(
  listId: ListId,
  previous: Record<string, string>,
  current: Record<string, string>,
  resultCount: number,
  textFilters: readonly string[] = []
): Record<string, unknown>[] {
  return Object.keys(current)
    .filter((name) => current[name] !== previous[name])
    .map((name) => {
      const value = current[name];
      const isText = textFilters.includes(name);
      return {
        list_id: listId,
        filter_name: name,
        filter_value: !isText && value && FILTER_VALUE.test(value) && value.length <= 40 ? value : undefined,
        query_length: isText ? value.trim().length : undefined,
        result_count: resultCount,
      };
    });
}
