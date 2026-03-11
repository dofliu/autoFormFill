# CLAUDE.md — SmartFill-Scholar 專案指引

本文件為 Claude Code 的專案上下文指引，幫助 AI 助手快速理解專案架構與開發慣例。

## 專案概述

SmartFill-Scholar 的定位是 **Personal Knowledge API** —— 將個人或組織的散落資料統一為可程式化查詢的知識層。表單自動填寫是第一個應用，底層的 SQL + Vector + LLM Router 架構可延伸到問答、郵件草稿、報告生成等多種場景。

> 詳細願景見 `docs/VISION.md`，技術藍圖見 `docs/ROADMAP.md`，任務追蹤見 `docs/TODO.md`

## 啟動方式

```bash
# 後端 (port 8000)
cd autoFill
python -m uvicorn main:app --reload

# 前端 (port 5173)
cd autoFill/frontend
npm run dev
```

前端透過 Vite proxy 將 `/api` 請求轉發至後端 `http://127.0.0.1:8000`。

## 技術棧

- **後端**：Python 3.11+ / FastAPI / async SQLAlchemy + aiosqlite / ChromaDB / Google Gemini API
- **前端**：React 19 / TypeScript 5.9 / Tailwind CSS v4 / Vite 7 / React Router v7
- **資料庫**：SQLite（使用者資料）+ ChromaDB（向量知識庫）
- **LLM**：Google Gemini（透過 Adapter Pattern，可切換）

## 架構慣例

### 後端

- **分層架構**：`models/` → `schemas/` → `services/` → `routers/`
- **路由前綴**：所有 API 路由在 `/api/v1/` 下
- **非同步優先**：所有 DB 操作使用 async SQLAlchemy；ChromaDB 同步呼叫用 `asyncio.to_thread()` 包裝
- **LLM 適配器**：`app/llm/base.py` 定義 ABC，`gemini_adapter.py` 為實作，`factory.py` 依 `LLM_PROVIDER` env var 切換
- **Job Store**：`app/job_store.py` 為 async 介面，優先使用 SQLite 持久化（`FormJob` ORM + `job_service.py`），無 db session 時 fallback 為 in-memory
- **Pydantic Settings**：`app/config.py` 使用 `pydantic-settings` 從 `.env` 載入設定
- **ORM 模型註冊**：`main.py` 中必須 import 所有 ORM 模型，否則 `init_db()` 不會建表
- **認證架構**：JWT（PyJWT）+ RBAC 三級角色（admin/user/viewer），`AUTH_ENABLED` env var 控制開關
- **認證依賴**：`get_current_user` → `require_auth` → `require_admin`，`verify_ownership(current_user, user_id)` 驗證資源所有權
- **多使用者隔離**：ChromaDB metadata-based 過濾（`user_id` + `shared` 欄位），Router 解析 user_id（auth token 優先 > request body）

### 前端

- **樣式系統**：只使用 Tailwind CSS，**不使用 MUI 或其他 UI 框架**
- **API 層**：`src/api/client.ts` 封裝 fetch，提供 `get/post/postForm/put/del/downloadUrl` 函式
- **postForm vs post**：`postForm()` 用於 FormData（multipart），`post()` 用於 JSON body
- **TypeScript 設定**：啟用 `erasableSyntaxOnly`，禁止 class constructor parameter properties（使用標準屬性宣告）
- **欄位色碼**：🟢 `sql` = green / 🟡 `rag` = amber / 🔴 `skip` = red / 🔵 `override` = blue
- **認證狀態**：`AuthContext` + `useAuth()` hook 管理 JWT token + user 狀態，localStorage 存 `smartfill_access_token` / `smartfill_refresh_token` / `smartfill_user`
- **路由守衛**：`ProtectedRoute` 元件包裹需認證的頁面，未登入自動跳轉 `/login`

### 命名規則

- 後端：snake_case（Python 慣例）
- 前端：camelCase 變數、PascalCase 元件、kebab-case 檔名（元件除外用 PascalCase）
- API 回應欄位：snake_case（前後端一致）
- 中文 UI 文字直接寫在元件中

