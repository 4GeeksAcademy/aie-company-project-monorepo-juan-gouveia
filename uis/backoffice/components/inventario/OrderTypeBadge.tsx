import type { OrderRow } from "@/lib/inventory-orders";

type OrderKind = OrderRow["kind"];

// Entrada en verde con "+" y salida en rojo con "−": el texto y el signo distinguen el tipo sin
// depender del color.
const STYLE: Record<OrderKind, string> = {
  entry: "border-green-700 bg-green-50 text-green-800",
  exit: "border-red-700 bg-red-50 text-red-800",
};

export const ORDER_LABEL: Record<OrderKind, string> = {
  entry: "Entrada",
  exit: "Salida",
};

export const ORDER_SIGN: Record<OrderKind, string> = {
  entry: "+",
  exit: "−",
};

export default function OrderTypeBadge({ kind }: { kind: OrderKind }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-semibold ${STYLE[kind]}`}
    >
      <span aria-hidden="true">{ORDER_SIGN[kind]}</span>
      {ORDER_LABEL[kind]}
    </span>
  );
}
