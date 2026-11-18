"use client";

import ErrorScreen from "@/components/ErrorScreen";
import Header from "@/components/Header";

// Límite de error de la aplicación: páginas públicas (login, registro, contraseña) y los layouts de
// cada grupo, incluido el de la zona protegida. Sustituye a esos layouts, así que pone su propia cabecera.
// No se muestra `error.message` ni `error.digest`: pueden contener detalles internos.
export default function AppError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <>
      <Header minimal />
      <main className="px-3 py-10 md:px-4">
        <ErrorScreen
          title="Algo salió mal"
          message="Ocurrió un problema inesperado al cargar esta página. Vuelve a intentarlo; si el problema continúa, regresa al inicio y prueba más tarde."
          onRetry={retry}
        />
      </main>
    </>
  );
}
