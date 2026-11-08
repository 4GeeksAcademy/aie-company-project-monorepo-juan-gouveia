// Respuesta de POST /incidents/analyze en la API de Brasaland (services/brasaland-api).

export interface RuleCount {
  rule: string;
  label: string;
  count: number;
}

export interface InvalidRecord {
  incident_id: string;
  // Fila del archivo, contando el encabezado como fila 1.
  row: number;
  rules: string[];
}

export interface CodeCount {
  code: string;
  count: number;
  percentage: number | null;
}

export interface ScoreCount {
  score: number;
  label: string;
  count: number;
  percentage: number | null;
}

export interface Satisfaction {
  closed_cases: number;
  scored_cases: number;
  average: number | null;
  distribution: ScoreCount[];
}

export interface IncidentAnalysis {
  source_file: string;
  analyzed_at: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  // Incluye siempre todas las reglas, aunque estén en 0.
  invalid_breakdown: RuleCount[];
  invalid_records_detail: InvalidRecord[];
  categories: CodeCount[];
  statuses: CodeCount[];
  satisfaction: Satisfaction;
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}
