"use client";

import { useState } from "react";
import Button from "@/components/Button";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import SupplierFilters from "@/components/proveedores/SupplierFilters";
import SupplierFormModal from "@/components/proveedores/SupplierFormModal";
import SupplierList from "@/components/proveedores/SupplierList";
import { useSuppliers } from "@/hooks/useSuppliers";
import type { Supplier } from "@/types/supplier";

export default function SupplierDirectory() {
  const { filters, updateFilter, clearFilters, hasFilters, suppliers, fetchState, replaceSupplier, reload } =
    useSuppliers();
  const [formOpen, setFormOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const activeCount = suppliers.filter((supplier) => supplier.status === "active").length;
  const summary = `${suppliers.length} proveedores: ${activeCount} activos y ${suppliers.length - activeCount} suspendidos`;

  function handleCreated(supplier: Supplier) {
    setFormOpen(false);
    setNotice(`Proveedor «${supplier.name}» registrado.`);
    // Se vuelve a pedir la lista: el nuevo proveedor solo aparece si cumple los filtros activos.
    reload();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <SupplierFilters filters={filters} onChange={updateFilter} onClear={clearFilters} hasFilters={hasFilters} />
        <Button
          size="md"
          onClick={() => {
            setNotice(null);
            setFormOpen(true);
          }}
        >
          Registrar proveedor
        </Button>
      </div>

      {notice && (
        <p role="status" className="text-sm font-semibold text-green-700">
          {notice}
        </p>
      )}

      {formOpen && <SupplierFormModal onClose={() => setFormOpen(false)} onCreated={handleCreated} />}

      {fetchState.status === "loading" && <LoadingMessage>Cargando proveedores...</LoadingMessage>}

      {fetchState.status === "error" && (
        <div role="alert" className="flex flex-col items-start gap-3">
          <ErrorMessage>{fetchState.message}</ErrorMessage>
          <Button variant="secondary" onClick={reload}>
            Reintentar
          </Button>
        </div>
      )}

      {fetchState.status === "success" && (
        <>
          <p className="text-sm text-black" aria-live="polite">
            {summary}
            {hasFilters && " con los filtros aplicados"}.
          </p>
          {suppliers.length === 0 ? (
            <EmptyMessage>
              {hasFilters ? "Ningún proveedor coincide con los filtros." : "Todavía no hay proveedores registrados."}
            </EmptyMessage>
          ) : (
            <SupplierList suppliers={suppliers} onUpdated={replaceSupplier} />
          )}
        </>
      )}
    </div>
  );
}
