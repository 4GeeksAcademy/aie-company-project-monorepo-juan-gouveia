import IncidentStatusBadge from "@/components/gestor-incidencias/IncidentStatusBadge";
import IncidentStatusControl from "@/components/gestor-incidencias/IncidentStatusControl";
import { formatDateTimeUtc } from "@/lib/format";
import { BRANCH_LABELS, CATEGORY_DESCRIPTIONS, ORIGIN_DESCRIPTIONS } from "@/lib/gestor-incidencias/labels";
import type { Incident, IncidentStatus } from "@/types/incident-manager";

interface IncidentListProps {
  incidents: Incident[];
  onStatusChange: (incident: Incident, next: IncidentStatus) => Promise<string | null>;
}

// Tarjetas apiladas en móvil y columnas alineadas desde lg, como el directorio de proveedores.
const COLUMNS =
  "lg:grid lg:grid-cols-[minmax(0,2.4fr)_minmax(0,1.1fr)_minmax(0,1.2fr)_minmax(0,1fr)_11rem] lg:gap-4";

export default function IncidentList({ incidents, onStatusChange }: IncidentListProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-white shadow-md">
      <div
        aria-hidden="true"
        className={`hidden border-b border-red-200 px-4 py-2 text-xs font-semibold uppercase text-red-700 ${COLUMNS}`}
      >
        <span>Incidencia</span>
        <span>Categoría y origen</span>
        <span>Sede</span>
        <span>Creada</span>
        <span>Estado</span>
      </div>

      <ul className="divide-y divide-red-100">
        {incidents.map((incident) => (
          <li key={incident.id} className={`flex flex-col gap-3 px-4 py-4 lg:items-start ${COLUMNS}`}>
            <div className="min-w-0">
              <p className="font-semibold text-black">
                <span className="text-gray-500">#{incident.id}</span> {incident.title}
              </p>
              {incident.description !== incident.title && (
                <p className="mt-1 line-clamp-2 text-sm text-gray-700">{incident.description}</p>
              )}
            </div>

            <div className="flex flex-wrap gap-1 text-xs lg:flex-col lg:items-start">
              <code title={CATEGORY_DESCRIPTIONS[incident.category]} className="rounded border border-red-200 px-2 py-0.5 text-red-700">
                {incident.category}
              </code>
              <code title={ORIGIN_DESCRIPTIONS[incident.origin]} className="rounded border border-gray-200 px-2 py-0.5 text-gray-700">
                {incident.origin}
              </code>
            </div>

            <p className="text-sm text-black">
              <span className="font-semibold text-red-700 lg:hidden">Sede: </span>
              {BRANCH_LABELS[incident.branch]}
            </p>

            <p className="text-sm text-black">
              <span className="font-semibold text-red-700 lg:hidden">Creada: </span>
              <time dateTime={incident.created_at}>{formatDateTimeUtc(incident.created_at)}</time>
            </p>

            <div className="flex flex-wrap items-center gap-2 lg:flex-col lg:items-start">
              <IncidentStatusBadge status={incident.status} />
              <IncidentStatusControl incident={incident} onChange={onStatusChange} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
