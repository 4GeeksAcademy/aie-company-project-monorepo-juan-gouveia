"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import PasswordField from "@/components/PasswordField";
import FormAlert from "@/components/auth/FormAlert";
import { login, register } from "@/lib/auth/api";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { safeNext } from "@/lib/auth/navigation";
import { setToken } from "@/lib/auth/token";
import {
  MAX_ADDRESS_LENGTH,
  MAX_NAME_LENGTH,
  MAX_PHONE_LENGTH,
  MIN_PASSWORD_LENGTH,
  validateRegister,
  type FieldErrors,
  type RegisterValues,
} from "@/lib/auth/validation";

const EMPTY: RegisterValues = { email: "", password: "", name: "", phone: "", address: "" };

// Campos que la API puede señalar en `details`.
const API_FIELDS = ["email", "password", "name", "phone", "address"] as const;

export default function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";

  const [values, setValues] = useState<RegisterValues>(EMPTY);
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<FieldErrors<RegisterValues>>({});
  const [apiMessage, setApiMessage] = useState<string | null>(null);
  // La cuenta se creó pero el login automático falló: se invita a entrar a mano.
  const [createdWithoutSession, setCreatedWithoutSession] = useState(false);

  const errors = attempted ? validateRegister(values) : {};
  const shown = { ...errors, ...apiFields };

  function setField(field: keyof RegisterValues, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setApiFields((prev) => ({ ...prev, [field]: undefined }));
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    if (Object.keys(validateRegister(values)).length > 0) return;

    setSubmitting(true);
    setApiMessage(null);
    setApiFields({});

    const email = values.email.trim();
    try {
      // Los campos de perfil vacíos no se envían: son opcionales.
      await register({
        email,
        password: values.password,
        ...(values.name.trim() && { name: values.name.trim() }),
        ...(values.phone.trim() && { phone: values.phone.trim() }),
        ...(values.address.trim() && { address: values.address.trim() }),
      });
    } catch (err) {
      const result = formErrorsFromApi(err, API_FIELDS, "No se pudo crear la cuenta.");
      setApiFields(result.fields);
      setApiMessage(result.message);
      setSubmitting(false);
      return;
    }

    try {
      const { access_token } = await login(email, values.password);
      setToken(access_token);
      router.replace(safeNext(next));
    } catch {
      setCreatedWithoutSession(true);
      setSubmitting(false);
    }
  }

  if (createdWithoutSession) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-red-700 md:text-2xl">Cuenta creada</h1>
        <FormAlert tone="info">Tu cuenta se creó, pero no se pudo iniciar sesión automáticamente.</FormAlert>
        <Link
          href={loginHref}
          className="rounded-md bg-red-700 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-red-800"
        >
          Ir a iniciar sesión
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-red-700 md:text-2xl">Crear cuenta</h1>

      {apiMessage && <FormAlert>{apiMessage}</FormAlert>}

      <FormField
        label="Email"
        type="email"
        value={values.email}
        onChange={(value) => setField("email", value)}
        required
        error={shown.email}
        disabled={submitting}
        inputProps={{ autoComplete: "email", name: "email" }}
      />
      <PasswordField
        label="Contraseña"
        value={values.password}
        onChange={(value) => setField("password", value)}
        required
        error={shown.password}
        hint={`Al menos ${MIN_PASSWORD_LENGTH} caracteres.`}
        disabled={submitting}
        name="password"
        autoComplete="new-password"
      />

      <fieldset className="flex flex-col gap-4 border-t border-red-100 pt-4">
        <legend className="text-sm text-gray-600">Datos de perfil (opcionales)</legend>
        <FormField
          label="Nombre y Apellido"
          value={values.name}
          onChange={(value) => setField("name", value)}
          error={shown.name}
          disabled={submitting}
          inputProps={{ autoComplete: "name", name: "name", maxLength: MAX_NAME_LENGTH }}
        />
        <FormField
          label="Teléfono"
          type="tel"
          value={values.phone}
          onChange={(value) => setField("phone", value)}
          error={shown.phone}
          disabled={submitting}
          inputProps={{ autoComplete: "tel", name: "phone", maxLength: MAX_PHONE_LENGTH }}
        />
        <FormField
          label="Dirección"
          value={values.address}
          onChange={(value) => setField("address", value)}
          error={shown.address}
          disabled={submitting}
          inputProps={{ autoComplete: "street-address", name: "address", maxLength: MAX_ADDRESS_LENGTH }}
        />
      </fieldset>

      <Button type="submit" size="md" disabled={submitting}>
        {submitting ? "Creando cuenta..." : "Crear cuenta"}
      </Button>

      <p className="text-center text-sm text-black">
        ¿Ya tienes cuenta?{" "}
        <Link href={loginHref} className="font-semibold text-red-700 underline hover:text-red-800">
          Inicia sesión
        </Link>
      </p>
    </form>
  );
}
