import Badge from "@/components/Badge";
import { STAGE_LABELS } from "@/lib/labels";
import type { RecordStage } from "@/types/record";

export default function StageBadge({ stage }: { stage: RecordStage }) {
  return <Badge>{STAGE_LABELS[stage]}</Badge>;
}
