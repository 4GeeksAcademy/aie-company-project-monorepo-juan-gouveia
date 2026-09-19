"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Button from "@/components/Button";
import LabeledSelect from "@/components/LabeledSelect";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { RecordStage, RecordStatus } from "@/types/record";

const SEARCH_DEBOUNCE_MS = 300;

export default function FilterBar({
  onSearchChange,
  onAddCandidate,
}: {
  onSearchChange: (search: string) => void;
  onAddCandidate: () => void;
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
        <Button onClick={onAddCandidate} className="col-span-2 whitespace-nowrap">
          Añadir candidato
        </Button>

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

        <LabeledSelect
          label="Filtrar por status"
          value={statusFilter}
          options={STATUS_LABELS}
          onChange={(value) => updateFilter("status", value)}
          placeholder="Todos los status"
          hideLabel
          fullWidth
        />

        <LabeledSelect
          label="Filtrar por stage"
          value={stageFilter}
          options={STAGE_LABELS}
          onChange={(value) => updateFilter("stage", value)}
          placeholder="Todos los stages"
          hideLabel
          fullWidth
        />

        <Button
          variant="secondary"
          onClick={clearFilters}
          disabled={!hasActiveFilters}
          className="col-span-2"
        >
          Limpiar filtros
        </Button>
      </div>
    </div>
  );
}
