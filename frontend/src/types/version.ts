export interface DocumentVersion {
  id: number;
  user_id: number;
  file_path: string;
  file_hash: string;
  version_number: number;
  content_length: number;
  label: string;
  created_at: string;
}

export interface DocumentVersionUpdate {
  label?: string;
}

export interface DiffLine {
  line_number_old: number | null;
  line_number_new: number | null;
  tag: "equal" | "insert" | "delete" | "replace";
  content: string;
}

export interface DiffHunk {
  old_start: number;
  old_count: number;
  new_start: number;
  new_count: number;
  lines: DiffLine[];
}

export interface DiffResult {
  file_path: string;
  old_version: number;
  new_version: number;
  old_hash: string;
  new_hash: string;
  hunks: DiffHunk[];
  total_additions: number;
  total_deletions: number;
  total_changes: number;
  identical: boolean;
}

export interface TrackedFile {
  file_path: string;
  version_count: number;
  latest_version: number;
  last_updated: string;
}