## 關鍵檔案

| 檔案 | 角色 |
|------|------|
| `main.py` | 應用進入點、CORS、路由註冊、lifespan |
| `app/auth/security.py` | 密碼 hash + JWT token 工具（PyJWT + passlib） |
| `app/auth/dependencies.py` | FastAPI 認證依賴注入（get_current_user, require_auth, verify_ownership） |
| `app/routers/auth.py` | 認證 API（register, login, refresh, me） |
| `app/schemas/auth.py` | 認證 Pydantic schemas（RegisterRequest, TokenResponse 等） |
| `app/services/form_filler.py` | 核心流程編排器（解析→路由→檢索→生成→輸出） |
| `app/services/document_generator.py` | 文件填寫（docx 模板 + PDF AcroForm widget） |
| `app/services/intent_router.py` | LLM 欄位分類（SQL_DB / VECTOR_DB / SKIP） |
| `app/services/rag_pipeline.py` | 檢索 + 生成 + 幻覺防護迴圈 |
| `app/llm/retry.py` | LLM 重試工具（`is_retryable()` + `@with_retry()` 指數退避） |
| `app/schemas/error.py` | 統一錯誤回應 schema + error code 常數 |
| `app/models/entity.py` | Entity ORM 模型（泛化實體 + JSON 屬性） |
| `app/services/entity_service.py` | Entity async CRUD + 屬性名聚合 |
| `app/routers/entities.py` | Entity CRUD API（`/api/v1/users/{id}/entities`） |
| `app/models/entity_relation.py` | EntityRelation ORM 模型（實體間有向關係） |
| `app/services/entity_relation_service.py` | EntityRelation async CRUD + graph query helpers |
| `app/routers/entity_relations.py` | Entity Relations CRUD + Graph API |
| `app/job_store.py` | 填寫任務持久化（async, DB-backed + in-memory fallback） |
| `app/models/form_job.py` | FormJob ORM 模型（job_id, user_id, fields_json...） |
| `app/services/job_service.py` | FormJob async CRUD 操作 |
| `app/models/file_index.py` | FileIndex ORM 模型（自動索引檔案追蹤） |
| `app/services/indexing_service.py` | 索引引擎（extract→chunk→embed→store + 增量邏輯） |
| `app/services/file_watcher.py` | watchdog 目錄監控 + debounce + async queue |
| `app/routers/indexing.py` | 索引管理 API（status / rescan / files） |
| `app/services/sse_pipeline.py` | 共用 SSE 管線（search + context format + StreamConfig + rag_sse_stream） |
| `app/services/chat_service.py` | Chat 編排器（prompt + 委派 sse_pipeline） |
| `app/routers/chat.py` | Chat SSE streaming endpoint |
| `app/services/email_generator.py` | Email 草稿編排器（prompt + 委派 sse_pipeline） |
| `app/routers/email.py` | Email SSE streaming endpoint |
| `app/services/report_generator.py` | 報告生成編排器（結構化大綱 + 委派 sse_pipeline） |
| `app/routers/report.py` | Report SSE streaming endpoint |
| `frontend/src/api/client.ts` | HTTP 客戶端封裝 |
| `frontend/src/api/chat.ts` | Chat SSE stream reader（async generator） |
| `frontend/src/api/email.ts` | Email SSE stream reader（async generator） |
| `frontend/src/api/report.ts` | Report SSE stream reader（async generator） |
| `frontend/src/pages/FormPreviewPage.tsx` | 填寫結果審查與編輯 |
| `frontend/src/pages/ChatPage.tsx` | 知識問答對話 UI |
| `frontend/src/pages/EmailDraftPage.tsx` | 郵件草稿生成 UI（表單 + 串流預覽） |
| `frontend/src/pages/ReportPage.tsx` | 報告生成 UI（表單 + Markdown 串流預覽 + 下載） |
| `frontend/src/pages/IndexingStatusPage.tsx` | 自動索引狀態監控頁面 |
| `frontend/src/pages/EntityPage.tsx` | 實體管理 UI（CRUD + 動態屬性 + 類型篩選） |
| `frontend/src/pages/KnowledgeGraphPage.tsx` | 知識圖譜視覺化（react-force-graph-2d + 篩選 + 側面板） |
| `frontend/src/components/AddRelationModal.tsx` | 新增關係對話框（來源/目標選擇 + 類型建議） |
| `app/models/compliance_rule.py` | ComplianceRule ORM 模型（規則引擎） |
| `app/services/compliance_service.py` | 合規檢查 CRUD + 驗證引擎（5 種規則類型） |
| `app/routers/compliance.py` | 合規 CRUD + `/check/{job_id}` API |
| `app/models/document_version.py` | DocumentVersion ORM 模型（版本追蹤） |
| `app/services/version_service.py` | 版本 CRUD + 行級 diff 引擎（difflib） |
| `app/routers/versions.py` | 版本 CRUD + `/diff/{old}/{new}` API |
| `app/models/reminder.py` | Reminder ORM 模型（智能提醒） |
| `app/services/reminder_service.py` | 提醒 CRUD + fill-diff 偵測 + 截止日掃描 |
| `app/routers/reminders.py` | 提醒 CRUD + `/dismiss-all` + `/fill-diff/{job_id}` API |
| `frontend/src/pages/CompliancePage.tsx` | 合規規則管理 UI（CRUD + 開關 + 嚴重等級色碼） |
| `frontend/src/pages/VersionPage.tsx` | 版本追蹤 UI（檔案側欄 + 版本歷史 + diff viewer） |
| `frontend/src/pages/ReminderPage.tsx` | 智能提醒 UI（篩選標籤 + 優先順序 + 新增表單） |
| `frontend/src/contexts/AuthContext.tsx` | React 認證 Context + useAuth() hook |
| `frontend/src/pages/LoginPage.tsx` | 登入頁面 |
| `frontend/src/pages/RegisterPage.tsx` | 註冊頁面 |
| `frontend/src/components/ProtectedRoute.tsx` | 路由守衛元件 |
| `frontend/src/components/ErrorBoundary.tsx` | 全域 React Error Boundary |
| `scripts/migrate_chroma_metadata.py` | ChromaDB metadata migration（Phase 6.2 多使用者隔離） |
| `frontend/vite.config.ts` | Vite 設定（proxy、plugins） |

