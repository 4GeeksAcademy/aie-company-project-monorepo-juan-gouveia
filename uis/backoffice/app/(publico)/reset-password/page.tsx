import type { Metadata } from "next";
import { Suspense } from "react";
import LoadingMessage from "@/components/LoadingMessage";
import ResetPasswordForm from "@/components/auth/ResetPasswordForm";

export const metadata: Metadata = {
  title: "Restablecer contraseña",
  description: "Elige una contraseña nueva para el backoffice de Brasaland.",
  // La URL lleva el token de restablecimiento: el navegador no debe enviarla como Referer a otros sitios.
  referrer: "no-referrer",
};

// ResetPasswordForm lee ?token= con useSearchParams, que necesita un Suspense para el build.
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<LoadingMessage compact>Cargando...</LoadingMessage>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
