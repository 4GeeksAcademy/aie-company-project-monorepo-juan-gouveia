import Link from "next/link";
import Button from "@/components/Button";

interface ErrorScreenProps {
  title: string;
  message: string;
  // Si se pasa, se muestra "Reintentar" (los límites de error de Next.js pasan su `retry`).
  onRetry?: () => void;
}

// Pantalla de error de página completa: los límites de error (error.tsx, global-error.tsx) y la
// página 404. Nunca muestra el error original: solo un texto legible y una salida clara.
export default function ErrorScreen({ title, message, onRetry }: ErrorScreenProps) {
  return (
    <div role="alert" className="mx-auto flex max-w-md flex-col items-center gap-4 text-center">
      <h1 className="text-xl font-semibold text-red-700 md:text-2xl">{title}</h1>
      <p className="text-sm text-black md:text-base">{message}</p>
      <div className="flex flex-wrap justify-center gap-3">
        {onRetry && (
          <Button size="md" onClick={onRetry}>
            Reintentar
          </Button>
        )}
        <Link
          href="/"
          className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
