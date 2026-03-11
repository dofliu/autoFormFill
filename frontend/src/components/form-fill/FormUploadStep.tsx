import { useEffect, useRef, useState } from "react";
import * as usersApi from "../../api/users";
import * as formsApi from "../../api/forms";
import { useAuth } from "../../contexts/AuthContext";
import type { UserProfile } from "../../types/user";
import type { FormFillResponse } from "../../types/form";

interface Props {
  onFilled: (response: FormFillResponse) => void;
}

export default function FormUploadStep({ onFilled }: Props) {
  const { user: authUser } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(authUser?.id ?? null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    usersApi.listUsers().then((list) => {
      setUsers(list);
      if (list.length > 0 && !selectedUserId) {
        setSelectedUserId(authUser?.id ?? list[0].id);
      }
    });
  }, []);

  const handleSubmit = async () => {
    if (!file || !selectedUserId) return;
    setLoading(true);
    setError("");
    try {
      const response = await formsApi.fillForm(file, selectedUserId);
      onFilled(response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "填寫失敗，請稍後再試");
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && /\.(docx|pdf)$/i.test(droppedFile.name)) {
      setFile(droppedFile);
    }
  };

  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800">智能表單填寫</h2>
          <p className="text-sm text-gray-500 mt-1">上傳空白表單，AI 自動填寫您的資料</p>
        </div>

        {/* File Drop Zone */}
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-blue-500 bg-blue-50"
              : file
                ? "border-green-400 bg-green-50"
                : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".docx,.pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          {file ? (
            <div>
              <p className="text-lg">📄</p>
              <p className="font-medium text-gray-800">{file.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                {(file.size / 1024).toFixed(1)} KB
              </p>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="mt-2 text-xs text-red-500 hover:text-red-700"
              >
                移除
              </button>
            </div>
          ) : (
            <div>
              <p className="text-3xl mb-2">📋</p>
              <p className="text-sm text-gray-600">拖放 .docx 或 .pdf 檔案至此</p>
              <p className="text-xs text-gray-400 mt-1">或點擊選擇檔案</p>
            </div>
          )}
        </div>

        {/* User Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">選擇使用者</label>
          <select
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            value={selectedUserId || ""}
            onChange={(e) => setSelectedUserId(parseInt(e.target.value))}
          >
            <option value="" disabled>
              請選擇使用者
            </option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name_zh || u.name_en || `User #${u.id}`}
              </option>
            ))}
          </select>
          {users.length === 0 && (
            <p className="text-xs text-amber-600 mt-1">
              尚無使用者，請先至「個人資料」頁面建立
            </p>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!file || !selectedUserId || loading}
          className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              AI 正在分析並填寫表單...
            </span>
          ) : (
            "開始智能填寫"
          )}
        </button>
      </div>
    </div>
  );
}
