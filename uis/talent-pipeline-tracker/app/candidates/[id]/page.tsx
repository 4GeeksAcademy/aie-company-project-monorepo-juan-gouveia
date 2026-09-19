"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getRecordById, updateRecord } from "@/lib/api";
import BackLink from "@/components/BackLink";
import CandidateDetails from "@/components/CandidateDetails";
import CandidateFormModal from "@/components/CandidateFormModal";
import CandidateHeader from "@/components/CandidateHeader";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import NotesSection from "@/components/NotesSection";
import StatusStageSelectors from "@/components/StatusStageSelectors";
import type { RecordCreateInput, RecordDetail } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);

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

  async function handleEdit(input: RecordCreateInput) {
    const updated = await updateRecord(id, input);
    setRecord(updated);
  }

  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <BackLink href="/">Volver a candidatos</BackLink>

      {status === "loading" && <LoadingMessage>Cargando candidato...</LoadingMessage>}

      {status === "error" && <ErrorMessage>{error}</ErrorMessage>}

      {status === "success" && record && (
        <article className="rounded-lg bg-white p-4 shadow-md md:p-6">
          <CandidateHeader name={record.full_name} onEdit={() => setEditOpen(true)} />
          <StatusStageSelectors record={record} onUpdated={setRecord} />
          <CandidateDetails record={record} />

          <NotesSection recordId={id} />

          {editOpen && (
            <CandidateFormModal
              title="Editar candidato"
              submitLabel="Guardar"
              submittingLabel="Guardando..."
              initialRecord={record}
              onClose={() => setEditOpen(false)}
              onSubmit={handleEdit}
            />
          )}
        </article>
      )}
    </main>
  );
}
