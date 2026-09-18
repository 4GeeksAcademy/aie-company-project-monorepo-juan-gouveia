import { useEffect, useState } from "react";
import { createNote, deleteNote, getNotes } from "@/lib/api";
import type { Note } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";

// Carga, creación y borrado (con selección múltiple) de las notas de un candidato.
export function useNotes(recordId: string) {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [notes, setNotes] = useState<Note[]>([]);
  const [error, setError] = useState<string | null>(null);
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

  // Lanza el error si falla, para que quien llama (el modal) pueda mostrarlo.
  async function create(content: string) {
    const note = await createNote(recordId, { content });
    setNotes((prev) => [note, ...prev]);
  }

  function toggleSelected(noteId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(noteId)) next.delete(noteId);
      else next.add(noteId);
      return next;
    });
  }

  // Borra las notas seleccionadas; las que fallan quedan seleccionadas y se avisa del error.
  async function deleteSelected() {
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

  return {
    status,
    notes,
    error,
    selected,
    deleting,
    deleteError,
    create,
    toggleSelected,
    deleteSelected,
  };
}
