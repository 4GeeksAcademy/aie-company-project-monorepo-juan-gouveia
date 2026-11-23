"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import FormAlert from "@/components/auth/FormAlert";
import IngredientSelect from "@/components/inventario/IngredientSelect";
import LocationSelect from "@/components/inventario/LocationSelect";
import StockPanel from "@/components/inventario/StockPanel";
import SupplierSelect from "@/components/inventario/SupplierSelect";
import { useIngredientStock } from "@/hooks/useIngredientStock";
import { useIngredientSuppliers } from "@/hooks/useIngredientSuppliers";
import { useIngredients } from "@/hooks/useIngredients";
import { useFormTelemetry } from "@/hooks/useFormTelemetry";
import { useLocations } from "@/hooks/useLocations";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { mergeFieldErrors } from "@/lib/auth/validation";
import { createEntry } from "@/lib/inventory";
import { FIELD_LABELS, formatQuantity } from "@/lib/inventory-labels";
import {
  conflictsWithLocation,
  findLocation,
  ingredientListHint,
  ingredientsForLocation,
  locationHintFor,
  removedIngredientNotice,
} from "@/lib/locations";
import {
  EMPTY_ENTRY_FORM,
  ENTRY_FORM_FIELDS,
  toEntryInput,
  validateEntryForm,
  type EntryFormErrors,
  type EntryFormField,
  type EntryFormValues,
} from "@/lib/inventory-validation";

type Message = { tone: "error" | "success"; text: string };

const UNKNOWN_INGREDIENT = "El ingrediente del enlace ya no existe. Elige otro.";

