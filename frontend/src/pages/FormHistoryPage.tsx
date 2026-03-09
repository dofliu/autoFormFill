import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getFormHistory } from "../api/forms";
import type { FormHistoryItem } from "../types/form";

export default function FormHistoryPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<FormHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const userId = parseInt(localStorage.getItem("smartfill_user_id") || "0");

  useEffect(() => {
    if (userId) {
      fetchHistory(userId);
    } else {
      setLoading(false);
    }
  }, [userId]);

  const fetchHistory = async (uid: number) => {
    try {
      setLoading(true);
      const data = await getFormHistory(uid);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "載入歷史記錄失敗");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-TW", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400 text-sm">載入中...</div>
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm px-4 py-3 rounded-lg">
          請先至「表單填寫」頁面選擇使用者
        </div>
        <button
          onClick={() => navigate("/")}
          className="mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          前往首頁
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">📋</span>
        <h2 className="text-xl font-bold text-gray-800">表單填寫歷史</h2>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        您過去填寫的表單記錄。點擊可查看詳細資料或重新填寫。
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="border border-gray-200 rounded-xl p-8 text-center">
          <p className="text-gray-400 mb-4">尚無表單填寫記錄</p>
          <button
            onClick={() => navigate("/")}
            className="px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            開始填寫表單
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((item) => (
            <button
              key={item.job_id}
              onClick={() => navigate(`/preview/${item.job_id}`)}
              className="w-full text-left border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-3">
                <span className="text-lg">📄</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-800 truncate">
                    {item.filename}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    範本: {item.template_filename}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs text-gray-600">
                    填寫: {item.fields_filled} 欄位
                    {item.fields_skipped > 0 && (
                      <span className="text-amber-600 ml-1">
                        / 略過: {item.fields_skipped}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formatDate(item.created_at)}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="flex justify-center mt-6">
        <button
          onClick={() => navigate("/")}
          className="px-4 py-2 border border-gray-300 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          返回首頁
        </button>
      </div>
    </div>
  );
}
