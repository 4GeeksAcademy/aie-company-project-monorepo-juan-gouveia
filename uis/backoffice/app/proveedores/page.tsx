import type { Metadata } from "next";
import SupplierDirectory from "@/components/proveedores/SupplierDirectory";

export const metadata: Metadata = {
  title: "Directorio de proveedores",
  description: "Fuente única del directorio de proveedores de Brasaland en Colombia y USA.",
};

export default function ProveedoresPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Directorio de proveedores
      </h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Consulta los proveedores de Colombia y USA, filtra por país o categoría, registra proveedores
        nuevos, actualiza tarifas y activa o suspende proveedores.
      </p>

      <SupplierDirectory />
    </main>
  );
}
