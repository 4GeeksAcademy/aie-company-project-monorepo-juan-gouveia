import type { Metadata } from "next";
import BackLink from "@/components/BackLink";
import ChangePasswordForm from "@/components/account/ChangePasswordForm";

export const metadata: Metadata = {
  title: "Cambiar contraseña",
  description: "Cambio de la contraseña de la cuenta con la sesión iniciada.",
};

export default function ChangePasswordPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-3xl lg:px-8">
      <BackLink href="/account/profile">Volver a Mi perfil</BackLink>
      <h1 className="mb-6 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Cambiar contraseña</h1>
      <section className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
        <ChangePasswordForm />
      </section>
    </main>
  );
}
