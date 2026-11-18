import type { Metadata } from "next";
import { Suspense } from "react";
import LoadingMessage from "@/components/LoadingMessage";
import RegisterForm from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Crear cuenta",
  description: "Registro del personal de Brasaland en el backoffice.",
};

// RegisterForm lee ?next= con useSearchParams, que necesita un Suspense para el build.
export default function RegisterPage() {
  return (
    <Suspense fallback={<LoadingMessage compact>Cargando...</LoadingMessage>}>
      <RegisterForm />
    </Suspense>
  );
}
