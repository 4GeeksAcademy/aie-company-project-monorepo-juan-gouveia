interface TooltipProps {
  // Texto del tooltip. Es solo visual: el control que envuelve debe tener su propio aria-label.
  label: string;
  children: React.ReactNode;
  // Lado al que se alinea bajo el control. "end" (por defecto) evita que se salga por la derecha
  // cuando el control está al final de la cabecera.
  align?: "start" | "end";
}

// Tooltip propio, solo con CSS: aparece al pasar el ratón y al llegar con el teclado (foco visible),
// no al tocar. En Tailwind 4, `hover` solo se aplica en dispositivos que admiten pasar el puntero por
// encima, así que en pantallas táctiles no se muestra; ahí basta el aria-label del control.
export default function Tooltip({ label, children, align = "end" }: TooltipProps) {
  return (
    <span className="group relative inline-flex">
      {children}
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute top-full z-50 mt-1 hidden max-w-64 truncate whitespace-nowrap rounded bg-red-800 px-2 py-1 text-xs font-semibold text-white shadow-md group-hover:block group-has-[:focus-visible]:block ${
          align === "end" ? "right-0" : "left-0"
        }`}
      >
        {label}
      </span>
    </span>
  );
}
