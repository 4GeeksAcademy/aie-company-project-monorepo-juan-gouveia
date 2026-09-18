import type { RecordListItem, RecordListResponse } from "@/types/record";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function getRecords(): Promise<RecordListItem[]> {
  const res = await fetch(`${API_BASE_URL}/records?limit=200`);

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudieron obtener los candidatos`);
  }

  const body: RecordListResponse = await res.json();
  return body.data;
}
