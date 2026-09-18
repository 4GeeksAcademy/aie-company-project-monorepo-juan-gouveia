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

export interface RecordPatch {
  status?: RecordStatus | null;
  stage?: RecordStage | null;
}

export interface NoteCreate {
  content: string;
}

export interface Note extends NoteCreate {
  id: string;
  created_at: string;
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface HTTPValidationError {
  detail: ValidationError[];
}
