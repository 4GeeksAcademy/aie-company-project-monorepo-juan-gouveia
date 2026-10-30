import { formatDateTime } from "@/lib/format";
import type { Note } from "@/types/record";

interface NoteItemProps {
  note: Note;
  selected: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export default function NoteItem({ note, selected, onToggle, disabled }: NoteItemProps) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-md border border-red-100 p-3 hover:bg-red-50">
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        disabled={disabled}
        aria-label="Seleccionar nota"
        className="mt-1 h-4 w-4 accent-red-700"
      />
      <span className="min-w-0 flex-1">
        <span className="block whitespace-pre-wrap break-words text-sm text-black">
          {note.content}
        </span>
        <span className="mt-1 block text-xs text-black/60">{formatDateTime(note.created_at)}</span>
      </span>
    </label>
  );
}
