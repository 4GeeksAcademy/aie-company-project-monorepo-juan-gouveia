"use client";

import { useId, useState } from "react";

interface PasswordFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  // Mensaje de error mostrado en rojo bajo el campo; null/undefined = sin error.
  error?: string | null;
  // Texto de ayuda bajo el campo (por ejemplo, la longitud mínima).
  hint?: string;
  disabled?: boolean;
  name?: string;
  autoComplete?: "current-password" | "new-password";
}

// Campo de contraseña con un botón para mostrarla u ocultarla. Mismo estilo que FormField.
// El botón queda fuera del <label> para que su texto no forme parte del nombre del campo.
export default function PasswordField({
  label,
  value,
  onChange,
  required = false,
  error,
  hint,
  disabled,
  name,
  autoComplete,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const inputId = useId();
  const hintId = `${inputId}-hint`;

  return (
    <div className="flex flex-col gap-1 text-sm text-black">
      <label htmlFor={inputId} className="font-semibold text-red-700">
        {label}
        {required && " *"}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          name={name}
          autoComplete={autoComplete}
          aria-invalid={Boolean(error)}
          aria-describedby={hint ? hintId : undefined}
          className="w-full rounded-md border border-red-200 py-2 pl-3 pr-20 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => setVisible((prev) => !prev)}
          disabled={disabled}
          aria-controls={inputId}
          aria-pressed={visible}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          className="absolute inset-y-1 right-1 rounded px-2 text-xs font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        >
          {visible ? "Ocultar" : "Mostrar"}
        </button>
      </div>
      {hint && (
        <span id={hintId} className="text-xs text-gray-600">
          {hint}
        </span>
      )}
      {error && <span className="text-xs text-red-700">{error}</span>}
    </div>
  );
}
