import Link from "next/link";
import StageBadge from "@/components/StageBadge";
import StatusBadge from "@/components/StatusBadge";
import type { RecordListItem } from "@/types/record";

export default function CandidateCard({ record }: { record: RecordListItem }) {
  return (
    <Link
      href={`/candidates/${record.id}`}
      className="rounded-lg bg-white p-4 shadow-md transition hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
    >
      <h2 className="mb-2 text-md font-semibold text-red-700 md:text-lg">{record.full_name}</h2>
      <p className="mb-1 text-sm text-black md:text-base">{record.position}</p>
      <p className="mb-1 text-sm text-black md:text-base">{record.email}</p>
      <p className="mb-1 text-sm text-black md:text-base">{record.phone}</p>
      <p className="mb-1 text-sm text-black md:text-base">
        Experiencia: {record.experience_years} años
      </p>
      <div className="mt-2 flex gap-2 text-xs">
        <StatusBadge status={record.status} />
        <StageBadge stage={record.stage} />
      </div>
    </Link>
  );
}
