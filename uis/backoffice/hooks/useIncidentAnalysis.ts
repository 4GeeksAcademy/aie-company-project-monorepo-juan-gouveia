import { useState } from "react";
import { ApiError } from "@/lib/api-client";
import { analyzeIncidents } from "@/lib/incidencias/api";
import type { IncidentAnalysis } from "@/types/incident";
import { toUserMessage } from "@/lib/error-message";

export type AnalysisState =
  | { status: "idle" }
  | { status: "loading"; fileName: string }
  // `retryable`: el fallo no es del archivo (red, tiempo agotado, servidor), así que tiene sentido
  // reintentar con el mismo; si es del archivo (4xx), hay que corregirlo y elegirlo de nuevo.
  | { status: "error"; fileName: string; message: string; file: File; retryable: boolean }
  | { status: "success"; fileName: string; result: IncidentAnalysis };

function isRetryable(err: unknown): boolean {
  return !(err instanceof ApiError && err.status >= 400 && err.status < 500);
}

// Envía el CSV a la API y guarda el estado del análisis: inactivo, cargando, error o resultado.
export function useIncidentAnalysis() {
  const [state, setState] = useState<AnalysisState>({ status: "idle" });

  async function analyze(file: File) {
    setState({ status: "loading", fileName: file.name });
    try {
      const result = await analyzeIncidents(file);
      setState({ status: "success", fileName: file.name, result });
    } catch (err) {
      setState({
        status: "error",
        fileName: file.name,
        message: toUserMessage(err, "No se pudo analizar el archivo."),
        file,
        retryable: isRetryable(err),
      });
    }
  }

  // Vuelve a enviar el archivo que falló, sin tener que elegirlo otra vez.
  function retry() {
    if (state.status === "error") analyze(state.file);
  }

  function reset() {
    setState({ status: "idle" });
  }

  return { state, analyze, retry, reset };
}
