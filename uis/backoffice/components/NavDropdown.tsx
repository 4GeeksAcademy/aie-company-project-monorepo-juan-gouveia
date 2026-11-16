"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useEscapeKey } from "@/hooks/useEscapeKey";
import type { ToolSection } from "@/lib/tools";

export const NAV_ITEM = "block rounded px-3 py-2 text-sm text-red-800 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700";

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      className={`h-4 w-4 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
    >
      <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Sección del menú con varias herramientas: un botón que abre la lista de sus enlaces (patrón de
// "disclosure": botón con aria-expanded y enlaces normales, sin role="menu"). Se cierra con Escape
// (devolviendo el foco al botón), al hacer clic fuera y al elegir un enlace.
export default function NavDropdown({ section }: { section: ToolSection }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  const closeAndFocus = useCallback(() => {
    setOpen(false);
    buttonRef.current?.focus();
  }, []);
  useEscapeKey(closeAndFocus, open);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(e: PointerEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className={`${NAV_ITEM} flex items-center gap-1`}
      >
        {section.name}
        <ChevronIcon open={open} />
      </button>
      {open && (
        <ul
          id={panelId}
          className="absolute left-0 top-full z-50 mt-1 min-w-56 rounded-md border border-red-200 bg-white p-1 shadow-lg"
        >
          {section.tools.map((tool) => (
            <li key={tool.href}>
              <Link href={tool.href} onClick={() => setOpen(false)} className={NAV_ITEM}>
                {tool.name}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
