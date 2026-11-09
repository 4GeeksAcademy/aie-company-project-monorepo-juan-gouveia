"use client";

import ErrorScreen from "@/components/ErrorScreen";
import RegistrationHeader from "@/components/RegistrationHeader";

// Límite de error del sitio: cualquier página por debajo del layout raíz.
// No se muestra `error.message` ni `error.digest`: pueden contener detalles internos.
export default function SiteError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <>
      <RegistrationHeader />
      {/* La cabecera es fija: el contenido empieza por debajo. */}
      <main className="pt-24">
        <ErrorScreen
          title="Algo salió mal"
          message="No pudimos mostrar esta página por un problema inesperado. Vuelve a intentarlo o regresa a la página principal."
          onRetry={retry}
        />
      </main>
    </>
  );
}
