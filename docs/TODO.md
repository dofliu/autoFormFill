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

### 持久化 Job Store `P0`
- [ ] 新增 `FormJob` ORM 模型 (`app/models/form_job.py`)
- [ ] 新增 `job_service.py` (async CRUD)
- [ ] 改造 `job_store.py` 為 DB-backed（保持介面不變）
- [ ] 更新 `forms.py` router 注入 db session
- [ ] 驗證：重啟後歷史仍在

### PDF 表單填寫 `P1`
- [ ] `document_generator.py` 新增 `fill_pdf()` 方法
- [ ] 支援 PDF AcroForm widget 填寫
- [ ] 驗證：上傳 PDF 表單 → 填寫 → 下載可開啟

### 測試補齊 `P1`
- [ ] `tests/test_form_parser.py` — 表單解析單元測試
- [ ] `tests/test_intent_router.py` — Mock LLM 的路由測試
- [ ] `tests/test_rag_pipeline.py` — Mock LLM + ChromaDB
- [ ] `tests/test_document_generator.py` — 模板填寫測試

### 錯誤處理 `P2`
- [ ] LLM 呼叫增加 retry (exponential backoff)
- [ ] 前端增加全域 Error Boundary
- [ ] API 統一 error response 格式 `{ detail, code, field? }`

---

## Phase 3 — 知識引擎基礎 ⭐

> 依賴：Phase 2.5 持久化 Job Store 完成
> 參考：`docs/ROADMAP.md` Phase 3 章節

### 3.1 資料夾監控 `P0`
- [ ] 安裝 `watchdog` 依賴
- [ ] 新增 `FileIndex` ORM 模型 (`app/models/file_index.py`)
  - 欄位：id, file_path, file_hash, status, chunks_count, collection, last_indexed_at
- [ ] 新增 `file_watcher.py` service (watchdog EventHandler)
- [ ] 新增 `indexing_service.py` (解析 + 切塊 + 嵌入 + FileIndex CRUD)
- [ ] `app/config.py` 新增 `WATCH_DIRS`, `WATCH_INTERVAL` 設定
- [ ] `main.py` lifespan 啟動 watcher background task
- [ ] 驗證：放檔案進監控資料夾 → 自動出現在語意搜尋結果

### 3.2 增量索引 `P0`
- [ ] FileIndex 狀態機：pending → indexing → indexed → stale → re-indexing
- [ ] 檔案 hash (SHA-256) 比對，只處理真正變動的檔案
- [ ] 刪除檔案時清除對應 ChromaDB chunks
- [ ] 修改檔案時：刪舊 chunks → 重新解析嵌入
- [ ] 驗證：修改已索引檔案 → 搜尋結果更新

### 3.3 索引管理 API + UI `P1`
- [ ] 新增 `app/routers/indexing.py`
  - `GET /api/v1/indexing/status` — 索引統計
  - `POST /api/v1/indexing/rescan` — 手動觸發全量掃描
  - `GET /api/v1/indexing/files` — 已索引檔案列表
- [ ] 前端新增「索引狀態」頁面 (`IndexingStatusPage.tsx`)
- [ ] Sidebar 加入索引狀態入口

### 3.4 多格式支援 `P1`
- [ ] `.txt` / `.md` 文本直讀
- [ ] `.pptx` (python-pptx) slide text extraction
- [ ] `.xlsx` (openpyxl) cell value extraction
- [ ] `document_service.py` 新增對應 extract 方法
- [ ] `file_utils.py` 更新 `detect_file_type()`

### 3.5 Entity 泛化（評估） `P2`
- [ ] 設計 `Entity` + `EntityAttribute` schema
- [ ] 評估是否新建表 or 擴展現有 UserProfile
- [ ] 更新 Intent Router 支援泛化 Entity 查詢
- [ ] 決策記錄寫入 `docs/ROADMAP.md`

---

## Phase 4 — 多輸出適配器

> 依賴：Phase 3.1 + 3.2 完成（自動索引可用）
> 參考：`docs/ROADMAP.md` Phase 4 章節

### 4.1 知識問答 (Chat) `P0`
- [ ] 新增 `app/services/chat_service.py`
- [ ] 新增 `app/routers/chat.py` — `POST /api/v1/chat` (streaming)
- [ ] FastAPI StreamingResponse + SSE
- [ ] 對話歷史管理（最近 N 輪 context）
- [ ] 前端新增 `ChatPage.tsx` — 對話 UI
- [ ] Sidebar 加入 Chat 入口

### 4.2 郵件草稿生成 `P1`
- [ ] 新增 `app/services/email_generator.py`
- [ ] 新增 `app/routers/email.py` — `POST /api/v1/email/draft`
- [ ] 前端新增 `EmailDraftPage.tsx`

### 4.3 報告生成 `P2`
- [ ] 新增 `app/services/report_generator.py`
- [ ] 新增 `app/routers/reports.py` — `POST /api/v1/reports/generate`
- [ ] 前端新增 `ReportPage.tsx`

### 4.4 Output Adapter 抽象 `P2`
- [ ] 抽取共同模式為 `app/adapters/base.py` (OutputAdapter ABC)
- [ ] 重構 form_filler, chat_service, email_generator 為 adapter 實作
- [ ] 統一 context retrieval 邏輯

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
