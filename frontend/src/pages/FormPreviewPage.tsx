import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getFormPreview, submitForm, getDownloadUrl } from "../api/forms";
import type { FormPreviewResponse, FormSubmitRequest } from "../types/form";
import { sourceColor, confidencePercent } from "../utils/formatters";

export default function FormPreviewPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [previewData, setPreviewData] = useState<FormPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (jobId) {
      fetchPreviewData(jobId);
    }
  }, [jobId]);

  const fetchPreviewData = async (id: string) => {
    try {
      setLoading(true);
      const data = await getFormPreview(id);
      setPreviewData(data);

      const initial: Record<string, string> = {};
      data.fields.forEach((f) => {
        initial[f.field_name] = f.value;
      });
      setFieldValues(initial);
    } catch (err) {
      setError(err instanceof Error ? err.message : "載入預覽失敗");
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldName: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [fieldName]: value }));
  };

  const handleSubmit = async () => {
    if (!jobId || !previewData) return;

    try {
      setSubmitting(true);

      const overrides: Record<string, string> = {};
      previewData.fields.forEach((f) => {
        if (fieldValues[f.field_name] !== f.value) {
          overrides[f.field_name] = fieldValues[f.field_name];
        }
      });

      const request: FormSubmitRequest = {
        job_id: jobId,
        field_overrides: overrides,
      };

      const result = await submitForm(request);

      // Trigger download
      const a = document.createElement("a");
      a.href = getDownloadUrl(result.filename);
      a.download = result.filename;
      a.click();

      navigate("/history");
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交失敗");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400 text-sm">載入中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
          {error}
        </div>
        <button
          onClick={() => navigate("/")}
          className="mt-3 px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
        >
          返回首頁
        </button>
      </div>
    );
  }

  if (!previewData) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm px-4 py-3 rounded-lg">
          找不到預覽資料
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← 返回
          </button>
          <h2 className="text-base font-semibold text-gray-800">表單預覽</h2>
        </div>
        <div className="text-xs text-gray-500">
          {previewData.filename}
          <span className="ml-2 text-gray-400">
            範本: {previewData.template_filename}
          </span>
        </div>
      </div>

      {/* Field cards */}
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full">
        <p className="text-sm text-gray-500 mb-4">
          審閱並編輯 AI 填寫的欄位。修改後按「確認提交」完成表單。
        </p>

        <div className="space-y-3">
          {previewData.fields.map((field) => {
            const colors = sourceColor(field.source);
            const isModified = fieldValues[field.field_name] !== field.value;

            return (
              <div
                key={field.field_name}
                className={`border rounded-xl p-4 transition-colors ${
                  isModified
                    ? "border-blue-300 bg-blue-50/30"
                    : "border-gray-200"
                }`}
              >
                {/* Header */}
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-2 h-2 rounded-full ${colors.bg}`} />
                  <span className="text-sm font-semibold text-gray-800 flex-1">
                    {field.field_name}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${colors.bg} ${colors.text}`}
                  >
                    {field.source.toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-400">
                    信心度: {confidencePercent(field.confidence)}
                  </span>
                  {isModified && (
                    <span className="text-xs text-blue-600 font-medium">
                      已修改
                    </span>
                  )}
                </div>

                {/* Editable field */}
                <textarea
                  rows={2}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y"
                  value={fieldValues[field.field_name] || ""}
                  onChange={(e) =>
                    handleFieldChange(field.field_name, e.target.value)
                  }
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50">
        <button
          onClick={() => navigate("/")}
          className="px-4 py-2 border border-gray-300 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          返回
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {submitting ? (
            <>
              <span className="animate-spin">⏳</span> 提交中...
            </>
          ) : (
            <>
              <span>✅</span> 確認提交
            </>
          )}
        </button>
      </div>
    </div>
  );
}
