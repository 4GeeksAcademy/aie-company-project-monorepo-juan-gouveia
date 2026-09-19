import Badge from "@/components/Badge";
import { STATUS_LABELS } from "@/lib/labels";
import type { RecordStatus } from "@/types/record";

export default function StatusBadge({ status }: { status: RecordStatus }) {
  return <Badge>{STATUS_LABELS[status]}</Badge>;
}
