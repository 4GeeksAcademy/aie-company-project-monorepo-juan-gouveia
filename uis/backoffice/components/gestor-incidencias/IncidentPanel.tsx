"use client";

import Link from "next/link";
import Button from "@/components/Button";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import IncidentFilters from "@/components/gestor-incidencias/IncidentFilters";
import IncidentList from "@/components/gestor-incidencias/IncidentList";
import IncidentSummaryPanel from "@/components/gestor-incidencias/IncidentSummaryPanel";
import { useIncidentSummary } from "@/hooks/useIncidentSummary";
import { useIncidents } from "@/hooks/useIncidents";
import type { Incident, IncidentStatus } from "@/types/incident-manager";

// Panel del gestor de incidencias: el resumen arriba y el listado con filtros debajo.
// Cada bloque carga por su cuenta y muestra su propio error, así que un fallo no rompe la página.
export default function IncidentPanel() {
  const { filters, updateFilter, clearFilters, hasFilters, incidents, fetchState, changeStatus, reload } =
    useIncidents();
  const summary = useIncidentSummary();

  async function handleStatusChange(incident: Incident, next: IncidentStatus): Promise<string | null> {
    const failure = await changeStatus(incident, next);
    // Las cifras del resumen cambian con cada transición aceptada.
    if (!failure) summary.refresh();
    return failure;
  }

  return (
    <div className="flex flex-col gap-6">
      <IncidentSummaryPanel state={summary.state} onRetry={summary.retry} />

      <section aria-labelledby="list-heading" className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <h2 id="list-heading" className="text-lg font-semibold text-red-700">
            Incidencias
          </h2>
          <Link
            href="/gestor-incidencias/nueva"
            className="rounded-md bg-red-700 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          >
            Registrar incidencia
          </Link>
        </div>

        <IncidentFilters filters={filters} onChange={updateFilter} onClear={clearFilters} hasFilters={hasFilters} />

        {fetchState.status === "loading" && <LoadingMessage>Cargando incidencias...</LoadingMessage>}

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
              {incidents.length === 1 ? "1 incidencia" : `${incidents.length} incidencias`}
              {hasFilters && " con los filtros aplicados"}, de la más reciente a la más antigua.
            </p>
            {incidents.length === 0 ? (
              <EmptyMessage>
                {hasFilters ? (
                  <>
                    Ninguna incidencia coincide con los filtros.{" "}
                    <button type="button" onClick={clearFilters} className="font-semibold text-red-700 underline">
                      Quitar filtros
                    </button>
                  </>
                ) : (
                  <>
                    Todavía no hay incidencias registradas.{" "}
                    <Link href="/gestor-incidencias/nueva" className="font-semibold text-red-700 underline">
                      Registrar la primera
                    </Link>
                  </>
                )}
              </EmptyMessage>
            ) : (
              <IncidentList incidents={incidents} onStatusChange={handleStatusChange} />
            )}
          </>
        )}
      </section>
    </div>
  );
}
