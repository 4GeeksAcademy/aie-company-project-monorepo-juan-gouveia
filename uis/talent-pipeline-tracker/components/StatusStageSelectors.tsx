"use client";

import LabeledSelect from "@/components/LabeledSelect";
import { usePatchField } from "@/hooks/usePatchField";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordDetail } from "@/types/record";

interface StatusStageSelectorsProps {
  record: RecordDetail;
  onUpdated: (record: RecordDetail) => void;
}

export default function StatusStageSelectors({ record, onUpdated }: StatusStageSelectorsProps) {
  const statusPatch = usePatchField(record.id, "status", onUpdated);
  const stagePatch = usePatchField(record.id, "stage", onUpdated);

  return (
    <div className="mb-4 flex items-start gap-3 md:gap-4">
      <LabeledSelect
        label="Status"
        value={record.status}
        options={STATUS_LABELS}
        onChange={statusPatch.update}
        disabled={statusPatch.updating}
      >
        {statusPatch.updating && <span className="text-xs text-black">Actualizando...</span>}
        {statusPatch.error && <span className="text-xs text-red-700">{statusPatch.error}</span>}
      </LabeledSelect>

      <LabeledSelect
        label="Stage"
        value={record.stage}
        options={STAGE_LABELS}
        onChange={stagePatch.update}
        disabled={stagePatch.updating}
      >
        {stagePatch.updating && <span className="text-xs text-black">Actualizando...</span>}
        {stagePatch.error && <span className="text-xs text-red-700">{stagePatch.error}</span>}
      </LabeledSelect>
    </div>
  );
}
