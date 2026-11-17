import Button from "@/components/Button";
import ErrorMessage from "@/components/ErrorMessage";

interface RetryableErrorProps {
  // Texto del error (normalmente el de toUserMessage).
  children: React.ReactNode;
  onRetry: () => void;
  // Versión pequeña para secciones dentro de una página (la de ErrorMessage).
  compact?: boolean;
}

// Error de carga de un bloque con el botón "Reintentar". role="alert" hace que los lectores de
// pantalla lo anuncien al aparecer, así que todos los bloques avisan igual.
export default function RetryableError({ children, onRetry, compact = false }: RetryableErrorProps) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3">
      <ErrorMessage compact={compact}>{children}</ErrorMessage>
      <Button variant="secondary" onClick={onRetry}>
        Reintentar
      </Button>
    </div>
  );
}
