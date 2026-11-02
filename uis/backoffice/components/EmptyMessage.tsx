interface EmptyMessageProps {
  children: React.ReactNode;
  // Versión pequeña para secciones dentro de una página.
  compact?: boolean;
}

export default function EmptyMessage({ children, compact = false }: EmptyMessageProps) {
  return (
    <p
      className={
        compact
          ? "text-sm text-black"
          : "rounded-lg border border-red-200 bg-white p-4 text-center text-black shadow-md"
      }
    >
      {children}
    </p>
  );
}
