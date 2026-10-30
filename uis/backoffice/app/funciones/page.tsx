import type { Metadata } from "next";
import FuncionesPanel from "@/components/funciones/FuncionesPanel";

export const metadata: Metadata = {
  title: "Pruebas de funciones",
  description: "Pruebas manuales de las utilidades de negocio de Brasaland.",
};

export default function FuncionesPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Pruebas del Sistema (Manual)
      </h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Ejecuta filtros, búsquedas, ordenamientos, reportes y validaciones con los datos de prueba
        definidos en TypeScript.
      </p>

      <FuncionesPanel />
    </main>
  );
}
