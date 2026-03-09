import { get, put, del } from "./client";
import type {
  DocumentVersion,
  DocumentVersionUpdate,
  DiffResult,
  TrackedFile,
} from "../types/version";

const basePath = (userId: number) => `/users/${userId}/versions`;

export async function listTrackedFiles(
  userId: number,
): Promise<TrackedFile[]> {
  return get<TrackedFile[]>(`${basePath(userId)}/files`);
}

export async function listVersions(
  userId: number,
  filePath?: string,
): Promise<DocumentVersion[]> {
  const params = filePath
    ? `?file_path=${encodeURIComponent(filePath)}`
    : "";
  return get<DocumentVersion[]>(basePath(userId) + "/" + params);
}

export async function getVersion(
  userId: number,
  versionId: number,
): Promise<DocumentVersion> {
  return get<DocumentVersion>(`${basePath(userId)}/${versionId}`);
}

export async function updateVersion(
  userId: number,
  versionId: number,
  data: DocumentVersionUpdate,
): Promise<DocumentVersion> {
  return put<DocumentVersion>(
    `${basePath(userId)}/${versionId}`,
    data,
  );
}

export async function deleteVersion(
  userId: number,
  versionId: number,
): Promise<void> {
  await del(`${basePath(userId)}/${versionId}`);
}

export async function diffVersions(
  userId: number,
  oldVersionId: number,
  newVersionId: number,
): Promise<DiffResult> {
  return get<DiffResult>(
    `${basePath(userId)}/diff/${oldVersionId}/${newVersionId}`,
  );
}
