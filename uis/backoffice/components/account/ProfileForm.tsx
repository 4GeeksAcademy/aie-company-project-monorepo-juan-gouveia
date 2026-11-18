"use client";

import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import FormAlert from "@/components/auth/FormAlert";
import { updateMyProfile } from "@/lib/auth/api";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { MAX_ADDRESS_LENGTH, MAX_NAME_LENGTH, MAX_PHONE_LENGTH } from "@/lib/auth/validation";
import type { Profile, ProfileFields } from "@/types/auth";

type Field = keyof ProfileFields;
type FormValues = Record<Field, string>;

const FIELDS: readonly Field[] = ["name", "phone", "address"];

function toFormValues(profile: Profile): FormValues {
  return { name: profile.name ?? "", phone: profile.phone ?? "", address: profile.address ?? "" };
}

// Valor que se envía a la API: sin espacios extremos, y null si queda vacío (vacía el campo).
function toApiValue(value: string): string | null {
  return value.trim() || null;
}

interface ProfileFormProps {
  profile: Profile;
  onSaved: (profile: Profile) => void;
}

// Edición de nombre y contacto con PUT /profiles/me. Solo se envían los campos que cambiaron.
export default function ProfileForm({ profile, onSaved }: ProfileFormProps) {
  const [saved, setSaved] = useState<FormValues>(() => toFormValues(profile));
  const [values, setValues] = useState<FormValues>(saved);
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<Field, string>>>({});
  const [message, setMessage] = useState<{ tone: "error" | "success"; text: string } | null>(null);

  const changed = FIELDS.filter((field) => toApiValue(values[field]) !== toApiValue(saved[field]));

  function setField(field: Field, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    setMessage(null);
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (changed.length === 0) return;

    setSubmitting(true);
    setFieldErrors({});
    setMessage(null);
    try {
      const updated = await updateMyProfile(
        Object.fromEntries(changed.map((field) => [field, toApiValue(values[field])]))
      );
      const next = toFormValues(updated);
      setSaved(next);
      setValues(next);
      setMessage({ tone: "success", text: "Cambios guardados." });
      onSaved(updated);
    } catch (err) {
      const result = formErrorsFromApi(err, FIELDS, "No se pudo guardar el perfil.");
      setFieldErrors(result.fields);
      if (result.message) setMessage({ tone: "error", text: result.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      {message && <FormAlert tone={message.tone}>{message.text}</FormAlert>}

      <FormField
        label="Nombre y Apellido"
        value={values.name}
        onChange={(value) => setField("name", value)}
        error={fieldErrors.name}
        disabled={submitting}
        inputProps={{ autoComplete: "name", name: "name", maxLength: MAX_NAME_LENGTH }}
      />
      <FormField
        label="Teléfono"
        type="tel"
        value={values.phone}
        onChange={(value) => setField("phone", value)}
        error={fieldErrors.phone}
        disabled={submitting}
        inputProps={{ autoComplete: "tel", name: "phone", maxLength: MAX_PHONE_LENGTH }}
      />
      <FormField
        label="Dirección"
        value={values.address}
        onChange={(value) => setField("address", value)}
        error={fieldErrors.address}
        disabled={submitting}
        inputProps={{ autoComplete: "street-address", name: "address", maxLength: MAX_ADDRESS_LENGTH }}
      />
      <p className="text-xs text-gray-600">Deja un campo vacío para borrarlo.</p>

      <div className="flex flex-wrap justify-end gap-3">
        <Button
          variant="secondary"
          size="md"
          onClick={() => {
            setValues(saved);
            setFieldErrors({});
            setMessage(null);
          }}
          disabled={submitting || changed.length === 0}
        >
          Descartar cambios
        </Button>
        <Button type="submit" size="md" disabled={submitting || changed.length === 0}>
          {submitting ? "Guardando..." : "Guardar cambios"}
        </Button>
      </div>
    </form>
  );
}
