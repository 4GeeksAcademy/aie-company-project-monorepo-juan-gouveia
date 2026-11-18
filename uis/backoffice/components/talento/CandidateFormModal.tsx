"use client";

import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import Modal from "@/components/Modal";
import { useAutoClose } from "@/hooks/useAutoClose";
import { toUserMessage } from "@/lib/error-message";
import { PartialSaveError } from "@/lib/talento/api";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/talento/labels";
import type { RecordCreateInput, RecordDetail, RecordStage, RecordStatus } from "@/types/record";

// Tiempo que se muestra el mensaje de éxito antes de cerrar el modal.
const RESULT_MESSAGE_MS = 5000;

// "partial": los datos se guardaron, pero no el status y el stage (PartialSaveError).
type SubmitResult =
  | { kind: "success" }
  | { kind: "error"; message: string }
  | { kind: "partial"; message: string };

// onSubmit no debe cerrar el modal: si tiene éxito lo cierra el propio modal tras el mensaje;
// si falla, el modal permanece abierto.
interface CandidateFormModalProps {
  title: string;
  submitLabel: string;
  submittingLabel: string;
  // Valores iniciales (edición); si se omite, el formulario arranca vacío (alta).
  initialRecord?: RecordDetail;
  onClose: () => void;
  onSubmit: (input: RecordCreateInput) => Promise<void>;
}

interface FormState {
  full_name: string;
  position: string;
  experience_years: string;
  email: string;
  phone: string;
  linkedin_url: string;
  cv_url: string;
  status: RecordStatus;
  stage: RecordStage;
}

const EMPTY_FORM: FormState = {
  full_name: "",
  position: "",
  experience_years: "",
  email: "",
  phone: "",
  linkedin_url: "",
  cv_url: "",
  status: "received",
  stage: "pending",
};

function toFormState(record: RecordDetail): FormState {
  return {
    full_name: record.full_name,
    position: record.position,
    experience_years: String(record.experience_years),
    email: record.email,
    phone: record.phone,
    linkedin_url: record.linkedin_url ?? "",
    cv_url: record.cv_url ?? "",
    status: record.status,
    stage: record.stage,
  };
}

const REQUIRED_FIELDS = [
  "full_name",
  "position",
  "experience_years",
  "email",
  "phone",
] as const;

const TEXT_FIELDS = [...REQUIRED_FIELDS, "linkedin_url", "cv_url"] as const;

type RequiredField = (typeof REQUIRED_FIELDS)[number];
type TextField = (typeof TEXT_FIELDS)[number];

function getFieldError(form: FormState, field: RequiredField): string | null {
  const value = form[field].trim();
  if (!value) return "Campo requerido";
  if (field === "email" && !value.includes("@")) return "El email debe contener @";
  if (field === "experience_years" && (Number.isNaN(Number(value)) || Number(value) < 0)) {
    return "Ingresa un número válido";
  }
  return null;
}

export default function CandidateFormModal({
  title,
  submitLabel,
  submittingLabel,
  initialRecord,
  onClose,
  onSubmit,
}: CandidateFormModalProps) {
  const isEditing = Boolean(initialRecord);
  const [form, setForm] = useState<FormState>(
    initialRecord ? toFormState(initialRecord) : EMPTY_FORM
  );
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);
  // Bloquea el formulario mientras se envía, mientras se muestra el éxito (antes de cerrar) y tras un
  // guardado parcial, porque reenviarlo crearía un duplicado. Tras un error completo el formulario
  // queda editable y el modal abierto para poder reintentar.
  const locked = submitting || result?.kind === "success" || result?.kind === "partial";

  useAutoClose(result?.kind === "success", RESULT_MESSAGE_MS, onClose);

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const errors = Object.fromEntries(
    REQUIRED_FIELDS.map((field) => [field, getFieldError(form, field)])
  ) as Record<RequiredField, string | null>;
  const isValid = REQUIRED_FIELDS.every((field) => !errors[field]);
  const hasInput = TEXT_FIELDS.some((field) => form[field].trim() !== "");

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!isValid) return;
    try {
      setSubmitting(true);
      setResult(null);
      await onSubmit({
        full_name: form.full_name.trim(),
        position: form.position.trim(),
        experience_years: Number(form.experience_years),
        email: form.email.trim(),
        phone: form.phone.trim(),
        linkedin_url: form.linkedin_url.trim() || null,
        cv_url: form.cv_url.trim() || null,
        status: form.status,
        stage: form.stage,
      });
      setResult({ kind: "success" });
    } catch (err) {
      if (err instanceof PartialSaveError) {
        setResult({ kind: "partial", message: err.message });
      } else {
        const fallback = `No se pudo ${isEditing ? "modificar" : "añadir"} el candidato. Inténtalo de nuevo.`;
        setResult({ kind: "error", message: toUserMessage(err, fallback) });
      }
    } finally {
      setSubmitting(false);
    }
  }

  // Props comunes de FormField para cada campo de texto; solo los obligatorios tienen error.
  function fieldProps(field: TextField) {
    const isRequired = field in errors;
    return {
      value: form[field],
      onChange: (value: string) => setField(field, value),
      required: isRequired,
      error: isRequired ? errors[field as RequiredField] : null,
      disabled: locked,
    };
  }

  return (
    <Modal title={title} onClose={onClose} busy={submitting} size="lg">
      <form onSubmit={handleSubmit} noValidate>
        <div className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
          <FormField label="Nombre" {...fieldProps("full_name")} />
          <FormField label="Posición" {...fieldProps("position")} />
          <FormField
            label="Experiencia (años)"
            type="number"
            inputProps={{ min: 0, step: "any" }}
            {...fieldProps("experience_years")}
          />
          <FormField label="Email" type="email" {...fieldProps("email")} />
          <FormField label="Teléfono" type="tel" {...fieldProps("phone")} />
          <FormField label="LinkedIn" type="url" {...fieldProps("linkedin_url")} />
          <FormField label="CV" type="url" {...fieldProps("cv_url")} />

          {!isEditing && (
            <>
              <LabeledSelect
                label="Status"
                value={form.status}
                options={STATUS_LABELS}
                onChange={(value) => setField("status", value)}
                disabled={locked}
                fullWidth
              />
              <LabeledSelect
                label="Stage"
                value={form.stage}
                options={STAGE_LABELS}
                onChange={(value) => setField("stage", value)}
                disabled={locked}
                fullWidth
              />
            </>
          )}
        </div>

        {result?.kind === "success" && (
          <p role="status" className="mt-3 text-sm font-semibold text-green-700">
            Candidato guardado con éxito
          </p>
        )}
        {(result?.kind === "error" || result?.kind === "partial") && (
          <p role="alert" className="mt-3 text-sm font-semibold text-red-700">
            {result.message}
          </p>
        )}

        <div className="mt-4 flex flex-wrap justify-end gap-3">
          {result?.kind === "partial" ? (
            // Los datos ya se guardaron: la única salida es cerrar, no reenviar.
            <Button size="md" onClick={onClose}>
              Cerrar
            </Button>
          ) : isEditing ? (
            <Button variant="secondary" size="md" onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="md"
              onClick={() => setForm(EMPTY_FORM)}
              disabled={!hasInput || locked}
            >
              Limpiar
            </Button>
          )}
          {result?.kind !== "partial" && (
            <Button type="submit" size="md" disabled={!isValid || locked}>
              {submitting ? submittingLabel : submitLabel}
            </Button>
          )}
        </div>
      </form>
    </Modal>
  );
}
