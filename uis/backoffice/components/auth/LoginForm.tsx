"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import PasswordField from "@/components/PasswordField";
import FormAlert from "@/components/auth/FormAlert";
import { login } from "@/lib/auth/api";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { safeNext, type LoginReason } from "@/lib/auth/navigation";
import { setToken } from "@/lib/auth/token";
import { validateLogin, type FieldErrors, type LoginValues } from "@/lib/auth/validation";

const REASON_MESSAGES: Record<LoginReason, string> = {
  expired: "Tu sesión ha caducado o no es válida. Vuelve a iniciar sesión.",
  inactive: "Tu cuenta está desactivada. Contacta con un administrador.",
};

const FIELDS = ["email", "password"] as const;

function isLoginReason(value: string | null): value is LoginReason {
  return value === "expired" || value === "inactive";
}

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const reason = searchParams.get("reason");

  const [values, setValues] = useState<LoginValues>({ email: "", password: "" });
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<FieldErrors<LoginValues>>({});
  const [apiMessage, setApiMessage] = useState<string | null>(null);

  const errors = attempted ? validateLogin(values) : {};
  const shown = { ...errors, ...apiFields };

  function setField(field: keyof LoginValues, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setApiFields((prev) => ({ ...prev, [field]: undefined }));
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    if (Object.keys(validateLogin(values)).length > 0) return;

    setSubmitting(true);
    setApiMessage(null);
    setApiFields({});
    try {
      const { access_token } = await login(values.email.trim(), values.password);
      setToken(access_token);
      router.replace(safeNext(next));
    } catch (err) {
      const result = formErrorsFromApi(err, FIELDS, "No se pudo iniciar sesión.");
      setApiFields(result.fields);
      setApiMessage(result.message);
      setSubmitting(false);
    }
  }

  const registerHref = next ? `/register?next=${encodeURIComponent(next)}` : "/register";

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-red-700 md:text-2xl">Iniciar sesión</h1>

      {isLoginReason(reason) && !apiMessage && <FormAlert tone="info">{REASON_MESSAGES[reason]}</FormAlert>}
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
        disabled={submitting}
        name="password"
        autoComplete="current-password"
      />

      <Button type="submit" size="md" disabled={submitting}>
        {submitting ? "Entrando..." : "Entrar"}
      </Button>

      <p className="text-center text-sm text-black">
        ¿No tienes cuenta?{" "}
        <Link href={registerHref} className="font-semibold text-red-700 underline hover:text-red-800">
          Regístrate
        </Link>
      </p>
    </form>
  );
}
