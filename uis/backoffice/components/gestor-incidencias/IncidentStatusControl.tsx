"use client";

import { useId, useState } from "react";
import { STATUS_TRANSITIONS } from "@/lib/gestor-incidencias/labels";
import type { Incident, IncidentStatus } from "@/types/incident-manager";

interface IncidentStatusControlProps {
  incident: Incident;
  // Cambio optimista: devuelve null si la API lo aceptó, o el mensaje de error (la fila ya volvió atrás).
  onChange: (incident: Incident, next: IncidentStatus) => Promise<string | null>;
}

// Cambio de estado desde el listado. Solo ofrece las transiciones válidas del ciclo de vida;
// resolved y discarded son finales. Si la petición falla, el estado vuelve al anterior y se avisa.
export default function IncidentStatusControl({ incident, onChange }: IncidentStatusControlProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectId = useId();
  const options = STATUS_TRANSITIONS[incident.status];

  async function handleChange(next: IncidentStatus) {
    setSaving(true);
    setError(null);
    const failure = await onChange(incident, next);
    setSaving(false);
    if (failure) setError(`No se cambió a ${next}: ${failure}`);
  }

  if (options.length === 0 && !saving) {
    return <span className="text-xs text-gray-600">Estado final</span>;
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <label htmlFor={selectId} className="sr-only">
        Cambiar el estado de la incidencia #{incident.id}
      </label>
      <select
        id={selectId}
        value=""
        onChange={(e) => {
          if (e.target.value) handleChange(e.target.value as IncidentStatus);
        }}
        disabled={saving}
        className="rounded-md border border-red-200 px-2 py-1.5 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
      >
        <option value="">{saving ? "Guardando..." : "Cambiar a..."}</option>
        {options.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
      {error && (
        <span role="alert" className="max-w-56 text-xs text-red-700">
          {error}
        </span>
      )}
    </div>
  );
}
