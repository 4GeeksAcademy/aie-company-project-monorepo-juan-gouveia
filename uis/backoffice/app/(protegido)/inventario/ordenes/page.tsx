import type { Metadata } from "next";
import OrdersPanel from "@/components/inventario/OrdersPanel";

export const metadata: Metadata = {
  title: "Inventario: historial de órdenes",
  description: "Entradas y salidas del inventario, con quién las registró y cuándo.",
};

export default function OrdersPage() {
  return (
    <>
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Historial de órdenes</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Todas las entradas y salidas, de la más reciente a la más antigua. Cada orden guarda el{" "}
        <code className="font-mono text-sm">user_uuid</code> de quien la registró; las tuyas llevan la etiqueta
        «Tú».
      </p>
      <OrdersPanel />
    </>
  );
}
