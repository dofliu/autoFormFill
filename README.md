# SmartFill-Scholar 智能學術表單填寫系統

自動填寫學術表單的全端應用程式。系統透過 SQL 資料庫查詢使用者靜態資料，並結合 RAG（Retrieval-Augmented Generation）從知識庫中擷取複雜欄位內容，最終由 LLM 生成填寫結果。

## 功能特色

- **表單解析**：支援 `.docx` 模板變數（`{{variable}}`）與 PDF 表單欄位自動偵測
- **智能欄位路由**：LLM 自動判斷每個欄位應從 SQL 資料庫或向量知識庫擷取
- **混合檢索填寫**：靜態資料（姓名、職稱等）走 SQL，複雜內容（研究摘要等）走 RAG
- **幻覺防護**：RAG 生成結果自動比對原始文件，偵測並修正幻覺內容
- **色彩標記審查**：填寫結果以色碼分類（🟢SQL / 🟡RAG / 🔴需人工 / 🔵手動覆寫）
- **表單歷史紀錄**：記錄每次填寫結果，支援回顧與重新編輯
- **知識庫管理**：上傳學術論文與研究計畫，建立語意搜尋索引

## 技術架構

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│   React 19 + TypeScript + Tailwind CSS v4       │
│   Vite 7 dev server (proxy → :8000)             │
├─────────────────────────────────────────────────┤
│                   Backend                        │
│   FastAPI + async SQLAlchemy + aiosqlite        │
├──────────────────┬──────────────────────────────┤
│   SQLite (SQL)   │   ChromaDB (Vector)          │
│   使用者資料      │   學術論文 / 研究計畫         │
├──────────────────┴──────────────────────────────┤
│              Google Gemini API                   │
│   text generation / JSON output / embeddings    │
└─────────────────────────────────────────────────┘
```

### 後端 (Python)

| 技術 | 用途 |
|------|------|
| FastAPI | 非同步 Web 框架 |
| SQLAlchemy 2.0 + aiosqlite | 非同步 ORM / SQLite |
| ChromaDB | 向量資料庫（PersistentClient） |
| Google Gemini API | 文字生成、JSON 結構化輸出、文本嵌入 |
| docxtpl / python-docx | Word 模板填寫 |
| PyMuPDF / pdfplumber | PDF 解析 |

### 前端 (TypeScript)

| 技術 | 用途 |
|------|------|
| React 19 | UI 框架 |
| TypeScript 5.9 | 型別安全 |
| Tailwind CSS v4 | 樣式系統 |
| Vite 7 | 建置工具與開發伺服器 |
| React Router v7 | 路由管理 |

## 快速開始

### 前置需求

- Python 3.11+
- Node.js 20+
- Google Gemini API Key（[取得方式](https://aistudio.google.com/apikey)）

### 1. 環境設定

```bash
# 複製專案
git clone <repo-url>
cd autoFill

# 建立 Python 虛擬環境
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 安裝後端依賴
pip install -r requirements.txt

# 安裝前端依賴
cd frontend && npm install && cd ..
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入你的 Gemini API Key：

```env
GEMINI_API_KEY=your-actual-gemini-api-key
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
DATABASE_URL=sqlite+aiosqlite:///./data/smartfill.db
CHROMA_PERSIST_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
OUTPUT_DIR=./data/outputs
```

### 3. 啟動服務

```bash
# Terminal 1 — 後端 (port 8000)
python -m uvicorn main:app --reload

# Terminal 2 — 前端 (port 5173)
cd frontend && npm run dev
```

### 4. 開始使用

- 前端 UI：http://localhost:5173
- API 文件（Swagger）：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

## 專案結構

