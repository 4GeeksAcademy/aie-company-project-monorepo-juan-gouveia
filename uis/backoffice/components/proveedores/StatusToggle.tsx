"use client";

import { useState } from "react";
import Button from "@/components/Button";
import { updateStatus } from "@/lib/proveedores/api";
import type { Supplier } from "@/types/supplier";

interface StatusToggleProps {
  supplier: Supplier;
  onUpdated: (supplier: Supplier) => void;
}

// Activa o suspende con un clic. El cambio se muestra cuando responde la API, no antes.
export default function StatusToggle({ supplier, onUpdated }: StatusToggleProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isActive = supplier.status === "active";

  async function handleClick() {
    setSaving(true);
    setError(null);
    try {
      onUpdated(await updateStatus(supplier.id, isActive ? "suspended" : "active"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cambiar el estado");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        variant={isActive ? "danger" : "secondary"}
        onClick={handleClick}
        disabled={saving}
        aria-label={`${isActive ? "Suspender" : "Activar"} a ${supplier.name}`}
      >
        {saving ? "Guardando..." : isActive ? "Suspender" : "Activar"}
      </Button>
      {error && (
        <span role="alert" className="text-xs text-red-700">
          {error}
        </span>
      )}
    </div>
  );
}
