export type DocType = "paper" | "project";

export interface DocumentMetadataInput {
  doc_type: DocType;
  title: string;
  authors?: string | null;
  publish_year?: number | null;
  keywords?: string | null;
  project_name?: string | null;
  funding_agency?: string | null;
  execution_period?: string | null;
  tech_stack?: string | null;
}

export interface DocumentUploadResponse {
  doc_id: string;
  collection: string;
  chunks_count: number;
  metadata: Record<string, string>;
}

export interface DocumentSearchResult {
  doc_id: string;
  text: string;
  metadata: Record<string, string>;
  distance: number | null;
}

export interface DocumentSearchResponse {
  query: string;
  collection: string;
  results: DocumentSearchResult[];
}
