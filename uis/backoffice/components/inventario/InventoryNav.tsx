"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Las cuatro vistas del inventario (decisión F2).
const SECTIONS = [
  { href: "/inventario/ingredientes", label: "Ingredientes" },
  { href: "/inventario/ordenes/entrada", label: "Registrar entrada" },
  { href: "/inventario/ordenes/salida", label: "Registrar salida" },
  { href: "/inventario/ordenes", label: "Historial de órdenes" },
];

// Pestañas entre las vistas del inventario. La activa se compara con la ruta exacta, porque
// /inventario/ordenes es prefijo de las rutas de entrada y salida. En móvil van en dos líneas de dos
// (con una sola fila desplazable, "Historial de órdenes" quedaba fuera de la vista); desde sm, en una.
export default function InventoryNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Secciones del inventario" className="mb-6 border-b border-red-200">
      <ul className="-mb-px grid grid-cols-2 gap-1 sm:flex">
        {SECTIONS.map((section) => {
          const active = pathname === section.href;
          return (
            <li key={section.href} className="sm:shrink-0">
              <Link
                href={section.href}
                aria-current={active ? "page" : undefined}
                className={`block h-full rounded-t border-b-2 px-3 py-2 text-center text-sm sm:text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 ${
                  active
                    ? "border-red-700 font-semibold text-red-700"
                    : "border-transparent text-red-800 hover:bg-red-50"
                }`}
              >
                {section.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
