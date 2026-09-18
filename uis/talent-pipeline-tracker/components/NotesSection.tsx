"use client";

import { useState } from "react";
import Button from "@/components/Button";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import NewNoteModal from "@/components/NewNoteModal";
import NoteItem from "@/components/NoteItem";
import { useNotes } from "@/hooks/useNotes";

interface NotesSectionProps {
  recordId: string;
}

export default function NotesSection({ recordId }: NotesSectionProps) {
  const {
    status,
    notes,
    error,
    selected,
    deleting,
    deleteError,
    create,
    toggleSelected,
    deleteSelected,
  } = useNotes(recordId);
  const [modalOpen, setModalOpen] = useState(false);

  async function handleCreate(content: string) {
    await create(content);
    setModalOpen(false);
  }

  return (
    <section className="mt-6 border-t border-red-100 pt-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-red-700 md:text-xl">Notas</h2>
        <div className="flex gap-2">
          {selected.size > 0 && (
            <Button variant="danger" onClick={deleteSelected} disabled={deleting}>
              {deleting ? "Eliminando..." : `Eliminar (${selected.size})`}
            </Button>
          )}
          <Button onClick={() => setModalOpen(true)}>Nueva nota</Button>
        </div>
      </div>

      {deleteError && <p className="mb-2 text-xs text-red-700">{deleteError}</p>}

      {status === "loading" && <LoadingMessage compact>Cargando notas...</LoadingMessage>}
      {status === "error" && <ErrorMessage compact>{error}</ErrorMessage>}
      {status === "success" && notes.length === 0 && (
        <EmptyMessage compact>Este candidato aún no tiene notas.</EmptyMessage>
      )}

      {status === "success" && notes.length > 0 && (
        <ul className="flex flex-col gap-2">
          {notes.map((note) => (
            <li key={note.id}>
              <NoteItem
                note={note}
                selected={selected.has(note.id)}
                onToggle={() => toggleSelected(note.id)}
                disabled={deleting}
              />
            </li>
          ))}
        </ul>
      )}

      {modalOpen && <NewNoteModal onClose={() => setModalOpen(false)} onSubmit={handleCreate} />}
    </section>
  );
}
