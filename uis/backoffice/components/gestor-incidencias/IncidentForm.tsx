"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import TextAreaField from "@/components/TextAreaField";
import FormAlert from "@/components/auth/FormAlert";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { createIncident } from "@/lib/gestor-incidencias/api";
import {
  BRANCH_LABELS,
  CATEGORY_DESCRIPTIONS,
  CATEGORY_OPTIONS,
  ORIGIN_DESCRIPTIONS,
  ORIGIN_OPTIONS,
  STATUS_DESCRIPTIONS,
} from "@/lib/gestor-incidencias/labels";
import {
  EMPTY_INCIDENT_FORM,
  INCIDENT_FORM_FIELDS,
  MAX_DESCRIPTION_LENGTH,
  MAX_TITLE_LENGTH,
  toCreateInput,
  validateIncidentForm,
  type IncidentFormErrors,
  type IncidentFormField,
  type IncidentFormValues,
} from "@/lib/gestor-incidencias/validation";
import { mergeFieldErrors } from "@/lib/auth/validation";

type Message = { tone: "error" | "success"; text: string };

// Registro de incidencias (gestor de incidencias centralizado).
// - Valida los obligatorios en el cliente antes de enviar; la API vuelve a validar (400 con el campo).
// - Durante el envío, el botón queda deshabilitado y muestra un indicador de carga.
// - Los errores de la API se muestran con su mensaje en español; si señalan un campo, junto a él.
// - Tras el éxito, el formulario se limpia y muestra una confirmación.
export default function IncidentForm() {
  const [values, setValues] = useState<IncidentFormValues>(EMPTY_INCIDENT_FORM);
  // Los errores locales se muestran tras el primer intento de envío.
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<IncidentFormErrors>({});
  const [message, setMessage] = useState<Message | null>(null);
  const messageRef = useRef<HTMLDivElement>(null);

  const errors = mergeFieldErrors(attempted ? validateIncidentForm(values) : {}, apiFields);
  const fromBranch = values.origin === "branch";

  function setField<K extends IncidentFormField>(field: K, value: IncidentFormValues[K]) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setApiFields((prev) => ({ ...prev, [field]: undefined }));
    setMessage(null);
  }

  function show(next: Message) {
    setMessage(next);
    // El aviso está arriba del formulario: en una tablet puede quedar fuera de la vista.
    requestAnimationFrame(() => messageRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    setMessage(null);
    if (Object.keys(validateIncidentForm(values)).length > 0) {
      show({ tone: "error", text: "Revisa los campos marcados." });
      return;
    }

    setSubmitting(true);
    setApiFields({});
    try {
      const incident = await createIncident(toCreateInput(values));
      setValues(EMPTY_INCIDENT_FORM);
      setAttempted(false);
      show({
        tone: "success",
        text: `Incidencia #${incident.id} registrada: «${incident.title}». Queda en estado ${incident.status}.`,
      });
    } catch (err) {
      const result = formErrorsFromApi(err, INCIDENT_FORM_FIELDS, "No se pudo registrar la incidencia.");
      setApiFields(result.fields);
      if (result.message) show({ tone: "error", text: result.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate aria-busy={submitting} className="flex flex-col gap-5">
      <div ref={messageRef}>
        {message && (
          <FormAlert tone={message.tone}>
            {message.text}
            {message.tone === "success" && (
              <>
                {" "}
                <Link href="/gestor-incidencias" className="font-semibold underline">
                  Ver en el panel
                </Link>
              </>
            )}
          </FormAlert>
        )}
      </div>

      <FormField
        label="Título"
        value={values.title}
        onChange={(value) => setField("title", value)}
        required
        size="lg"
        error={errors.title}
        hint={`Una frase breve. Máximo ${MAX_TITLE_LENGTH} caracteres (${values.title.trim().length}/${MAX_TITLE_LENGTH}).`}
        disabled={submitting}
        inputProps={{ name: "title", maxLength: MAX_TITLE_LENGTH, autoComplete: "off" }}
      />

      <TextAreaField
        label="Descripción"
        value={values.description}
        onChange={(value) => setField("description", value)}
        required
        size="lg"
        rows={5}
        error={errors.description}
        hint="Qué pasó, dónde y desde cuándo. Si es de un cliente, qué reclamó."
        disabled={submitting}
        textareaProps={{ name: "description", maxLength: MAX_DESCRIPTION_LENGTH }}
      />

      <div className="grid gap-5 md:grid-cols-2">
        <LabeledSelect
          label="Categoría (category)"
          value={values.category}
          options={CATEGORY_OPTIONS}
          onChange={(value) => setField("category", value)}
          placeholder="Elige una categoría"
          required
          size="lg"
          fullWidth
          invalid={Boolean(errors.category)}
          disabled={submitting}
        >
          {values.category && <span className="text-xs text-gray-600">{CATEGORY_DESCRIPTIONS[values.category]}</span>}
          {errors.category && <span className="text-xs text-red-700">{errors.category}</span>}
        </LabeledSelect>

        <LabeledSelect
          label="Origen (origin)"
          value={values.origin}
          options={ORIGIN_OPTIONS}
          onChange={(value) => setField("origin", value)}
          placeholder="Elige el origen"
          required
          size="lg"
          fullWidth
          invalid={Boolean(errors.origin)}
          disabled={submitting}
        >
          {values.origin && <span className="text-xs text-gray-600">{ORIGIN_DESCRIPTIONS[values.origin]}</span>}
          {errors.origin && <span className="text-xs text-red-700">{errors.origin}</span>}
        </LabeledSelect>
      </div>

      {/* La sede es siempre visible y obligatoria; con origin = branch se resalta. */}
      <div
        className={
          fromBranch
            ? "rounded-lg border-2 border-amber-400 bg-amber-50 p-3 transition-colors md:p-4"
            : "rounded-lg border-2 border-transparent transition-colors"
        }
      >
        {fromBranch && (
          <p className="mb-2 text-sm font-semibold text-amber-900">
            Estás reportando desde una sede: confirma en qué local ocurre.
          </p>
        )}
        <LabeledSelect
          label="Sede (branch)"
          value={values.branch}
          options={BRANCH_LABELS}
          onChange={(value) => setField("branch", value)}
          placeholder="Elige una sede"
          required
          size="lg"
          fullWidth
          invalid={Boolean(errors.branch)}
          disabled={submitting}
        >
          <span className="text-xs text-gray-600">Usa «Central (Medellín / Miami)» si no corresponde a un local.</span>
          {errors.branch && <span className="text-xs text-red-700">{errors.branch}</span>}
        </LabeledSelect>
      </div>

      <div className="rounded-md border border-red-100 bg-red-50/40 p-3 text-sm text-black">
        <p>
          <span className="font-semibold text-red-700">Estado (status):</span> <code>open</code>
        </p>
        <p className="text-xs text-gray-600">{STATUS_DESCRIPTIONS.open}. Toda incidencia nueva empieza así; el estado se cambia después desde el panel.</p>
      </div>

      <p className="text-xs text-gray-600">Los campos con * son obligatorios.</p>

      <div className="flex justify-end">
        <Button type="submit" size="md" disabled={submitting} className="inline-flex items-center gap-2 px-6 py-3 text-base">
          {submitting && (
            <span
              aria-hidden="true"
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
            />
          )}
          {submitting ? "Registrando incidencia..." : "Registrar incidencia"}
        </Button>
      </div>
    </form>
  );
}
