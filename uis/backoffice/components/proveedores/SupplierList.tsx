import RateEditor from "@/components/proveedores/RateEditor";
import StatusToggle from "@/components/proveedores/StatusToggle";
import SupplierStatusBadge from "@/components/proveedores/SupplierStatusBadge";
import type { Supplier } from "@/types/supplier";

interface SupplierListProps {
  suppliers: Supplier[];
  onUpdated: (supplier: Supplier) => void;
}

// Una sola lista: tarjetas apiladas en móvil y columnas alineadas desde md.
const COLUMNS = "md:grid md:grid-cols-[minmax(0,2fr)_6rem_minmax(0,1.5fr)_minmax(0,1.4fr)_8rem] md:gap-4";

export default function SupplierList({ suppliers, onUpdated }: SupplierListProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-white shadow-md">
      <div
        aria-hidden="true"
        className={`hidden border-b border-red-200 px-4 py-2 text-xs font-semibold uppercase text-red-700 ${COLUMNS}`}
      >
        <span>Proveedor</span>
        <span>País</span>
        <span>Categorías</span>
        <span>Tarifa por unidad</span>
        <span>Estado</span>
      </div>

      <ul className="divide-y divide-red-100">
        {suppliers.map((supplier) => {
          const suspended = supplier.status === "suspended";
          return (
            <li
              key={supplier.id}
              className={`flex flex-col gap-3 px-4 py-4 md:items-start ${COLUMNS} ${suspended ? "bg-gray-50" : ""}`}
            >
              <div className="min-w-0">
                <p className={`font-semibold ${suspended ? "text-gray-600" : "text-black"}`}>{supplier.name}</p>
                {supplier.contact_email && (
                  <a
                    href={`mailto:${supplier.contact_email}`}
                    className="break-all text-xs text-red-700 underline-offset-2 hover:underline"
                  >
                    {supplier.contact_email}
                  </a>
                )}
                {supplier.notes && <p className="mt-1 text-xs text-gray-600">{supplier.notes}</p>}
              </div>

              <p className="text-sm text-black">
                <span className="font-semibold text-red-700 md:hidden">País: </span>
                {supplier.country}
              </p>

              <ul aria-label="Categorías" className="flex flex-wrap gap-1">
                {supplier.categories.map((category) => (
                  <li key={category} className="rounded border border-red-200 px-2 py-0.5 text-xs text-red-700">
                    {category}
                  </li>
                ))}
              </ul>

              <RateEditor supplier={supplier} onUpdated={onUpdated} />

              <div className="flex flex-wrap items-center gap-2 md:flex-col md:items-start">
                <SupplierStatusBadge status={supplier.status} />
                <StatusToggle supplier={supplier} onUpdated={onUpdated} />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
