import { useEffect, useState } from "react";
import * as usersApi from "../api/users";
import * as educationApi from "../api/education";
import type { UserProfile, UserProfileCreate } from "../types/user";
import type { EducationExperience, EducationExperienceCreate } from "../types/education";

export default function UserProfilePage() {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [selected, setSelected] = useState<UserProfile | null>(null);
  const [entries, setEntries] = useState<EducationExperience[]>([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<UserProfileCreate>({});
  const [saving, setSaving] = useState(false);
  const [eduForm, setEduForm] = useState<EducationExperienceCreate | null>(null);

  useEffect(() => {
    usersApi.listUsers().then(setUsers);
  }, []);

  useEffect(() => {
    if (selected) {
      educationApi.listEntries(selected.id).then(setEntries);
    } else {
      setEntries([]);
    }
  }, [selected]);

  const handleSelect = (u: UserProfile) => {
    setSelected(u);
    setEditing(false);
  };

  const startCreate = () => {
    setForm({});
    setEditing(true);
    setSelected(null);
  };

  const startEdit = () => {
    if (!selected) return;
    setForm({
      name_zh: selected.name_zh,
      name_en: selected.name_en,
      title: selected.title,
      department: selected.department,
      university: selected.university,
      email: selected.email,
      phone_office: selected.phone_office,
      address: selected.address,
    });
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (selected) {
        const updated = await usersApi.updateUser(selected.id, form);
        setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
        setSelected(updated);
      } else {
        const created = await usersApi.createUser(form);
        setUsers((prev) => [...prev, created]);
        setSelected(created);
      }
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    await usersApi.deleteUser(selected.id);
    setUsers((prev) => prev.filter((u) => u.id !== selected.id));
    setSelected(null);
  };

  const handleAddEdu = async () => {
    if (!selected || !eduForm) return;
    const entry = await educationApi.createEntry(selected.id, eduForm);
    setEntries((prev) => [...prev, entry]);
    setEduForm(null);
  };

  const handleDeleteEdu = async (entryId: number) => {
    if (!selected) return;
    await educationApi.deleteEntry(selected.id, entryId);
    setEntries((prev) => prev.filter((e) => e.id !== entryId));
  };

  const field = (key: keyof UserProfileCreate, label: string) => (
    <div key={key}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        value={(form[key] as string) || ""}
        onChange={(e) => setForm({ ...form, [key]: e.target.value || null })}
      />
    </div>
  );

  return (
    <div className="flex h-full">
      {/* Left: User List */}
      <div className="w-64 border-r border-gray-200 p-4 flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">使用者</h2>
        <button
          onClick={startCreate}
          className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新增使用者
        </button>
        <div className="flex flex-col gap-1 mt-2">
          {users.map((u) => (
            <button
              key={u.id}
              onClick={() => handleSelect(u)}
              className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selected?.id === u.id
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {u.name_zh || u.name_en || `User #${u.id}`}
            </button>
          ))}
        </div>
      </div>

      {/* Right: Detail / Edit */}
      <div className="flex-1 p-6 overflow-y-auto">
        {editing ? (
          <div className="max-w-lg">
            <h2 className="text-lg font-semibold mb-4">
              {selected ? "編輯個人資料" : "新增使用者"}
            </h2>
            <div className="grid gap-3">
              {field("name_zh", "中文姓名")}
              {field("name_en", "英文姓名")}
              {field("title", "職稱")}
              {field("department", "系所")}
              {field("university", "學校")}
              {field("email", "Email")}
              {field("phone_office", "辦公室電話")}
              {field("address", "地址")}
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "儲存中..." : "儲存"}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
            </div>
          </div>
        ) : selected ? (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <h2 className="text-lg font-semibold">{selected.name_zh || selected.name_en}</h2>
              <button
                onClick={startEdit}
                className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                編輯
              </button>
              <button
                onClick={handleDelete}
                className="px-3 py-1 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
              >
                刪除
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm max-w-lg">
              {[
                ["中文姓名", selected.name_zh],
                ["英文姓名", selected.name_en],
                ["職稱", selected.title],
                ["系所", selected.department],
                ["學校", selected.university],
                ["Email", selected.email],
                ["電話", selected.phone_office],
                ["地址", selected.address],
              ].map(([label, val]) => (
                <div key={label as string}>
                  <span className="text-gray-500">{label}</span>
                  <p className="font-medium text-gray-800">{(val as string) || "—"}</p>
                </div>
              ))}
            </div>

            {/* Education */}
            <div className="mt-8">
              <div className="flex items-center gap-3 mb-3">
                <h3 className="text-base font-semibold">學經歷</h3>
                <button
                  onClick={() => setEduForm({ type: "Education" })}
                  className="px-3 py-1 text-xs bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  + 新增
                </button>
              </div>

              {eduForm && (
                <div className="border border-gray-200 rounded-lg p-4 mb-3 bg-gray-50">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">類型</label>
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={eduForm.type}
                        onChange={(e) =>
                          setEduForm({ ...eduForm, type: e.target.value as "Education" | "Experience" })
                        }
                      >
                        <option value="Education">學歷</option>
                        <option value="Experience">經歷</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">機構</label>
                      <input
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={eduForm.organization || ""}
                        onChange={(e) => setEduForm({ ...eduForm, organization: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">學位/職位</label>
                      <input
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={eduForm.role_degree || ""}
                        onChange={(e) => setEduForm({ ...eduForm, role_degree: e.target.value })}
                      />
                    </div>
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <label className="block text-xs text-gray-500 mb-1">開始</label>
                        <input
                          className="w-full border rounded px-2 py-1.5 text-sm"
                          value={eduForm.start_date || ""}
                          onChange={(e) => setEduForm({ ...eduForm, start_date: e.target.value })}
                          placeholder="YYYY-MM"
                        />
                      </div>
                      <div className="flex-1">
                        <label className="block text-xs text-gray-500 mb-1">結束</label>
                        <input
                          className="w-full border rounded px-2 py-1.5 text-sm"
                          value={eduForm.end_date || ""}
                          onChange={(e) => setEduForm({ ...eduForm, end_date: e.target.value })}
                          placeholder="YYYY-MM"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={handleAddEdu}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      新增
                    </button>
                    <button
                      onClick={() => setEduForm(null)}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              {entries.length === 0 ? (
                <p className="text-sm text-gray-400">尚無學經歷紀錄</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {entries.map((e) => (
                    <div
                      key={e.id}
                      className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-2.5"
                    >
                      <div className="text-sm">
                        <span
                          className={`inline-block px-1.5 py-0.5 text-xs rounded mr-2 ${
                            e.type === "Education"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-purple-100 text-purple-700"
                          }`}
                        >
                          {e.type === "Education" ? "學歷" : "經歷"}
                        </span>
                        <span className="font-medium">{e.organization}</span>
                        {e.role_degree && <span className="text-gray-500 ml-2">{e.role_degree}</span>}
                        {e.start_date && (
                          <span className="text-gray-400 ml-2 text-xs">
                            {e.start_date} ~ {e.end_date || "迄今"}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteEdu(e.id)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        刪除
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            請從左側選擇或新增使用者
          </div>
        )}
      </div>
    </div>
  );
}
