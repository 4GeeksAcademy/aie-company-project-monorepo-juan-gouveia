import type { Metadata } from "next";
import IncidentPanel from "@/components/gestor-incidencias/IncidentPanel";

export const metadata: Metadata = {
  title: "Gestor de incidencias",
  description: "Resumen y seguimiento de las incidencias de todas las sedes de Brasaland.",
};

export default function IncidentManagerPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Gestor de incidencias</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Qué está pasando en cada sede: totales por estado, categoría, origen y sede, y el listado completo para
        hacer seguimiento y cambiar el estado de cada incidencia.
      </p>
      <IncidentPanel />
    </main>
  );
}
