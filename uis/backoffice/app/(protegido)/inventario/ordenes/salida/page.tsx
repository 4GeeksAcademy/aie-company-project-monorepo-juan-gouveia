import type { Metadata } from "next";
import ExitForm from "@/components/inventario/ExitForm";
import { presetIngredientId } from "@/lib/inventory-validation";

export const metadata: Metadata = {
  title: "Inventario: registrar salida",
  description: "Registro de los consumos y las mermas que restan stock a un ingrediente.",
};

interface ExitPageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function ExitPage({ searchParams }: ExitPageProps) {
  // ?ingredient_id= llega desde la lista de ingredientes y preselecciona el ingrediente. La `key`
  // reinicia el formulario si el enlace cambia sin salir de la página (por ejemplo, desde la pestaña).
  const preset = presetIngredientId((await searchParams).ingredient_id);

  return (
    <div className="lg:max-w-3xl">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Registrar salida</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Registra un consumo o una merma: la cantidad se resta del stock actual del ingrediente. El stock nunca puede
        quedar en negativo.
      </p>
      <section className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
        <ExitForm key={preset} presetIngredientId={preset} />
      </section>
    </div>
  );
}
