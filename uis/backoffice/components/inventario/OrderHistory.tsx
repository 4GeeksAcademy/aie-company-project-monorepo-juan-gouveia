import OrderTypeBadge, { ORDER_SIGN } from "@/components/inventario/OrderTypeBadge";
import { formatDateTime } from "@/lib/format";
import {
  FIELD_LABELS,
  REASON_DESCRIPTIONS,
  WASTE_REASON_DESCRIPTIONS,
  formatAmount,
  formatQuantity,
  locationLabel,
} from "@/lib/inventory-labels";
import type { OrderRow } from "@/lib/inventory-orders";

interface OrderHistoryProps {
  orders: OrderRow[];
  // id del usuario de la sesión: sus órdenes llevan la etiqueta "Tú" (decisión F6).
  currentUserId: string | null;
}

// Una sola lista: tarjetas apiladas en móvil y tablet, y columnas alineadas desde lg.
const COLUMNS =
  "lg:grid lg:grid-cols-[6rem_minmax(0,1.6fr)_7rem_minmax(0,1.4fr)_5rem_minmax(0,1.1fr)_minmax(0,1.3fr)] lg:items-start lg:gap-4";

// Etiqueta de campo visible solo en las tarjetas (en lg la da la cabecera de columnas).
function CardLabel({ children }: { children: React.ReactNode }) {
  return <span className="font-semibold text-red-700 lg:hidden">{children}: </span>;
}

// Proveedor de la entrada, o motivo de la salida con su código exacto y su descripción. Debajo, el
// coste unitario de la entrada o el motivo de la merma (brechas B5 y B6), si la orden los tiene: las
// órdenes anteriores no los guardaron.
function detail(row: OrderRow): { label: string; text: string; extra: string | null } {
  if (row.kind === "entry") {
    const { unit_cost, ingredient_unit } = row.order;
    return {
      label: FIELD_LABELS.supplier_name,
      text: row.order.supplier_name,
      extra: unit_cost === null ? null : `${FIELD_LABELS.unit_cost}: ${formatAmount(unit_cost)} por ${ingredient_unit}`,
    };
  }
  const { reason, waste_reason } = row.order;
  return {
    label: FIELD_LABELS.reason,
    text: `${reason} (${REASON_DESCRIPTIONS[reason]})`,
    extra: waste_reason === null ? null : `${waste_reason} (${WASTE_REASON_DESCRIPTIONS[waste_reason]})`,
  };
}

export default function OrderHistory({ orders, currentUserId }: OrderHistoryProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-white shadow-md">
      <div
        aria-hidden="true"
        className={`hidden border-b border-red-200 px-4 py-2 text-xs font-semibold uppercase text-red-700 ${COLUMNS}`}
      >
        <span>Tipo</span>
        <span>Ingrediente</span>
        <span>{FIELD_LABELS.quantity}</span>
        <span>Proveedor o motivo</span>
        <span>{FIELD_LABELS.location_id}</span>
        <span>{FIELD_LABELS.created_at}</span>
        <span>{FIELD_LABELS.user_uuid}</span>
      </div>

      <ul className="divide-y divide-red-100">
        {orders.map((row) => {
          const { order } = row;
          const { label, text, extra } = detail(row);
          const mine = currentUserId !== null && order.user_uuid === currentUserId;
          return (
            <li key={row.key} className={`flex flex-col gap-2 px-4 py-4 ${COLUMNS}`}>
              <div>
                <OrderTypeBadge kind={row.kind} />
              </div>

              <div className="min-w-0">
                <p className="font-semibold text-black">{order.ingredient_name}</p>
                <p className="break-all text-xs text-gray-600">{order.ingredient_sku}</p>
              </div>

              <p className="text-sm text-black">
                <CardLabel>{FIELD_LABELS.quantity}</CardLabel>
                <span className={`font-semibold ${row.kind === "entry" ? "text-green-800" : "text-red-800"}`}>
                  {ORDER_SIGN[row.kind]}
                  {formatQuantity(order.quantity, order.ingredient_unit)}
                </span>
              </p>

              <p className="min-w-0 break-words text-sm text-black">
                <CardLabel>{label}</CardLabel>
                {text}
                {extra && <span className="block text-xs text-gray-600">{extra}</span>}
              </p>

              <p className="text-sm text-black">
                <CardLabel>{FIELD_LABELS.location_id}</CardLabel>
                {locationLabel(order.location_id)}
              </p>

              <p className="text-sm text-black">
                <CardLabel>{FIELD_LABELS.created_at}</CardLabel>
                <time dateTime={order.created_at}>{formatDateTime(order.created_at)}</time>
              </p>

              <div className="min-w-0 text-sm text-black">
                <CardLabel>{FIELD_LABELS.user_uuid}</CardLabel>
                {mine && (
                  <span className="mr-1 inline-block rounded-full border border-red-700 px-2 py-0.5 text-xs font-semibold text-red-700">
                    Tú
                  </span>
                )}
                <code className="break-all font-mono text-xs text-gray-700">{order.user_uuid}</code>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
