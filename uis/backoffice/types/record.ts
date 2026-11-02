// El backend expone status/stage como string sin enum en el schema; estos valores
// vienen de las descripciones de los query params, no de un contrato garantizado.
export type RecordStatus = "received" | "in_progress" | "selected" | "discarded";
export type RecordStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export interface RecordCreate {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
}

export interface RecordOut extends RecordCreate {
  id: string;
  status: RecordStatus;
  stage: RecordStage;
  notes_count: number;
  applied_at: string;
  updated_at: string;
}

// Confirmado contra la API: GET /records/{id} devuelve RecordOut tal cual.
export type RecordDetail = RecordOut;

// Confirmado contra la API: cada elemento de la lista embebe además el array de notas.
export interface RecordListItem extends RecordOut {
  notes: Note[];
}

// Confirmado contra la API: GET /records responde { total, page, limit, data }.
export interface RecordListResponse {
  total: number;
  page: number;
  limit: number;
  data: RecordListItem[];
}

export interface RecordPatch {
  status?: RecordStatus | null;
  stage?: RecordStage | null;
}

export interface NoteCreate {
  content: string;
}

// Confirmado contra la API (el spec solo define NoteCreate para el input).
export interface Note extends NoteCreate {
  id: string;
  record_id: string;
  created_at: string;
}

// Confirmado contra la API: GET /records/{id}/notes responde { data, meta: { total } }.
export interface NoteListResponse {
  data: Note[];
  meta: {
    total: number;
  };
}

// La API solo declara RecordCreate en el POST; status y stage se envían igualmente y,
// si el servidor los ignora, createRecord los corrige con un PATCH.
export interface RecordCreateInput extends RecordCreate {
  status: RecordStatus;
  stage: RecordStage;
}
