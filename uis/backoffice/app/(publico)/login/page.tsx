import type { Metadata } from "next";
import { Suspense } from "react";
import LoadingMessage from "@/components/LoadingMessage";
import LoginForm from "@/components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Iniciar sesión",
  description: "Acceso del personal de Brasaland al backoffice.",
};

// LoginForm lee ?next= y ?reason= con useSearchParams, que necesita un Suspense para el build.
export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingMessage compact>Cargando...</LoadingMessage>}>
      <LoginForm />
    </Suspense>
  );
}
