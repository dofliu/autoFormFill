# SmartFill-Scholar — 任務追蹤

> 最後更新：2026-03-09
> 使用方式：完成任務後將 `[ ]` 改為 `[x]`，git commit 即可追蹤進度

---

## Phase 1 — 後端 MVP ✅

- [x] FastAPI 應用骨架 (main.py, config, database)
- [x] UserProfile ORM + CRUD API
- [x] EducationExperience ORM + CRUD API
- [x] LLM Adapter (Gemini) + Factory
- [x] ChromaDB 向量庫 + Document 上傳/搜尋
- [x] 表單解析 (docx template vars + PDF widgets)
- [x] Intent Router (LLM 欄位分類)
- [x] RAG Pipeline (檢索 + 生成 + 幻覺防護)
- [x] Form Filler 流程編排
- [x] Document Generator (docx 模板填寫)

## Phase 2 — 前端 MVP ✅

- [x] Vite + React 19 + TypeScript + Tailwind CSS v4
- [x] API Client 封裝 (typed fetch)
- [x] AppShell + Sidebar 導覽
- [x] UserProfilePage (CRUD + 學經歷)
- [x] KnowledgeBasePage (上傳 + 語意搜尋)
- [x] FormFillPage (上傳 → 預覽)
- [x] FormPreviewPage (色碼卡片 + 編輯 + 提交)
- [x] FormHistoryPage (填寫歷史)

---

## Phase 2.5 — 收尾補強

### 持久化 Job Store `P0` ✅
- [x] 新增 `FormJob` ORM 模型 (`app/models/form_job.py`)
- [x] 新增 `job_service.py` (async CRUD)
- [x] 改造 `job_store.py` 為 DB-backed（純 async 介面）
- [x] 更新 `forms.py` router 注入 db session
- [x] 驗證：重啟後歷史仍在

### PDF 表單填寫 `P1` ✅
- [x] `document_generator.py` 新增 `fill_pdf()` 方法
- [x] 支援 PDF AcroForm widget 填寫
- [x] 驗證：上傳 PDF 表單 → 填寫 → 下載可開啟
- [x] 建立 `data/test_template.pdf` 測試模板（10 個 AcroForm 欄位）

### 測試補齊 `P1` ✅
- [x] `tests/test_form_parser.py` — 表單解析單元測試（DOCX + PDF + regex，32 tests）
- [x] `tests/test_intent_router.py` — Mock LLM 的路由測試（分類 + 預設值 + 邊界，18 tests）
- [x] `tests/test_rag_pipeline.py` — Mock LLM + ChromaDB（生成 + 縮短 + 幻覺防護 + 信心度，33 tests）
- [x] `tests/test_document_generator.py` — 模板填寫測試（PDF + DOCX，12 tests）

### 錯誤處理 `P2`
- [ ] LLM 呼叫增加 retry (exponential backoff)
- [ ] 前端增加全域 Error Boundary
- [ ] API 統一 error response 格式 `{ detail, code, field? }`

---

## Phase 3 — 知識引擎基礎 ⭐

> 依賴：Phase 2.5 持久化 Job Store 完成
> 參考：`docs/ROADMAP.md` Phase 3 章節

### 3.1 資料夾監控 `P0` ✅
- [x] 安裝 `watchdog` 依賴
- [x] 新增 `FileIndex` ORM 模型 (`app/models/file_index.py`)
  - 欄位：id, file_path, file_hash, file_size, file_type, status, chunks_count, collection, doc_id, error_message, last_indexed_at
- [x] 新增 `file_watcher.py` service (watchdog EventHandler + debounce + async queue)
- [x] 新增 `indexing_service.py` (解析 + 切塊 + 嵌入 + FileIndex CRUD)
- [x] `app/config.py` 新增 `WATCH_DIRS`, `WATCH_INTERVAL`, `AUTO_INDEX_COLLECTION`, `SUPPORTED_EXTENSIONS` 設定
- [x] `main.py` lifespan 啟動/停止 watcher background task
- [ ] 驗證：放檔案進監控資料夾 → 自動出現在語意搜尋結果

