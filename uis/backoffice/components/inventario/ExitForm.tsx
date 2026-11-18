"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import FormAlert from "@/components/auth/FormAlert";
import IngredientSelect from "@/components/inventario/IngredientSelect";
import StockPanel from "@/components/inventario/StockPanel";
import { useIngredientStock } from "@/hooks/useIngredientStock";
import { useIngredients } from "@/hooks/useIngredients";
import { mergeFieldErrors } from "@/lib/auth/validation";
import { createExit } from "@/lib/inventory";
import { FIELD_LABELS, LOCATION_OPTIONS, REASON_DESCRIPTIONS, REASON_OPTIONS, formatQuantity } from "@/lib/inventory-labels";
import {
  EMPTY_EXIT_FORM,
  exceedsStock,
  exitErrorsFromApi,
  toExitInput,
  validateExitForm,
  type ExitFormErrors,
  type ExitFormField,
  type ExitFormValues,
} from "@/lib/inventory-validation";

type Message = { tone: "error" | "success"; text: string };

const UNKNOWN_INGREDIENT = "El ingrediente del enlace ya no existe. Elige otro.";

// Registro de salidas (consumo o merma), con el patrón de EntryForm:
// - muestra el stock actual del ingrediente elegido, pedido a la API al elegirlo;
// - avisa, sin bloquear, si la cantidad supera ese stock: la API aplica la regla con el stock del
//   momento (puede haber cambiado) y su 400 `insufficient_stock` se muestra junto a la cantidad;
// - tras el éxito, limpia la cantidad (conserva ingrediente, motivo y local) y refresca el stock.
export default function ExitForm({ presetIngredientId }: { presetIngredientId: string }) {
  const { ingredients, fetchState, reload } = useIngredients();
  const [values, setValues] = useState<ExitFormValues>({ ...EMPTY_EXIT_FORM, ingredient_id: presetIngredientId });
  // Los errores locales se muestran tras el primer intento de envío.
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiFields, setApiFields] = useState<ExitFormErrors>({});
  const [message, setMessage] = useState<Message | null>(null);
  const messageRef = useRef<HTMLDivElement>(null);

  const selected = ingredients.find((ingredient) => String(ingredient.id) === values.ingredient_id);
  // Un id del enlace que no está en la lista (ingrediente borrado o enlace manipulado).
  const unknownIngredient = fetchState.status === "success" && Boolean(values.ingredient_id) && !selected;
  // Solo se pide el stock de un ingrediente que existe.
  const { stock, refresh } = useIngredientStock(selected ? values.ingredient_id : "");
  const shownStock = stock.status === "success" ? stock.ingredient.current_stock : null;
  const overStock = exceedsStock(values.quantity, shownStock);

  function localErrors(): ExitFormErrors {
    const errors = validateExitForm(values);
    if (!errors.ingredient_id && unknownIngredient) errors.ingredient_id = UNKNOWN_INGREDIENT;
    return errors;
  }

  const errors = mergeFieldErrors(
    attempted ? localErrors() : unknownIngredient ? { ingredient_id: UNKNOWN_INGREDIENT } : {},
    apiFields
  );

  function setField<K extends ExitFormField>(field: K, value: ExitFormValues[K]) {
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
      const exit = await createExit(toExitInput(values));
      setValues((prev) => ({ ...prev, quantity: "" }));
      setAttempted(false);
      show({
        tone: "success",
        text: `Salida #${exit.id} registrada: ${formatQuantity(exit.quantity, exit.ingredient_unit)} de ${exit.ingredient_name} (${exit.reason}: ${REASON_DESCRIPTIONS[exit.reason]}).`,
      });
      refresh();
    } catch (err) {
      const result = exitErrorsFromApi(err);
      setApiFields(result.fields);
      if (result.message) show({ tone: "error", text: result.message });
      // Con stock insuficiente, el mostrado estaba desactualizado: se vuelve a pedir.
      if (result.fields.quantity) refresh();
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
        onChange={(value) => setField("ingredient_id", value)}
        error={errors.ingredient_id}
        disabled={submitting}
      />

      <div aria-live="polite" className="rounded-md border border-red-100 bg-red-50/40 p-3">
        <StockPanel stock={stock} onRetry={refresh} />
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="flex flex-col gap-1">
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
          {/* Aviso, no error: no bloquea el envío. Se oculta si la cantidad ya tiene un error. */}
          {overStock && !errors.quantity && shownStock !== null && selected && (
            <p role="status" className="rounded border border-amber-400 bg-amber-50 px-2 py-1 text-xs text-amber-900">
              La cantidad supera el stock actual ({formatQuantity(shownStock, selected.unit)}). La API rechazará la
              salida si sigue sin haber stock suficiente.
            </p>
          )}
        </div>

        <LabeledSelect
          label={FIELD_LABELS.reason}
          value={values.reason}
          options={REASON_OPTIONS}
          onChange={(value) => setField("reason", value)}
          placeholder="Elige el motivo"
          required
          size="lg"
          fullWidth
          invalid={Boolean(errors.reason)}
          disabled={submitting}
        >
          {values.reason && <span className="text-xs text-gray-600">{REASON_DESCRIPTIONS[values.reason]}</span>}
          {errors.reason && <span className="text-xs text-red-700">{errors.reason}</span>}
        </LabeledSelect>
      </div>

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
        <span className="text-xs text-gray-600">Local donde se consume o se desecha.</span>
        {errors.location_id && <span className="text-xs text-red-700">{errors.location_id}</span>}
      </LabeledSelect>

      <p className="text-xs text-gray-600">Los campos con * son obligatorios.</p>

      <div className="flex justify-end">
        <Button
          type="submit"
          size="md"
          // Sin la lista de ingredientes no se puede elegir ni comprobar el ingrediente.
          disabled={submitting || fetchState.status !== "success"}
          className="inline-flex items-center gap-2 px-6 py-3 text-base"
        >
          {submitting && (
            <span
              aria-hidden="true"
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
            />
          )}
          {submitting ? "Registrando salida..." : "Registrar salida"}
        </Button>
      </div>
    </form>
  );
}
