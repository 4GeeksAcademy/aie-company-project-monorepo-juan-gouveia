import { useCallback, useEffect, useRef, useState } from "react";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getTelemetryReport, type ReportProgress } from "@/lib/telemetry-report";
import type { ReportDates } from "@/types/telemetry-report";

const NO_DATES: ReportDates = { from: "", to: "" };

// Carga el reporte técnico para las fechas aplicadas (vacías = los últimos 7 días). El reporte es una
// tarea asíncrona (ticket #DEV-55): se encola y se consulta su estado hasta que termina. `progress` dice
// en qué punto está mientras carga (`null` al encolar, `pending` en cola, `started` calculando).
// `apply` cambia las fechas y `reload` repite la petición ("Reintentar"); los dos, igual que salir de la
// vista, cancelan el sondeo anterior.
export function useTelemetryReport() {
  const [dates, setDates] = useState<ReportDates>(NO_DATES);
  const [progress, setProgress] = useState<ReportProgress | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const load = useCallback(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setProgress(null);
    return getTelemetryReport(dates, {
      signal: controller.signal,
      // Un sondeo cancelado no puede pisar el estado del siguiente.
      onProgress: (next) => {
        if (!controller.signal.aborted) setProgress(next);
      },
    });
  }, [dates]);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const { state, reload } = useAsyncData(load, "No se pudo cargar el reporte técnico.");

  return { fetchState: state, progress, dates, apply: setDates, reload };
}
