import { get, post } from "./client";

export interface WatcherStatus {
  running: boolean;
  watch_dirs: string[];
  queue_size: number;
  supported_extensions: string[];
}

export interface IndexStats {
  total_files: number;
  total_chunks: number;
  by_status: Record<string, number>;
  watch_dirs: string[];
  supported_extensions: string[];
}

export interface IndexingStatusResponse {
  watcher: WatcherStatus;
  index: IndexStats;
}

export interface IndexedFile {
  id: number;
  file_path: string;
  file_hash: string;
  file_size: number;
  file_type: string;
  status: string;
  collection: string;
  doc_id: string;
  chunks_count: number;
  error_message: string;
  last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IndexedFilesResponse {
  files: IndexedFile[];
  total: number;
}

export interface RescanResponse {
  message: string;
  stats: Record<string, Record<string, number | string>>;
}

export function getIndexingStatus(): Promise<IndexingStatusResponse> {
  return get<IndexingStatusResponse>("/indexing/status");
}

export function rescanDirectories(): Promise<RescanResponse> {
  return post<RescanResponse>("/indexing/rescan", {});
}

export function getIndexedFiles(
  status?: string,
  limit = 100,
): Promise<IndexedFilesResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  return get<IndexedFilesResponse>(`/indexing/files?${params.toString()}`);
}

export function indexSingleFile(filePath: string): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>("/indexing/index-file", { file_path: filePath });
}

export function removeSingleFile(filePath: string): Promise<void> {
  // DELETE with JSON body
  return post<void>("/indexing/remove-file", { file_path: filePath });
}
