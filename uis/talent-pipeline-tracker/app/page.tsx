"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { getRecords } from "@/lib/api";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordListItem, RecordStage, RecordStatus } from "@/types/record";

type FetchStatus = "loading" | "success" | "error";

const SEARCH_DEBOUNCE_MS = 300;

export default function Home() {
  return (
    <Suspense fallback={<p className="px-3 py-6 text-center text-black">Cargando candidatos...</p>}>
      <CandidateList />
    </Suspense>
  );
}

function CandidateList() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const statusFilter = (searchParams.get("status") as RecordStatus | null) ?? "";
  const stageFilter = (searchParams.get("stage") as RecordStage | null) ?? "";

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [status, setStatus] = useState<FetchStatus>("loading");
  const [records, setRecords] = useState<RecordListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Debounce el texto de búsqueda para no disparar una petición por cada tecla.
  useEffect(() => {
    const timeout = setTimeout(() => setSearch(searchInput), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timeout);
  }, [searchInput]);

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
  }, [statusFilter, stageFilter, search]);

  function updateFilter(key: "status" | "stage", value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  function clearFilters() {
    setSearchInput("");
    setSearch("");
    router.replace(pathname, { scroll: false });
  }

  const hasActiveFilters = Boolean(statusFilter || stageFilter || search);

  return (
    <>
      {/* 89px = altura del header (logo h-18 + py-2 + border-b), para anclar justo debajo */}
      <div className="sticky top-[89px] z-40 border-b border-red-200 bg-white">
        <div className="mx-auto flex flex-col gap-3 px-3 py-3 md:flex-row md:items-center md:px-4 lg:max-w-6xl lg:px-8">
          <label className="flex flex-col gap-1 text-sm text-black md:flex-1">
            <span className="sr-only">Buscar por nombre o correo</span>
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar por nombre o correo..."
              className="rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm text-black">
            <span className="sr-only">Filtrar por status</span>
            <select
              value={statusFilter}
              onChange={(e) => updateFilter("status", e.target.value)}
              className="rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            >
              <option value="">Todos los status</option>
              {(Object.entries(STATUS_LABELS) as [RecordStatus, string][]).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm text-black">
            <span className="sr-only">Filtrar por stage</span>
            <select
              value={stageFilter}
              onChange={(e) => updateFilter("stage", e.target.value)}
              className="rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            >
              <option value="">Todos los stages</option>
              {(Object.entries(STAGE_LABELS) as [RecordStage, string][]).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            onClick={clearFilters}
            disabled={!hasActiveFilters}
            className="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-transparent"
          >
            Limpiar filtros
          </button>
        </div>
      </div>

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
            {hasActiveFilters
              ? "Ningún candidato cumple con estas condiciones."
              : "No hay candidatos registrados."}
          </p>
        )}

        {status === "success" && records.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {records.map((record) => (
              <Link
                key={record.id}
                href={`/candidates/${record.id}`}
                className="rounded-lg bg-white p-4 shadow-md transition hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
              >
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
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
