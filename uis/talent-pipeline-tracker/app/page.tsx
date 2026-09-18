"use client";

import { useEffect, useState } from "react";
import { getRecords } from "@/lib/api";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordListItem } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";

export default function Home() {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [records, setRecords] = useState<RecordListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRecords() {
      try {
        setStatus("loading");
        const data = await getRecords();
        setRecords(data);
        setStatus("success");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error desconocido");
        setStatus("error");
      }
    }

    loadRecords();
  }, []);

  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-6 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Candidatos
      </h1>

      {status === "loading" && (
        <p className="text-center text-black md:text-base lg:text-lg">Cargando candidatos...</p>
      )}

      {status === "error" && (
        <p className="rounded-lg border border-red-200 bg-white p-4 text-red-700 shadow-md">
          {error}
        </p>
      )}

      {status === "success" && records.length === 0 && (
        <p className="rounded-lg border border-red-200 bg-white p-4 text-center text-black shadow-md">
          No hay candidatos registrados.
        </p>
      )}

      {status === "success" && records.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {records.map((record) => (
            <article key={record.id} className="rounded-lg bg-white p-4 shadow-md">
              <h2 className="mb-2 text-md font-semibold text-red-700 md:text-lg">
                {record.full_name}
              </h2>
              <p className="mb-1 text-sm text-black md:text-base">{record.position}</p>
              <p className="mb-1 text-sm text-black md:text-base">{record.email}</p>
              <p className="mb-1 text-sm text-black md:text-base">{record.phone}</p>
              <p className="mb-1 text-sm text-black md:text-base">
                Experiencia: {record.experience_years} años
              </p>
              <div className="mt-2 flex gap-2 text-xs">
                <span className="rounded border border-red-200 px-2 py-1 text-red-700">
                  {STATUS_LABELS[record.status]}
                </span>
                <span className="rounded border border-red-200 px-2 py-1 text-red-700">
                  {STAGE_LABELS[record.stage]}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
