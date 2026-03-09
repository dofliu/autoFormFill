# SmartFill-Scholar — 技術藍圖

> 最後更新：2026-03-09

## 總覽

```
Phase 1  ✅  後端 MVP          — FastAPI + SQLite + ChromaDB + Gemini
Phase 2  ✅  前端 MVP          — React 19 + TypeScript + Tailwind CSS
Phase 2.5 ⬜ 收尾補強          — 已知問題修補、測試補齊
Phase 3  ⬜  知識引擎基礎       — 自動索引、增量更新、Entity 泛化
Phase 4  ⬜  多輸出適配器       — Chat 問答、郵件草稿、報告生成
Phase 5  ⬜  智能化            — 知識圖譜、合規檢查、版本追蹤
Phase 6  ⬜  協作與部署         — 多使用者、權限、Docker、CI/CD
```

---

## Phase 2.5 — 收尾補強

> 目標：把目前的 MVP 穩定化，補齊已知缺漏

### 2.5.1 持久化 Job Store

**問題**：目前 `job_store.py` 是 in-memory dict，伺服器重啟就遺失。

**方案**：將 job 資料存入 SQLite（新增 `FormJob` ORM 模型）。

```
新增/修改檔案：
├── app/models/form_job.py          # FormJob ORM (job_id, user_id, filename, fields JSON, created_at)
├── app/services/job_service.py     # async CRUD for FormJob
├── app/job_store.py                # 改為呼叫 job_service（保持介面不變）
└── app/routers/forms.py            # 注入 db session
```

**驗證**：填寫表單 → 重啟伺服器 → `/forms/history/{user_id}` 仍然回傳歷史。

### 2.5.2 PDF 表單填寫

**問題**：目前只能解析 PDF 欄位，無法填寫輸出。

**方案**：使用 `pdfrw` 或 `PyMuPDF` 填寫 PDF widget。

```
修改檔案：
└── app/services/document_generator.py    # 新增 fill_pdf() 方法
```

### 2.5.3 測試補齊

**目標**：為尚未覆蓋的核心服務補齊單元測試。

```
新增檔案：
├── tests/test_form_parser.py
├── tests/test_intent_router.py    # mock LLM
├── tests/test_rag_pipeline.py     # mock LLM + ChromaDB
└── tests/test_document_generator.py
```

### 2.5.4 錯誤處理強化

- LLM 呼叫增加 retry（exponential backoff）
- 前端增加全域 error boundary
- API 統一 error response 格式

---

## Phase 3 — 知識引擎基礎 ⭐ 最高優先

> 目標：讓資料「自動流入」，不再依賴手動上傳
> 預估：2-3 週

### 3.1 資料夾監控 (File Watcher)

**做什麼**：指定一個或多個資料夾，系統在背景持續監控檔案變動。

**技術選型**：
- `watchdog` (Python) — 跨平台 filesystem watcher
- Background task 在 FastAPI lifespan 中啟動

**流程**：
```
資料夾變動偵測
    │
    ├── 新增檔案
    │   ├── 計算檔案 hash (SHA-256)
    │   ├── 解析文本（docx/pdf/txt/md/pptx/xlsx）
    │   ├── 切塊 + 嵌入 → ChromaDB
    │   └── 記錄 metadata → SQLite (FileIndex 表)
    │
    ├── 修改檔案
    │   ├── 比對 hash → 確認真的有改
    │   ├── 刪除舊 chunks (by doc_id)
    │   └── 重新解析 + 嵌入
    │
    └── 刪除檔案
        ├── 刪除對應 chunks
        └── 標記 FileIndex 為 deleted
```

```
新增/修改檔案：
├── app/models/file_index.py           # FileIndex ORM (path, hash, status, last_indexed, chunk_count)
├── app/services/file_watcher.py       # watchdog EventHandler + async queue
├── app/services/indexing_service.py    # 解析 + 切塊 + 嵌入 + FileIndex CRUD
├── app/config.py                      # 新增 WATCH_DIRS, WATCH_INTERVAL 設定
├── main.py                            # lifespan 中啟動 watcher background task
└── app/routers/indexing.py            # 手動觸發重新索引 / 查看索引狀態
```

