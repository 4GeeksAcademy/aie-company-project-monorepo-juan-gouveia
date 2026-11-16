import InventoryNav from "@/components/inventario/InventoryNav";

// Marco común de las cuatro vistas del inventario: el mismo ancho que el resto del backoffice y las
// pestañas para pasar de una vista a otra. Cada página pone su título, su descripción y su metadata.
export default function InventoryLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <InventoryNav />
      {children}
    </main>
  );
}
