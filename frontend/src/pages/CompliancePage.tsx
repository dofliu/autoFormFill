import { useCallback, useEffect, useState } from "react";
import * as complianceApi from "../api/compliance";
import type {
  ComplianceRule,
  ComplianceRuleCreate,
} from "../types/compliance";

const RULE_TYPES = [
  { value: "required", label: "必填" },
  { value: "min_length", label: "最少字數" },
  { value: "max_length", label: "最多字數" },
  { value: "regex", label: "正規表達式" },
  { value: "contains", label: "必須包含" },
];

const SEVERITIES = [
  { value: "error", label: "錯誤", color: "text-red-600 bg-red-50" },
  { value: "warning", label: "警告", color: "text-amber-600 bg-amber-50" },
  { value: "info", label: "資訊", color: "text-blue-600 bg-blue-50" },
];

export default function CompliancePage() {
  const userId = Number(localStorage.getItem("smartfill_user_id") || "1");

  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [error, setError] = useState("");

  // Add form state
  const [form, setForm] = useState<ComplianceRuleCreate>({
    rule_name: "",
    field_pattern: "*",
    rule_type: "required",
    rule_value: "",
    severity: "warning",
    message: "",
  });

  const loadRules = useCallback(async () => {
    try {
      setLoading(true);
      const data = await complianceApi.listRules(userId);
      setRules(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleAdd = async () => {
    if (!form.rule_name.trim()) {
      setError("請輸入規則名稱");
      return;
    }
    try {
      await complianceApi.createRule(userId, form);
      setShowAdd(false);
      setForm({
        rule_name: "",
        field_pattern: "*",
        rule_type: "required",
        rule_value: "",
        severity: "warning",
        message: "",
      });
      await loadRules();
    } catch (e) {
      setError(e instanceof Error ? e.message : "建立失敗");
    }
  };

  const handleToggle = async (rule: ComplianceRule) => {
    await complianceApi.updateRule(userId, rule.id, {
      is_active: !rule.is_active,
    });
    await loadRules();
  };

  const handleDelete = async (ruleId: number) => {
    await complianceApi.deleteRule(userId, ruleId);
    await loadRules();
  };

  const severityBadge = (severity: string) => {
    const s = SEVERITIES.find((s) => s.value === severity);
    return (
      <span
        className={`text-xs px-2 py-0.5 rounded-full ${s?.color || "text-gray-600 bg-gray-100"}`}
      >
        {s?.label || severity}
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">合規檢查</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            設定表單欄位驗證規則，自動檢查填寫結果
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新增規則
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-3 p-3 bg-red-50 text-red-600 text-sm rounded-lg">
          {error}
          <button
            onClick={() => setError("")}
            className="ml-2 text-red-400 hover:text-red-600"
          >
            ×
          </button>
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <div className="mx-6 mt-4 p-4 border border-blue-200 bg-blue-50/30 rounded-xl">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            新增驗證規則
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                規則名稱
              </label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="例如：必填欄位檢查"
                value={form.rule_name}
                onChange={(e) =>
                  setForm({ ...form, rule_name: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                欄位模式
              </label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="* = 所有欄位，或指定欄位名稱"
                value={form.field_pattern}
                onChange={(e) =>
                  setForm({ ...form, field_pattern: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                規則類型
              </label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.rule_type}
                onChange={(e) =>
                  setForm({ ...form, rule_type: e.target.value })
                }
              >
                {RULE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                規則值
              </label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="例如：10、\\d{4}/\\d{2}/\\d{2}"
                value={form.rule_value}
                onChange={(e) =>
                  setForm({ ...form, rule_value: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                嚴重程度
              </label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.severity}
                onChange={(e) =>
                  setForm({ ...form, severity: e.target.value })
                }
              >
                {SEVERITIES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                自訂訊息（選填）
              </label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="留空使用預設訊息"
                value={form.message}
                onChange={(e) =>
                  setForm({ ...form, message: e.target.value })
                }
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
              建立規則
            </button>
          </div>
        </div>
      )}

      {/* Rules list */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="text-center text-gray-400 text-sm py-12">
            載入中...
          </div>
        ) : rules.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-12">
            尚無驗證規則。點擊「+ 新增規則」開始設定。
          </div>
        ) : (
          <div className="space-y-3">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className={`border rounded-xl p-4 transition-colors ${
                  rule.is_active
                    ? "border-gray-200 bg-white"
                    : "border-gray-100 bg-gray-50 opacity-60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleToggle(rule)}
                    className={`w-8 h-5 rounded-full transition-colors flex items-center ${
                      rule.is_active ? "bg-blue-600" : "bg-gray-300"
                    }`}
                  >
                    <span
                      className={`inline-block w-3.5 h-3.5 rounded-full bg-white shadow transform transition-transform ${
                        rule.is_active ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                  <span className="text-sm font-semibold text-gray-800 flex-1">
                    {rule.rule_name}
                  </span>
                  {severityBadge(rule.severity)}
                  <span className="text-xs text-gray-400 px-2 py-0.5 bg-gray-100 rounded">
                    {RULE_TYPES.find((t) => t.value === rule.rule_type)?.label ||
                      rule.rule_type}
                  </span>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    className="text-xs text-red-400 hover:text-red-600"
                  >
                    刪除
                  </button>
                </div>
                <div className="mt-2 text-xs text-gray-500 flex gap-4">
                  <span>
                    欄位：
                    <code className="bg-gray-100 px-1 rounded">
                      {rule.field_pattern}
                    </code>
                  </span>
                  {rule.rule_value && (
                    <span>
                      值：
                      <code className="bg-gray-100 px-1 rounded">
                        {rule.rule_value}
                      </code>
                    </span>
                  )}
                  {rule.message && (
                    <span className="text-gray-400">
                      訊息：{rule.message}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
