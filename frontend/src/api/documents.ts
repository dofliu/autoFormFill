import { get, getCurrentUserId, postForm } from "./client";
import type { DocumentMetadataInput, DocumentUploadResponse, DocumentSearchResponse } from "../types/document";

export async function uploadDocument(
  file: File,
  metadata: DocumentMetadataInput,
): Promise<DocumentUploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("doc_type", metadata.doc_type);
  fd.append("title", metadata.title);
  if (metadata.authors) fd.append("authors", metadata.authors);
  if (metadata.publish_year) fd.append("publish_year", String(metadata.publish_year));
  if (metadata.keywords) fd.append("keywords", metadata.keywords);
  if (metadata.project_name) fd.append("project_name", metadata.project_name);
  if (metadata.funding_agency) fd.append("funding_agency", metadata.funding_agency);
  if (metadata.execution_period) fd.append("execution_period", metadata.execution_period);
  if (metadata.tech_stack) fd.append("tech_stack", metadata.tech_stack);

  // Inject user_id for multi-user isolation
  const uid = getCurrentUserId();
  if (uid !== null) fd.append("user_id", String(uid));

  return postForm<DocumentUploadResponse>("/documents/upload", fd);
}

export async function searchDocuments(
  q: string,
  collection = "academic_papers",
  nResults = 5,
): Promise<DocumentSearchResponse> {
  const params = new URLSearchParams({ q, collection, n_results: String(nResults) });
  return get<DocumentSearchResponse>(`/documents/search?${params}`);
}
