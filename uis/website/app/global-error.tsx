"use client";

import "./globals.css";
import ErrorScreen from "@/components/ErrorScreen";

// Último recurso: errores en el layout raíz. Sustituye al documento entero, así que define su
// propio <html> y <body> y carga los estilos globales. No admite `metadata`: el título va con <title>.
// No se muestra `error.message` ni `error.digest`: pueden contener detalles internos.
export default function GlobalError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="es">
      <body className="bg-gray-100">
        <title>Brasaland: algo salió mal</title>
        <main>
          <ErrorScreen
            title="Algo salió mal"
            message="El sitio no pudo cargarse por un problema inesperado. Vuelve a intentarlo en unos minutos."
            onRetry={retry}
          />
        </main>
      </body>
    </html>
  );
}
