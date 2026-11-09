import Link from "next/link";

interface ErrorScreenProps {
  title: string;
  message: string;
  // Si se pasa, se muestra "Reintentar" (los límites de error de Next.js pasan su `retry`).
  onRetry?: () => void;
}

const ACTION_CLASS =
  "inline-flex items-center justify-center rounded-md px-5 py-3 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 md:text-base";

// Pantalla de error de página completa: los límites de error (error.tsx, global-error.tsx) y la
// página 404. Nunca muestra el error original: solo un texto legible y una salida clara.
export default function ErrorScreen({ title, message, onRetry }: ErrorScreenProps) {
  return (
    <section role="alert" className="mx-auto flex max-w-xl flex-col items-center gap-4 px-3 py-12 text-center md:px-4">
      <h1 className="text-3xl font-bold text-gray-800 sm:text-4xl">{title}</h1>
      <p className="text-lg text-gray-600">{message}</p>
      <div className="flex flex-wrap justify-center gap-3">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className={`${ACTION_CLASS} bg-red-700 text-white shadow-sm hover:bg-red-800`}
          >
            Reintentar
          </button>
        )}
        <Link href="/" className={`${ACTION_CLASS} border border-red-200 bg-white text-red-700 hover:bg-red-50`}>
          Volver a la página principal
        </Link>
      </div>
    </section>
  );
}
