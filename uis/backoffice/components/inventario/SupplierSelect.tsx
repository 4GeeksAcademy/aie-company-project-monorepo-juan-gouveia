import Link from "next/link";
import Button from "@/components/Button";
import LabeledSelect from "@/components/LabeledSelect";
import type { IngredientSuppliers } from "@/hooks/useIngredientSuppliers";
import { FIELD_LABELS } from "@/lib/inventory-labels";
import { supplierFiltersFor } from "@/lib/inventory-suppliers";
import type { Ingredient } from "@/types/inventory";

interface SupplierSelectProps {
  ingredient: Ingredient | undefined;
  suppliers: IngredientSuppliers;
  onRetry: () => void;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

const LABEL_CLASS = "text-base font-semibold text-red-700";

// Proveedor de la entrada: solo los activos del directorio del país y la categoría del ingrediente.
// Se envía su nombre en `supplier_name`, como pide el briefing; sin proveedores, no hay texto libre:
// hay que registrarlo o reactivarlo en el directorio.
export default function SupplierSelect({
  ingredient,
  suppliers,
  onRetry,
  value,
  onChange,
  error,
  disabled,
}: SupplierSelectProps) {
  if (suppliers.status === "error") {
    return (
      <div role="alert" className="flex flex-col items-start gap-2 text-sm">
        <span className={LABEL_CLASS}>{FIELD_LABELS.supplier_name} *</span>
        <p className="text-red-700">{suppliers.message}</p>
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      </div>
    );
  }

  if (suppliers.status === "success" && suppliers.names.length === 0 && ingredient) {
    const filters = supplierFiltersFor(ingredient);
    return (
      <div role="alert" className="flex flex-col items-start gap-1 text-sm">
        <span className={LABEL_CLASS}>{FIELD_LABELS.supplier_name} *</span>
        <p className="rounded border border-amber-400 bg-amber-50 px-3 py-2 text-amber-900">
          No hay proveedores activos de <code>{filters.category}</code> en {filters.country}. Regístralo o
          reactívalo en el{" "}
          <Link href="/proveedores" className="font-semibold underline">
            directorio de proveedores
          </Link>{" "}
          para poder registrar la entrada.
        </p>
        {error && <span className="text-xs text-red-700">{error}</span>}
      </div>
    );
  }

  const names = suppliers.status === "success" ? suppliers.names : [];
  const options: Record<string, string> = Object.fromEntries(names.map((name) => [name, name]));
  const placeholder =
    suppliers.status === "idle"
      ? "Elige primero el ingrediente"
      : suppliers.status === "loading"
        ? "Cargando proveedores..."
        : "Elige el proveedor";

  return (
    <LabeledSelect
      label={FIELD_LABELS.supplier_name}
      value={value}
      options={options}
      onChange={onChange}
      placeholder={placeholder}
      required
      size="lg"
      fullWidth
      invalid={Boolean(error)}
      disabled={disabled || suppliers.status !== "success"}
    >
      <span className="text-xs text-gray-600">
        Proveedores activos del directorio para el país y la categoría del ingrediente.
      </span>
      {error && <span className="text-xs text-red-700">{error}</span>}
    </LabeledSelect>
  );
}
