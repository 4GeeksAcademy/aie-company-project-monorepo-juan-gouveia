"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import CandidateCard from "@/components/CandidateCard";
import FilterBar from "@/components/FilterBar";
import CandidateFormModal from "@/components/CandidateFormModal";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import { createRecord, getRecords } from "@/lib/api";
import type { RecordCreateInput, RecordListItem, RecordStage, RecordStatus } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="px-3 py-6">
          <LoadingMessage>Cargando candidatos...</LoadingMessage>
        </div>
      }
    >
      <CandidateList />
    </Suspense>
  );
}

function CandidateList() {
  const searchParams = useSearchParams();

  const statusFilter = (searchParams.get("status") as RecordStatus | null) ?? "";
  const stageFilter = (searchParams.get("stage") as RecordStage | null) ?? "";

  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const [status, setStatus] = useState<FetchStatus>("loading");
  const [records, setRecords] = useState<RecordListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRecords() {
      try {
        setStatus("loading");
        const data = await getRecords({
          status: statusFilter || undefined,
          stage: stageFilter || undefined,
          search: search || undefined,
        });
        setRecords(data);
        setStatus("success");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error desconocido");
        setStatus("error");
      }
    }

    loadRecords();
  }, [statusFilter, stageFilter, search, reloadKey]);

  async function handleCreate(input: RecordCreateInput) {
    await createRecord(input);
    setModalOpen(false);
    setReloadKey((k) => k + 1);
  }

  const hasActiveFilters = Boolean(statusFilter || stageFilter || search);

  return (
    <>
      <FilterBar onSearchChange={setSearch} onAddCandidate={() => setModalOpen(true)} />

      {modalOpen && (
        <CandidateFormModal
          title="Añadir candidato"
          submitLabel="Enviar"
          submittingLabel="Enviando..."
          onClose={() => setModalOpen(false)}
          onSubmit={handleCreate}
        />
      )}

      <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
        <h1 className="mb-6 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
          Candidatos
        </h1>

        {status === "loading" && <LoadingMessage>Cargando candidatos...</LoadingMessage>}

        {status === "error" && <ErrorMessage>{error}</ErrorMessage>}

        {status === "success" && records.length === 0 && (
          <EmptyMessage>
            {hasActiveFilters
              ? "Ningún candidato cumple con estas condiciones."
              : "No hay candidatos registrados."}
          </EmptyMessage>
        )}

        {status === "success" && records.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {records.map((record) => (
              <CandidateCard key={record.id} record={record} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
