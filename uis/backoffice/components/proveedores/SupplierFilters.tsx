import Button from "@/components/Button";
import LabeledSelect from "@/components/LabeledSelect";
import { CATEGORY_OPTIONS, COUNTRY_OPTIONS } from "@/lib/proveedores/labels";
import type { SupplierFilters as Filters } from "@/types/supplier";

interface SupplierFiltersProps {
  filters: Filters;
  onChange: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  onClear: () => void;
  hasFilters: boolean;
}

export default function SupplierFilters({ filters, onChange, onClear, hasFilters }: SupplierFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <LabeledSelect
        label="País"
        value={filters.country}
        options={COUNTRY_OPTIONS}
        placeholder="Todos"
        onChange={(value) => onChange("country", value)}
      />
      <LabeledSelect
        label="Categoría"
        value={filters.category}
        options={CATEGORY_OPTIONS}
        placeholder="Todas"
        onChange={(value) => onChange("category", value)}
      />
      <Button variant="secondary" onClick={onClear} disabled={!hasFilters}>
        Quitar filtros
      </Button>
    </div>
  );
}
