"use client";

import { useId, useState } from "react";

interface FileDropzoneProps {
  onFileSelected: (file: File) => void;
  // Extensiones o tipos aceptados por el selector, p. ej. ".csv". Al soltar no se filtra:
  // la validación real la hace quien recibe el archivo.
  accept?: string;
  label?: string;
  hint?: string;
  fileName?: string;
  disabled?: boolean;
}

// Zona para arrastrar y soltar un archivo, con un selector accesible como alternativa.
export default function FileDropzone({
  onFileSelected,
  accept,
  label = "Arrastra un archivo aquí o haz clic para elegirlo",
  hint,
  fileName,
  disabled = false,
}: FileDropzoneProps) {
  const inputId = useId();
  const hintId = useId();
  const [dragging, setDragging] = useState(false);

  function handleDragOver(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (!disabled) setDragging(true);
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (!disabled && file) onFileSelected(file);
  }

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onFileSelected(file);
    // Permite volver a elegir el mismo archivo.
    event.target.value = "";
  }

  const stateClass = disabled
    ? "cursor-not-allowed border-gray-200 bg-gray-50 text-gray-400"
    : dragging
      ? "cursor-copy border-red-700 bg-red-50 text-red-700"
      : "cursor-pointer border-red-200 bg-white text-black hover:border-red-700 hover:bg-red-50";

  return (
    <label
      htmlFor={inputId}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center shadow-md focus-within:ring-2 focus-within:ring-red-700 focus-within:ring-offset-2 md:p-10 ${stateClass}`}
    >
      <input
        id={inputId}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={handleChange}
        aria-describedby={hint ? hintId : undefined}
        className="sr-only"
      />
      <span className="text-sm font-semibold md:text-base">{label}</span>
      {hint && (
        <span id={hintId} className="text-xs text-gray-600 md:text-sm">
          {hint}
        </span>
      )}
      {fileName && (
        <span className="mt-1 break-all text-sm font-medium text-red-700">{fileName}</span>
      )}
    </label>
  );
}
