import Button from "@/components/Button";

interface CandidateHeaderProps {
  name: string;
  onEdit: () => void;
}

export default function CandidateHeader({ name, onEdit }: CandidateHeaderProps) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h1 className="min-w-0 break-words text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        {name}
      </h1>
      <Button onClick={onEdit} className="shrink-0">
        Editar candidato
      </Button>
    </div>
  );
}
