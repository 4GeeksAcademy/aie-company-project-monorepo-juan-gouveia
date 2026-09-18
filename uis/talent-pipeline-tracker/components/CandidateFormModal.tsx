"use client";

import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import Modal from "@/components/Modal";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordCreateInput, RecordDetail, RecordStage, RecordStatus } from "@/types/record";

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
  const [error, setError] = useState<string | null>(null);

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const errors = Object.fromEntries(
    REQUIRED_FIELDS.map((field) => [field, getFieldError(form, field)])
  ) as Record<RequiredField, string | null>;
  const isValid = REQUIRED_FIELDS.every((field) => !errors[field]);
  const hasInput = TEXT_FIELDS.some((field) => form[field].trim() !== "");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;
    try {
      setSubmitting(true);
      setError(null);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
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
      disabled: submitting,
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
                disabled={submitting}
                fullWidth
              />
              <LabeledSelect
                label="Stage"
                value={form.stage}
                options={STAGE_LABELS}
                onChange={(value) => setField("stage", value)}
                disabled={submitting}
                fullWidth
              />
            </>
          )}
        </div>

        {error && <p className="mt-3 text-xs text-red-700">{error}</p>}

        <div className="mt-4 flex flex-wrap justify-end gap-3">
          {isEditing ? (
            <Button variant="secondary" size="md" onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="md"
              onClick={() => setForm(EMPTY_FORM)}
              disabled={!hasInput || submitting}
            >
              Limpiar
            </Button>
          )}
          <Button type="submit" size="md" disabled={!isValid || submitting}>
            {submitting ? submittingLabel : submitLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
