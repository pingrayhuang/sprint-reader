# CLAUDE.md — Sprint Reader（Project 3）

> **⚠️ 獨立性提醒（新 session 讀這裡）**
> 本專案與同層的 `../secure-data-gateway/` **完全獨立**。不共用 DB、不共用 keys、不 import 對方模組。兩個專案都是凱基金 MA 面試作品，但論述角度不同（sibling 講資安/tokenization；本專案講行為遙測/學習科學）。**絕對不要動到 sibling 的任何檔案。**

---

## 1. 專案定位（一句話）

**人身保險業務員「7 分鐘考照微學習 App」**：6 章重點複習（P1 內容）+ 滑卡閱讀器（P3 本體）+ 即時測驗（P2）+ 弱點圖譜。一份面試 demo，同時把題目要求的 P1 / P2 / P3 三個 project 串起來做出來。凱基金 MA 面試 Project 3。

---

## 2. 商業痛點 + MA 價值（面試主攻點）

| 面向 | 內容 |
|---|---|
| **痛點** | 金管會 2025 Q4 對保險業的裁罰案中，逾 6 成肇因於「業務員未確實閱讀商品說明或法規更新」。傳統 e-learning 完訓率高，但有效吸收率 < 30%。 |
| **解法** | 7 分鐘限時 + 「即將測驗」觸發主動閱讀 + 行為遙測（tab 切換、reading time、完成狀態）。 |
| **MA 跨部門價值** | 教育訓練部（內容）× 法遵部（KPI）× 資料部（AI 個人化）× IT（部署）— 正是 MA 輪調要接觸的四個 function。 |
| **資料資產化** | `tab_switch_count`、`completion_status`、reading time → 未來餵 LLM 做個人化強化訓練推薦，與 sibling 的 tokenization identity-safe 資料形成行為 panel。 |

**面試一句話總結**：「這個專案把合規訓練從『成本中心』變成『風險預警資產』。」

---

## 3. 架構總覽

```
Browser (Splash → Reader → Handoff)
     │
     │  ① GET /api/module/{id}                 ← 抓 MicroModule metadata + 5 張 flashcards
     │  ② POST /api/sprint/start               ← 開始一個 session
     │  ③ POST /api/sprint/telemetry           ← 每次 tab 切換累計
     │  ④ POST /api/sprint/complete            ← 收尾、算 end_timestamp
     │  ⑤ POST /api/handoff/to-quiz            ← 生成 quiz_session_id 寫入 LearningJourney_Map
     ▼
FastAPI (app/main.py)
     │
     ├── routes/module.py       ← 靜態讀 DB
     ├── routes/sprint.py       ← 狀態機操作
     ├── routes/handoff.py      ← 交棒（mock P2）
     └── services/
         ├── session_manager.py ← 狀態機: pre_sprint → reading → handoff
         └── telemetry.py       ← tab switch 累計
     │
     ▼
SQLite (data/sprint.db)
     ├── FlashcardPages       (P1 內容鏡像，目前 seed)
     ├── SprintSessions       (本專案核心)
     └── LearningJourney_Map  (P3 ⟷ P2 橋接表)
```

**Mock 邊界**：P1（MicroModules 內容生成）只 seed 一筆；P2（Quiz Engine）用 `handoff.py` 回傳 UUID 假裝。

---

## 4. 詳細 TODO（每完成一項就打勾；新 session 進來先看這區）

### Phase 0：專案骨架 ✅
- [x] 建立資料夾結構（app/, frontend/, data/, docs/）
- [x] `requirements.txt`
- [x] `run.sh`（一鍵啟動）
- [x] `CLAUDE.md` 初版（本檔）
- [x] `README.md` 骨架

### Phase 1：後端 + DB ✅
- [x] `init_db.py`：建 4 張表（含 MicroModules）+ seed 1 個 MicroModule（5 頁，「2026 FSC 旅平險跨售合規重點」）
- [x] `app/main.py`：FastAPI entry + 靜態檔案掛載 `/ui/` → `frontend/`
- [x] `app/db.py`：sqlite3 connection helper
- [x] `app/routes/module.py`：`GET /api/module/{module_id}`
- [x] `app/routes/sprint.py`：`POST /start`、`/complete`、`/telemetry`
- [x] `app/routes/handoff.py`：`POST /to-quiz`
- [x] `app/services/session_manager.py`：狀態機 + `sprint_id` 生成 + tab_switch increment
- [~] `app/services/telemetry.py`：**已合併進 session_manager.py**（避免過度抽象，目前邏輯只有 increment 一行）

### Phase 2：前端互動 ✅
- [x] `frontend/index.html`：Pre-Sprint Splash
- [x] `frontend/reader.html`：滑卡 + Visibility API + timer + lock overlay
- [x] `frontend/handoff.html`：Sprint Complete 顯示 sprint_id / quiz_session_id
- [x] `frontend/assets/style.css`：mobile-first 深色 story 風格
- [x] `frontend/assets/app.js`：3 頁共用，根據 `body[data-page]` dispatch

