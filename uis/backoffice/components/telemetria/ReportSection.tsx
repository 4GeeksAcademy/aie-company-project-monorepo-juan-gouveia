import EmptyMessage from "@/components/EmptyMessage";

interface ReportSectionProps {
  title: string;
  // La pregunta operacional que responde la métrica.
  question: string;
  // Sin filas: se muestra `emptyText` en lugar del contenido.
  isEmpty: boolean;
  emptyText: string;
  children: React.ReactNode;
}

// Bloque de una métrica del reporte: título, pregunta que responde y su gráfico o tabla.
export default function ReportSection({ title, question, isEmpty, emptyText, children }: ReportSectionProps) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-red-200 bg-white p-4 shadow-md">
      <div>
        <h2 className="text-lg font-semibold text-red-700">{title}</h2>
        <p className="text-sm text-black">{question}</p>
      </div>
      {isEmpty ? <EmptyMessage compact>{emptyText}</EmptyMessage> : children}
    </section>
  );
}
