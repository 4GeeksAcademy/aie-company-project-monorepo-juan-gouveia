import { STOCK_LEVEL_LABELS, type StockLevel } from "@/lib/inventory-stock-level";

// Sin stock en rojo, bajo en ámbar y saludable en verde, siempre con el texto del nivel y un punto:
// el color nunca es la única señal.
const STYLE: Record<StockLevel, string> = {
  out: "border-red-700 bg-red-50 text-red-800",
  low: "border-amber-600 bg-amber-50 text-amber-800",
  healthy: "border-green-700 bg-green-50 text-green-800",
};

const DOT: Record<StockLevel, string> = {
  out: "bg-red-700",
  low: "bg-amber-500",
  healthy: "bg-green-700",
};

export default function StockLevelBadge({ level }: { level: StockLevel }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-semibold ${STYLE[level]}`}
    >
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${DOT[level]}`} />
      {STOCK_LEVEL_LABELS[level]}
    </span>
  );
}