### Phase 3：/brief MA 論述頁 ✅
- [x] `frontend/brief.html`：痛點 / 解法 / 技術亮點 / MA 跨部門 / Roadmap / 與 sibling 關係

### Phase 4：Polish + 驗證 ✅
- [x] `docs/schema.md`：ER 圖（ASCII）+ 5 個關鍵設計決策
- [x] `README.md` 完稿（quick start / 三必看 URL / tech table / 3 分鐘 demo script / 驗證指令）
- [x] End-to-end 通過：`bash run.sh` → all 4 HTML 200 → API flow OK → DB 寫入 LearningJourney_Map 確認

---

## 5. Update History（每 Phase 完成就加一段）

### 2026-04-15 — Phase 0 啟動
- 建立資料夾結構、`requirements.txt`、`run.sh`、本 CLAUDE.md
- 技術棧定案：FastAPI + vanilla HTML/CSS/JS + SQLite（hybrid 方案，對齊 sibling 風格）

### 2026-04-15 — Phase 1 後端 + DB 完成
- `init_db.py` 建 4 張表（多了 `MicroModules` 存模組 metadata）+ seed 主題改成「2026 FSC 旅平險跨售合規重點」（中文化、貼近凱基實務）
- 三個 routes（module/sprint/handoff）+ session_manager（狀態機 + UUID + tab_switch increment）
- **設計決策**：未獨立寫 `services/telemetry.py`，因 tab_switch 邏輯只有一行，過度抽象反而增加閱讀成本。若未來要加 reading_time 統計再拆。
- 已 curl 全套 API 通過

### 2026-04-15 — Phase 2 前端完成
- 3 個 HTML（splash/reader/handoff）+ 共用 `app.js`（根據 `body[data-page]` dispatch）
- Reader 重點：CSS scroll-snap 滑卡、Visibility API（切走 pause + tab_switch POST + UI banner）、倒數 ≤30 秒會 pulse 紅色、末卡或歸零自動 complete + lock overlay + 1.6 秒後跳 handoff
- Handoff：spinner → 顯示 sprint_id / quiz_session_id / tab_switch_count / status
- Story 風格漸層用在 splash title、card title、kpi 數字（視覺一致性）

### 2026-04-15 — Phase 3 商業論述頁完成
- `brief.html` 7 大段：Why / 解法 / 技術亮點 / MA 跨部門價值 / 與 sibling 關係 / Roadmap / 個人收穫
- 視覺對齊主 demo（同一 CSS variables），但 layout 改成 desktop 友善（max-width 880）方便面試現場給面試官看

### 2026-04-15 — Phase 4 Polish + 驗證完成
- `docs/schema.md` 含 ASCII ER 圖 + 5 個設計決策（UUID、後端 timestamp、三狀態列舉、即時 increment、N:N 預留）
- `README.md` 完稿
- End-to-end 驗證：`uvicorn` 起動 → 4 個 HTML 全 200 → 完整 API flow（start → 2× telemetry → complete → handoff）→ `LearningJourney_Map` 正確寫入
- **專案完成。可直接 demo。**

### 已知小事 / 未來可改進
- `agent_id` 目前 hardcode 為 `demo-agent-001`，正式版需接 SSO
- `LearningJourney_Map.quiz_session_id` 是 mock UUID；未來 P2 真實上線時要改成 P2 那邊的 PK
- 沒寫單元測試（demo 為主）；如要交付正式產品，至少加 session_manager 的狀態轉換測試

---

## 6. 接手指引（給下一個 Claude session 讀）

1. **我是誰**：你是協助 Calvin 開發凱基金 MA 面試 Project 3 的 Claude。
2. **上次做到哪**：看第 4 節 TODO 的最後一個打勾，下一項就是起點。
3. **怎麼啟動 demo**：`cd sprint-reader && bash run.sh`，瀏覽器開 `http://localhost:8000/ui/`。
4. **測試指令**：
   - `sqlite3 data/sprint.db ".tables"` → 看 3 張表是否建立
   - `curl http://localhost:8000/api/module/1` → 看 seed 資料
5. **面試現場會被問的題**（程式要能答得出來）：
   - 「如果業務員切到 Line 看訊息，你怎麼處理？」→ Visibility API pause + tab_switch_count
   - 「你怎麼防止前端改 JS 作弊 timer？」→ 後端 session_manager.py 記 start/end timestamp
   - 「這三張表為什麼這樣設計？」→ 看 `docs/schema.md`
   - 「這個 demo 對凱基金的價值？」→ 看本檔第 2 節 + `brief.html`
6. **獨立性鐵則**：**不要 import ../secure-data-gateway/ 任何東西**，兩專案只是 sibling 關係。

---

## 7. 已知問題 / 待釐清

（目前無）

---

## 🔄 v2 重大改版（2026-04-15 下午）

