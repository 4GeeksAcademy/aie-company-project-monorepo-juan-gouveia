"use client";

import Link from "next/link";
import { useCallback, useId, useRef, useState } from "react";
import { useEscapeKey } from "@/hooks/useEscapeKey";
import { toolSections } from "@/lib/tools";

// Enlaces más altos y con texto más grande que en escritorio, para tocarlos con el dedo.
const MOBILE_ITEM =
  "block rounded py-3 text-base text-red-800 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700";

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
      {open ? (
        <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
      ) : (
        <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
      )}
    </svg>
  );
}

// Menú hamburguesa de móvil y tablet (por debajo de xl, donde la cabecera no tiene sitio para el
// menú). El panel se despliega bajo la cabecera, a todo el ancho y superpuesto a la página, así que
// la altura fija de la cabecera (de la que depende FilterBar) no cambia. Muestra las mismas secciones
// que el menú de escritorio, con todos sus enlaces visibles. Se cierra con el botón, con Escape
// (devolviendo el foco al botón), al tocar fuera y al elegir un enlace.
export default function MobileNav() {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  const closeAndFocus = useCallback(() => {
    setOpen(false);
    buttonRef.current?.focus();
  }, []);
  useEscapeKey(closeAndFocus, open);

  return (
    <div className="xl:hidden">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={open ? "Cerrar menú" : "Abrir menú"}
        onClick={() => setOpen((value) => !value)}
        className="flex h-10 w-10 items-center justify-center rounded text-red-800 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
      >
        <MenuIcon open={open} />
      </button>

      {open && (
        <>
          {/* Fondo bajo la cabecera: oscurece la página y cierra el menú al tocarlo. */}
          <div aria-hidden="true" onClick={() => setOpen(false)} className="absolute inset-x-0 top-full h-screen bg-black/30" />
          <nav
            id={panelId}
            aria-label="Herramientas"
            className="absolute inset-x-0 top-full max-h-[75vh] overflow-y-auto border-b border-red-200 bg-white px-3 py-3 shadow-lg md:px-4"
          >
            <ul className="flex flex-col gap-1">
              {toolSections.map((section) =>
                section.tools.length === 1 ? (
                  <li key={section.name}>
                    <Link href={section.tools[0].href} onClick={() => setOpen(false)} className={`${MOBILE_ITEM} px-3`}>
                      {section.name}
                    </Link>
                  </li>
                ) : (
                  <li key={section.name} className="mt-2">
                    <p className="px-3 pb-1 text-xs font-semibold uppercase text-red-700">{section.name}</p>
                    <ul className="flex flex-col gap-1">
                      {section.tools.map((tool) => (
                        <li key={tool.href}>
                          <Link href={tool.href} onClick={() => setOpen(false)} className={`${MOBILE_ITEM} pl-6 pr-3`}>
                            {tool.name}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </li>
                )
              )}
            </ul>
          </nav>
        </>
      )}
    </div>
  );
}
