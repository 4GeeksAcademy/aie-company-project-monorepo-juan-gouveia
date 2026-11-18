"use client";

import { useState } from "react";
import Button from "@/components/Button";
import ErrorMessage from "@/components/ErrorMessage";
import { downloadResults } from "@/lib/incidencias/api";
import { toUserMessage } from "@/lib/error-message";

export default function ExportButton() {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    try {
      setDownloading(true);
      setError(null);
      await downloadResults();
    } catch (err) {
      setError(toUserMessage(err, "No se pudo descargar el CSV. Inténtalo de nuevo."));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button size="md" onClick={handleClick} disabled={downloading}>
        {downloading ? "Descargando..." : "Descargar results.csv"}
      </Button>
      {error && <ErrorMessage compact>{error}</ErrorMessage>}
    </div>
  );
}
