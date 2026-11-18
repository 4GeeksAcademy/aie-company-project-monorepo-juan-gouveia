import Button from "@/components/Button";
import LabeledSelect from "@/components/LabeledSelect";
import { BRANCH_LABELS, ORIGIN_OPTIONS, STATUS_OPTIONS } from "@/lib/gestor-incidencias/labels";
import type { IncidentFilters as Filters } from "@/types/incident-manager";

interface IncidentFiltersProps {
  filters: Filters;
  onChange: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  onClear: () => void;
  hasFilters: boolean;
}

// Filtros del listado por status, origin y branch (los que pide la consigna).
export default function IncidentFilters({ filters, onChange, onClear, hasFilters }: IncidentFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <LabeledSelect
        label="Estado (status)"
        value={filters.status}
        options={STATUS_OPTIONS}
        placeholder="Todos"
        onChange={(value) => onChange("status", value)}
      />
      <LabeledSelect
        label="Origen (origin)"
        value={filters.origin}
        options={ORIGIN_OPTIONS}
        placeholder="Todos"
        onChange={(value) => onChange("origin", value)}
      />
      <LabeledSelect
        label="Sede (branch)"
        value={filters.branch}
        options={BRANCH_LABELS}
        placeholder="Todas"
        onChange={(value) => onChange("branch", value)}
      />
      <Button variant="secondary" onClick={onClear} disabled={!hasFilters}>
        Quitar filtros
      </Button>
    </div>
  );
}
