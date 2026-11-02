import FieldError from "@/components/FieldError";
import RequiredMark from "@/components/RequiredMark";
import type { Option } from "@/lib/locations";

interface SelectFieldProps {
  id: string;
  label: string;
  value: string;
  options: Option[];
  placeholder: string;
  onChange: (value: string) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
}

export default function SelectField({
  id,
  label,
  value,
  options,
  placeholder,
  onChange,
  required = false,
  disabled = false,
  error,
}: SelectFieldProps) {
  const errorId = `${id}-error`;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-gray-700">
        {label} {required && <RequiredMark />}
      </label>
      <select
        id={id}
        name={id}
        value={value}
        required={required}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded border border-gray-300 px-3 py-2 focus:border-red-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <FieldError id={errorId} message={error} />
    </div>
  );
}