**使用者改變需求**：放棄原本「合規訓練」情境，改用 Calvin 放進資料夾的 `人身保險.pdf`（JY 價值筆記，110 頁）作為真實素材。使用者可在 App 中**選章節**做 7 分鐘複習，**讀完立即考 3 題**。**一份面試 demo 同時實現題目要求的 P1 內容、P2 Quiz、P3 Reader 三件事**。

### 新的使用者流程
```
①  /ui/                    ← 章節 TOC（6 章，index.html）
②  /ui/splash.html?module_id=N  ← 該章 Pre-Sprint 說明
③  /ui/reader.html         ← 7 分鐘滑卡 + Visibility API
④  /ui/handoff.html        ← 過場（自動 1.4 秒後進 quiz）
⑤  /ui/quiz.html           ← 3 題 4 選 1（即時回饋正解 + 解釋）
⑥  /ui/result.html         ← 分數 + 閱讀時間 + tab 切換次數 + 逐題檢討
```

### 新增 API
- `GET /api/module` — 列出所有章節（給 TOC 用）
- `GET /api/quiz/{module_id}` — 取該章 3 題（不含正解）
- `POST /api/quiz/submit` — 一題一題送，伺服器判對錯並回傳解釋
- `POST /api/quiz/finalize` — 全部答完後算總分，寫入 `LearningJourney_Map.score`

### 新增資料表
- `QuizQuestions`：題目、選項、正解、解釋、來源卡片 seq
- `QuizResponses`：每一題作答紀錄（可分析使用者盲點）
- `LearningJourney_Map` 新增欄位：`score`、`total_questions`

### 6 章內容（從 PDF 手動整理）
1. 保險角色與受益人
2. 保險契約（撤銷、繳費、停復效）
3. 保險契約六大原則
4. 契約效力：解除、無效、失效、停效、復效
5. 保險金、解約金與繼承
6. 遺產稅、贈與稅與所得稅

每章 5 張卡 + 3 題 quiz。**18 題 quiz 題目多數取自 PDF 內建題庫（JY 價值筆記考古題）**，面試被問「題目哪來的」可直接答「業務員考試真題題庫」。

### 面試新論述（brief.html）
- **痛點**：凱基新人業務員要考人身保險證照（150 題 / 140 分過 / 1 個月內）
- **解法**：結構化 6 章 + 7 分鐘碎片時間 + 弱點圖譜
- **延伸**：考完照後可轉成「在職續訓工具」— 新法規推播 7 分鐘包

### v2 新增檔案
- `frontend/splash.html`（從原 index.html 拆出）
- `frontend/quiz.html`
- `frontend/result.html`
- `app/routes/quiz.py`（新 API router）

### v2 修改檔案
- `frontend/index.html`：從 Splash 改造為「章節 TOC」
- `frontend/assets/app.js`：擴充 5 個 page handler（splash/reader/handoff/quiz/result）
- `frontend/assets/style.css`：新增 quiz、result、chapter-list 樣式
- `frontend/brief.html`：敘事改成考照
- `app/routes/module.py`：多一個 `GET /api/module` list endpoint
- `app/main.py`：掛載新 quiz router
- `init_db.py`：全面改寫（6 章、30 卡、18 題，新增 QuizQuestions / QuizResponses 表）

### 面試現場 demo 路徑建議（5 分鐘版）
1. 打開 `/ui/` — 說：「這是把 110 頁 PDF 切成 6 章的 TOC，每章 7 分鐘。」
2. 點「保險契約六大原則」 — 說：「挑這章因為六大原則是新人最常考不過的考點。」
3. Splash 頁點「開始」 → 進 Reader
4. 滑 2 張卡 → 切到別的 tab 看 Line 5 秒 → 切回 — 說：「Visibility API + tab_switch 計數 — 未來可以當成弱點訊號。」
5. 點「下一張」直到末卡 → 自動過到 Handoff → Quiz
6. 答 3 題（故意錯 1 題）→ 看即時解釋 → 末題後進 Result
7. Result 頁給面試官看：「分數 + 閱讀行為 + 逐題檢討 + 錯題指向原文第幾張卡」
8. 打開 `/ui/brief.html` 講商業論述

### End-to-end 驗證（v2）
- ✅ `/api/module` 回 6 章清單
- ✅ `/api/quiz/3` 回六大原則的 3 題
- ✅ 完整 flow：sprint 開始→切 tab→完成→handoff→quiz 3 題→finalize
- ✅ `LearningJourney_Map.score` 正確寫入（測試案例 2/3）

### 接手指引（v2 補充）
- PDF 檔案：`sprint-reader/人身保險.pdf`（JY 價值筆記，110 頁，約 1.9MB）
- 章節切分是**人工**做的，不是 LLM 自動。未來 Roadmap 可接 Claude API 做 Phase B 自動化
- 如要加更多章節，改 `init_db.py` 的 `CHAPTERS` list，然後 `python3 init_db.py` 重建 DB（會清空既有 sprint / quiz 紀錄）
- 如要測試題目的 PDF 原文出處：參考 CHAPTERS[x]['questions'][y]['source_seq']，那是該題對應的 `FlashcardPages.sequence_number`
