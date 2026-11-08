import { useId } from "react";

interface TextAreaFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  // Mensaje de error mostrado en rojo bajo el campo; null/undefined = sin error.
  error?: string | null;
  // Texto de ayuda bajo el campo (por ejemplo, el límite de caracteres).
  hint?: string;
  disabled?: boolean;
  rows?: number;
  // "lg": campo y texto más grandes, para formularios que se usan en pantallas táctiles.
  size?: "md" | "lg";
  textareaProps?: Omit<
    React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    "value" | "onChange" | "disabled" | "rows"
  >;
}

const SIZE_CLASS = {
  md: "px-3 py-2 text-sm",
  lg: "px-4 py-3 text-base",
};

// Campo de texto de varias líneas, con el mismo estilo que FormField.
export default function TextAreaField({
  label,
  value,
  onChange,
  required = false,
  error,
  hint,
  disabled,
  rows = 4,
  size = "md",
  textareaProps,
}: TextAreaFieldProps) {
  const hintId = useId();
  return (
    <label className="flex flex-col gap-1 text-sm text-black">
      <span className={`font-semibold text-red-700 ${size === "lg" ? "text-base" : ""}`}>
        {label}
        {required && " *"}
      </span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={rows}
        aria-invalid={Boolean(error)}
        aria-describedby={hint ? hintId : undefined}
        className={`w-full resize-y rounded-md border border-red-200 text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60 ${SIZE_CLASS[size]}`}
        {...textareaProps}
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
