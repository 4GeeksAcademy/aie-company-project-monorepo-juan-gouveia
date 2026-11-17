import LoadingMessage from "@/components/LoadingMessage";
import IncidentStatusBadge from "@/components/gestor-incidencias/IncidentStatusBadge";
import RetryableError from "@/components/RetryableError";
import {
  BRANCH_LABELS,
  CATEGORY_DESCRIPTIONS,
  ORIGIN_DESCRIPTIONS,
  STATUS_DESCRIPTIONS,
} from "@/lib/gestor-incidencias/labels";
import type { AsyncState } from "@/hooks/useAsyncData";
import type { IncidentStatus, IncidentSummary } from "@/types/incident-manager";

interface IncidentSummaryPanelProps {
  state: AsyncState<IncidentSummary>;
  onRetry: () => void;
}

// Métricas de GET /incidents/summary: totales por estado, categoría, origen y sede.
// Tiene sus propios estados de carga y error, así que un fallo no rompe el resto de la página.
// Mientras carga pinta la misma cuadrícula con las etiquetas reales y "—" en lugar de las cifras:
// las filas no dependen de los datos (estados, categorías, orígenes y sedes son fijos), así que el
// bloque ya ocupa su altura final y el listado de debajo no se desplaza al llegar el resumen (CLS).
export default function IncidentSummaryPanel({ state, onRetry }: IncidentSummaryPanelProps) {
  return (
    <section
      aria-labelledby="summary-heading"
      aria-busy={state.status === "loading"}
      className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6"
    >
      <h2 id="summary-heading" className="mb-3 text-lg font-semibold text-red-700">
        Resumen
      </h2>

      {state.status === "loading" && (
        <>
          <div className="sr-only">
            <LoadingMessage compact>Cargando el resumen...</LoadingMessage>
          </div>
          <SummaryContent summary={null} />
        </>
      )}

      {state.status === "error" && (
        <RetryableError compact onRetry={onRetry}>
          {state.message}
        </RetryableError>
      )}

      {state.status === "success" && <SummaryContent summary={state.data} />}
    </section>
  );
}

// Cifras de un desglose: las del resumen o, mientras carga (summary null), null para cada código
// conocido, en el mismo orden que devuelve la API (el de las tablas del briefing).
function countsOf<T extends string>(counts: Record<T, number> | undefined, codes: Record<T, string>) {
  return (Object.keys(counts ?? codes) as T[]).map((code) => [code, counts ? counts[code] : null] as const);
}

// summary null = cargando: misma estructura y altura, con "—" en lugar de cada cifra.
function SummaryContent({ summary }: { summary: IncidentSummary | null }) {
  const statuses = countsOf<IncidentStatus>(summary?.by_status, STATUS_DESCRIPTIONS);
  return (
    <div className="flex flex-col gap-5">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <li className="rounded-md border border-red-200 p-3">
          <p className="text-xs font-semibold uppercase text-red-700">Total</p>
          <Count value={summary ? summary.total : null} className="text-2xl" />
        </li>
        {statuses.map(([status, count]) => (
          <li key={status} className="rounded-md border border-red-100 p-3">
            <IncidentStatusBadge status={status} />
            <Count value={count} className="mt-1 text-2xl" />
          </li>
        ))}
      </ul>

      <div className="grid gap-5 md:grid-cols-3">
        <Breakdown
          title="Por categoría"
          rows={countsOf(summary?.by_category, CATEGORY_DESCRIPTIONS).map(([code, count]) => ({
            key: code,
            label: <code>{code}</code>,
            hint: CATEGORY_DESCRIPTIONS[code],
            count,
          }))}
        />
        <Breakdown
          title="Por origen"
          rows={countsOf(summary?.by_origin, ORIGIN_DESCRIPTIONS).map(([code, count]) => ({
            key: code,
            label: <code>{code}</code>,
            hint: ORIGIN_DESCRIPTIONS[code],
            count,
          }))}
        />
        <Breakdown
          title="Por sede"
          rows={countsOf(summary?.by_branch, BRANCH_LABELS).map(([code, count]) => ({
            key: code,
            label: BRANCH_LABELS[code],
            count,
          }))}
        />
      </div>
    </div>
  );
}

// Cifra grande de una tarjeta; "—" (sin anunciar) mientras carga.
function Count({ value, className }: { value: number | null; className: string }) {
  return value === null ? (
    <p className={`${className} font-semibold text-gray-400`} aria-hidden="true">
      —
    </p>
  ) : (
    <p className={`${className} font-semibold text-black`}>{value}</p>
  );
}

interface BreakdownRow {
  key: string;
  label: React.ReactNode;
  hint?: string;
  // null mientras carga.
  count: number | null;
}

function Breakdown({ title, rows }: { title: string; rows: BreakdownRow[] }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-red-700">{title}</h3>
      <dl className="divide-y divide-red-50 text-sm">
        {rows.map((row) => {
          const muted = row.count === null || row.count === 0;
          return (
            <div key={row.key} className="flex items-baseline justify-between gap-3 py-1" title={row.hint}>
              <dt className={`min-w-0 break-words ${muted ? "text-gray-500" : "text-black"}`}>{row.label}</dt>
              <dd className={`font-semibold tabular-nums ${muted ? "text-gray-500" : "text-black"}`}>
                {row.count === null ? <span aria-hidden="true">—</span> : row.count}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
