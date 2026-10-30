interface LoadingMessageProps {
  children: React.ReactNode;
  // Versión pequeña para secciones dentro de una página.
  compact?: boolean;
}

export default function LoadingMessage({ children, compact = false }: LoadingMessageProps) {
  return (
    <p className={compact ? "text-sm text-black" : "text-center text-black md:text-base lg:text-lg"}>
      {children}
    </p>
  );
}
