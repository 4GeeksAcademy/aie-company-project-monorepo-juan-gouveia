import Button from "@/components/Button";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import IncidentStatusBadge from "@/components/gestor-incidencias/IncidentStatusBadge";
import { BRANCH_LABELS, CATEGORY_DESCRIPTIONS, ORIGIN_DESCRIPTIONS } from "@/lib/gestor-incidencias/labels";
import type { IncidentStatus, IncidentSummary } from "@/types/incident-manager";

type SummaryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; summary: IncidentSummary };

interface IncidentSummaryPanelProps {
  state: SummaryState;
  onRetry: () => void;
}

// Métricas de GET /incidents/summary: totales por estado, categoría, origen y sede.
// Tiene sus propios estados de carga y error, así que un fallo no rompe el resto de la página.
export default function IncidentSummaryPanel({ state, onRetry }: IncidentSummaryPanelProps) {
  return (
    <section aria-labelledby="summary-heading" className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
      <h2 id="summary-heading" className="mb-3 text-lg font-semibold text-red-700">
        Resumen
      </h2>

      {state.status === "loading" && <LoadingMessage compact>Cargando el resumen...</LoadingMessage>}

      {state.status === "error" && (
        <div role="alert" className="flex flex-col items-start gap-3">
          <ErrorMessage compact>{state.message}</ErrorMessage>
          <Button variant="secondary" onClick={onRetry}>
            Reintentar
          </Button>
        </div>
      )}

      {state.status === "success" && <SummaryContent summary={state.summary} />}
    </section>
  );
}

function SummaryContent({ summary }: { summary: IncidentSummary }) {
  const statuses = Object.entries(summary.by_status) as [IncidentStatus, number][];
  return (
    <div className="flex flex-col gap-5">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <li className="rounded-md border border-red-200 p-3">
          <p className="text-xs font-semibold uppercase text-red-700">Total</p>
          <p className="text-2xl font-semibold text-black">{summary.total}</p>
        </li>
        {statuses.map(([status, count]) => (
          <li key={status} className="rounded-md border border-red-100 p-3">
            <IncidentStatusBadge status={status} />
            <p className="mt-1 text-2xl font-semibold text-black">{count}</p>
          </li>
        ))}
      </ul>

      <div className="grid gap-5 md:grid-cols-3">
        <Breakdown
          title="Por categoría"
          rows={Object.entries(summary.by_category).map(([code, count]) => ({
            key: code,
            label: <code>{code}</code>,
            hint: CATEGORY_DESCRIPTIONS[code as keyof typeof CATEGORY_DESCRIPTIONS],
            count,
          }))}
        />
        <Breakdown
          title="Por origen"
          rows={Object.entries(summary.by_origin).map(([code, count]) => ({
            key: code,
            label: <code>{code}</code>,
            hint: ORIGIN_DESCRIPTIONS[code as keyof typeof ORIGIN_DESCRIPTIONS],
            count,
          }))}
        />
        <Breakdown
          title="Por sede"
          rows={Object.entries(summary.by_branch).map(([code, count]) => ({
            key: code,
            label: BRANCH_LABELS[code as keyof typeof BRANCH_LABELS],
            count,
          }))}
        />
      </div>
    </div>
  );
}

interface BreakdownRow {
  key: string;
  label: React.ReactNode;
  hint?: string;
  count: number;
}

function Breakdown({ title, rows }: { title: string; rows: BreakdownRow[] }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-red-700">{title}</h3>
      <dl className="divide-y divide-red-50 text-sm">
        {rows.map((row) => (
          <div key={row.key} className="flex items-baseline justify-between gap-3 py-1" title={row.hint}>
            <dt className={`min-w-0 break-words ${row.count === 0 ? "text-gray-500" : "text-black"}`}>{row.label}</dt>
            <dd className={`font-semibold tabular-nums ${row.count === 0 ? "text-gray-500" : "text-black"}`}>{row.count}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