```
autoFill/
├── main.py                          # FastAPI 應用進入點
├── requirements.txt                 # Python 依賴
├── .env.example                     # 環境變數範本
├── .gitignore
│
├── app/
│   ├── config.py                    # pydantic-settings 設定
│   ├── database.py                  # 非同步 SQLAlchemy 引擎
│   ├── vector_store.py              # ChromaDB 客戶端
│   ├── job_store.py                 # 表單填寫任務暫存（in-memory）
│   │
│   ├── models/                      # ORM 模型
│   │   ├── user_profile.py
│   │   └── education_experience.py
│   │
│   ├── schemas/                     # Pydantic 請求/回應模型
│   │   ├── user_profile.py
│   │   ├── education_experience.py
│   │   ├── document.py
│   │   └── form.py
│   │
│   ├── routers/                     # API 路由
│   │   ├── user_profiles.py         # /api/v1/users
│   │   ├── education_experience.py  # /api/v1/users/{id}/education
│   │   ├── documents.py             # /api/v1/documents
│   │   └── forms.py                 # /api/v1/forms
│   │
│   ├── services/                    # 業務邏輯
│   │   ├── user_service.py          # 使用者 CRUD
│   │   ├── education_service.py     # 學經歷 CRUD
│   │   ├── document_service.py      # 文件上傳、切塊、嵌入
│   │   ├── form_parser.py           # 表單欄位偵測
│   │   ├── intent_router.py         # LLM 欄位分類
│   │   ├── rag_pipeline.py          # 檢索 + 生成 + 幻覺防護
│   │   ├── form_filler.py           # 完整填寫流程編排
│   │   └── document_generator.py    # docx 模板渲染
│   │
│   ├── llm/                         # LLM 適配器
│   │   ├── base.py                  # 抽象基底類別
│   │   ├── gemini_adapter.py        # Gemini 實作
│   │   └── factory.py               # 工廠模式（依 .env 切換）
│   │
│   └── utils/
│       ├── chunker.py               # 文本切塊
│       └── file_utils.py            # 檔案處理
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts               # Vite + React + Tailwind + API proxy
│   ├── tsconfig.app.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx                  # React DOM 進入點
│       ├── App.tsx                   # 路由設定（5 頁面）
│       ├── index.css                 # Tailwind 匯入
│       │
│       ├── api/                      # 型別化 API 客戶端
│       │   ├── client.ts             # fetch 封裝 + 錯誤處理
│       │   ├── users.ts
│       │   ├── education.ts
│       │   ├── documents.ts
│       │   └── forms.ts
│       │
│       ├── types/                    # TypeScript 介面定義
│       │   ├── user.ts
│       │   ├── education.ts
│       │   ├── document.ts
│       │   └── form.ts
│       │
│       ├── pages/
│       │   ├── FormFillPage.tsx      # 表單上傳 → 導向預覽
│       │   ├── FormPreviewPage.tsx   # 欄位審查與編輯
│       │   ├── FormHistoryPage.tsx   # 填寫歷史紀錄
│       │   ├── UserProfilePage.tsx   # 使用者資料管理
│       │   └── KnowledgeBasePage.tsx # 知識庫上傳與搜尋
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx      # 主要佈局（Sidebar + Outlet）
│       │   │   └── Sidebar.tsx       # 導覽列
│       │   └── form-fill/
│       │       ├── FormUploadStep.tsx # 檔案上傳區
│       │       ├── FieldReviewPanel.tsx # 分割檢視面板
│       │       └── FilledFieldCard.tsx  # 色碼欄位卡片
│       │
│       └── utils/
│           ├── cn.ts                 # class name 合併
│           └── formatters.ts         # 來源標籤、色碼、信心度
│
├── data/                             # 執行時產生（已 gitignore）
│   ├── smartfill.db                  # SQLite 資料庫
│   ├── chroma/                       # ChromaDB 向量資料
│   ├── uploads/                      # 上傳暫存
│   └── outputs/                      # 填寫結果
│
└── tests/
    ├── test_form_history.py
    ├── test_form_preview.py
    └── test_frontend_preview.py
```

## API 端點

### 使用者

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/v1/users/` | 列出所有使用者 |
| POST | `/api/v1/users/` | 建立使用者 |
| GET | `/api/v1/users/{id}` | 取得使用者詳情 |
| PUT | `/api/v1/users/{id}` | 更新使用者 |
| DELETE | `/api/v1/users/{id}` | 刪除使用者 |

### 學經歷

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/v1/users/{id}/education/` | 列出使用者學經歷 |
| POST | `/api/v1/users/{id}/education/` | 新增學經歷 |
| DELETE | `/api/v1/users/{id}/education/{entry_id}` | 刪除學經歷 |

### 文件

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/documents/upload` | 上傳文件（multipart） |
| GET | `/api/v1/documents/search` | 語意搜尋 |

### 表單

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/forms/parse` | 解析表單欄位（multipart） |
| POST | `/api/v1/forms/fill` | 智能填寫（multipart: file + user_id） |
| GET | `/api/v1/forms/download/{filename}` | 下載填寫結果 |
| GET | `/api/v1/forms/preview/{job_id}` | 取得填寫預覽 |
| POST | `/api/v1/forms/submit` | 提交修改後的表單（JSON） |
| GET | `/api/v1/forms/history/{user_id}` | 使用者填寫歷史 |

## 核心流程

```
使用者上傳表單 (.docx/.pdf)
        │
        ▼
  ① 表單解析 (form_parser)
     偵測 {{variable}} 或 PDF widget
        │
        ▼
  ② 意圖路由 (intent_router)
     LLM 分類每個欄位 → SQL_DB / VECTOR_DB / SKIP
        │
        ├── SQL_DB → 查詢 UserProfile / EducationExperience
        │
        ├── VECTOR_DB → ③ RAG 流程 (rag_pipeline)
        │   ├── ChromaDB 語意檢索
        │   ├── Gemini 生成答案
        │   └── 幻覺防護 + 自修正迴圈
        │
        └── SKIP → 標記 [需人工補充]
        │
        ▼
  ④ 文件生成 (document_generator)
     docxtpl 渲染 → 輸出填寫完成的文件
        │
        ▼
  ⑤ 結果審查 (前端 FormPreviewPage)
     色碼標記、信心度、手動編輯 → 確認提交
```

## 開發指令

```bash
# 後端
python -m uvicorn main:app --reload           # 開發伺服器
python -m pytest tests/ -v                     # 執行測試

# 前端
cd frontend
npm run dev                                    # Vite 開發伺服器
npm run build                                  # TypeScript 檢查 + 生產建置
npm run lint                                   # ESLint 檢查
npx tsc --noEmit                               # 僅型別檢查
```

## 設計決策

- **ChromaDB sync → async**：ChromaDB 為同步 API，所有呼叫透過 `asyncio.to_thread()` 包裝，避免阻塞 FastAPI 事件迴圈
- **LLM Adapter Pattern**：抽象基底類別 + 工廠模式，可透過 `.env` 的 `LLM_PROVIDER` 切換不同 LLM 供應商
- **`[需人工補充]`**：資料不足時的預設填充標記，前端以紅色標示提醒使用者
- **Job Store**：表單填寫結果以 in-memory 方式暫存，支援預覽、編輯、重新提交流程
- **docxtpl**：處理 Word 模板中變數可能被拆分到多個 XML run 的問題，比純 regex 替換更可靠

## 授權

MIT License
