import { useState } from "react";
import { analyzeIncidents } from "@/lib/incidencias/api";
import type { IncidentAnalysis } from "@/types/incident";
import { toUserMessage } from "@/lib/error-message";

export type AnalysisState =
  | { status: "idle" }
  | { status: "loading"; fileName: string }
  | { status: "error"; fileName: string; message: string }
  | { status: "success"; fileName: string; result: IncidentAnalysis };

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
        message: toUserMessage(err, "No se pudo analizar el archivo. Inténtalo de nuevo."),
      });
    }
  }

  function reset() {
    setState({ status: "idle" });
  }

  return { state, analyze, reset };
}
