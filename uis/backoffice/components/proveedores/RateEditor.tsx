"use client";

import { useId, useState } from "react";
import Button from "@/components/Button";
import { formatDateTime } from "@/lib/format";
import { updateRate } from "@/lib/proveedores/api";
import { formatRate } from "@/lib/proveedores/labels";
import { rateError } from "@/lib/proveedores/validation";
import type { Supplier } from "@/types/supplier";
import { toUserMessage } from "@/lib/error-message";

interface RateEditorProps {
  supplier: Supplier;
  onUpdated: (supplier: Supplier) => void;
}

// Muestra la tarifa vigente y la fecha de su último cambio, y permite editarla en la misma fila.
export default function RateEditor({ supplier, onUpdated }: RateEditorProps) {
  const inputId = useId();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validationError = editing ? rateError(value) : null;

  function startEditing() {
    setValue(String(supplier.rate_per_unit));
    setApiError(null);
    setEditing(true);
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (validationError) return;
    setSaving(true);
    setApiError(null);
    try {
      onUpdated(await updateRate(supplier.id, Number(value)));
      setEditing(false);
    } catch (err) {
      setApiError(toUserMessage(err, "No se pudo actualizar la tarifa. Inténtalo de nuevo."));
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="flex flex-col items-start gap-1">
        <span className="font-semibold text-black">{formatRate(supplier.rate_per_unit, supplier.currency)}</span>
        <span className="text-xs text-gray-600">Actualizada: {formatDateTime(supplier.updated_at)}</span>
        <button
          type="button"
          onClick={startEditing}
          aria-label={`Actualizar la tarifa de ${supplier.name}`}
          className="text-xs font-semibold text-red-700 underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
        >
          Actualizar tarifa
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col items-start gap-1">
      <label htmlFor={inputId} className="text-xs font-semibold text-red-700">
        Nueva tarifa ({supplier.currency})
      </label>
      <input
        id={inputId}
        type="number"
        min="0"
        step="any"
        inputMode="decimal"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={saving}
        aria-invalid={Boolean(validationError)}
        autoFocus
        className="w-36 rounded-md border border-red-200 px-2 py-1 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
      />
      {validationError && <span className="text-xs text-red-700">{validationError}</span>}
      {apiError && (
        <span role="alert" className="text-xs text-red-700">
          {apiError}
        </span>
      )}
      <div className="flex gap-2">
        <Button type="submit" disabled={Boolean(validationError) || saving}>
          {saving ? "Guardando..." : "Guardar"}
        </Button>
        <Button variant="secondary" onClick={() => setEditing(false)} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
