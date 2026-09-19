"use client";

import { useState } from "react";
import Button from "@/components/Button";
import Modal from "@/components/Modal";

interface NewNoteModalProps {
  onClose: () => void;
  onSubmit: (content: string) => Promise<void>;
}

export default function NewNoteModal({ onClose, onSubmit }: NewNoteModalProps) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
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
    <Modal title="Nueva nota" onClose={onClose} busy={submitting}>
      <form onSubmit={handleSubmit}>
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
          <Button variant="secondary" size="md" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" size="md" disabled={!content.trim() || submitting}>
            {submitting ? "Añadiendo..." : "Añadir"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
