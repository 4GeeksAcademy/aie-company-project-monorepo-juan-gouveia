import { STATUS_DESCRIPTIONS } from "@/lib/gestor-incidencias/labels";
import type { IncidentStatus } from "@/types/incident-manager";

const STATUS_CLASS: Record<IncidentStatus, string> = {
  open: "border-amber-300 bg-amber-50 text-amber-900",
  in_progress: "border-blue-300 bg-blue-50 text-blue-900",
  resolved: "border-green-300 bg-green-50 text-green-800",
  discarded: "border-gray-300 bg-gray-100 text-gray-700",
};

// Estado con su código exacto; la descripción del briefing va en el title.
export default function IncidentStatusBadge({ status }: { status: IncidentStatus }) {
  return (
    <span
      title={STATUS_DESCRIPTIONS[status]}
      className={`inline-block rounded border px-2 py-0.5 font-mono text-xs ${STATUS_CLASS[status]}`}
    >
      {status}
    </span>
  );
}
