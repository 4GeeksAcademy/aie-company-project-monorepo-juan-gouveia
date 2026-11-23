import { useCallback, useState } from "react";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getLatestPipelineRun, getWeeklyReport } from "@/lib/weekly-report";
import type { PipelineRun, WeeklyReportResult } from "@/types/weekly-report";

export interface WeeklyReportData {
  result: WeeklyReportResult;
  // undefined: no se pudo consultar la última corrida (la vista muestra los KPIs igual); null: nunca corrió.
  latestRun: PipelineRun | null | undefined;
}

// Carga el reporte de una semana (null = la última calculada) junto con la última corrida del pipeline,
// que dice cuándo se actualizaron los datos. `showWeek` cambia de semana; `reload` repite la petición.
export function useWeeklyReport() {
  const [weekStart, setWeekStart] = useState<string | null>(null);

  const load = useCallback(async (): Promise<WeeklyReportData> => {
    const [result, latestRun] = await Promise.all([
      getWeeklyReport(weekStart),
      // La fecha de actualización es secundaria: si falla, no impide ver los números.
      getLatestPipelineRun().catch(() => undefined),
    ]);
    return { result, latestRun };
  }, [weekStart]);

  const { state, reload } = useAsyncData(load, "No se pudo cargar el reporte semanal.");

  return { fetchState: state, showWeek: setWeekStart, reload };
}