// Registro de entradas (entregas de proveedor), con el patrón de IncidentForm:
// - el local va primero y solo deja elegir ingredientes de su país (la API lo exige: 422
//   `location_country_mismatch`); elegir un local de otro país descarta el ingrediente y lo avisa;
// - muestra el stock actual del ingrediente elegido bajo la cantidad, como el formulario de salida;
// - valida los obligatorios en el cliente antes de enviar; la API vuelve a validar (422 por campo);
// - durante el envío, el botón queda deshabilitado y muestra un indicador;
// - los errores de la API se muestran con su mensaje y, si señalan un campo, junto a él;
// - tras el éxito, el formulario se limpia (conserva el ingrediente que venía en el enlace).
export default function EntryForm({ presetIngredientId }: { presetIngredientId: string }) {
  const initialValues: EntryFormValues = { ...EMPTY_ENTRY_FORM, ingredient_id: presetIngredientId };
  const { ingredients, fetchState, reload } = useIngredients();
  const { locations, fetchState: locationsState, reload: reloadLocations } = useLocations();
  // Telemetría: errores de validación y abandono del formulario (solo nombres de campo).
  const formTelemetry = useFormTelemetry("inbound_order");
  const [values, setValues] = useState<EntryFormValues>(initialValues);
  // Aviso cuando un cambio de local descarta el ingrediente elegido.
  const [ingredientNotice, setIngredientNotice] = useState<string | null>(null);
  // Los errores locales se muestran tras el primer intento de envío.
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<EntryFormErrors>({});
  const [message, setMessage] = useState<Message | null>(null);
  const messageRef = useRef<HTMLDivElement>(null);

  const selected = ingredients.find((ingredient) => String(ingredient.id) === values.ingredient_id);
  // Un id del enlace que no está en la lista (ingrediente borrado o enlace manipulado).
  const unknownIngredient = fetchState.status === "success" && Boolean(values.ingredient_id) && !selected;
  const { suppliers, reload: reloadSuppliers } = useIngredientSuppliers(selected);
  // Stock actual del ingrediente, como en las salidas: solo se pide el de un ingrediente que existe.
  const { stock, refresh: refreshStock } = useIngredientStock(selected ? values.ingredient_id : "");
  const location = findLocation(locations, values.location_id);
  // Moneda del coste unitario: la del local (COP en Colombia, USD en Florida). El ingrediente es del
  // mismo país, porque la lista solo ofrece los del país del local.
  const currency = location?.currency ?? null;

  function localErrors(): EntryFormErrors {
    const errors = validateEntryForm(values);
    if (!errors.ingredient_id && unknownIngredient) errors.ingredient_id = UNKNOWN_INGREDIENT;
    return errors;
  }

  const errors = mergeFieldErrors(
    attempted ? localErrors() : unknownIngredient ? { ingredient_id: UNKNOWN_INGREDIENT } : {},
    apiFields
  );

  function setField<K extends EntryFormField>(field: K, value: EntryFormValues[K]) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setApiFields((prev) => ({ ...prev, [field]: undefined }));
    setMessage(null);
    formTelemetry.fieldChanged(field);
  }

  function changeLocation(value: string) {
    setField("location_id", value);
    const next = findLocation(locations, value);
    if (selected && next && conflictsWithLocation(selected, next)) {
      setField("ingredient_id", "");
      setField("supplier_name", "");
      setIngredientNotice(removedIngredientNotice(selected, next));
    } else {
      setIngredientNotice(null);
    }
  }

  function show(next: Message) {
    setMessage(next);
    // El aviso está arriba del formulario: en una tablet puede quedar fuera de la vista.
    requestAnimationFrame(() => messageRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    setMessage(null);
    const invalid = localErrors();
    if (Object.keys(invalid).length > 0) {
      formTelemetry.validationFailed(invalid);
      show({ tone: "error", text: "Revisa los campos marcados." });
      return;
    }

    setSubmitting(true);
    setApiFields({});
    try {
      const supplierId = suppliers.status === "success" ? suppliers.idsByName[values.supplier_name.trim()] : undefined;
      // `selected` y `location` existen: la validación local rechaza un ingrediente o un local desconocidos.
      const entry = await createEntry(
        toEntryInput(values),
        selected && location ? { ingredient: selected, location, supplierId } : undefined
      );
      formTelemetry.submitted();
      setValues(initialValues);
      setIngredientNotice(null);
      setAttempted(false);
      // Si el formulario conserva el ingrediente del enlace, su stock ya cambió con la entrada.
      refreshStock();
      show({
        tone: "success",
        text: `Entrada #${entry.id} registrada: ${formatQuantity(entry.quantity, entry.ingredient_unit)} de ${entry.ingredient_name}.`,
      });
    } catch (err) {
      const result = formErrorsFromApi(err, ENTRY_FORM_FIELDS, "No se pudo registrar la entrada.");
      setApiFields(result.fields);
      if (result.message) show({ tone: "error", text: result.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate aria-busy={submitting} className="flex flex-col gap-5">
      <div ref={messageRef}>
        {message && (
          <FormAlert tone={message.tone}>
            {message.text}
            {message.tone === "success" && (
              <>
                {" "}
                <Link href="/inventario/ingredientes" className="font-semibold underline">
                  Ver ingredientes
                </Link>{" "}
                ·{" "}
                <Link href="/inventario/ordenes" className="font-semibold underline">
                  Ver historial
                </Link>
              </>
            )}
          </FormAlert>
        )}
      </div>

      <LocationSelect
        locations={locations}
        fetchState={locationsState}
        onRetry={reloadLocations}
        value={values.location_id}
        onChange={changeLocation}
        hint={locationHintFor("Local que recibe la entrega.", selected, location)}
        error={errors.location_id}
        disabled={submitting}
      />

      <IngredientSelect
        ingredients={ingredientsForLocation(ingredients, location)}
        fetchState={fetchState}
        onRetry={reload}
        value={values.ingredient_id}
        onChange={(value) => {
          setField("ingredient_id", value);
          // Los proveedores dependen del ingrediente: el elegido puede no servir para el nuevo.
          setField("supplier_name", "");
          setIngredientNotice(null);
        }}
        hint={ingredientNotice ?? ingredientListHint(location)}
        error={errors.ingredient_id}
        disabled={submitting}
      />

      <FormField
        label={selected ? `${FIELD_LABELS.quantity} (${selected.unit})` : FIELD_LABELS.quantity}
        value={values.quantity}
        onChange={(value) => setField("quantity", value)}
        required
        size="lg"
        error={errors.quantity}
        hint={selected ? `En ${selected.unit}. Admite decimales: 12.5` : "Elige primero el ingrediente para ver su unidad."}
        disabled={submitting}
        inputProps={{ name: "quantity", inputMode: "decimal", autoComplete: "off" }}
      />

      <div aria-live="polite" className="rounded-md border border-red-100 bg-red-50/40 p-3">
        <StockPanel stock={stock} onRetry={refreshStock} />
      </div>

      <SupplierSelect
        ingredient={selected}
        suppliers={suppliers}
        onRetry={reloadSuppliers}
        value={values.supplier_name}
        onChange={(value) => setField("supplier_name", value)}
        error={errors.supplier_name}
        disabled={submitting}
      />

      <FormField
        label={selected && currency ? `${FIELD_LABELS.unit_cost} (${currency} por ${selected.unit})` : FIELD_LABELS.unit_cost}
        value={values.unit_cost}
        onChange={(value) => setField("unit_cost", value)}
        required
        size="lg"
        error={errors.unit_cost}
        hint={
          selected && currency
            ? `Precio de este proveedor por cada ${selected.unit}, en ${currency}. Admite decimales: 6.8`
            : "Elige primero el local y el ingrediente para ver la moneda y la unidad."
        }
        disabled={submitting}
        inputProps={{ name: "unit_cost", inputMode: "decimal", autoComplete: "off" }}
      />

      <p className="text-xs text-gray-600">Los campos con * son obligatorios.</p>

      <div className="flex justify-end">
        <Button
          type="submit"
          size="md"
          // Sin las listas de ingredientes y locales no se pueden elegir ni comprobar.
          disabled={submitting || fetchState.status !== "success" || locationsState.status !== "success"}
          className="inline-flex items-center gap-2 px-6 py-3 text-base">
          {submitting && (
            <span
              aria-hidden="true"
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
            />
          )}
          {submitting ? "Registrando entrada..." : "Registrar entrada"}
        </Button>
      </div>
    </form>
  );
}
