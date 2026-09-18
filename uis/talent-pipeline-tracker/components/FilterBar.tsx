"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordStage, RecordStatus } from "@/types/record";

const SEARCH_DEBOUNCE_MS = 300;

export default function FilterBar({
  onSearchChange,
}: {
  onSearchChange: (search: string) => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const statusFilter = (searchParams.get("status") as RecordStatus | null) ?? "";
  const stageFilter = (searchParams.get("stage") as RecordStage | null) ?? "";

  const [searchInput, setSearchInput] = useState("");

  // Debounce el texto de búsqueda para no disparar una petición por cada tecla.
  useEffect(() => {
    const timeout = setTimeout(() => onSearchChange(searchInput), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

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
    onSearchChange("");
    router.replace(pathname, { scroll: false });
  }

  const hasActiveFilters = Boolean(statusFilter || stageFilter || searchInput);

  return (
    // 57px = altura del header en móvil (logo h-10 + py-2 + border-b), 89px en md+ (logo h-18)
    <div className="sticky top-[57px] z-40 border-b border-red-200 bg-white md:top-[89px]">
      <div className="mx-auto grid grid-cols-2 gap-2 px-3 py-3 md:flex md:flex-row md:items-center md:gap-3 md:px-4 lg:max-w-6xl lg:px-8">
        <label className="col-span-2 flex flex-col gap-1 text-sm text-black md:flex-1">
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
            className="w-full rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
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
            className="w-full rounded-md border border-red-200 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
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
          className="col-span-2 rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-transparent"
        >
          Limpiar filtros
        </button>
      </div>
    </div>
  );
}
