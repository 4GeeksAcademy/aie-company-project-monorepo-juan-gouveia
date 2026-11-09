"use client";

import { useState } from "react";
import FilterPanel from "@/components/funciones/FilterPanel";
import ReportsPanel from "@/components/funciones/ReportsPanel";
import ResultPanel, { type Result } from "@/components/funciones/ResultPanel";
import SearchSortPanel from "@/components/funciones/SearchSortPanel";
import { funcionesApi } from "@/lib/funciones/runner";

const INITIAL_RESULT: Result = {
  title: "Estado inicial",
  payload: {
    message: "Panel listo. Usa los botones para ejecutar operaciones.",
    dataset: {
      menuItems: funcionesApi.dataset.sampleMenuItems.length,
      sales: funcionesApi.dataset.sampleSales.length,
      locations: funcionesApi.dataset.sampleLocations.length,
      wasteRecords: funcionesApi.dataset.sampleWasteRecords.length,
    },
  },
};

export default function FuncionesPanel() {
  const [result, setResult] = useState<Result>(INITIAL_RESULT);

  function run(title: string, action: () => unknown) {
    try {
      setResult({ title, payload: action() });
    } catch (error) {
      // Herramienta de pruebas: además del mensaje legible se conserva el error técnico, que es lo
      // que necesita quien prueba las funciones. @repo/brasa-core no lanza errores propios, así que
      // aquí solo llegan fallos inesperados (p. ej. un TypeError).
      setResult({
        title: `Error en ${title}`,
        payload: {
          message: "La función falló de forma inesperada. Revisa el detalle técnico y los datos de entrada.",
          detail: error instanceof Error ? `${error.name}: ${error.message}` : String(error),
        },
      });
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <FilterPanel run={run} />
      <SearchSortPanel run={run} />
      <ReportsPanel run={run} />
      <ResultPanel result={result} />
    </div>
  );
}
