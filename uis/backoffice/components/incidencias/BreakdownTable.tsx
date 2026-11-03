import { formatPercentage } from "@/lib/format";

export interface BreakdownRow {
  key: string;
  label: string;
  // Texto secundario bajo la etiqueta, p. ej. la descripción de una categoría.
  description?: string;
  count: number;
  percentage: number | null;
}

interface BreakdownTableProps {
  title: string;
  // Nombre de la primera columna, p. ej. "Categoría".
  itemHeader: string;
  rows: BreakdownRow[];
  // Texto bajo el título que explica sobre qué total se calcula el porcentaje.
  caption?: string;
}

// Tabla de cantidades y porcentajes con una barra proporcional por fila.
export default function BreakdownTable({ title, itemHeader, rows, caption }: BreakdownTableProps) {
  return (
    <section className="rounded-lg bg-white p-4 shadow-md">
      <h2 className="text-lg font-semibold text-red-700">{title}</h2>
      {caption && <p className="mt-1 text-xs text-gray-600 md:text-sm">{caption}</p>}

      <table className="mt-3 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-gray-600">
            <th scope="col" className="py-2 pr-2 font-medium">
              {itemHeader}
            </th>
            <th scope="col" className="px-2 py-2 text-right font-medium">
              Cantidad
            </th>
            <th scope="col" className="py-2 pl-2 text-right font-medium">
              %
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b border-gray-100 last:border-0">
              <td className="py-2 pr-2">
                <span className="block font-mono text-black">{row.label}</span>
                {row.description && (
                  <span className="block text-xs text-gray-600">{row.description}</span>
                )}
                <span className="mt-1 block h-1.5 rounded-full bg-gray-100" aria-hidden="true">
                  <span
                    className="block h-full rounded-full bg-red-700"
                    style={{ width: `${Math.min(row.percentage ?? 0, 100)}%` }}
                  />
                </span>
              </td>
              <td className="px-2 py-2 text-right tabular-nums">{row.count}</td>
              <td className="py-2 pl-2 text-right tabular-nums">{formatPercentage(row.percentage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
