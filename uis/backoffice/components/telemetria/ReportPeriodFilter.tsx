"use client";

import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import { datesError } from "@/lib/telemetry-report";
import type { ReportDates } from "@/types/telemetry-report";

interface ReportPeriodFilterProps {
  applied: ReportDates;
  onApply: (dates: ReportDates) => void;
  disabled?: boolean;
}

// Fechas del reporte (las dos incluidas, en UTC). Vacías = los últimos 7 días. Las fechas no se aplican
// hasta pulsar "Aplicar", para no pedir el reporte a cada tecla.
export default function ReportPeriodFilter({ applied, onApply, disabled = false }: ReportPeriodFilterProps) {
  const [dates, setDates] = useState<ReportDates>(applied);
  const [error, setError] = useState<string | null>(null);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const problem = datesError(dates);
    setError(problem);
    if (!problem) onApply(dates);
  }

  function reset() {
    const empty = { from: "", to: "" };
    setDates(empty);
    setError(null);
    onApply(empty);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 md:flex-row md:items-end" aria-label="Período del reporte">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:w-96">
        <FormField
          label="Desde (UTC)"
          type="date"
          value={dates.from}
          onChange={(from) => setDates((current) => ({ ...current, from }))}
          disabled={disabled}
        />
        <FormField
          label="Hasta (UTC, incluido)"
          type="date"
          value={dates.to}
          onChange={(to) => setDates((current) => ({ ...current, to }))}
          disabled={disabled}
        />
      </div>
      <div className="flex gap-2">
        <Button type="submit" size="md" disabled={disabled}>
          Aplicar
        </Button>
        <Button variant="secondary" size="md" onClick={reset} disabled={disabled}>
          Últimos 7 días
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700 md:self-center">
          {error}
        </p>
      )}
    </form>
  );
}
