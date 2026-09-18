"use client";

import { useEffect, useState } from "react";
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

const INPUT_CLASS =
  "w-full rounded-md border border-red-200 px-3 py-2 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60";

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

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, submitting]);

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

  function renderField(
    field: RequiredField | "linkedin_url" | "cv_url",
    label: string,
    type = "text",
    extra: React.InputHTMLAttributes<HTMLInputElement> = {}
  ) {
    const fieldError = field in errors ? errors[field as RequiredField] : null;
    const required = field in errors;
    return (
      <label className="flex flex-col gap-1 text-sm text-black">
        <span className="font-semibold text-red-700">
          {label}
          {required && " *"}
        </span>
        <input
          type={type}
          value={form[field]}
          onChange={(e) => setField(field, e.target.value)}
          disabled={submitting}
          aria-invalid={Boolean(fieldError)}
          className={INPUT_CLASS}
          {...extra}
        />
        {fieldError && <span className="text-xs text-red-700">{fieldError}</span>}
      </label>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={() => !submitting && onClose()}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-form-title"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
        className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-4 shadow-md md:p-6"
      >
        <button
          type="button"
          onClick={onClose}
          disabled={submitting}
          aria-label="Cerrar"
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md text-xl leading-none text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        >
          ×
        </button>

        <h2
          id="candidate-form-title"
          className="mb-4 pr-8 text-lg font-semibold text-red-700 md:text-xl"
        >
          {title}
        </h2>

        <div className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
          {renderField("full_name", "Nombre")}
          {renderField("position", "Posición")}
          {renderField("experience_years", "Experiencia (años)", "number", {
            min: 0,
            step: "any",
          })}
          {renderField("email", "Email", "email")}
          {renderField("phone", "Teléfono", "tel")}
          {renderField("linkedin_url", "LinkedIn", "url")}
          {renderField("cv_url", "CV", "url")}

          {!isEditing && (
            <>
          <label className="flex flex-col gap-1 text-sm text-black">
            <span className="font-semibold text-red-700">Status</span>
            <select
              value={form.status}
              onChange={(e) => setField("status", e.target.value as RecordStatus)}
              disabled={submitting}
              className={INPUT_CLASS}
            >
              {(Object.entries(STATUS_LABELS) as [RecordStatus, string][]).map(
                ([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm text-black">
            <span className="font-semibold text-red-700">Stage</span>
            <select
              value={form.stage}
              onChange={(e) => setField("stage", e.target.value as RecordStage)}
              disabled={submitting}
              className={INPUT_CLASS}
            >
              {(Object.entries(STAGE_LABELS) as [RecordStage, string][]).map(
                ([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                )
              )}
            </select>
          </label>
            </>
          )}
        </div>

        {error && <p className="mt-3 text-xs text-red-700">{error}</p>}

        <div className="mt-4 flex flex-wrap justify-end gap-3">
          {isEditing ? (
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancelar
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setForm(EMPTY_FORM)}
              disabled={!hasInput || submitting}
              className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-transparent"
            >
              Limpiar
            </button>
          )}
          <button
            type="submit"
            disabled={!isValid || submitting}
            className="rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? submittingLabel : submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
