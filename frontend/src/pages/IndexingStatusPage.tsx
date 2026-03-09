import { useCallback, useEffect, useState } from "react";
import * as indexingApi from "../api/indexing";
import type {
  IndexingStatusResponse,
  IndexedFile,
} from "../api/indexing";

const STATUS_COLORS: Record<string, string> = {
  indexed: "bg-green-100 text-green-700",
  indexing: "bg-blue-100 text-blue-700",
  pending: "bg-gray-100 text-gray-600",
  error: "bg-red-100 text-red-700",
  deleted: "bg-gray-200 text-gray-500",
  stale: "bg-amber-100 text-amber-700",
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortenPath(filePath: string): string {
  const parts = filePath.replace(/\\/g, "/").split("/");
  if (parts.length <= 3) return parts.join("/");
  return `.../${parts.slice(-3).join("/")}`;
}

export default function IndexingStatusPage() {
  const [status, setStatus] = useState<IndexingStatusResponse | null>(null);
  const [files, setFiles] = useState<IndexedFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [rescanning, setRescanning] = useState(false);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [statusRes, filesRes] = await Promise.all([
        indexingApi.getIndexingStatus(),
        indexingApi.getIndexedFiles(filterStatus || undefined),
      ]);
      setStatus(statusRes);
      setFiles(filesRes.files);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    refresh();
    // Auto-refresh every 10 seconds
    const interval = setInterval(refresh, 10_000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleRescan = async () => {
    setRescanning(true);
    setError("");
    try {
      await indexingApi.rescanDirectories();
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Rescan failed");
    } finally {
      setRescanning(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center text-gray-500">
        <div className="animate-spin mr-2 h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
        Loading...
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">索引狀態</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={refresh}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            重新整理
          </button>
          <button
            onClick={handleRescan}
            disabled={rescanning}
            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {rescanning ? "掃描中..." : "全量重新掃描"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Overview cards */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="border border-gray-200 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-gray-800">
              {status.index.total_files}
            </div>
            <div className="text-xs text-gray-500 mt-1">總檔案數</div>
          </div>
          <div className="border border-gray-200 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {status.index.total_chunks}
            </div>
            <div className="text-xs text-gray-500 mt-1">總文本區塊</div>
          </div>
          <div className="border border-gray-200 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-green-600">
              {status.index.by_status?.indexed || 0}
            </div>
            <div className="text-xs text-gray-500 mt-1">已索引</div>
          </div>
          <div className="border border-gray-200 rounded-xl p-4 text-center">
            <div className={`text-2xl font-bold ${status.watcher.running ? "text-green-600" : "text-gray-400"}`}>
              {status.watcher.running ? "ON" : "OFF"}
            </div>
            <div className="text-xs text-gray-500 mt-1">監控狀態</div>
          </div>
        </div>
      )}

      {/* Watcher info */}
      {status && (
        <section className="border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">監控設定</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-gray-500 w-24 shrink-0">監控目錄：</span>
              <div className="space-y-1">
                {status.watcher.watch_dirs.length > 0 ? (
                  status.watcher.watch_dirs.map((d) => (
                    <div key={d} className="font-mono text-xs bg-gray-50 px-2 py-1 rounded">
                      {d}
                    </div>
                  ))
                ) : (
                  <span className="text-gray-400">
                    未設定 (請在 .env 中設定 WATCH_DIRS)
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500 w-24 shrink-0">支援格式：</span>
              <div className="flex gap-1.5">
                {status.watcher.supported_extensions.map((ext) => (
                  <span
                    key={ext}
                    className="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded"
                  >
                    {ext}
                  </span>
                ))}
              </div>
            </div>
            {status.watcher.queue_size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-gray-500 w-24 shrink-0">待處理：</span>
                <span className="text-amber-600 font-medium">
                  {status.watcher.queue_size} 個檔案
                </span>
              </div>
            )}
          </div>

          {/* Status breakdown */}
          {Object.keys(status.index.by_status).length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <h4 className="text-xs text-gray-500 mb-2">狀態分佈</h4>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(status.index.by_status).map(([s, count]) => (
                  <span
                    key={s}
                    className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[s] || "bg-gray-100 text-gray-600"}`}
                  >
                    {s}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Indexed files list */}
      <section className="border border-gray-200 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700">已索引檔案</h3>
          <select
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">全部狀態</option>
            <option value="indexed">已索引</option>
            <option value="indexing">索引中</option>
            <option value="error">錯誤</option>
            <option value="deleted">已刪除</option>
          </select>
        </div>

        {files.length === 0 ? (
          <div className="text-center py-10 text-gray-400 text-sm">
            {filterStatus ? `沒有「${filterStatus}」狀態的檔案` : "尚無索引檔案"}
            <p className="mt-2 text-xs">
              在 .env 中設定 WATCH_DIRS 指定監控目錄，或使用「全量重新掃描」
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                  <th className="pb-2 pr-3 font-medium">檔案</th>
                  <th className="pb-2 pr-3 font-medium">類型</th>
                  <th className="pb-2 pr-3 font-medium">大小</th>
                  <th className="pb-2 pr-3 font-medium">區塊</th>
                  <th className="pb-2 pr-3 font-medium">狀態</th>
                  <th className="pb-2 font-medium">索引時間</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr
                    key={f.id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <td className="py-2.5 pr-3">
                      <div className="font-medium text-gray-800 truncate max-w-xs" title={f.file_path}>
                        {f.file_path.replace(/\\/g, "/").split("/").pop()}
                      </div>
                      <div className="text-xs text-gray-400 font-mono truncate max-w-xs" title={f.file_path}>
                        {shortenPath(f.file_path)}
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">
                        {f.file_type}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-gray-500">
                      {formatBytes(f.file_size)}
                    </td>
                    <td className="py-2.5 pr-3 text-gray-500 text-center">
                      {f.chunks_count}
                    </td>
                    <td className="py-2.5 pr-3">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[f.status] || "bg-gray-100 text-gray-600"}`}
                      >
                        {f.status}
                      </span>
                      {f.error_message && (
                        <div className="text-xs text-red-500 mt-1 truncate max-w-[200px]" title={f.error_message}>
                          {f.error_message}
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 text-gray-400 text-xs">
                      {formatTime(f.last_indexed_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
