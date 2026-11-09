"use client";

import "./globals.css";
import ErrorScreen from "@/components/ErrorScreen";

// Último recurso: errores en el layout raíz. Sustituye al documento entero, así que define su
// propio <html> y <body> y carga los estilos globales. No admite `metadata`: el título va con <title>.
// No se muestra `error.message` ni `error.digest`: pueden contener detalles internos.
export default function GlobalError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-gray-100">
        <title>Error | Brasaland</title>
        <main className="px-3 py-10 md:px-4">
          <ErrorScreen
            title="El backoffice no está disponible"
            message="Ocurrió un problema inesperado y la aplicación no pudo cargarse. Vuelve a intentarlo en unos minutos."
            onRetry={retry}
          />
        </main>
      </body>
    </html>
  );
}
