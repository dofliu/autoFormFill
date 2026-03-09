export type FieldSource = "sql" | "rag" | "override" | "skip";

export interface FormField {
  field_name: string;
  field_label: string | null;
  field_type: string;
  location: string | null;
}

export interface FormParseResponse {
  filename: string;
  file_type: string;
  fields: FormField[];
  total_fields: number;
}

export interface FieldFillResult {
  field_name: string;
  value: string;
  source: FieldSource;
  confidence: number;
}

export interface FormFillResponse {
  job_id: string;
  filename: string;
  fields_filled: number;
  fields_skipped: number;
  results: FieldFillResult[];
  output_path: string;
}

export interface FormPreviewResponse {
  job_id: string;
  filename: string;
  template_filename: string;
  fields: FieldFillResult[];
  created_at: string;
}

export interface FormSubmitRequest {
  job_id: string;
  field_overrides: Record<string, string>;
}

export interface FormHistoryItem {
  job_id: string;
  filename: string;
  template_filename: string;
  fields_filled: number;
  fields_skipped: number;
  created_at: string;
}
