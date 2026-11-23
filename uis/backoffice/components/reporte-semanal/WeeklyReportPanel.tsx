"use client";

import { useState } from "react";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import RetryableError from "@/components/RetryableError";
import CountrySummaryCards from "@/components/reporte-semanal/CountrySummaryCards";
import KpiSection from "@/components/reporte-semanal/KpiSection";
import LocationsTable from "@/components/reporte-semanal/LocationsTable";
import ReportNotices from "@/components/reporte-semanal/ReportNotices";
import WeekNavigator from "@/components/reporte-semanal/WeekNavigator";
import { useWeeklyReport } from "@/hooks/useWeeklyReport";
import {
  currentWeekStart,
  formatWeekPeriod,
  isSilentWeek,
  KPIS,
  READERS_ONLY_MESSAGE,
  summarizeByCountry,
} from "@/lib/weekly-report";

// Reporte Semanal de Costo y Merma por Local: el período, la actualización, el resumen por país, un
// bloque por KPI del briefing y la tabla completa. Solo muestra lo que calculó el pipeline.
export default function WeeklyReportPanel() {
  const { fetchState, showWeek, reload } = useWeeklyReport();
  // La hora de referencia para "semana en curso" y "datos desactualizados", fijada al montar la vista.
  const [now] = useState(() => new Date());
  const currentWeek = currentWeekStart(now);
  const loading = fetchState.status === "loading";

  if (fetchState.status === "loading") return <LoadingMessage>Cargando el reporte semanal...</LoadingMessage>;

  if (fetchState.status === "error") {
    return fetchState.message === READERS_ONLY_MESSAGE ? (
      <ErrorMessage>{READERS_ONLY_MESSAGE}</ErrorMessage>
    ) : (
      <RetryableError onRetry={reload}>{fetchState.message}</RetryableError>
    );
  }

  const { result, latestRun } = fetchState.data;

  if (result.status === "not_computed") {
    if (result.weekStart === null) {
      return <EmptyMessage>Todavía no hay ninguna semana calculada. El primer reporte estará listo el lunes.</EmptyMessage>;
    }
    return (
      <div className="flex flex-col gap-4">
        <WeekNavigator weekStart={result.weekStart} currentWeek={currentWeek} onShowWeek={showWeek} disabled={loading} />
        <EmptyMessage>
          {formatWeekPeriod(result.weekStart)}: esta semana no está calculada. El reporte guarda las semanas que el
          sistema calculó desde que empezó a funcionar.
        </EmptyMessage>
        <p>
          <button type="button" onClick={() => showWeek(null)} className="text-sm font-semibold text-red-700 underline">
            Ver la última semana calculada
          </button>
        </p>
      </div>
    );
  }

  const { report } = result;

  return (
    <div className="flex flex-col gap-4">
      <WeekNavigator weekStart={report.week_start} currentWeek={currentWeek} onShowWeek={showWeek} disabled={loading} />
      <ReportNotices weekStart={report.week_start} latestRun={latestRun} silentWeek={isSilentWeek(report)} now={now} />
      <CountrySummaryCards summaries={summarizeByCountry(report)} />
      {KPIS.map((kpi) => (
        <KpiSection key={kpi.key} kpi={kpi} report={report} />
      ))}
      <LocationsTable report={report} />
    </div>
  );
}
