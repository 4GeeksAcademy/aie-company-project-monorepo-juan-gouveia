import { useCallback, useState } from "react";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getTelemetryReport } from "@/lib/telemetry-report";
import type { ReportDates } from "@/types/telemetry-report";

const NO_DATES: ReportDates = { from: "", to: "" };

// Carga el reporte técnico para las fechas aplicadas (vacías = los últimos 7 días). `apply` cambia las
// fechas y vuelve a pedirlo; `reload` repite la petición ("Reintentar").
export function useTelemetryReport() {
  const [dates, setDates] = useState<ReportDates>(NO_DATES);
  const load = useCallback(() => getTelemetryReport(dates), [dates]);
  const { state, reload } = useAsyncData(load, "No se pudo cargar el reporte técnico.");

  return { fetchState: state, dates, apply: setDates, reload };
}
