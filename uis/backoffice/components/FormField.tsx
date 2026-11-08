import { useId } from "react";

interface FormFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  // Mensaje de error mostrado en rojo bajo el campo; null/undefined = sin error.
  error?: string | null;
  // Texto de ayuda bajo el campo (por ejemplo, el límite de caracteres).
  hint?: string;
  disabled?: boolean;
  // "lg": campo y texto más grandes, para formularios que se usan en pantallas táctiles.
  size?: "md" | "lg";
  inputProps?: Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    "value" | "onChange" | "type" | "disabled"
  >;
}

const SIZE_CLASS = {
  md: "px-3 py-2 text-sm",
  lg: "px-4 py-3 text-base",
};

export default function FormField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  error,
  hint,
  disabled,
  size = "md",
  inputProps,
}: FormFieldProps) {
  const hintId = useId();
  return (
    <label className="flex flex-col gap-1 text-sm text-black">
      <span className={`font-semibold text-red-700 ${size === "lg" ? "text-base" : ""}`}>
        {label}
        {required && " *"}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={hint ? hintId : undefined}
        className={`w-full rounded-md border border-red-200 text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60 ${SIZE_CLASS[size]}`}
        {...inputProps}
      />
      {hint && (
        <span id={hintId} className="text-xs text-gray-600">
          {hint}
        </span>
      )}
      {error && <span className="text-xs text-red-700">{error}</span>}
    </label>
  );
}