### 3.2 增量索引 `P0` ✅
- [x] FileIndex 狀態機：pending → indexing → indexed → stale → deleted → error
- [x] 檔案 hash (SHA-256) 比對，只處理真正變動的檔案
- [x] 刪除檔案時清除對應 ChromaDB chunks
- [x] 修改檔案時：刪舊 chunks → 重新解析嵌入
- [ ] 驗證：修改已索引檔案 → 搜尋結果更新

### 3.3 索引管理 API + UI `P1` ✅
- [x] 新增 `app/routers/indexing.py`
  - `GET /api/v1/indexing/status` — 索引統計 + watcher 狀態
  - `POST /api/v1/indexing/rescan` — 手動觸發全量掃描
  - `GET /api/v1/indexing/files` — 已索引檔案列表（支援狀態篩選）
  - `POST /api/v1/indexing/index-file` — 手動索引單一檔案
  - `DELETE /api/v1/indexing/remove-file` — 手動移除索引
- [x] 前端新增「索引狀態」頁面 (`IndexingStatusPage.tsx`)
- [x] Sidebar 加入索引狀態入口（🔍 自動索引）
- [x] 前端 API wrapper (`src/api/indexing.ts`)

### 3.4 多格式支援 `P1` ✅
- [x] `.txt` / `.md` 文本直讀（含多編碼偵測）
- [x] `.pptx` (python-pptx) slide text extraction — 支援文字框、標題、表格、多 slide
- [x] `.xlsx` (openpyxl) cell value extraction — 支援多工作表、混合型別、空行跳過
- [x] `document_service.py` 新增 `extract_text_from_plaintext()`
- [x] `document_service.py` 新增 `extract_text_from_pptx()` + `extract_text_from_xlsx()`
- [x] `file_utils.py` 更新 `detect_file_type()` 支援 txt/md/pptx/xlsx
- [x] `config.py` 更新 `SUPPORTED_EXTENSIONS` 預設值加入 `.pptx,.xlsx`
- [x] 新增 `tests/test_multi_format.py`（29 tests — 檔案偵測 + PPTX 解析 + XLSX 解析 + dispatcher + config）

### 3.5 Entity 泛化（評估） `P2`
- [ ] 設計 `Entity` + `EntityAttribute` schema
- [ ] 評估是否新建表 or 擴展現有 UserProfile
- [ ] 更新 Intent Router 支援泛化 Entity 查詢
- [ ] 決策記錄寫入 `docs/ROADMAP.md`

---

## Phase 4 — 多輸出適配器 ✅

> 依賴：Phase 3.1 + 3.2 完成（自動索引可用）
> 參考：`docs/ROADMAP.md` Phase 4 章節

### 4.1 知識問答 (Chat) `P0` ✅
- [x] 新增 `app/services/chat_service.py`（多 collection 並行搜尋 + prompt 組合 + SSE 串流）
- [x] 新增 `app/routers/chat.py` — `POST /api/v1/chat` (streaming)
- [x] FastAPI StreamingResponse + SSE（sources → chunks → done 事件協議）
- [x] LLM Adapter 串流擴展（`generate_text_stream()` in base + gemini）
- [x] 對話歷史管理（前端管理，最近 N 輪 context）
- [x] 前端新增 `ChatPage.tsx` — 對話 UI（即時串流 + 來源引用 + 取消按鈕）
- [x] 前端新增 `ChatMessage.tsx` — 訊息氣泡元件（來源收合 + collection 色碼）
- [x] Sidebar 加入 Chat 入口（💬 知識問答）

### 4.2 郵件草稿生成 `P1` ✅
- [x] 新增 `app/schemas/email.py`（EmailDraftRequest Pydantic model）
- [x] 新增 `app/services/email_generator.py`（RAG → prompt → SSE 串流編排）
- [x] 新增 `app/routers/email.py` — `POST /api/v1/email/draft`（SSE StreamingResponse）
- [x] 前端新增 `frontend/src/types/email.ts` + `frontend/src/api/email.ts`
- [x] 前端新增 `EmailDraftPage.tsx`（分割視圖：表單 + 串流預覽 + 複製/下載）
- [x] Sidebar 加入郵件草稿入口（✉️ 郵件草稿）
- [x] 新增 `tests/test_email_generator.py`（25 tests — prompt 組合 + SSE 事件 + 搜尋 + 錯誤處理 + schema）

