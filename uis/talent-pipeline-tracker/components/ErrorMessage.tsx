interface ErrorMessageProps {
  children: React.ReactNode;
  // Versión pequeña para secciones dentro de una página.
  compact?: boolean;
}

export default function ErrorMessage({ children, compact = false }: ErrorMessageProps) {
  return (
    <p
      className={
        compact
          ? "text-sm text-red-700"
          : "rounded-lg border border-red-200 bg-white p-4 text-red-700 shadow-md"
      }
    >
      {children}
    </p>
  );
}
