"use client";

import { useId } from "react";
import { useEscapeKey } from "@/hooks/useEscapeKey";

interface ModalProps {
  title: string;
  onClose: () => void;
  // Mientras está ocupado (p. ej. enviando) no se puede cerrar ni con Escape ni con clic fuera.
  busy?: boolean;
  size?: "md" | "lg";
  children: React.ReactNode;
}

const SIZE_CLASS = { md: "max-w-md", lg: "max-w-2xl" } as const;

export default function Modal({ title, onClose, busy = false, size = "md", children }: ModalProps) {
  const titleId = useId();
  useEscapeKey(onClose, !busy);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={() => !busy && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
        className={`relative max-h-[90vh] w-full ${SIZE_CLASS[size]} overflow-y-auto rounded-lg bg-white p-4 shadow-md md:p-6`}
      >
        <button
          type="button"
          onClick={onClose}
          disabled={busy}
          aria-label="Cerrar"
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md text-xl leading-none text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        >
          ×
        </button>

        <h2 id={titleId} className="mb-4 pr-8 text-lg font-semibold text-red-700 md:text-xl">
          {title}
        </h2>

        {children}
      </div>
    </div>
  );
}