### 4.3 報告生成 `P2` ✅
- [x] 新增 `app/schemas/report.py`（ReportRequest Pydantic model — topic, report_type, target_audience, sections, language）
- [x] 新增 `app/services/report_generator.py`（RAG → 結構化報告 prompt → SSE 串流，3 種報告類型 + 3 種讀者語調）
- [x] 新增 `app/routers/report.py` — `POST /api/v1/report/generate`（SSE StreamingResponse）
- [x] `main.py` 註冊 report router
- [x] 前端新增 `frontend/src/types/report.ts` + `frontend/src/api/report.ts`（SSE async generator）
- [x] 前端新增 `frontend/src/pages/ReportPage.tsx`（分割視圖：表單 + Markdown 串流預覽 + 複製/下載 .md/.txt）
- [x] `frontend/src/App.tsx` 新增 `/report` route + `Sidebar.tsx` 新增導覽入口
- [x] 新增 `tests/test_report_generator.py`（29 tests — prompt 組合 + SSE 事件 + 搜尋查詢 + 錯誤處理 + schema + DEFAULT_SECTIONS）

### 4.4 Output Adapter 抽象 `P2` ✅
- [x] 新增 `app/services/sse_pipeline.py`（共用 SSE 管線：`_sse()` + `search_all_collections()` + context formatters + `StreamConfig` + `rag_sse_stream()`）
- [x] 重構 `chat_service.py` — 移除重複管線碼，委派給 `rag_sse_stream()`，re-export 向後相容符號
- [x] 重構 `email_generator.py` — import 來源改為 `sse_pipeline`，使用 `format_context_default()` + `rag_sse_stream()`
- [x] 重構 `report_generator.py` — import 來源改為 `sse_pipeline`，使用 `format_context_report()` + `rag_sse_stream()`
- [x] 更新測試 mock 路徑（`test_email_generator.py` + `test_report_generator.py`）
- [x] 新增 `tests/test_sse_pipeline.py`（24 tests — SSE 格式化 + 多 collection 搜尋 + context formatter + StreamConfig + 完整管線）

---

## Phase 5 — 智能化

> 依賴：Phase 4.1 完成
> 參考：`docs/ROADMAP.md` Phase 5 章節

### 5.1 知識圖譜 `P1`
- [ ] 設計 Entity Relation 資料模型
- [ ] 新增關聯 API endpoints
- [ ] 前端新增圖譜視覺化（D3.js / vis-network）

### 5.2 合規檢查 `P2`
- [ ] 設計 Rule Engine 架構
- [ ] 必填欄位 / 格式 / 字數自動檢查
- [ ] 前端 warning indicators

### 5.3 版本追蹤 `P2`
- [ ] Document versioning 資料模型
- [ ] Diff engine (text-based)
- [ ] 前端 diff viewer

### 5.4 智能提醒 `P3`
- [ ] 截止日期偵測
- [ ] 填寫差異提醒
- [ ] 通知系統（in-app）

---

## Phase 6 — 協作與部署

> 依賴：Phase 5 部分功能完成
> 參考：`docs/ROADMAP.md` Phase 6 章節

### 6.1 認證與權限 `P0`
- [ ] JWT 認證 middleware
- [ ] RBAC: admin / user / viewer
- [ ] API key 支援

### 6.2 多使用者隔離 `P1`
- [ ] 每人獨立 ChromaDB collection
- [ ] 共享知識庫（組織級）
- [ ] 資料隔離驗證

### 6.3 Docker 部署 `P1`
- [ ] Dockerfile (backend)
- [ ] Dockerfile (frontend, nginx)
- [ ] docker-compose.yml
- [ ] 部署文件

### 6.4 CI/CD `P2`
- [ ] GitHub Actions: lint + test on PR
- [ ] Auto build + deploy pipeline
- [ ] 環境變數管理

---

## 優先級說明

| 標記 | 含義 |
|------|------|
| `P0` | 必做，阻擋後續任務 |
| `P1` | 重要，應盡快完成 |
| `P2` | 有價值，可排入 |
| `P3` | Nice to have，有空再做 |

## 快速統計指令

```bash
# 計算剩餘待辦
grep -c "\- \[ \]" docs/TODO.md

# 計算已完成
grep -c "\- \[x\]" docs/TODO.md

# 查看特定 Phase 的待辦
grep -A 100 "## Phase 3" docs/TODO.md | grep "\- \[ \]"
```
