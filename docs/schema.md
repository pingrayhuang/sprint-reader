# DB Schema — Sprint Reader

## ER 圖（ASCII）

```
┌─────────────────────┐         ┌──────────────────────┐
│   MicroModules      │         │   FlashcardPages     │
│─────────────────────│  1   N  │──────────────────────│
│ module_id (PK)      ├────────<│ page_id (PK)         │
│ title               │         │ module_id (FK)       │
│ source_doc          │         │ sequence_number      │
│ domain_tags (JSON)  │         │ page_content_json    │
│ duration_sec        │         └──────────────────────┘
│ page_count          │
│ quiz_count          │
└──────────┬──────────┘
           │
           │ 1
           │
           N
┌──────────┴──────────┐         ┌──────────────────────┐
│   SprintSessions    │  1   N  │   LearningJourney_   │
│─────────────────────├────────<│        Map           │
│ sprint_id (PK,UUID) │         │──────────────────────│
│ agent_id            │         │ journey_id (PK)      │
│ module_id (FK)      │         │ sprint_id (FK)       │
│ start_timestamp     │         │ quiz_session_id      │  ← P2 (mock)
│ end_timestamp       │         │ created_at           │
│ tab_switch_count    │         └──────────────────────┘
│ completion_status   │
└─────────────────────┘
```

## 為什麼這樣設計？三表分離 = 三種使用者

| 表 | 主要使用者 | 目的 |
|---|---|---|
| `MicroModules` + `FlashcardPages` | **教育訓練部** | 內容版本控管。`page_content_json` 用 JSON 而非欄位化，是因為內容形態多變（文字、highlight、未來可加圖片），讓內容團隊更新內容時不需 schema migration。 |
| `SprintSessions` | **法遵部** | 稽核軌跡。每個 session 都有 `sprint_id`（UUID 不連號，避免被推測）+ 完整 timestamps + `tab_switch_count`，可作為「業務員確實閱讀過」的法律證據。 |
| `LearningJourney_Map` | **資料部 / AI** | 把 P3 閱讀行為與 P2 測驗結果關聯，是訓練「個人化合規 AI」的核心資料表。 |

## 關鍵設計決策

### 1. `sprint_id` 用 UUID v4，不用 auto-increment
**Why**：保護隱私 — 若用流水號，可從 `sprint_id` 推測「公司今天有多少業務員上線」這類敏感資訊。UUID 不可枚舉。

### 2. `start_timestamp` 與 `end_timestamp` 由後端蓋章
**Why**：防作弊。前端 timer 純展示，所有時間戳由 `app/services/session_manager.py` 在伺服器端產生。即使業務員修改瀏覽器時間或 JS，也無法偽造完訓時間。

### 3. `completion_status` 列舉三種狀態
- `finished_early`：在限時內主動完成（理想路徑）
- `timed_out`：被倒數歸零強制結束（仍視為完訓，但行為訊號較差）
- `abandoned`：中途離開（透過 `beforeunload` + `sendBeacon` 回報，best-effort）

**Why**：未來資料分析時，這三類別行為意義完全不同，不能混為一談。

### 4. `tab_switch_count` 即時 increment
**Why**：不批次寫入是因為 — 業務員可能切走後直接關 tab，若批次寫入會掉資料。每次 visibilitychange 都馬上 POST，雖犧牲一點效能，但保證稽核完整性。

### 5. `LearningJourney_Map` 為什麼獨立成表，不直接放欄位在 `SprintSessions`？
**Why**：未來一個 sprint 可能對應多個 quiz attempt（重考機制）。表分離為 N:N 預留空間，避免日後 schema migration。

## 與 sibling `secure-data-gateway` 的關係

兩個 DB **物理隔離**：
- `secure-data-gateway/data/{vault,audit,analytics}/` — 處理客戶 PII tokenization
- `sprint-reader/data/sprint.db` — 處理員工學習行為

**不共用任何表、不互相 import**。但敘事上互補：sibling 確保「資料安全」，本專案在資料安全的前提下，利用行為資料為 AI 鋪路。
