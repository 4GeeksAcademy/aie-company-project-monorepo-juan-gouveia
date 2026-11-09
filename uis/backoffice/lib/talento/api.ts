import { ApiError, errorFromStatus, jsonBody, readJson } from "@/lib/api-client";
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

const NOT_CONFIGURED_MESSAGE = "El servicio de candidatos no está disponible en este momento. Inténtalo más tarde.";
const NETWORK_ERROR_MESSAGE =
  "No se pudo conectar con el servicio de candidatos. Revisa tu conexión e inténtalo de nuevo.";

// Si el servicio no responde en este tiempo, se corta la petición: la pantalla no se queda cargando
// indefinidamente. Es el mismo límite que usa el intermediario con la API de Brasaland.
const REQUEST_TIMEOUT_MS = 15_000;
const TIMEOUT_MESSAGE = "El servicio de candidatos tarda demasiado en responder. Inténtalo de nuevo en unos minutos.";
// En una escritura, el servicio pudo guardar el cambio aunque la respuesta no llegara a tiempo.
const WRITE_TIMEOUT_MESSAGE =
  "El servicio de candidatos tarda demasiado en responder. Recarga la página para comprobar si el cambio se guardó antes de repetirlo.";

const UNEXPECTED_DATA_MESSAGE =
  "El servicio de candidatos respondió con datos que no se pueden mostrar. Inténtalo de nuevo en unos minutos.";

export interface RecordFilters {
  status?: RecordStatus;
  stage?: RecordStage;
  search?: string;
}

// Petición a la API del tracker. Devuelve la respuesta solo si es correcta; si no, lanza un ApiError
// con un mensaje legible. No se usa el mensaje de error del servicio: es de terceros y puede venir en
// inglés o con detalles técnicos. `fallback` dice qué falló (ej.: "no se pudo crear la nota").
async function talentFetch(path: string, fallback: string, init?: RequestInit): Promise<Response> {
  if (!API_BASE_URL) {
    // Sin la URL, fetch pediría "undefined/records" al propio backoffice.
    throw new ApiError(NOT_CONFIGURED_MESSAGE, 0, "not_configured");
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      const isRead = !init?.method || init.method === "GET";
      throw new ApiError(isRead ? TIMEOUT_MESSAGE : WRITE_TIMEOUT_MESSAGE, 0, "timeout");
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, 0, "network_error");
  }

  if (!res.ok) throw errorFromStatus(res.status, fallback);
  return res;
}

// La lista `data` de una respuesta del tracker. Si no es una lista (el servicio de terceros cambió su
// formato o respondió null), se lanza un error en vez de devolver undefined, que rompería la página, o
// una lista vacía, que haría creer que no hay datos. Así la pantalla muestra su estado de error.
function listFrom<T>(body: { data?: unknown } | null): T[] {
  if (Array.isArray(body?.data)) return body.data as T[];
  throw new ApiError(UNEXPECTED_DATA_MESSAGE, 200, "invalid_response");
}

export async function getRecords(filters: RecordFilters = {}): Promise<RecordListItem[]> {
  const params = new URLSearchParams({ limit: "200" });
  if (filters.status) params.set("status", filters.status);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.search) params.set("search", filters.search);

  const res = await talentFetch(`/records?${params.toString()}`, "no se pudieron obtener los candidatos");
  return listFrom<RecordListItem>(await readJson<RecordListResponse | null>(res));
}

export async function getRecordById(id: string): Promise<RecordDetail> {
  const res = await talentFetch(`/records/${id}`, "no se pudo obtener el candidato");
  return readJson(res);
}

export async function patchRecord(id: string, patch: RecordPatch): Promise<RecordDetail> {
  const res = await talentFetch(`/records/${id}`, "no se pudo actualizar el candidato", jsonBody("PATCH", patch));
  return readJson(res);
}

export async function getNotes(recordId: string): Promise<Note[]> {
  const res = await talentFetch(`/records/${recordId}/notes`, "no se pudieron obtener las notas");
  return listFrom<Note>(await readJson<NoteListResponse | null>(res));
}

export async function createNote(recordId: string, note: NoteCreate): Promise<Note> {
  const res = await talentFetch(`/records/${recordId}/notes`, "no se pudo crear la nota", jsonBody("POST", note));
  return readJson(res);
}

export async function deleteNote(recordId: string, noteId: string): Promise<void> {
  await talentFetch(`/records/${recordId}/notes/${noteId}`, "no se pudo eliminar la nota", { method: "DELETE" });
}

export async function createRecord(input: RecordCreateInput): Promise<RecordDetail> {
  const res = await talentFetch("/records", "no se pudo crear el candidato", jsonBody("POST", input));
  const created = await readJson<RecordDetail>(res);
  if (created.status !== input.status || created.stage !== input.stage) {
    return patchRecord(created.id, { status: input.status, stage: input.stage });
  }
  return created;
}

// PUT solo declara los campos de RecordCreate; como reemplaza el registro, se restauran
// status y stage con un PATCH si el servidor los reinicia.
export async function updateRecord(id: string, input: RecordCreateInput): Promise<RecordDetail> {
  const { status, stage, ...fields } = input;
  const res = await talentFetch(`/records/${id}`, "no se pudo actualizar el candidato", jsonBody("PUT", fields));
  const updated = await readJson<RecordDetail>(res);
  if (updated.status !== status || updated.stage !== stage) {
    return patchRecord(id, { status, stage });
  }
  return updated;
}
