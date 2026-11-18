"use client";

import Button from "@/components/Button";
import ErrorMessage from "@/components/ErrorMessage";
import Header from "@/components/Header";
import LoadingMessage from "@/components/LoadingMessage";
import AccountMenu from "@/components/auth/AccountMenu";
import { useSession } from "@/hooks/useSession";

// Muestra la zona protegida solo con la sesión comprobada. Mientras tanto, ni la navegación
// ni la página: así no se ve contenido antes de saber si hay sesión.
export default function ProtectedShell({ children }: { children: React.ReactNode }) {
  const { status, error, refresh } = useSession();

  if (status === "authenticated") {
    return (
      <>
        <Header account={<AccountMenu />} />
        {children}
      </>
    );
  }

  return (
    <>
      <Header minimal />
      <main className="px-3 py-10 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
        {status === "error" ? (
          <div className="flex flex-col items-center gap-4">
            <ErrorMessage>{error}</ErrorMessage>
            <Button size="md" onClick={refresh}>
              Reintentar
            </Button>
          </div>
        ) : (
          <LoadingMessage>Comprobando la sesión...</LoadingMessage>
        )}
      </main>
    </>
  );
}
