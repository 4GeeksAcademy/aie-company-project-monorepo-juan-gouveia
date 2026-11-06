import type { Metadata } from "next";
import IncidentAnalysisPanel from "@/components/incidencias/IncidentAnalysisPanel";

export const metadata: Metadata = {
  title: "Análisis de incidencias",
  description: "Resumen del reporte de incidentes de Operaciones a partir de un CSV.",
};

export default function IncidenciasPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Análisis de incidencias
      </h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Sube el CSV de incidentes de Operaciones para validar los registros, ver el resumen por
        categoría, estado y satisfacción, y descargar las métricas.
      </p>

      <IncidentAnalysisPanel />
    </main>
  );
}
