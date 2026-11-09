"use client";

import ErrorScreen from "@/components/ErrorScreen";

// Límite de error de las herramientas. Está dentro del layout protegido, así que la cabecera y la
// sesión siguen visibles. No se muestra `error.message` ni `error.digest`: pueden contener detalles internos.
export default function ProtegidoError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <main className="px-3 py-10 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <ErrorScreen
        title="No se pudo mostrar esta página"
        message="Ocurrió un problema inesperado al cargar esta herramienta. Vuelve a intentarlo; si el problema continúa, regresa al inicio y prueba más tarde."
        onRetry={retry}
      />
    </main>
  );
}
