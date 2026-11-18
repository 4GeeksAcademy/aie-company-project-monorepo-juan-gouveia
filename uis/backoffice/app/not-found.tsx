import type { Metadata } from "next";
import ErrorScreen from "@/components/ErrorScreen";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "Página no encontrada",
};

// Rutas que no existen. Queda fuera de los grupos, así que pone su propia cabecera.
export default function NotFound() {
  return (
    <>
      <Header minimal />
      <main className="px-3 py-10 md:px-4">
        <ErrorScreen
          title="Página no encontrada"
          message="La página que buscas no existe o cambió de dirección. Vuelve al inicio para elegir una herramienta."
        />
      </main>
    </>
  );
}
