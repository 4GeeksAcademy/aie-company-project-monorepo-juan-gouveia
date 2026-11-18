"use client";

import { useState } from "react";
import Button from "@/components/Button";
import PasswordField from "@/components/PasswordField";
import FormAlert from "@/components/auth/FormAlert";
import { ApiError } from "@/lib/api-client";
import { changePassword } from "@/lib/auth/api";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { setToken } from "@/lib/auth/token";
import {
  MIN_PASSWORD_LENGTH,
  mergeFieldErrors,
  validateChangePassword,
  type ChangePasswordValues,
  type FieldErrors,
} from "@/lib/auth/validation";

const EMPTY: ChangePasswordValues = { currentPassword: "", newPassword: "", confirmPassword: "" };

// Nombres de los campos en la API (detalles de los 422).
const API_FIELDS = ["current_password", "new_password"] as const;

// Cambio de contraseña con sesión (ticket AUTH-03). La nueva y su confirmación deben coincidir antes
// de llamar a la API. Con éxito, la API invalida los tokens anteriores y devuelve uno nuevo, que se
// guarda para seguir en la sesión; las demás pestañas lo leen de localStorage.
export default function ChangePasswordForm() {
  const [values, setValues] = useState<ChangePasswordValues>(EMPTY);
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<FieldErrors<ChangePasswordValues>>({});
  const [message, setMessage] = useState<{ tone: "error" | "success"; text: string } | null>(null);

  const shown = mergeFieldErrors(attempted ? validateChangePassword(values) : {}, apiFields);

  function setField(field: keyof ChangePasswordValues, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setApiFields((prev) => ({ ...prev, [field]: undefined }));
    setMessage(null);
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    setMessage(null);
    if (Object.keys(validateChangePassword(values)).length > 0) return;

    setSubmitting(true);
    setApiFields({});
    try {
      const result = await changePassword(values.currentPassword, values.newPassword);
      setToken(result.access_token);
      setValues(EMPTY);
      setAttempted(false);
      setMessage({ tone: "success", text: "Contraseña actualizada." });
    } catch (err) {
      if (err instanceof ApiError && err.code === "invalid_current_password") {
        setApiFields({ currentPassword: err.message });
      } else {
        const result = formErrorsFromApi(err, API_FIELDS, "No se pudo cambiar la contraseña.");
        setApiFields({
          currentPassword: result.fields.current_password,
          newPassword: result.fields.new_password,
        });
        if (result.message) setMessage({ tone: "error", text: result.message });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      {message && <FormAlert tone={message.tone}>{message.text}</FormAlert>}

      <PasswordField
        label="Contraseña actual"
        value={values.currentPassword}
        onChange={(value) => setField("currentPassword", value)}
        required
        error={shown.currentPassword}
        disabled={submitting}
        name="current-password"
        autoComplete="current-password"
      />
      <PasswordField
        label="Contraseña nueva"
        value={values.newPassword}
        onChange={(value) => setField("newPassword", value)}
        required
        error={shown.newPassword}
        hint={`Al menos ${MIN_PASSWORD_LENGTH} caracteres.`}
        disabled={submitting}
        name="new-password"
        autoComplete="new-password"
      />
      <PasswordField
        label="Repite la contraseña nueva"
        value={values.confirmPassword}
        onChange={(value) => setField("confirmPassword", value)}
        required
        error={shown.confirmPassword}
        disabled={submitting}
        name="confirm-password"
        autoComplete="new-password"
      />
      <p className="text-xs text-gray-600">Al cambiarla se cerrarán las sesiones abiertas en otros dispositivos.</p>

      <div className="flex justify-end">
        <Button type="submit" size="md" disabled={submitting}>
          {submitting ? "Guardando..." : "Cambiar contraseña"}
        </Button>
      </div>
    </form>
  );
}
