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
}

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
}: LabeledSelectProps<T>) {
  return (
    <label className="flex min-w-0 flex-col items-start gap-1 text-sm text-black">
      <span className={hideLabel ? "sr-only" : "font-semibold text-red-700"}>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        disabled={disabled}
        className={`${fullWidth ? "w-full" : "w-auto"} max-w-full rounded-md border border-red-200 px-3 py-2 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60`}
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
