"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import FormAlert from "@/components/auth/FormAlert";
import IngredientSelect from "@/components/inventario/IngredientSelect";
import SupplierSelect from "@/components/inventario/SupplierSelect";
import { useIngredientSuppliers } from "@/hooks/useIngredientSuppliers";
import { useIngredients } from "@/hooks/useIngredients";
import { formErrorsFromApi } from "@/lib/auth/api-errors";
import { mergeFieldErrors } from "@/lib/auth/validation";
import { createEntry } from "@/lib/inventory";
import { FIELD_LABELS, LOCATION_OPTIONS, formatQuantity } from "@/lib/inventory-labels";
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
// - valida los obligatorios en el cliente antes de enviar; la API vuelve a validar (422 por campo);
// - durante el envío, el botón queda deshabilitado y muestra un indicador;
// - los errores de la API se muestran con su mensaje y, si señalan un campo, junto a él;
// - tras el éxito, el formulario se limpia (conserva el ingrediente que venía en el enlace).
export default function EntryForm({ presetIngredientId }: { presetIngredientId: string }) {
  const initialValues: EntryFormValues = { ...EMPTY_ENTRY_FORM, ingredient_id: presetIngredientId };
  const { ingredients, fetchState, reload } = useIngredients();
  const [values, setValues] = useState<EntryFormValues>(initialValues);
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
    if (Object.keys(localErrors()).length > 0) {
      show({ tone: "error", text: "Revisa los campos marcados." });
      return;
    }

    setSubmitting(true);
    setApiFields({});
    try {
      const entry = await createEntry(toEntryInput(values));
      setValues(initialValues);
      setAttempted(false);
      show({
        tone: "success",
        text: `Entrada #${entry.id} registrada: ${formatQuantity(entry.quantity, entry.ingredient.unit)} de ${entry.ingredient.name}.`,
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

      <IngredientSelect
        ingredients={ingredients}
        fetchState={fetchState}
        onRetry={reload}
        value={values.ingredient_id}
        onChange={(value) => {
          setField("ingredient_id", value);
          // Los proveedores dependen del ingrediente: el elegido puede no servir para el nuevo.
          setField("supplier_name", "");
        }}
        error={errors.ingredient_id}
        disabled={submitting}
      />

      <div className="grid gap-5 md:grid-cols-2">
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

        <LabeledSelect
          label={FIELD_LABELS.location_id}
          value={values.location_id}
          options={LOCATION_OPTIONS}
          onChange={(value) => setField("location_id", value)}
          placeholder="Elige el local"
          required
          size="lg"
          fullWidth
          invalid={Boolean(errors.location_id)}
          disabled={submitting}
        >
          <span className="text-xs text-gray-600">Local que recibe la entrega.</span>
          {errors.location_id && <span className="text-xs text-red-700">{errors.location_id}</span>}
        </LabeledSelect>
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

      <p className="text-xs text-gray-600">Los campos con * son obligatorios.</p>

      <div className="flex justify-end">
        <Button
          type="submit"
          size="md"
          // Sin la lista de ingredientes no se puede elegir ni comprobar el ingrediente.
          disabled={submitting || fetchState.status !== "success"}
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