## API 路由總覽

```
GET    /health                                  健康檢查
POST   /api/v1/auth/register                    使用者註冊
POST   /api/v1/auth/login                       登入（回傳 JWT）
POST   /api/v1/auth/refresh                     刷新 access token
GET    /api/v1/auth/me                          當前使用者資訊
POST   /api/v1/users/                           建立使用者
GET    /api/v1/users/                           列出使用者
GET    /api/v1/users/{id}                       使用者詳情
PUT    /api/v1/users/{id}                       更新使用者
DELETE /api/v1/users/{id}                       刪除使用者
GET    /api/v1/users/{id}/education/            學經歷列表
POST   /api/v1/users/{id}/education/            新增學經歷
DELETE /api/v1/users/{id}/education/{entry_id}  刪除學經歷
POST   /api/v1/users/{id}/entities/              新增實體
GET    /api/v1/users/{id}/entities/              實體列表（支援 ?entity_type 篩選）
GET    /api/v1/users/{id}/entities/{eid}         實體詳情
PUT    /api/v1/users/{id}/entities/{eid}         更新實體
DELETE /api/v1/users/{id}/entities/{eid}         刪除實體（含 cascade 關聯清理）
POST   /api/v1/users/{id}/entity-relations/      新增關係
GET    /api/v1/users/{id}/entity-relations/      關係列表（?relation_type, ?entity_id）
GET    /api/v1/users/{id}/entity-relations/types  關係類型列表
GET    /api/v1/users/{id}/entity-relations/graph  完整圖譜資料
GET    /api/v1/users/{id}/entity-relations/graph/{eid}  1-hop 子圖
GET    /api/v1/users/{id}/entity-relations/{rid}  關係詳情
PUT    /api/v1/users/{id}/entity-relations/{rid}  更新關係
DELETE /api/v1/users/{id}/entity-relations/{rid}  刪除關係
POST   /api/v1/documents/upload                 上傳文件（multipart）
GET    /api/v1/documents/search                 語意搜尋
POST   /api/v1/forms/parse                      解析表單欄位
POST   /api/v1/forms/fill                       智能填寫（multipart）
GET    /api/v1/forms/download/{filename}        下載填寫結果
GET    /api/v1/forms/preview/{job_id}           填寫預覽
POST   /api/v1/forms/submit                     提交修改（JSON）
GET    /api/v1/forms/history/{user_id}          填寫歷史
GET    /api/v1/indexing/status                  索引統計 + watcher 狀態
POST   /api/v1/indexing/rescan                  手動觸發全量掃描
GET    /api/v1/indexing/files                   已索引檔案列表
POST   /api/v1/indexing/index-file              手動索引單一檔案
POST   /api/v1/indexing/remove-file             手動移除索引
POST   /api/v1/chat                              知識問答（SSE streaming）
POST   /api/v1/email/draft                       郵件草稿生成（SSE streaming）
POST   /api/v1/report/generate                   報告生成（SSE streaming）
POST   /api/v1/users/{id}/compliance-rules/      新增合規規則
GET    /api/v1/users/{id}/compliance-rules/      規則列表（?active_only）
GET    /api/v1/users/{id}/compliance-rules/{rid} 規則詳情
PUT    /api/v1/users/{id}/compliance-rules/{rid} 更新規則
DELETE /api/v1/users/{id}/compliance-rules/{rid} 刪除規則
POST   /api/v1/users/{id}/compliance-rules/check/{job_id}  執行合規檢查
GET    /api/v1/users/{id}/versions/              版本列表
GET    /api/v1/users/{id}/versions/files         追蹤檔案列表
GET    /api/v1/users/{id}/versions/{vid}         版本詳情
PUT    /api/v1/users/{id}/versions/{vid}         更新版本標籤
DELETE /api/v1/users/{id}/versions/{vid}         刪除版本
GET    /api/v1/users/{id}/versions/diff/{old}/{new}  版本差異比對
POST   /api/v1/users/{id}/reminders/             新增提醒
GET    /api/v1/users/{id}/reminders/             提醒列表（?status, ?reminder_type）
GET    /api/v1/users/{id}/reminders/count        未讀提醒數量
GET    /api/v1/users/{id}/reminders/{rid}        提醒詳情
PUT    /api/v1/users/{id}/reminders/{rid}        更新提醒狀態
DELETE /api/v1/users/{id}/reminders/{rid}        刪除提醒
POST   /api/v1/users/{id}/reminders/dismiss-all  批次忽略所有提醒
GET    /api/v1/users/{id}/reminders/fill-diff/{job_id}  填寫差異比對
```

