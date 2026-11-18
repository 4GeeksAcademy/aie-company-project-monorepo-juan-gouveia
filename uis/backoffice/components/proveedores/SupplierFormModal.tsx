"use client";

import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import Modal from "@/components/Modal";
import { ApiError } from "@/lib/api-client";
import { createSupplier } from "@/lib/proveedores/api";
import { CATEGORIES, COUNTRY_OPTIONS, CURRENCY_BY_COUNTRY, STATUS_OPTIONS } from "@/lib/proveedores/labels";
import { validateSupplierForm, type SupplierFormValues } from "@/lib/proveedores/validation";
import type { ApiFieldError } from "@/types/api";
import type { Category, Supplier } from "@/types/supplier";
import { toUserMessage } from "@/lib/error-message";

interface SupplierFormModalProps {
  onClose: () => void;
  onCreated: (supplier: Supplier) => void;
}

const EMPTY_FORM: SupplierFormValues = {
  name: "",
  country: "",
  categories: [],
  rate_per_unit: "",
  status: "active",
  contact_email: "",
  notes: "",
};

interface ApiFailure {
  message: string;
  details: ApiFieldError[];
}

// Nombre en español de cada campo que la API puede señalar en `details`.
const FIELD_LABELS: Record<string, string> = {
  name: "Nombre",
  country: "País",
  categories: "Categorías",
  rate_per_unit: "Tarifa por unidad",
  currency: "Moneda",
  status: "Estado",
  contact_email: "Email de contacto",
  notes: "Notas internas",
};

// "categories.1" es un elemento de la lista: se nombra como el campo. Un campo desconocido no se
// nombra (se muestra solo el mensaje) para no enseñar nombres técnicos de la API.
function fieldLabel(field: string): string | null {
  return FIELD_LABELS[field.split(".")[0]] ?? null;
}

export default function SupplierFormModal({ onClose, onCreated }: SupplierFormModalProps) {
  const [form, setForm] = useState<SupplierFormValues>(EMPTY_FORM);
  // Los errores de cada campo se muestran tras el primer intento de envío.
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFailure, setApiFailure] = useState<ApiFailure | null>(null);

  const errors = validateSupplierForm(form);
  const shownErrors = attempted ? errors : {};
  // La moneda se deriva del país (restricción del briefing); no se elige a mano.
  const currency = form.country ? CURRENCY_BY_COUNTRY[form.country] : null;

  function setField<K extends keyof SupplierFormValues>(key: K, value: SupplierFormValues[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleCategory(category: Category) {
    setForm((prev) => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter((item) => item !== category)
        : [...prev.categories, category],
    }));
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    if (Object.keys(errors).length > 0 || !form.country || !currency) return;

    setSubmitting(true);
    setApiFailure(null);
    try {
      const created = await createSupplier({
        name: form.name.trim(),
        country: form.country,
        // En el orden de la lista del briefing, sea cual sea el orden en que se marcaron.
        categories: CATEGORIES.filter((category) => form.categories.includes(category)),
        rate_per_unit: Number(form.rate_per_unit),
        currency,
        status: form.status,
        contact_email: form.contact_email.trim() || null,
        notes: form.notes.trim() || null,
      });
      onCreated(created);
    } catch (err) {
      setApiFailure({
        message: toUserMessage(err, "No se pudo registrar el proveedor. Inténtalo de nuevo."),
        details: err instanceof ApiError ? err.details : [],
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Registrar proveedor" onClose={onClose} busy={submitting} size="lg">
      <form onSubmit={handleSubmit} noValidate>
        <div className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
          <FormField
            label="Nombre (name)"
            value={form.name}
            onChange={(value) => setField("name", value)}
            required
            error={shownErrors.name}
            disabled={submitting}
          />

          <LabeledSelect
            label="País (country) *"
            value={form.country}
            options={COUNTRY_OPTIONS}
            placeholder="Elige un país"
            onChange={(value) => setField("country", value)}
            disabled={submitting}
            fullWidth
          >
            {shownErrors.country && <span className="text-xs text-red-700">{shownErrors.country}</span>}
          </LabeledSelect>

          <FormField
            label={`Tarifa por unidad (rate_per_unit)${currency ? ` en ${currency}` : ""}`}
            type="number"
            value={form.rate_per_unit}
            onChange={(value) => setField("rate_per_unit", value)}
            required
            error={shownErrors.rate_per_unit}
            disabled={submitting}
            inputProps={{ min: 0, step: "any", inputMode: "decimal" }}
          />

          <div className="flex flex-col gap-1 text-sm text-black">
            <span className="font-semibold text-red-700">Moneda (currency)</span>
            <p className="rounded-md border border-red-100 bg-gray-50 px-3 py-2">
              {currency ?? "Se asigna según el país"}
            </p>
          </div>

          <LabeledSelect
            label="Estado (status) *"
            value={form.status}
            options={STATUS_OPTIONS}
            onChange={(value) => setField("status", value)}
            disabled={submitting}
            fullWidth
          />

          <FormField
            label="Email de contacto (contact_email)"
            type="email"
            value={form.contact_email}
            onChange={(value) => setField("contact_email", value)}
            error={shownErrors.contact_email}
            disabled={submitting}
          />

          <fieldset className="sm:col-span-2">
            <legend className="mb-1 text-sm font-semibold text-red-700">Categorías (categories) *</legend>
            <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
              {CATEGORIES.map((category) => (
                <label key={category} className="flex items-center gap-2 text-sm text-black">
                  <input
                    type="checkbox"
                    checked={form.categories.includes(category)}
                    onChange={() => toggleCategory(category)}
                    disabled={submitting}
                    className="h-4 w-4 accent-red-700"
                  />
                  {category}
                </label>
              ))}
            </div>
            {shownErrors.categories && <span className="text-xs text-red-700">{shownErrors.categories}</span>}
          </fieldset>

          <label className="flex flex-col gap-1 text-sm text-black sm:col-span-2">
            <span className="font-semibold text-red-700">Notas internas (notes)</span>
            <textarea
              value={form.notes}
              onChange={(e) => setField("notes", e.target.value)}
              disabled={submitting}
              rows={3}
              maxLength={1000}
              className="w-full rounded-md border border-red-200 px-3 py-2 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
            />
          </label>
        </div>

        {apiFailure && (
          <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <p className="font-semibold">{apiFailure.message}</p>
            {apiFailure.details.length > 0 && (
              <ul className="mt-1 list-disc pl-5">
                {apiFailure.details.map((detail) => {
                  const label = fieldLabel(detail.field);
                  return (
                    <li key={`${detail.field}-${detail.message}`}>
                      {label && <span className="font-semibold">{label}: </span>}
                      {detail.message}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-wrap justify-end gap-3">
          <Button variant="secondary" size="md" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" size="md" disabled={submitting}>
            {submitting ? "Registrando..." : "Registrar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
