import FieldError from "@/components/FieldError";
import RequiredMark from "@/components/RequiredMark";

interface CheckboxFieldProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  required?: boolean;
  error?: string;
}

export default function CheckboxField({
  id,
  label,
  checked,
  onChange,
  required = false,
  error,
}: CheckboxFieldProps) {
  const errorId = `${id}-error`;

  return (
    <div>
      <label htmlFor={id} className="flex items-center gap-2 text-gray-700">
        <input
          id={id}
          type="checkbox"
          name={id}
          checked={checked}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          onChange={(event) => onChange(event.target.checked)}
          className="h-4 w-4 rounded border border-red-200 text-red-600 focus:ring-red-500"
        />
        <span>
          {label} {required && <RequiredMark />}
        </span>
      </label>
      <FieldError id={errorId} message={error} />
    </div>
  );
}
