import type { Metadata } from "next";
import EntryForm from "@/components/inventario/EntryForm";
import { presetIngredientId } from "@/lib/inventory-validation";

export const metadata: Metadata = {
  title: "Inventario: registrar entrada",
  description: "Registro de las entregas de proveedor que suman stock a un ingrediente.",
};

interface EntryPageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function EntryPage({ searchParams }: EntryPageProps) {
  // ?ingredient_id= llega desde la lista de ingredientes y preselecciona el ingrediente. La `key`
  // reinicia el formulario si el enlace cambia sin salir de la página (por ejemplo, desde la pestaña).
  const preset = presetIngredientId((await searchParams).ingredient_id);

  return (
    <div className="lg:max-w-3xl">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Registrar entrada</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Registra una entrega de proveedor: la cantidad se suma al stock actual del ingrediente en cuanto se guarda.
      </p>
      <section className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
        <EntryForm key={preset} presetIngredientId={preset} />
      </section>
    </div>
  );
}
