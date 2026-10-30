interface FormFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  // Mensaje de error mostrado en rojo bajo el campo; null/undefined = sin error.
  error?: string | null;
  disabled?: boolean;
  inputProps?: Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    "value" | "onChange" | "type" | "disabled"
  >;
}

export default function FormField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  error,
  disabled,
  inputProps,
}: FormFieldProps) {
  return (
    <label className="flex flex-col gap-1 text-sm text-black">
      <span className="font-semibold text-red-700">
        {label}
        {required && " *"}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        className="w-full rounded-md border border-red-200 px-3 py-2 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        {...inputProps}
      />
      {error && <span className="text-xs text-red-700">{error}</span>}
    </label>
  );
}