## 常見陷阱

1. **ChromaDB 是同步的**：所有 ChromaDB 呼叫必須包在 `await asyncio.to_thread(...)` 中
2. **ORM 模型必須先 import**：`main.py` 中 `from app.models import ...` 確保 `Base.metadata` 有表定義
3. **FormData vs JSON**：前端上傳檔案用 `postForm()`（不設 Content-Type），JSON payload 用 `post()`
4. **erasableSyntaxOnly**：TypeScript class 不能用 `constructor(public x: number)`，要用 `x: number; constructor(x) { this.x = x; }`
5. **`[需人工補充]`**：RAG/SQL 無法填寫的欄位會以此標記，前端以紅色顯示
6. **Port 衝突**：Vite 若偵測 5173 被占用會自動跳 5174，CORS 已設定兩個 port
7. **AUTH_ENABLED**：測試預設 `AUTH_ENABLED=False`（`tests/conftest.py`），直接呼叫 router 函式的測試需傳入 `current_user=None`
8. **user_id 穿透**：所有 service 函式的 `user_id` 參數預設 `None`（向後相容），測試中 `assert_called_with()` 需包含 `user_id=None`

## 測試

```bash
# 後端測試（430 tests）
python -m pytest tests/ -v

# 前端型別檢查
cd frontend && npx tsc --noEmit

# 前端生產建置（含型別檢查）
cd frontend && npm run build
```

