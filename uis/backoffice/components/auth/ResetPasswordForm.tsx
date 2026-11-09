"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Button from "@/components/Button";
import LoadingMessage from "@/components/LoadingMessage";
import PasswordField from "@/components/PasswordField";
import FormAlert from "@/components/auth/FormAlert";
import { ApiError } from "@/lib/api-client";
import { resetPassword, validateResetToken } from "@/lib/auth/api";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import {
  MIN_PASSWORD_LENGTH,
  mergeFieldErrors,
  validateNewPassword,
  type FieldErrors,
  type NewPasswordValues,
} from "@/lib/auth/validation";
import { toUserMessage } from "@/lib/error-message";

const MISSING_TOKEN = "El enlace de restablecimiento no es válido. Solicita uno nuevo.";

// "checking": se está comprobando el enlace con la API; "ready": el formulario se puede usar;
// "unusable": el enlace no sirve (falta, no es válido, caducó o ya se usó).
type LinkStatus = "checking" | "ready" | "unusable";

// Nueva contraseña a partir del enlace del correo (ticket AUTH-03). El token llega en ?token=.
// Al abrir la página se comprueba el enlace con la API (sin usarlo), para avisar enseguida si no
// sirve en vez de después de escribir la contraseña. Al guardar, la API vuelve a comprobarlo.
export default function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token");

  const [status, setStatus] = useState<LinkStatus>(token ? "checking" : "unusable");
  const [linkError, setLinkError] = useState<string>(MISSING_TOKEN);
  const [values, setValues] = useState<NewPasswordValues>({ newPassword: "", confirmPassword: "" });
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<FieldErrors<NewPasswordValues>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    validateResetToken(token)
      .then(() => {
        if (active) setStatus("ready");
      })
      .catch((err: unknown) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 400) {
          setLinkError(err.message);
          setStatus("unusable");
        } else {
          // Sin conexión o API caída: no se sabe si el enlace sirve. Se deja intentar; al guardar,
          // la API lo comprobará de nuevo.
          setError(toUserMessage(err, "No se pudo comprobar el enlace. Puedes elegir la contraseña igualmente: se comprobará al guardarla."));
          setStatus("ready");
        }
      });
    return () => {
      active = false;
    };
  }, [token]);

  const shown = mergeFieldErrors(attempted ? validateNewPassword(values) : {}, apiFields);

  function setField(field: keyof NewPasswordValues, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setApiFields((prev) => ({ ...prev, [field]: undefined }));
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    if (!token || Object.keys(validateNewPassword(values)).length > 0) return;

    setSubmitting(true);
    setError(null);
    setApiFields({});
    try {
      await resetPassword(token, values.newPassword);
      router.replace("/login?reset=success");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        // El enlace dejó de servir entre la comprobación inicial y el envío (por ejemplo, caducó).
        setLinkError(err.message);
        setStatus("unusable");
      } else {
        // La API nombra el campo `new_password`; aquí se llama `newPassword`.
        const result = formErrorsFromApi(err, ["new_password"] as const, "No se pudo restablecer la contraseña.");
        if (result.fields.new_password) setApiFields({ newPassword: result.fields.new_password });
        setError(result.fields.new_password ? null : result.message);
      }
      setSubmitting(false);
    }
  }

  if (status === "checking") {
    return <LoadingMessage compact>Comprobando el enlace...</LoadingMessage>;
  }

  if (status === "unusable") {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-red-700 md:text-2xl">Restablecer contraseña</h1>
        <FormAlert>{linkError}</FormAlert>
        <Link
          href="/forgot-password"
          className="rounded-md bg-red-700 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
        >
          Solicitar un nuevo enlace
        </Link>
        <p className="text-center text-sm text-black">
          <Link href="/login" className="font-semibold text-red-700 underline hover:text-red-800">
            Volver a iniciar sesión
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-red-700 md:text-2xl">Elige una contraseña nueva</h1>

      {error && <FormAlert>{error}</FormAlert>}

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

      <Button type="submit" size="md" disabled={submitting}>
        {submitting ? "Guardando..." : "Guardar contraseña"}
      </Button>

      <p className="text-center text-sm text-black">
        <Link href="/login" className="font-semibold text-red-700 underline hover:text-red-800">
          Volver a iniciar sesión
        </Link>
      </p>
    </form>
  );
}
