"use client";

import { useEffect, useState } from "react";
import { createNote, deleteNote, getNotes } from "@/lib/api";
import type { Note } from "@/types/record";
import NewNoteModal from "./NewNoteModal";

type FetchStatus = "loading" | "success" | "error";

interface NotesSectionProps {
  recordId: string;
}

export default function NotesSection({ recordId }: NotesSectionProps) {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [notes, setNotes] = useState<Note[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    async function loadNotes() {
      try {
        setStatus("loading");
        setNotes(await getNotes(recordId));
        setStatus("success");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error desconocido");
        setStatus("error");
      }
    }

    loadNotes();
  }, [recordId]);

  async function handleCreate(content: string) {
    const note = await createNote(recordId, { content });
    setNotes((prev) => [note, ...prev]);
    setModalOpen(false);
  }

  function toggleSelected(noteId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(noteId)) next.delete(noteId);
      else next.add(noteId);
      return next;
    });
  }

  async function handleDelete() {
    const ids = [...selected];
    setDeleting(true);
    setDeleteError(null);

    const results = await Promise.allSettled(ids.map((noteId) => deleteNote(recordId, noteId)));
    const deletedIds = new Set(ids.filter((_, i) => results[i].status === "fulfilled"));

    setNotes((prev) => prev.filter((n) => !deletedIds.has(n.id)));
    setSelected(new Set(ids.filter((noteId) => !deletedIds.has(noteId))));
    if (deletedIds.size < ids.length) {
      setDeleteError(`No se pudieron eliminar ${ids.length - deletedIds.size} nota(s)`);
    }
    setDeleting(false);
  }

  return (
    <section className="mt-6 border-t border-red-100 pt-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-red-700 md:text-xl">Notas</h2>
        <div className="flex gap-2">
          {selected.size > 0 && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-md border border-red-700 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
            >
              {deleting ? "Eliminando..." : `Eliminar (${selected.size})`}
            </button>
          )}
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="rounded-md bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          >
            Nueva nota
          </button>
        </div>
      </div>

      {deleteError && <p className="mb-2 text-xs text-red-700">{deleteError}</p>}

      {status === "loading" && <p className="text-sm text-black">Cargando notas...</p>}
      {status === "error" && <p className="text-sm text-red-700">{error}</p>}
      {status === "success" && notes.length === 0 && (
        <p className="text-sm text-black">Este candidato aún no tiene notas.</p>
      )}

      {status === "success" && notes.length > 0 && (
        <ul className="flex flex-col gap-2">
          {notes.map((note) => (
            <li key={note.id}>
              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-red-100 p-3 hover:bg-red-50">
                <input
                  type="checkbox"
                  checked={selected.has(note.id)}
                  onChange={() => toggleSelected(note.id)}
                  disabled={deleting}
                  aria-label="Seleccionar nota"
                  className="mt-1 h-4 w-4 accent-red-700"
                />
                <span className="min-w-0 flex-1">
                  <span className="block whitespace-pre-wrap break-words text-sm text-black">
                    {note.content}
                  </span>
                  <span className="mt-1 block text-xs text-black/60">
                    {new Date(note.created_at).toLocaleString("es", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}

      {modalOpen && (
        <NewNoteModal onClose={() => setModalOpen(false)} onSubmit={handleCreate} />
      )}
    </section>
  );
}
