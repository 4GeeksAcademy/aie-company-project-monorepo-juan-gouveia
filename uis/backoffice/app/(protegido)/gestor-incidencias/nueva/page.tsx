import type { Metadata } from "next";
import IncidentForm from "@/components/gestor-incidencias/IncidentForm";

export const metadata: Metadata = {
  title: "Registrar incidencia",
  description: "Registro de incidencias operativas, de cliente o internas en cualquier sede de Brasaland.",
};

export default function NewIncidentPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-3xl lg:px-8">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Registrar incidencia</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Registra un problema operativo, una queja de cliente o una incidencia interna. Queda guardada al momento,
        con su categoría y su sede, para que Operaciones haga el seguimiento.
      </p>
      <section className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
        <IncidentForm />
      </section>
    </main>
  );
}
