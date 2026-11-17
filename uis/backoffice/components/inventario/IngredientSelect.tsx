import Button from "@/components/Button";
import LabeledSelect from "@/components/LabeledSelect";
import type { AsyncState } from "@/hooks/useAsyncData";
import type { Ingredient } from "@/types/inventory";

interface IngredientSelectProps {
  ingredients: Ingredient[];
  fetchState: AsyncState<Ingredient[]>;
  onRetry: () => void;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

// Selector de ingrediente de los formularios de entrada y salida: por nombre, con SKU y unidad para
// distinguir los de cada país. Mientras carga queda deshabilitado; si falla, ofrece reintentar.
export default function IngredientSelect({
  ingredients,
  fetchState,
  onRetry,
  value,
  onChange,
  error,
  disabled,
}: IngredientSelectProps) {
  if (fetchState.status === "error") {
    return (
      <div role="alert" className="flex flex-col items-start gap-2 text-sm">
        <span className="text-base font-semibold text-red-700">Ingrediente *</span>
        <p className="text-red-700">{fetchState.message}</p>
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      </div>
    );
  }

  const loading = fetchState.status === "loading";
  const options: Record<string, string> = Object.fromEntries(
    ingredients.map((ingredient) => [
      String(ingredient.id),
      `${ingredient.name} · ${ingredient.sku} · ${ingredient.unit}`,
    ])
  );

  return (
    <LabeledSelect
      label="Ingrediente"
      value={value}
      options={options}
      onChange={onChange}
      placeholder={loading ? "Cargando ingredientes..." : "Elige el ingrediente"}
      required
      size="lg"
      fullWidth
      invalid={Boolean(error)}
      disabled={disabled || loading}
    >
      {error && <span className="text-xs text-red-700">{error}</span>}
    </LabeledSelect>
  );
}
