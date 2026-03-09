import { post, postForm, get, downloadUrl } from "./client";
import type { FormParseResponse, FormFillResponse, FormPreviewResponse, FormSubmitRequest, FormHistoryItem } from "../types/form";

export async function parseForm(file: File): Promise<FormParseResponse> {
  const fd = new FormData();
  fd.append("file", file);
  return postForm<FormParseResponse>("/forms/parse", fd);
}

export async function fillForm(file: File, userId: number): Promise<FormFillResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("user_id", String(userId));
  return postForm<FormFillResponse>("/forms/fill", fd);
}

export function getDownloadUrl(filename: string): string {
  return downloadUrl(filename);
}

export async function getFormPreview(jobId: string): Promise<FormPreviewResponse> {
  return get<FormPreviewResponse>(`/forms/preview/${jobId}`);
}

export async function submitForm(request: FormSubmitRequest): Promise<FormFillResponse> {
  return post<FormFillResponse>("/forms/submit", request);
}

export async function getFormHistory(userId: number, limit: number = 20): Promise<FormHistoryItem[]> {
  return get<FormHistoryItem[]>(`/forms/history/${userId}?limit=${limit}`);
}

export async function getSimilarForms(userId: number, templateFilename: string, limit: number = 10): Promise<FormHistoryItem[]> {
  return get<FormHistoryItem[]>(`/forms/history/${userId}/similar/${templateFilename}?limit=${limit}`);
}
