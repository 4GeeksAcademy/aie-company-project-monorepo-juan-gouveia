import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import { ORDER_LABEL } from "@/components/inventario/OrderTypeBadge";
import type { OrderFilters as Filters } from "@/lib/inventory-orders";

interface OrderFiltersProps {
  filters: Filters;
  onChange: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  onClear: () => void;
  hasFilters: boolean;
}

// Filtros del historial: tipo de orden e ingrediente (nombre o SKU). Se aplican en el navegador sobre
// las órdenes ya cargadas: GET /inventory/orders no admite filtros.
export default function OrderFilters({ filters, onChange, onClear, hasFilters }: OrderFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <LabeledSelect
        label="Tipo"
        value={filters.kind}
        options={ORDER_LABEL}
        placeholder="Todas"
        onChange={(value) => onChange("kind", value)}
      />
      <div className="w-full sm:w-64">
        <FormField
          label="Ingrediente"
          type="search"
          value={filters.ingredient}
          onChange={(value) => onChange("ingredient", value)}
          inputProps={{ placeholder: "Nombre o SKU", autoComplete: "off" }}
        />
      </div>
      <Button variant="secondary" onClick={onClear} disabled={!hasFilters}>
        Quitar filtros
      </Button>
    </div>
  );
}
