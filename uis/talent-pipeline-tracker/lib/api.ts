import type {
  Note,
  NoteCreate,
  NoteListResponse,
  RecordCreateInput,
  RecordDetail,
  RecordListItem,
  RecordListResponse,
  RecordPatch,
  RecordStage,
  RecordStatus,
} from "@/types/record";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export interface RecordFilters {
  status?: RecordStatus;
  stage?: RecordStage;
  search?: string;
}

export async function getRecords(filters: RecordFilters = {}): Promise<RecordListItem[]> {
  const params = new URLSearchParams({ limit: "200" });
  if (filters.status) params.set("status", filters.status);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.search) params.set("search", filters.search);

  const res = await fetch(`${API_BASE_URL}/records?${params.toString()}`);

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudieron obtener los candidatos`);
  }

  const body: RecordListResponse = await res.json();
  return body.data;
}

export async function getRecordById(id: string): Promise<RecordDetail> {
  const res = await fetch(`${API_BASE_URL}/records/${id}`);

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudo obtener el candidato`);
  }

  return res.json();
}

export async function patchRecord(id: string, patch: RecordPatch): Promise<RecordDetail> {
  const res = await fetch(`${API_BASE_URL}/records/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudo actualizar el candidato`);
  }

  return res.json();
}

export async function getNotes(recordId: string): Promise<Note[]> {
  const res = await fetch(`${API_BASE_URL}/records/${recordId}/notes`);

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudieron obtener las notas`);
  }

  const body: NoteListResponse = await res.json();
  return body.data;
}

export async function createNote(recordId: string, note: NoteCreate): Promise<Note> {
  const res = await fetch(`${API_BASE_URL}/records/${recordId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(note),
  });

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudo crear la nota`);
  }

  return res.json();
}

export async function deleteNote(recordId: string, noteId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/records/${recordId}/notes/${noteId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudo eliminar la nota`);
  }
}

export async function createRecord(input: RecordCreateInput): Promise<RecordDetail> {
  const res = await fetch(`${API_BASE_URL}/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    throw new Error(`Error ${res.status}: no se pudo crear el candidato`);
  }

  const created: RecordDetail = await res.json();
  if (created.status !== input.status || created.stage !== input.stage) {
    return patchRecord(created.id, { status: input.status, stage: input.stage });
  }
  return created;
}
