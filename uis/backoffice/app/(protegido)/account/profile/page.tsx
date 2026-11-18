import type { Metadata } from "next";
import AccountProfile from "@/components/account/AccountProfile";

export const metadata: Metadata = {
  title: "Mi perfil",
  description: "Email de la cuenta, nombre y datos de contacto.",
};

export default function AccountProfilePage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-3xl lg:px-8">
      <h1 className="mb-6 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Mi perfil</h1>
      <AccountProfile />
    </main>
  );
}
