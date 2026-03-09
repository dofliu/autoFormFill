import { useRef, useState } from "react";
import * as docsApi from "../api/documents";
import type { DocumentMetadataInput, DocumentUploadResponse, DocumentSearchResponse } from "../types/document";

export default function KnowledgeBasePage() {
  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<"paper" | "project">("paper");
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [keywords, setKeywords] = useState("");
  const [projectName, setProjectName] = useState("");
  const [fundingAgency, setFundingAgency] = useState("");
  const [period, setPeriod] = useState("");
  const [techStack, setTechStack] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search state
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState("academic_papers");
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<DocumentSearchResponse | null>(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file || !title) return;
    setUploading(true);
    setError("");
    setUploadResult(null);
    try {
      const meta: DocumentMetadataInput = {
        doc_type: docType,
        title,
        authors: authors || undefined,
        publish_year: year ? parseInt(year) : undefined,
        keywords: keywords || undefined,
        project_name: projectName || undefined,
        funding_agency: fundingAgency || undefined,
        execution_period: period || undefined,
        tech_stack: techStack || undefined,
      };
      const result = await docsApi.uploadDocument(file, meta);
      setUploadResult(result);
      // Reset form
      setFile(null);
      setTitle("");
      setAuthors("");
      setYear("");
      setKeywords("");
      setProjectName("");
      setFundingAgency("");
      setPeriod("");
      setTechStack("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "上傳失敗");
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const result = await docsApi.searchDocuments(query, collection);
      setSearchResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "搜尋失敗");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <h2 className="text-xl font-bold text-gray-800">知識庫管理</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Upload Section */}
      <section className="border border-gray-200 rounded-xl p-5">
        <h3 className="text-base font-semibold mb-4">上傳文件</h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          {/* File */}
          <div className="col-span-2">
            <label className="block text-gray-600 mb-1">文件檔案</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1 file:text-blue-700 file:text-sm"
            />
          </div>

          {/* Doc Type */}
          <div>
            <label className="block text-gray-600 mb-1">文件類型</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              value={docType}
              onChange={(e) => setDocType(e.target.value as "paper" | "project")}
            >
              <option value="paper">學術論文</option>
              <option value="project">研究計畫</option>
            </select>
          </div>

          {/* Title */}
          <div>
            <label className="block text-gray-600 mb-1">標題 *</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="文件標題"
            />
          </div>

          {/* Conditional fields */}
          {docType === "paper" ? (
            <>
              <div>
                <label className="block text-gray-600 mb-1">作者</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  placeholder="Wang et al."
                />
              </div>
              <div>
                <label className="block text-gray-600 mb-1">年份</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  placeholder="2025"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-gray-600 mb-1">關鍵字</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="Wind Power, Fault Diagnosis"
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-gray-600 mb-1">計畫名稱</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-gray-600 mb-1">補助單位</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={fundingAgency}
                  onChange={(e) => setFundingAgency(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-gray-600 mb-1">執行期間</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  placeholder="2024/08 - 2025/07"
                />
              </div>
              <div>
                <label className="block text-gray-600 mb-1">技術棧</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  value={techStack}
                  onChange={(e) => setTechStack(e.target.value)}
                  placeholder="Python, SCADA"
                />
              </div>
            </>
          )}
        </div>

        <button
          onClick={handleUpload}
          disabled={!file || !title || uploading}
          className="mt-4 px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {uploading ? "上傳中..." : "上傳並嵌入"}
        </button>

        {uploadResult && (
          <div className="mt-3 bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-lg">
            上傳成功！已分割為 <strong>{uploadResult.chunks_count}</strong> 個文本區塊並存入{" "}
            <strong>{uploadResult.collection}</strong>
          </div>
        )}
      </section>

      {/* Search Section */}
      <section className="border border-gray-200 rounded-xl p-5">
        <h3 className="text-base font-semibold mb-4">語意搜尋</h3>

        <div className="flex gap-3">
          <input
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="輸入搜尋內容，例如：風力發電 故障診斷"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={collection}
            onChange={(e) => setCollection(e.target.value)}
          >
            <option value="academic_papers">學術論文</option>
            <option value="research_projects">研究計畫</option>
          </select>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || searching}
            className="px-5 py-2 bg-gray-800 text-white text-sm rounded-lg hover:bg-gray-900 disabled:opacity-50"
          >
            {searching ? "搜尋中..." : "搜尋"}
          </button>
        </div>

        {searchResult && (
          <div className="mt-4 space-y-3">
            <p className="text-xs text-gray-500">
              找到 {searchResult.results.length} 筆結果 — 搜尋「{searchResult.query}」
            </p>
            {searchResult.results.map((r, i) => (
              <div key={r.doc_id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">#{i + 1}</span>
                  <span className="text-xs text-gray-500 font-mono">{r.doc_id}</span>
                  {r.distance !== null && (
                    <span className="text-xs text-gray-400">距離: {r.distance.toFixed(4)}</span>
                  )}
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-4">{r.text}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(r.metadata).map(([k, v]) => (
                    <span key={k} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
                      {k}: {v}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