**前端**：新增「索引狀態」頁面，顯示監控的資料夾、檔案數、最後索引時間。

**驗證**：
1. 設定監控 `~/Documents/papers/`
2. 放入一個 PDF → 系統自動索引 → 語意搜尋可以找到
3. 修改該 PDF → 系統偵測並重新索引
4. 刪除該 PDF → 對應 chunks 消失

### 3.2 增量索引 (Incremental Indexing)

**核心概念**：不要每次全部重建，只處理變動的部分。

```
FileIndex 表結構：
─────────────────────────────────────────────
id | file_path | file_hash | status      | chunks_count | last_indexed_at
1  | /papers/a.pdf | sha256:... | indexed   | 15          | 2026-03-09T10:00
2  | /papers/b.docx| sha256:... | pending   | 0           | null
3  | /papers/c.pdf | sha256:... | deleted   | 0           | 2026-03-08T15:00
```

**狀態機**：`pending` → `indexing` → `indexed` → `stale`(hash 變了) → `indexing` → `indexed`

### 3.3 多格式支援

目前只支援 `.docx` 和 `.pdf`。擴展：

| 格式 | 解析方式 | 優先級 |
|------|---------|--------|
| `.docx` | python-docx（已有） | ✅ |
| `.pdf` | pdfplumber + PyMuPDF（已有） | ✅ |
| `.txt` / `.md` | 直接讀取 | P0 |
| `.pptx` | python-pptx slide text | P1 |
| `.xlsx` | openpyxl cell values | P1 |
| `.html` | BeautifulSoup text extraction | P2 |

```
修改檔案：
└── app/services/document_service.py    # 新增 extract_text_from_* 方法
```

### 3.4 Entity 泛化

**問題**：目前 SQL 層只有 `UserProfile` + `EducationExperience`，太學術導向。

**方案**：抽象為 `Entity` + `EntityAttribute` 模式，讓使用者自訂結構。

```
目前：                          泛化後：
UserProfile                     Entity
├── name_zh                     ├── entity_type: "person" | "org" | "project"
├── name_en                     ├── name
├── title                       └── attributes: JSON
├── department                      ├── name_zh: "王小明"
└── ...                             ├── title: "教授"
                                    └── custom_field_1: "..."
```

**注意**：Phase 3 先做「旁邊加」而不是「替換掉」現有 UserProfile。新舊並存，Intent Router 自動判斷查哪個。

---

## Phase 4 — 多輸出適配器

> 目標：同一套知識庫，支援多種輸出方式
> 預估：2-3 週

### 4.1 知識問答 (Chat with Your Docs)

**架構**：新增 `/api/v1/chat` endpoint，streaming response。

```
使用者：「王教授去年發了幾篇論文？」
       ↓
  Intent Router: VECTOR_DB (搜尋 academic_papers collection)
       ↓
  RAG Pipeline: 檢索 → 生成回答
       ↓
  回傳：「根據知識庫中的記錄，王教授在 2025 年發表了 3 篇論文：...」
```

```
新增檔案：
├── app/services/chat_service.py      # 對話管理 + context window
├── app/routers/chat.py               # POST /api/v1/chat (streaming)
└── frontend/src/pages/ChatPage.tsx    # 對話 UI
```

**技術重點**：
- FastAPI `StreamingResponse` + Server-Sent Events
- 前端用 `EventSource` 或 `fetch` + `ReadableStream`
- 對話歷史保留最近 N 輪作為 context

### 4.2 郵件草稿生成

**架構**：給定情境描述 + 收件人資訊，從知識庫拉相關 context 生成信件。

```
新增檔案：
├── app/services/email_generator.py   # context retrieval + email template
├── app/routers/email.py              # POST /api/v1/email/draft
└── frontend/src/pages/EmailDraftPage.tsx
```

### 4.3 結構化報告生成

**架構**：給定報告大綱（或使用預設模板），逐段從知識庫填充內容。

```
新增檔案：
├── app/services/report_generator.py  # section-by-section generation
├── app/routers/reports.py            # POST /api/v1/reports/generate
└── frontend/src/pages/ReportPage.tsx
```

### 4.4 Output Adapter 抽象層

