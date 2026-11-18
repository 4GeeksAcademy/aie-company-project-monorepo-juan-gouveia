"use client";

import Link from "next/link";
import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import FormAlert from "@/components/auth/FormAlert";
import { forgotPassword } from "@/lib/auth/api";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { emailError } from "@/lib/auth/validation";

// Mismo texto que la API: no dice si el email está registrado (evita la enumeración de usuarios).
const CONFIRMATION = "Si esa dirección está registrada, recibirás un enlace en breve.";

// Solicitud del enlace de restablecimiento (ticket AUTH-03). Tras el envío, el formulario queda
// desactivado para evitar peticiones duplicadas. Solo vuelve a activarse si la petición no llegó
// a la API (sin conexión, API caída): en ese caso no se envió nada y hay que reintentar.
export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const shownError = fieldError ?? (attempted ? emailError(email) : null);
  const locked = submitting || sent;

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (locked) return;
    setAttempted(true);
    if (emailError(email)) return;

    setSubmitting(true);
    setError(null);
    setFieldError(null);
    try {
      await forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      const result = formErrorsFromApi(err, ["email"] as const, "No se pudo enviar la solicitud.");
      setFieldError(result.fields.email ?? null);
      setError(result.fields.email ? null : result.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-red-700 md:text-2xl">¿Olvidaste tu contraseña?</h1>

      {sent ? (
        <FormAlert tone="success">{CONFIRMATION}</FormAlert>
      ) : (
        <p className="text-sm text-black">
          Escribe el email de tu cuenta y te enviaremos un enlace para elegir una contraseña nueva.
        </p>
      )}
      {error && <FormAlert>{error}</FormAlert>}

      <FormField
        label="Email"
        type="email"
        value={email}
        onChange={(value) => {
          setEmail(value);
          setFieldError(null);
        }}
        required
        error={shownError}
        disabled={locked}
        inputProps={{ autoComplete: "email", name: "email" }}
      />

      <Button type="submit" size="md" disabled={locked}>
        {submitting ? "Enviando..." : sent ? "Enlace solicitado" : "Enviar enlace"}
      </Button>

      <p className="text-center text-sm text-black">
        <Link href="/login" className="font-semibold text-red-700 underline hover:text-red-800">
          Volver a iniciar sesión
        </Link>
      </p>
    </form>
  );
}
