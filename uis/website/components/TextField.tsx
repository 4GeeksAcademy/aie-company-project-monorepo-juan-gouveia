import FieldError from "@/components/FieldError";
import RequiredMark from "@/components/RequiredMark";

interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  error?: string;
  // Etiqueta y campo en una sola fila, con el ancho natural del campo.
  inline?: boolean;
}

export default function TextField({
  id,
  label,
  value,
  onChange,
  onBlur,
  type = "text",
  placeholder,
  required = false,
  error,
  inline = false,
}: TextFieldProps) {
  const errorId = `${id}-error`;

  return (
    <div className="flex flex-col gap-2">
      <div className={inline ? "flex items-center gap-3" : "flex flex-col gap-2"}>
        <label htmlFor={id} className={`text-gray-700 ${inline ? "whitespace-nowrap" : ""}`.trim()}>
          {label} {required && <RequiredMark />}
        </label>
        <input
          id={id}
          type={type}
          name={id}
          value={value}
          placeholder={placeholder}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          onChange={(event) => onChange(event.target.value)}
          onBlur={onBlur}
          className={`${inline ? "" : "w-full "}rounded border border-gray-300 px-3 py-2 focus:border-red-500 focus:outline-none`}
        />
      </div>
      <FieldError id={errorId} message={error} />
    </div>
  );
}
