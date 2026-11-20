interface ReportTableProps {
  // Cabeceras de columna; las marcadas con `numeric` se alinean a la derecha.
  columns: { label: string; numeric?: boolean }[];
  children: React.ReactNode;
}

// Tabla de una métrica. En pantallas estrechas se desplaza en horizontal dentro de su bloque, sin
// desbordar la página.
export default function ReportTable({ columns, children }: ReportTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] text-left text-sm text-black">
        <thead>
          <tr className="border-b border-red-200 text-xs uppercase text-red-700">
            {columns.map((column) => (
              <th key={column.label} scope="col" className={`px-2 py-2 font-semibold ${column.numeric ? "text-right" : ""}`}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-red-100">{children}</tbody>
      </table>
    </div>
  );
}

// Celda numérica, alineada a la derecha y con cifras de ancho fijo.
export function NumericCell({ children }: { children: React.ReactNode }) {
  return <td className="px-2 py-2 text-right tabular-nums">{children}</td>;
}

export function Cell({ children }: { children: React.ReactNode }) {
  return <td className="px-2 py-2">{children}</td>;
}