### 測試檔案

| 測試檔案 | 測試數 | 覆蓋範圍 |
|----------|--------|---------|
| `tests/test_form_parser.py` | 32 | DOCX/PDF 表單解析 + regex + 去重 + 邊界 |
| `tests/test_intent_router.py` | 18 | LLM 欄位分類 + 預設值 + 錯誤傳播 |
| `tests/test_rag_pipeline.py` | 33 | RAG 生成 + 縮短 + 幻覺防護 + 信心度 |
| `tests/test_document_generator.py` | 12 | PDF/DOCX 填寫 + dispatcher + round-trip |
| `tests/test_form_preview.py` | 10 | Job Store CRUD + schema + 覆寫提交 |
| `tests/test_form_history.py` | 7 | 填寫歷史查詢 + 篩選 + schema |
| `tests/test_frontend_preview.py` | 4 | 前端型別 + routing 驗證 |
| `tests/test_email_generator.py` | 25 | Email prompt 組合 + SSE 事件 + 搜尋查詢 + 錯誤處理 + schema |
| `tests/test_multi_format.py` | 29 | PPTX/XLSX 解析 + 檔案偵測 + dispatcher + config 驗證 |
| `tests/test_report_generator.py` | 29 | Report prompt 組合 + SSE 事件 + 搜尋查詢 + 錯誤處理 + schema + DEFAULT_SECTIONS |
| `tests/test_sse_pipeline.py` | 24 | SSE 格式化 + 多 collection 搜尋 + context formatter + StreamConfig + RAG 管線 |
| `tests/test_llm_retry.py` | 18 | Retry 邏輯 + 錯誤分類 + fallback + SSE retry + ErrorResponse schema |
| `tests/test_entity.py` | 25 | Entity model + schema + service + form filler 整合 + intent router 整合 |
| `tests/test_entity_relation.py` | 26 | EntityRelation model + schema + service CRUD + graph queries + router 整合 |
| `tests/test_compliance.py` | 33 | ComplianceRule model + schema + field match + rule check + compliance engine + router |
| `tests/test_version_tracking.py` | 15 | DocumentVersion model + schema + diff engine + service + router |
| `tests/test_reminders.py` | 32 | Reminder model + schema + fill diff + date extraction + service + constants |
| `tests/test_auth.py` | 29 | 密碼 hash + JWT token + auth schemas + router endpoints + dependencies + model fields |
| `tests/test_multi_user_isolation.py` | 27 | metadata 建構 + search 過濾 + user_id 穿透 + schema + router 解析 + 跨使用者隔離 |

## 環境變數

