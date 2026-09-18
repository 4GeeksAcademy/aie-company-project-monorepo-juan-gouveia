"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getRecordById, patchRecord } from "@/lib/api";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordDetail, RecordStage, RecordStatus } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";
type UpdateStatus = "idle" | "loading" | "error";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [statusUpdate, setStatusUpdate] = useState<UpdateStatus>("idle");
  const [statusUpdateError, setStatusUpdateError] = useState<string | null>(null);
  const [stageUpdate, setStageUpdate] = useState<UpdateStatus>("idle");
  const [stageUpdateError, setStageUpdateError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRecord() {
      try {
        setStatus("loading");
        const data = await getRecordById(id);
        setRecord(data);
        setStatus("success");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error desconocido");
        setStatus("error");
      }
    }

    loadRecord();
  }, [id]);

  async function handleStatusChange(newStatus: RecordStatus) {
    try {
      setStatusUpdate("loading");
      setStatusUpdateError(null);
      const updated = await patchRecord(id, { status: newStatus });
      setRecord(updated);
      setStatusUpdate("idle");
    } catch (err) {
      setStatusUpdateError(err instanceof Error ? err.message : "Error desconocido");
      setStatusUpdate("error");
    }
  }

  async function handleStageChange(newStage: RecordStage) {
    try {
      setStageUpdate("loading");
      setStageUpdateError(null);
      const updated = await patchRecord(id, { stage: newStage });
      setRecord(updated);
      setStageUpdate("idle");
    } catch (err) {
      setStageUpdateError(err instanceof Error ? err.message : "Error desconocido");
      setStageUpdate("error");
    }
  }

  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1 text-sm font-semibold text-red-700 hover:underline md:text-base"
      >
        ← Volver a candidatos
      </Link>

      {status === "loading" && (
        <p className="text-center text-black md:text-base lg:text-lg">Cargando candidato...</p>
      )}

      {status === "error" && (
        <p className="rounded-lg border border-red-200 bg-white p-4 text-red-700 shadow-md">
          {error}
        </p>
      )}

      {status === "success" && record && (
        <article className="rounded-lg bg-white p-4 shadow-md md:p-6">
          <h1 className="mb-4 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
            {record.full_name}
          </h1>

          <div className="mb-4 flex items-start gap-3 md:gap-4">
            <label className="flex min-w-0 flex-col items-start gap-1 text-sm text-black">
              <span className="font-semibold text-red-700">Status</span>
              <select
                value={record.status}
                onChange={(e) => handleStatusChange(e.target.value as RecordStatus)}
                disabled={statusUpdate === "loading"}
                className="w-auto max-w-full rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
              >
                {(Object.entries(STATUS_LABELS) as [RecordStatus, string][]).map(
                  ([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  )
                )}
              </select>
              {statusUpdate === "loading" && (
                <span className="text-xs text-black">Actualizando...</span>
              )}
              {statusUpdate === "error" && (
                <span className="text-xs text-red-700">{statusUpdateError}</span>
              )}
            </label>

            <label className="flex min-w-0 flex-col items-start gap-1 text-sm text-black">
              <span className="font-semibold text-red-700">Stage</span>
              <select
                value={record.stage}
                onChange={(e) => handleStageChange(e.target.value as RecordStage)}
                disabled={stageUpdate === "loading"}
                className="w-auto max-w-full rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-60"
              >
                {(Object.entries(STAGE_LABELS) as [RecordStage, string][]).map(
                  ([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  )
                )}
              </select>
              {stageUpdate === "loading" && (
                <span className="text-xs text-black">Actualizando...</span>
              )}
              {stageUpdate === "error" && (
                <span className="text-xs text-red-700">{stageUpdateError}</span>
              )}
            </label>
          </div>

          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 md:grid-cols-2">
            <div>
              <dt className="text-sm font-semibold text-red-700">Posición</dt>
              <dd className="text-black">{record.position}</dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-red-700">Experiencia</dt>
              <dd className="text-black">{record.experience_years} años</dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-red-700">Fecha de aplicación</dt>
              <dd className="text-black">
                {new Date(record.applied_at).toLocaleDateString("es", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-red-700">Email</dt>
              <dd className="text-black">{record.email}</dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-red-700">Teléfono</dt>
              <dd className="text-black">{record.phone}</dd>
            </div>
            {record.linkedin_url && (
              <div>
                <dt className="text-sm font-semibold text-red-700">LinkedIn</dt>
                <dd>
                  <a
                    href={record.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-red-700 hover:underline"
                  >
                    Ver perfil
                  </a>
                </dd>
              </div>
            )}
            {record.cv_url && (
              <div>
                <dt className="text-sm font-semibold text-red-700">CV</dt>
                <dd>
                  <a
                    href={record.cv_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-red-700 hover:underline"
                  >
                    Ver CV
                  </a>
                </dd>
              </div>
            )}
          </dl>
        </article>
      )}
    </main>
  );
}
