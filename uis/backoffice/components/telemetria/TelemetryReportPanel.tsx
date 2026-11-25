"use client";

import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import RetryableError from "@/components/RetryableError";
import AuthFailureTable from "@/components/telemetria/AuthFailureTable";
import ErrorRateTable from "@/components/telemetria/ErrorRateTable";
import EventsPerDayChart from "@/components/telemetria/EventsPerDayChart";
import LatencyTable from "@/components/telemetria/LatencyTable";
import ReportPeriodFilter from "@/components/telemetria/ReportPeriodFilter";
import ReportSection from "@/components/telemetria/ReportSection";
import { useTelemetryReport } from "@/hooks/useTelemetryReport";
import { ADMIN_ONLY_MESSAGE, formatInstantUtc, progressLabel } from "@/lib/telemetry-report";

// Vista técnica del reporte de telemetría: el período y un bloque por métrica, sin métricas propias.
// El reporte se calcula en segundo plano (ticket #DEV-55): mientras tanto se muestra si está en cola o
// calculándose.
export default function TelemetryReportPanel() {
  const { fetchState, progress, dates, apply, reload } = useTelemetryReport();

  return (
    <div className="flex flex-col gap-4">
      <ReportPeriodFilter applied={dates} onApply={apply} disabled={fetchState.status === "loading"} />

      {fetchState.status === "loading" && <LoadingMessage>{progressLabel(progress)}</LoadingMessage>}

      {fetchState.status === "error" &&
        (fetchState.message === ADMIN_ONLY_MESSAGE ? (
          <ErrorMessage>{ADMIN_ONLY_MESSAGE}</ErrorMessage>
        ) : (
          <RetryableError onRetry={reload}>{fetchState.message}</RetryableError>
        ))}

      {fetchState.status === "success" && (
        <>
          <p className="rounded-lg border border-red-200 bg-white p-3 text-sm text-black shadow-md" aria-live="polite">
            <span className="font-semibold text-red-700">Período: </span>
            <time dateTime={fetchState.data.period.from}>{formatInstantUtc(fetchState.data.period.from)}</time>
            {" → "}
            <time dateTime={fetchState.data.period.to}>{formatInstantUtc(fetchState.data.period.to)}</time>
            <span className="text-gray-600"> (el final no se incluye). Los días son días UTC.</span>
          </p>

          <ReportSection
            title="Eventos por día"
            question="¿Cuánto volumen tiene el sistema cada día y qué parte es aviso o error?"
            isEmpty={fetchState.data.metrics.events_per_day.length === 0}
            emptyText="No hay días en este período."
          >
            <EventsPerDayChart days={fetchState.data.metrics.events_per_day} />
          </ReportSection>

          <ReportSection
            title="Tasa de fallos por tipo"
            question="¿Qué tipos de fallo dominan cada día y qué peso tienen sobre el volumen del día?"
            isEmpty={fetchState.data.metrics.error_rate_by_type.length === 0}
            emptyText="Ningún aviso ni error en este período."
          >
            <ErrorRateTable rows={fetchState.data.metrics.error_rate_by_type} />
          </ReportSection>

          <ReportSection
            title="Latencia de la API por ruta"
            question="¿Qué rutas de la API responden lento y cuánto? (Media ponderada por el muestreo)"
            isEmpty={fetchState.data.metrics.api_latency_by_route.length === 0}
            emptyText="No hay latencias registradas en este período."
          >
            <LatencyTable rows={fetchState.data.metrics.api_latency_by_route} />
          </ReportSection>

          <ReportSection
            title="Tasa de fallos de login"
            question="¿Qué proporción de los intentos de inicio de sesión falla cada día?"
            isEmpty={fetchState.data.metrics.auth_failure_rate.length === 0}
            emptyText="No hubo intentos de inicio de sesión en este período."
          >
            <AuthFailureTable rows={fetchState.data.metrics.auth_failure_rate} />
          </ReportSection>
        </>
      )}
    </div>
  );
}
