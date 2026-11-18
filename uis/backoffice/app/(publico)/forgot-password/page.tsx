import type { Metadata } from "next";
import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export const metadata: Metadata = {
  title: "Recuperar contraseña",
  description: "Solicita un enlace para restablecer la contraseña del backoffice de Brasaland.",
};

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
