import { useState } from "react";
import { patchRecord } from "@/lib/talento/api";
import type { RecordDetail, RecordPatch } from "@/types/record";
import { toUserMessage } from "@/lib/error-message";

type PatchableField = keyof RecordPatch;

// Gestiona el PATCH de un solo campo de un candidato: estado de carga, error y llamada.
export function usePatchField<K extends PatchableField>(
  recordId: string,
  field: K,
  onUpdated: (record: RecordDetail) => void
) {
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function update(value: NonNullable<RecordPatch[K]>) {
    try {
      setUpdating(true);
      setError(null);
      onUpdated(await patchRecord(recordId, { [field]: value }));
    } catch (err) {
      setError(toUserMessage(err, "No se pudo guardar el cambio. Inténtalo de nuevo."));
    } finally {
      setUpdating(false);
    }
  }

  return { updating, error, update };
}
