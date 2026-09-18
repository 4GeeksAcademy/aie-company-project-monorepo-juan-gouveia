"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import StageBadge from "@/components/StageBadge";
import StatusBadge from "@/components/StatusBadge";
import { getRecordById } from "@/lib/api";
import type { RecordDetail } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

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

          <div className="mb-4 flex flex-wrap gap-2 text-xs md:text-sm">
            <StatusBadge status={record.status} />
            <StageBadge stage={record.stage} />
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
