"use client";

import { useEffect, useState } from "react";

interface NewNoteModalProps {
  onClose: () => void;
  onSubmit: (content: string) => Promise<void>;
}

export default function NewNoteModal({ onClose, onSubmit }: NewNoteModalProps) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, submitting]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      setSubmitting(true);
      setError(null);
      await onSubmit(content.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={() => !submitting && onClose()}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-note-title"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="relative w-full max-w-md rounded-lg bg-white p-4 shadow-md md:p-6"
      >
        <button
          type="button"
          onClick={onClose}
          disabled={submitting}
          aria-label="Cerrar"
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md text-xl leading-none text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        >
          ×
        </button>

        <h2 id="new-note-title" className="mb-4 pr-8 text-lg font-semibold text-red-700 md:text-xl">
          Nueva nota
        </h2>

        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={submitting}
          rows={5}
          autoFocus
          placeholder="Escribe la nota..."
          className="w-full resize-none rounded-md border border-red-200 px-3 py-2 text-sm text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
        />

        {error && <p className="mt-2 text-xs text-red-700">{error}</p>}

        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={!content.trim() || submitting}
            className="rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Añadiendo..." : "Añadir"}
          </button>
        </div>
      </form>
    </div>
  );
}
