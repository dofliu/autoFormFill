import { useCallback, useEffect, useState } from "react";
import * as versionsApi from "../api/versions";
import { useAuth } from "../contexts/AuthContext";
import type { DocumentVersion, DiffResult, TrackedFile } from "../types/version";

export default function VersionPage() {
  const { user } = useAuth();
  const userId = user?.id ?? 1;

  const [trackedFiles, setTrackedFiles] = useState<TrackedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Diff selection
  const [oldVersionId, setOldVersionId] = useState<number | "">("");
  const [newVersionId, setNewVersionId] = useState<number | "">("");

  const loadFiles = useCallback(async () => {
    try {
      setLoading(true);
      const files = await versionsApi.listTrackedFiles(userId);
      setTrackedFiles(files);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const loadVersions = async (filePath: string) => {
    setSelectedFile(filePath);
    setDiffResult(null);
    setOldVersionId("");
    setNewVersionId("");
    try {
      const vers = await versionsApi.listVersions(userId, filePath);
      setVersions(vers);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入版本失敗");
    }
  };

  const handleDiff = async () => {
    if (oldVersionId === "" || newVersionId === "") return;
    try {
      const result = await versionsApi.diffVersions(
        userId,
        Number(oldVersionId),
        Number(newVersionId),
      );
      setDiffResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "比較失敗");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-semibold text-gray-800">版本追蹤</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          追蹤文件版本變更，比較不同版本之間的差異
        </p>
      </div>

      {error && (
        <div className="mx-6 mt-3 p-3 bg-red-50 text-red-600 text-sm rounded-lg">
          {error}
          <button onClick={() => setError("")} className="ml-2 text-red-400">×</button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* File list */}
        <div className="w-72 border-r border-gray-200 overflow-y-auto p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">追蹤文件</h3>
          {loading ? (
            <div className="text-xs text-gray-400 py-4 text-center">載入中...</div>
          ) : trackedFiles.length === 0 ? (
            <div className="text-xs text-gray-400 py-4 text-center">
              尚無追蹤文件。文件在自動索引時會自動建立版本。
            </div>
          ) : (
            <div className="space-y-2">
              {trackedFiles.map((f) => {
                const filename = f.file_path.split(/[/\\]/).pop() || f.file_path;
                return (
                  <button
                    key={f.file_path}
                    onClick={() => loadVersions(f.file_path)}
                    className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
                      selectedFile === f.file_path
                        ? "border-blue-300 bg-blue-50"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <div className="font-medium text-gray-800 truncate">
                      {filename}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {f.version_count} 個版本 · v{f.latest_version}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Version detail + diff */}
        <div className="flex-1 overflow-y-auto p-6">
          {!selectedFile ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              選擇左側文件以查看版本歷史
            </div>
          ) : (
            <>
              {/* Version list */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  版本列表
                </h3>
                <div className="space-y-2">
                  {versions.map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg text-sm"
                    >
                      <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">
                        v{v.version_number}
                      </span>
                      <span className="text-gray-700 flex-1">{v.label}</span>
                      <span className="text-xs text-gray-400">
                        {v.content_length.toLocaleString()} 字
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(v.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Diff comparison */}
              {versions.length >= 2 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">
                    版本比較
                  </h3>
                  <div className="flex items-center gap-3 mb-3">
                    <select
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      value={oldVersionId}
                      onChange={(e) =>
                        setOldVersionId(e.target.value ? Number(e.target.value) : "")
                      }
                    >
                      <option value="">選擇舊版本</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.version_number} — {v.label}
                        </option>
                      ))}
                    </select>
                    <span className="text-gray-400">vs</span>
                    <select
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      value={newVersionId}
                      onChange={(e) =>
                        setNewVersionId(e.target.value ? Number(e.target.value) : "")
                      }
                    >
                      <option value="">選擇新版本</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.version_number} — {v.label}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleDiff}
                      disabled={oldVersionId === "" || newVersionId === ""}
                      className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      比較
                    </button>
                  </div>

                  {/* Diff result */}
                  {diffResult && (
                    <div className="border border-gray-200 rounded-xl overflow-hidden">
                      {/* Diff summary */}
                      <div className="flex items-center gap-4 px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs">
                        <span>
                          v{diffResult.old_version} → v{diffResult.new_version}
                        </span>
                        {diffResult.identical ? (
                          <span className="text-green-600 font-medium">
                            內容相同
                          </span>
                        ) : (
                          <>
                            <span className="text-green-600">
                              +{diffResult.total_additions}
                            </span>
                            <span className="text-red-600">
                              -{diffResult.total_deletions}
                            </span>
                            <span className="text-gray-500">
                              共 {diffResult.total_changes} 處變更
                            </span>
                          </>
                        )}
                      </div>

                      {/* Diff lines */}
                      {diffResult.hunks.map((hunk, hi) => (
                        <div key={hi} className="border-b border-gray-100 last:border-0">
                          <div className="px-4 py-1 bg-blue-50 text-xs text-blue-600 font-mono">
                            @@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@
                          </div>
                          {hunk.lines.map((line, li) => (
                            <div
                              key={li}
                              className={`flex font-mono text-xs ${
                                line.tag === "delete"
                                  ? "bg-red-50 text-red-800"
                                  : line.tag === "insert"
                                    ? "bg-green-50 text-green-800"
                                    : "text-gray-600"
                              }`}
                            >
                              <span className="w-12 text-right px-2 text-gray-400 select-none border-r border-gray-200">
                                {line.line_number_old ?? ""}
                              </span>
                              <span className="w-12 text-right px-2 text-gray-400 select-none border-r border-gray-200">
                                {line.line_number_new ?? ""}
                              </span>
                              <span className="w-4 text-center select-none">
                                {line.tag === "delete"
                                  ? "-"
                                  : line.tag === "insert"
                                    ? "+"
                                    : " "}
                              </span>
                              <span className="flex-1 px-2 whitespace-pre-wrap break-all">
                                {line.content}
                              </span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
