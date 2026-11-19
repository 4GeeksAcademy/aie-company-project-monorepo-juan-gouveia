"use client";

import Link from "next/link";
import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import Modal from "@/components/Modal";
import FormAlert from "@/components/auth/FormAlert";
import { ApiError } from "@/lib/api-client";
import { toUserMessage } from "@/lib/error-message";
import { attemptDirectStockEdit } from "@/lib/inventory";
import { FIELD_LABELS, formatAmount, formatQuantity } from "@/lib/inventory-labels";
import { parseQuantity } from "@/lib/inventory-validation";
import type { Ingredient } from "@/types/inventory";

// "Ajustar stock" (plan de telemetría, §3.2, y decisión C3). La regla del inventario es que el stock
// no se modifica directamente: solo cambia con órdenes de entrada y de salida trazables a un usuario.
// Esta acción existe para medir cuánto personal intenta saltarse esa regla desde la herramienta que
// usa (métrica obligatoria `direct_stock_edit_rejected`): envía el cambio real a la API, que lo
// rechaza, y explica cómo se hace bien, con enlaces a las dos órdenes del mismo ingrediente.
//
// Los rechazos esperados son el 405 (la API no admite PATCH sobre el producto) y el 422 por un campo
// de stock no permitido. Cualquier otro error (red, sesión…) se muestra con su mensaje.

type Result = { kind: "rejected" } | { kind: "error"; message: string };

function isStockEditRejection(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 405 || err.status === 422);
}

export default function StockAdjustModal({ ingredient, onClose }: { ingredient: Ingredient; onClose: () => void }) {
  const [value, setValue] = useState(formatAmount(ingredient.current_stock));
  const [error, setError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const query = `?ingredient_id=${ingredient.id}`;

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    const stock = parseQuantity(value);
    if (stock === null) {
      setError("Escribe un número, por ejemplo 40 o 12.5.");
      return;
    }
    setError(undefined);
    setSubmitting(true);
    try {
      await attemptDirectStockEdit(ingredient.id, stock);
    } catch (err) {
      setResult(
        isStockEditRejection(err)
          ? { kind: "rejected" }
          : { kind: "error", message: toUserMessage(err, "No se pudo ajustar el stock. Inténtalo de nuevo.") }
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={`Ajustar stock: ${ingredient.name}`} onClose={onClose} busy={submitting}>
      {result?.kind === "rejected" ? (
        <div className="flex flex-col gap-4 text-sm text-black">
          <FormAlert tone="error">
            El stock no se puede editar directamente. Solo cambia con órdenes de entrada y de salida, para que cada
            cambio quede registrado con quién lo hizo, cuándo y por qué.
          </FormAlert>
          <p>
            Stock actual: <strong>{formatQuantity(ingredient.current_stock, ingredient.unit)}</strong>. Para corregirlo:
          </p>
          <ul className="list-disc pl-5">
            <li>si hay más de lo que dice el sistema, registra una entrada;</li>
            <li>si hay menos, registra una salida (consumo o merma, con su motivo).</li>
          </ul>
          <div className="flex flex-wrap justify-end gap-2">
            <Link
              href={`/inventario/ordenes/entrada${query}`}
              className="rounded-md border border-red-200 px-4 py-2 font-semibold text-red-700 hover:bg-red-50"
            >
              Registrar entrada
            </Link>
            <Link
              href={`/inventario/ordenes/salida${query}`}
              className="rounded-md border border-red-200 px-4 py-2 font-semibold text-red-700 hover:bg-red-50"
            >
              Registrar salida
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate aria-busy={submitting} className="flex flex-col gap-4">
          {result?.kind === "error" && <FormAlert tone="error">{result.message}</FormAlert>}
          <FormField
            label={`${FIELD_LABELS.current_stock} (${ingredient.unit})`}
            value={value}
            onChange={setValue}
            required
            error={error}
            hint={`Stock que debería tener ${ingredient.name}, en ${ingredient.unit}.`}
            disabled={submitting}
            inputProps={{ name: "current_stock", inputMode: "decimal", autoComplete: "off" }}
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Guardando..." : "Guardar ajuste"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
