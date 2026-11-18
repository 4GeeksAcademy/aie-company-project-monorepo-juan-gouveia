import { redirect } from "next/navigation";

// /inventario no tiene vista propia: la sección empieza en la lista de ingredientes (decisión F2).
export default function InventoryPage() {
  redirect("/inventario/ingredientes");
}
