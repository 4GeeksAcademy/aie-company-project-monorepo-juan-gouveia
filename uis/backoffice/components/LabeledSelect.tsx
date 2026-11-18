interface LabeledSelectProps<T extends string> {
  label: string;
  value: string;
  options: Record<T, string>;
  onChange: (value: T) => void;
  disabled?: boolean;
  // Oculta la etiqueta visualmente (sigue disponible para lectores de pantalla).
  hideLabel?: boolean;
  // Ancho completo del contenedor; por defecto se ajusta a la opción más larga.
  fullWidth?: boolean;
  // Si se define, añade una opción con value "" (por eso onChange puede recibir "").
  placeholder?: string;
  // Contenido bajo el select (p. ej. mensajes de estado o error).
  children?: React.ReactNode;
  // "lg": select y texto más grandes, para formularios que se usan en pantallas táctiles.
  size?: "md" | "lg";
  required?: boolean;
  // Marca el select como inválido para los lectores de pantalla (el mensaje va en children).
  invalid?: boolean;
}

const SIZE_CLASS = {
  md: "px-3 py-2 text-sm",
  lg: "px-4 py-3 text-base",
};

export default function LabeledSelect<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled,
  hideLabel = false,
  fullWidth = false,
  placeholder,
  children,
  size = "md",
  required = false,
  invalid = false,
}: LabeledSelectProps<T>) {
  const labelClass = hideLabel ? "sr-only" : `font-semibold text-red-700 ${size === "lg" ? "text-base" : ""}`;
  return (
    <label className="flex min-w-0 flex-col items-start gap-1 text-sm text-black">
      <span className={labelClass}>
        {label}
        {required && " *"}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        disabled={disabled}
        aria-invalid={invalid}
        className={`${fullWidth ? "w-full" : "w-auto"} max-w-full rounded-md border border-red-200 text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60 ${SIZE_CLASS[size]}`}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {(Object.entries(options) as [T, string][]).map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
      {children}
    </label>
  );
}
