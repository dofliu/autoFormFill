import { useCallback, useEffect, useState } from "react";
import * as remindersApi from "../api/reminders";
import { useAuth } from "../contexts/AuthContext";
import type { Reminder, ReminderCreate } from "../types/reminder";

const PRIORITY_COLORS: Record<string, string> = {
  high: "text-red-600 bg-red-50 border-red-200",
  medium: "text-amber-600 bg-amber-50 border-amber-200",
  low: "text-blue-600 bg-blue-50 border-blue-200",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const TYPE_LABELS: Record<string, string> = {
  deadline: "截止日期",
  fill_diff: "填寫差異",
  manual: "手動提醒",
};

const TYPE_ICONS: Record<string, string> = {
  deadline: "⏰",
  fill_diff: "🔄",
  manual: "📌",
};

export default function ReminderPage() {
  const { user } = useAuth();
  const userId = user?.id ?? 1;

  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [filter, setFilter] = useState<"all" | "active" | "read" | "dismissed">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  // Add form
  const [form, setForm] = useState<ReminderCreate>({
    title: "",
    message: "",
    reminder_type: "manual",
    priority: "medium",
    due_date: "",
  });

  const loadReminders = useCallback(async () => {
    try {
      setLoading(true);
      const status = filter === "all" ? undefined : filter;
      const data = await remindersApi.listReminders(userId, { status });
      setReminders(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [userId, filter]);

  useEffect(() => {
    loadReminders();
  }, [loadReminders]);

  const handleAdd = async () => {
    if (!form.title.trim()) {
      setError("請輸入標題");
      return;
    }
    try {
      await remindersApi.createReminder(userId, form);
      setShowAdd(false);
      setForm({ title: "", message: "", reminder_type: "manual", priority: "medium", due_date: "" });
      await loadReminders();
    } catch (e) {
      setError(e instanceof Error ? e.message : "建立失敗");
    }
  };

  const handleMarkRead = async (id: number) => {
    await remindersApi.updateReminder(userId, id, { status: "read" });
    await loadReminders();
  };

  const handleDismiss = async (id: number) => {
    await remindersApi.updateReminder(userId, id, { status: "dismissed" });
    await loadReminders();
  };

  const handleDismissAll = async () => {
    await remindersApi.dismissAll(userId);
    await loadReminders();
  };

  const handleDelete = async (id: number) => {
    await remindersApi.deleteReminder(userId, id);
    await loadReminders();
  };

  const activeCount = reminders.filter((r) => r.status === "active").length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            智能提醒
            {activeCount > 0 && (
              <span className="ml-2 text-xs bg-red-500 text-white rounded-full px-2 py-0.5">
                {activeCount}
              </span>
            )}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            截止日期偵測、填寫差異提醒、自訂通知
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <button
              onClick={handleDismissAll}
              className="px-3 py-1.5 border border-gray-300 text-sm text-gray-600 rounded-lg hover:bg-gray-50"
            >
              全部已讀
            </button>
          )}
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            + 新增提醒
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-3 p-3 bg-red-50 text-red-600 text-sm rounded-lg">
          {error}
          <button onClick={() => setError("")} className="ml-2 text-red-400">×</button>
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <div className="mx-6 mt-4 p-4 border border-blue-200 bg-blue-50/30 rounded-xl">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">新增提醒</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-gray-600 mb-1">標題</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="提醒標題"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-600 mb-1">內容</label>
              <textarea
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-y"
                rows={2}
                placeholder="提醒內容（選填）"
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">優先順序</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              >
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">截止日期（選填）</label>
              <input
                type="date"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.due_date || ""}
                onChange={(e) => setForm({ ...form, due_date: e.target.value || undefined })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleAdd}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
            >
              建立
            </button>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-1 px-6 pt-4">
        {(["all", "active", "read", "dismissed"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filter === f
                ? "bg-blue-600 text-white"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            {f === "all" ? "全部" : f === "active" ? "未讀" : f === "read" ? "已讀" : "已忽略"}
          </button>
        ))}
      </div>

      {/* Reminder list */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="text-center text-gray-400 text-sm py-12">載入中...</div>
        ) : reminders.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-12">
            {filter === "all" ? "尚無提醒" : `沒有${filter === "active" ? "未讀" : filter === "read" ? "已讀" : "已忽略"}提醒`}
          </div>
        ) : (
          <div className="space-y-3">
            {reminders.map((r) => (
              <div
                key={r.id}
                className={`border rounded-xl p-4 transition-colors ${
                  r.status === "active"
                    ? `${PRIORITY_COLORS[r.priority] || "border-gray-200"}`
                    : "border-gray-100 bg-gray-50 opacity-70"
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg">
                    {TYPE_ICONS[r.reminder_type] || "📌"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-800">
                        {r.title}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-500">
                        {TYPE_LABELS[r.reminder_type] || r.reminder_type}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          PRIORITY_COLORS[r.priority] || ""
                        }`}
                      >
                        {PRIORITY_LABELS[r.priority] || r.priority}
                      </span>
                    </div>
                    {r.message && (
                      <p className="text-sm text-gray-600 mt-1">{r.message}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                      {r.due_date && (
                        <span>
                          截止：{new Date(r.due_date).toLocaleDateString()}
                        </span>
                      )}
                      <span>
                        {new Date(r.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {r.status === "active" && (
                      <>
                        <button
                          onClick={() => handleMarkRead(r.id)}
                          className="text-xs text-blue-500 hover:text-blue-700 px-2 py-1"
                        >
                          已讀
                        </button>
                        <button
                          onClick={() => handleDismiss(r.id)}
                          className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1"
                        >
                          忽略
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="text-xs text-red-400 hover:text-red-600 px-2 py-1"
                    >
                      刪除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
