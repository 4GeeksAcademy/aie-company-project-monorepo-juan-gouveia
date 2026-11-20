import Button from "@/components/Button";
import LabeledSelect from "@/components/LabeledSelect";
import type { AsyncState } from "@/hooks/useAsyncData";
import { FIELD_LABELS } from "@/lib/inventory-labels";
import { locationOptions } from "@/lib/locations";
import type { Location } from "@/types/locations";

interface LocationSelectProps {
  locations: Location[];
  fetchState: AsyncState<Location[]>;
  onRetry: () => void;
  value: string;
  onChange: (value: string) => void;
  // Texto de ayuda bajo el select (qué hace el local en esta orden).
  hint: string;
  error?: string;
  disabled?: boolean;
}

// Selector de local de los formularios de entrada y salida: los 14 locales del catálogo con su
// nombre y su país. Mientras carga queda deshabilitado; si falla, ofrece reintentar.
export default function LocationSelect({
  locations,
  fetchState,
  onRetry,
  value,
  onChange,
  hint,
  error,
  disabled,
}: LocationSelectProps) {
  if (fetchState.status === "error") {
    return (
      <div role="alert" className="flex flex-col items-start gap-2 text-sm">
        <span className="text-base font-semibold text-red-700">{FIELD_LABELS.location_id} *</span>
        <p className="text-red-700">{fetchState.message}</p>
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      </div>
    );
  }

  const loading = fetchState.status === "loading";

  return (
    <LabeledSelect
      label={FIELD_LABELS.location_id}
      value={value}
      options={locationOptions(locations)}
      onChange={onChange}
      placeholder={loading ? "Cargando locales..." : "Elige el local"}
      required
      size="lg"
      fullWidth
      invalid={Boolean(error)}
      disabled={disabled || loading}
    >
      <span className="text-xs text-gray-600">{hint}</span>
      {error && <span className="text-xs text-red-700">{error}</span>}
    </LabeledSelect>
  );
}
