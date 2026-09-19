import DetailItem from "@/components/DetailItem";
import ExternalLink from "@/components/ExternalLink";
import { formatDate } from "@/lib/format";
import type { RecordDetail } from "@/types/record";

export default function CandidateDetails({ record }: { record: RecordDetail }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-2 md:grid-cols-2">
      <DetailItem label="Posición">{record.position}</DetailItem>
      <DetailItem label="Experiencia">{record.experience_years} años</DetailItem>
      <DetailItem label="Fecha de aplicación">
        {formatDate(record.applied_at)}
      </DetailItem>
      <DetailItem label="Email">{record.email}</DetailItem>
      <DetailItem label="Teléfono">{record.phone}</DetailItem>
      {record.linkedin_url && (
        <DetailItem label="LinkedIn">
          <ExternalLink href={record.linkedin_url}>Ver perfil</ExternalLink>
        </DetailItem>
      )}
      {record.cv_url && (
        <DetailItem label="CV">
          <ExternalLink href={record.cv_url}>Ver CV</ExternalLink>
        </DetailItem>
      )}
    </dl>
  );
}
