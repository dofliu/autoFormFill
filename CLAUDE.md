# CLAUDE.md — SmartFill-Scholar 專案指引

本文件為 Claude Code 的專案上下文指引，幫助 AI 助手快速理解專案架構與開發慣例。

## 專案概述

SmartFill-Scholar 是一套智能學術表單自動填寫系統，透過混合檢索（SQL + RAG）與 LLM 生成來自動填寫學術申請表單。

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
- **Job Store**：`app/job_store.py` 為 in-memory dict，暫存表單填寫結果供預覽/編輯
- **Pydantic Settings**：`app/config.py` 使用 `pydantic-settings` 從 `.env` 載入設定
- **ORM 模型註冊**：`main.py` 中必須 import 所有 ORM 模型，否則 `init_db()` 不會建表

### 前端

- **樣式系統**：只使用 Tailwind CSS，**不使用 MUI 或其他 UI 框架**
- **API 層**：`src/api/client.ts` 封裝 fetch，提供 `get/post/postForm/put/del/downloadUrl` 函式
- **postForm vs post**：`postForm()` 用於 FormData（multipart），`post()` 用於 JSON body
- **TypeScript 設定**：啟用 `erasableSyntaxOnly`，禁止 class constructor parameter properties（使用標準屬性宣告）
- **欄位色碼**：🟢 `sql` = green / 🟡 `rag` = amber / 🔴 `skip` = red / 🔵 `override` = blue
- **localStorage**：`smartfill_user_id` 儲存選取的使用者 ID

### 命名規則

- 後端：snake_case（Python 慣例）
- 前端：camelCase 變數、PascalCase 元件、kebab-case 檔名（元件除外用 PascalCase）
- API 回應欄位：snake_case（前後端一致）
- 中文 UI 文字直接寫在元件中

## 關鍵檔案

| 檔案 | 角色 |
|------|------|
| `main.py` | 應用進入點、CORS、路由註冊、lifespan |
| `app/services/form_filler.py` | 核心流程編排器（解析→路由→檢索→生成→輸出） |
| `app/services/intent_router.py` | LLM 欄位分類（SQL_DB / VECTOR_DB / SKIP） |
| `app/services/rag_pipeline.py` | 檢索 + 生成 + 幻覺防護迴圈 |
| `app/job_store.py` | 填寫任務 in-memory 暫存 |
| `frontend/src/api/client.ts` | HTTP 客戶端封裝 |
| `frontend/src/pages/FormPreviewPage.tsx` | 填寫結果審查與編輯 |
| `frontend/vite.config.ts` | Vite 設定（proxy、plugins） |

## API 路由總覽

```
GET    /health                                  健康檢查
POST   /api/v1/users/                           建立使用者
GET    /api/v1/users/                           列出使用者
GET    /api/v1/users/{id}                       使用者詳情
PUT    /api/v1/users/{id}                       更新使用者
DELETE /api/v1/users/{id}                       刪除使用者
GET    /api/v1/users/{id}/education/            學經歷列表
POST   /api/v1/users/{id}/education/            新增學經歷
DELETE /api/v1/users/{id}/education/{entry_id}  刪除學經歷
POST   /api/v1/documents/upload                 上傳文件（multipart）
GET    /api/v1/documents/search                 語意搜尋
POST   /api/v1/forms/parse                      解析表單欄位
POST   /api/v1/forms/fill                       智能填寫（multipart）
GET    /api/v1/forms/download/{filename}        下載填寫結果
GET    /api/v1/forms/preview/{job_id}           填寫預覽
POST   /api/v1/forms/submit                     提交修改（JSON）
GET    /api/v1/forms/history/{user_id}          填寫歷史
```

## 常見陷阱

1. **ChromaDB 是同步的**：所有 ChromaDB 呼叫必須包在 `await asyncio.to_thread(...)` 中
2. **ORM 模型必須先 import**：`main.py` 中 `from app.models import ...` 確保 `Base.metadata` 有表定義
3. **FormData vs JSON**：前端上傳檔案用 `postForm()`（不設 Content-Type），JSON payload 用 `post()`
4. **erasableSyntaxOnly**：TypeScript class 不能用 `constructor(public x: number)`，要用 `x: number; constructor(x) { this.x = x; }`
5. **`[需人工補充]`**：RAG/SQL 無法填寫的欄位會以此標記，前端以紅色顯示
6. **Port 衝突**：Vite 若偵測 5173 被占用會自動跳 5174，CORS 已設定兩個 port

## 測試

```bash
# 後端測試
python -m pytest tests/ -v

# 前端型別檢查
cd frontend && npx tsc --noEmit

# 前端生產建置（含型別檢查）
cd frontend && npm run build
```

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