到 Phase 4 結束時，應該浮現一個共同模式：

```python
# app/adapters/base.py
class OutputAdapter(ABC):
    async def generate(self, query: str, context: list[str], template: str | None) -> str:
        ...

# app/adapters/form_adapter.py — 表單填寫
# app/adapters/chat_adapter.py — 問答
# app/adapters/email_adapter.py — 郵件
# app/adapters/report_adapter.py — 報告
```

---

## Phase 5 — 智能化

> 目標：從「被動查詢」進化到「主動洞察」
> 預估：3-4 週

### 5.1 知識圖譜 (Entity Relations)

在 Entity 之間建立關聯：

```
王教授 ──[作者]──→ 論文A
王教授 ──[主持人]──→ 計畫B
論文A  ──[引用]──→ 論文C
計畫B  ──[合作]──→ 李教授
```

**技術選型**：SQLite + 關聯表（不需要 Neo4j），或考慮 `NetworkX` 做 in-memory graph。

### 5.2 合規檢查

針對表單或文件，自動檢查是否符合規範：

```
規則引擎：
├── 必填欄位是否都填了？
├── 日期格式是否正確？
├── 字數限制是否超過？
└── 自訂規則（regex / LLM 判斷）
```

### 5.3 版本追蹤與差異比對

追蹤同一份文件的多個版本：

```
計畫書_v1.docx → v2.docx → v3.docx
           diff →     diff →
      「新增了第三章」  「修改了預算表」
```

### 5.4 智能提醒

基於知識庫內容主動提醒：

- 「你的 MOST 計畫書下個月到期」
- 「這份表單有 3 個欄位跟上次填的不一樣，要確認嗎？」

---

## Phase 6 — 協作與部署

> 目標：從個人工具變成可部署的產品
> 預估：4-6 週

### 6.1 認證與權限

- JWT-based 認證
- RBAC: admin / user / viewer
- API key 支援（讓外部系統呼叫）

### 6.2 多使用者

- 每個使用者獨立的知識庫（ChromaDB collection per user）
- 共享知識庫（組織級）
- 資料隔離

### 6.3 Docker 部署

```yaml
# docker-compose.yml
services:
  backend:
    build: .
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]
  frontend:
    build: ./frontend
    ports: ["3000:80"]
```

### 6.4 CI/CD

- GitHub Actions: lint + test + build on PR
- Auto deploy to staging on merge to main

---

## 技術決策記錄

| 決策 | 選擇 | 原因 | 替代方案 |
|------|------|------|---------|
| 向量資料庫 | ChromaDB | 輕量、本地、Python-native | Qdrant, Weaviate, Pinecone |
| SQL 資料庫 | SQLite | 零配置、單檔案、夠用 | PostgreSQL（Phase 6 考慮） |
| LLM | Gemini | 免費額度高、支援 JSON mode | OpenAI, Claude（adapter 可切換） |
| 前端 | React + Tailwind | 生態系最大、CSS utility-first | Vue, Svelte |
| 檔案監控 | watchdog | Python 跨平台標準 | inotify, polling |
| 任務佇列 | asyncio.Task | 輕量、不需額外 infra | Celery, Dramatiq（Phase 6 考慮） |

---

## 里程碑時間表（預估）

```
2026 Q1 (已完成)
  ✅ Phase 1: Backend MVP
  ✅ Phase 2: Frontend MVP

2026 Q2
  ⬜ Phase 2.5: 收尾補強 (1-2 週)
  ⬜ Phase 3: 知識引擎基礎 (2-3 週)
  ⬜ Phase 4.1: Chat 問答 (1 週)

2026 Q3
  ⬜ Phase 4.2-4.4: 郵件 + 報告 + Adapter 抽象 (2-3 週)
  ⬜ Phase 5.1-5.2: 知識圖譜 + 合規檢查 (3-4 週)

2026 Q4
  ⬜ Phase 5.3-5.4: 版本追蹤 + 智能提醒 (2-3 週)
  ⬜ Phase 6: 協作與部署 (4-6 週)
```

> 注：時間表為粗估，實際取決於開發時間投入。每個 Phase 完成後應重新評估優先級。
