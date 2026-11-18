"use client";

import Button from "@/components/Button";
import ErrorMessage from "@/components/ErrorMessage";
import FileDropzone from "@/components/FileDropzone";
import LoadingMessage from "@/components/LoadingMessage";
import BreakdownTable from "@/components/incidencias/BreakdownTable";
import ExportButton from "@/components/incidencias/ExportButton";
import InvalidRecordsNotice from "@/components/incidencias/InvalidRecordsNotice";
import SatisfactionPanel from "@/components/incidencias/SatisfactionPanel";
import SummaryCards from "@/components/incidencias/SummaryCards";
import { useIncidentAnalysis } from "@/hooks/useIncidentAnalysis";
import { formatDateTime } from "@/lib/format";
import { categoryDescription } from "@/lib/incidencias/labels";
import type { CodeCount } from "@/types/incident";

// Se muestra el código exacto de la API; la descripción, si existe, lo acompaña.
function toRows(items: CodeCount[], describe?: (code: string) => string | undefined) {
  return items.map((item) => ({
    key: item.code,
    label: item.code,
    description: describe?.(item.code),
    count: item.count,
    percentage: item.percentage,
  }));
}

export default function IncidentAnalysisPanel() {
  const { state, analyze, retry } = useIncidentAnalysis();
  const loading = state.status === "loading";

  return (
    <div className="flex flex-col gap-6">
      <FileDropzone
        accept=".csv"
        label="Arrastra el CSV de incidentes aquí o haz clic para elegirlo"
        hint="Archivo .csv en UTF-8, de hasta 5 MB. Al elegir otro archivo se reemplaza el análisis."
        fileName={state.status === "idle" ? undefined : state.fileName}
        disabled={loading}
        onFileSelected={analyze}
      />

      {/* Anuncia el cambio de estado a los lectores de pantalla sin leer todo el resumen. */}
      <p className="sr-only" aria-live="polite">
        {state.status === "success" && "Análisis completado."}
      </p>

      <div className="flex flex-col gap-6">
        {loading && <LoadingMessage>Analizando el archivo...</LoadingMessage>}

        {state.status === "error" && (
          <div role="alert" className="flex flex-col items-start gap-3">
            <ErrorMessage>{state.message}</ErrorMessage>
            {state.retryable ? (
              <Button variant="secondary" onClick={retry}>
                Reintentar con el mismo archivo
              </Button>
            ) : (
              <p className="text-sm text-black">
                Corrige el archivo y vuelve a elegirlo en la zona de arriba.
              </p>
            )}
          </div>
        )}

        {state.status === "success" && (
          <>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-black">
                Análisis de <span className="font-semibold">{state.result.source_file}</span> ·{" "}
                {formatDateTime(state.result.analyzed_at)}
              </p>
              <ExportButton />
            </div>

            <SummaryCards result={state.result} />

            <InvalidRecordsNotice
              invalid_records={state.result.invalid_records}
              invalid_breakdown={state.result.invalid_breakdown}
              invalid_records_detail={state.result.invalid_records_detail}
            />

            <div className="grid gap-4 lg:grid-cols-2">
              <BreakdownTable
                title="Desglose por categoría (registros válidos)"
                itemHeader="category"
                caption="Porcentaje sobre los registros válidos."
                rows={toRows(state.result.categories, categoryDescription)}
              />
              <BreakdownTable
                title="Desglose por estado (registros válidos)"
                itemHeader="status"
                caption="Porcentaje sobre los registros válidos."
                rows={toRows(state.result.statuses)}
              />
            </div>

            <SatisfactionPanel satisfaction={state.result.satisfaction} />
          </>
        )}
      </div>
    </div>
  );
}
