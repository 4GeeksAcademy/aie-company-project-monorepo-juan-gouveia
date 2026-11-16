import type { Metadata } from "next";
import IngredientsPanel from "@/components/inventario/IngredientsPanel";

export const metadata: Metadata = {
  title: "Inventario: ingredientes",
  description: "Ingredientes de Brasaland con su stock actual y su nivel de stock.",
};

export default function IngredientsPage() {
  return (
    <>
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Ingredientes</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Stock actual de cada ingrediente, calculado a partir de sus entradas y salidas. Desde cada fila se puede
        registrar una entrada o una salida.
      </p>
      <IngredientsPanel />
    </>
  );
}