參考 `.env.example`，所有設定透過 `app/config.py` 的 `Settings` 類別載入：

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `GEMINI_API_KEY` | （必填） | Google Gemini API Key |
| `LLM_PROVIDER` | `gemini` | LLM 供應商（可擴充） |
| `GEMINI_MODEL` | `gemini-2.0-flash` | 文字生成模型 |
| `GEMINI_EMBEDDING_MODEL` | `text-embedding-004` | 嵌入模型 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/smartfill.db` | 資料庫連線字串 |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB 持久化路徑 |
| `UPLOAD_DIR` | `./data/uploads` | 上傳暫存目錄 |
| `OUTPUT_DIR` | `./data/outputs` | 填寫結果輸出目錄 |
| `WATCH_DIRS` | `""` | 監控目錄（逗號分隔路徑） |
| `WATCH_INTERVAL` | `5` | 檔案系統輪詢間隔（秒） |
| `AUTO_INDEX_COLLECTION` | `auto_indexed` | 自動索引用的 ChromaDB 集合 |
| `SUPPORTED_EXTENSIONS` | `.docx,.pdf,.txt,.md,.pptx,.xlsx` | 支援索引的副檔名 |
| `CHAT_CONTEXT_ROUNDS` | `5` | Chat 對話保留最近 N 輪作為 LLM context |
| `AUTH_ENABLED` | `True` | 認證開關（`False` 跳過 JWT 驗證，dev 模式） |
| `JWT_SECRET_KEY` | `CHANGE-ME-IN-PRODUCTION` | JWT 簽名密鑰 |
| `JWT_ALGORITHM` | `HS256` | JWT 演算法 |
| `JWT_ACCESS_TOKEN_EXPIRE_HOURS` | `24` | Access token 有效期（小時） |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token 有效期（天） |

---

## 專案進度與規劃

### 目前狀態

| Phase | 狀態 | 說明 |
|-------|------|------|
| Phase 1 | ✅ 完成 | 後端 MVP（FastAPI + SQLite + ChromaDB + Gemini） |
| Phase 2 | ✅ 完成 | 前端 MVP（React 19 + TypeScript + Tailwind CSS） |
| Phase 2.5 | ✅ 完成 | 收尾：~~持久化 Job Store~~✅、~~PDF 填寫~~✅、~~測試補齊~~✅、~~錯誤處理~~✅ |
| Phase 3 | ✅ 完成 | 知識引擎基礎：~~資料夾監控~~✅ ~~增量索引~~✅ ~~索引 API+UI~~✅ ~~多格式~~✅ ~~Entity 泛化~~✅ |
| Phase 4 | ✅ 完成 | 多輸出適配器：~~Chat 問答~~✅、~~郵件草稿~~✅、~~報告生成~~✅、~~Adapter 抽象~~✅ |
| Phase 5 | ✅ 完成 | 智能化：~~知識圖譜~~✅、~~合規檢查~~✅、~~版本追蹤~~✅、~~智能提醒~~✅ |
| Phase 6.1 | ✅ 完成 | 認證與權限：JWT + RBAC（admin/user/viewer）+ 前端 Auth 系統 |
| Phase 6.2 | ✅ 完成 | 多使用者隔離：ChromaDB metadata 過濾 + user_id 穿透全鏈路 |
| Phase 6.3-6.4 | ⬜ 規劃 | Docker 部署、CI/CD |

### 下一步優先級

> 以下為尚未完成的任務，依建議優先順序排列。
> 已完成項目（Phase 1-5）詳見 `docs/TODO.md`。

1. **Phase 6.3** — Docker 部署
2. **Phase 6.4** — CI/CD

### 架構演進方向

```
Layer 3 應用層: 表單填寫 | Chat 問答 | 郵件草稿 | 報告生成 | ...
Layer 2 路由層: Intent Router (SQL_DB / VECTOR_DB / SKIP)
Layer 1 資料層: SQLite (結構化) + ChromaDB (向量) + File Watcher (自動索引)
```

每個新「應用」= 一組新的 service + router + 前端頁面，不需改動底層引擎。

### 規劃文件索引

| 文件 | 內容 | 何時讀 |
|------|------|--------|
| `docs/VISION.md` | 核心願景、定位、架構哲學、應用場景 | 理解「為什麼」 |
| `docs/ROADMAP.md` | 分階段技術藍圖、每階段詳細設計 | 理解「怎麼做」 |
| `docs/TODO.md` | 可追蹤的 checkbox 任務清單 | 理解「做什麼」 |
| `CLAUDE.md` (本文) | 開發慣例、架構約定、常見陷阱 | 每次開始前必讀 |

### 新 session 快速上手

1. 讀本文件 (`CLAUDE.md`) 了解架構約定
2. 讀 `docs/TODO.md` 找到下一個待辦任務
3. 如需理解設計背景，讀 `docs/VISION.md` 和 `docs/ROADMAP.md`
4. 開始開發前確認後端/前端能正常啟動（見上方「啟動方式」）
