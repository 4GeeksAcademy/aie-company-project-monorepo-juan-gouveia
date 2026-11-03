import type { SupplierStatus } from "@/types/supplier";

// Activo en verde y suspendido en gris, con un punto además del color para no depender solo de él.
const STYLE: Record<SupplierStatus, string> = {
  active: "border-green-700 bg-green-50 text-green-800",
  suspended: "border-gray-400 bg-gray-100 text-gray-700",
};

const DOT: Record<SupplierStatus, string> = {
  active: "bg-green-700",
  suspended: "bg-gray-500",
};

export default function SupplierStatusBadge({ status }: { status: SupplierStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-semibold ${STYLE[status]}`}
    >
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${DOT[status]}`} />
      {status}
    </span>
  );
}
