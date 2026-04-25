# Sprint Reader — 7 分鐘保險考照微學習 App

> 利用零碎時間複習人身保險考照重點，透過「即將測驗」機制強化主動閱讀與認知留存。

## 🔗 Live Demo

| | 連結 |
|---|---|
| **主 Demo** | https://rayhuang.pythonanywhere.com/ui/ |
| **商業論述** | https://rayhuang.pythonanywhere.com/ui/brief.html |
| **投影片簡報** | https://rayhuang.pythonanywhere.com/ui/pitch.html |

---

## 畫面預覽

![章節選擇頁](docs/screenshots/01-index.png)

**左側儀表板**
- 整體完成度、連續學習天數、累計 Sprint 次數、總答對率
- **今日推薦**：根據「答錯率 × log(距上次複習天數 + 1)」自動推算最需複習的章節
- **錯題複習**：匯集所有答錯紀錄，一鍵進入專項練習

**右側章節卡（6 章）**
- 每章顯示閱讀進度條、完成次數與該章答對率
- 點任一章節 → 7 分鐘閱讀衝刺 → 3 題即時測驗 → 分數 + 逐題解釋 + 原文卡片回溯

---

## 解決的問題

保險業務員備考時間有限，傳統 PDF 複習方式難以持續。**Sprint Reader** 把 110 頁考照筆記切成 6 章，每章 7 分鐘，讀完立即接 3 題測驗，強迫主動提取記憶。

**核心設計**：
- **7 分鐘限時閱讀** — 通勤、等候的零碎時間就能完成一章
- **即時 Quiz** — 每章閱讀後立即測驗 3 題，搭配解釋與原文卡片回溯
- **間隔重複推薦** — 根據答錯率與距上次複習天數，自動推薦優先章節
- **行為遙測** — 記錄 `tab_switch_count`、閱讀時間、完成狀態，建立個人弱點圖譜
- **Server-authoritative timer** — 所有 timestamp 由後端蓋章，防止前端竄改

---

## Quick Start

```bash
bash run.sh
```

開瀏覽器：`http://localhost:8000/ui/`

第一次執行會自動建 venv、裝套件、建 DB，約 30 秒後啟動。無需額外設定環境變數或外部服務。

---

## API 文件

FastAPI 自動產出 Swagger 文件：`http://localhost:8000/docs`

| Method | Endpoint | 說明 |
|---|---|---|
| `GET` | `/api/module` | 列出全部 6 章節 metadata（標題、卡片數、預估時間） |
| `GET` | `/api/module/{id}` | 取得指定章節 + 5 張閱讀卡完整內容 |
| `POST` | `/api/sprint/start` | 開始一次 Sprint，後端記錄 start_timestamp，回傳 sprint_id |
| `POST` | `/api/sprint/telemetry` | 記錄一次 tab 切換事件（tab_switch_count + 1） |
| `POST` | `/api/sprint/complete` | 結束 Sprint，記錄 end_timestamp，狀態機轉為 handoff |
| `GET` | `/api/quiz/{module_id}` | 取得該章 3 題測驗題目（不含正解，防止前端作弊） |
| `POST` | `/api/quiz/submit` | 提交單題作答，回傳是否正確 + 解釋 + source_seq 原文索引 |
| `POST` | `/api/quiz/finalize` | 計算最終分數，寫入 LearningJourney_Map，更新 ChapterMastery |

---

## 5 分鐘 Demo 腳本

| 步驟 | 操作 | 說明重點 |
|---|---|---|
| 1 | 打開 `/ui/` | 左側儀表板：今日推薦算法、連續學習天數、整體答對率 |
| 2 | 點「保險契約六大原則」 | 此章是新人最常考不過的考點；右側顯示該章歷史答對率 |
| 3 | Splash 頁 → 開始衝刺 | Pre-Sprint 說明：「即將測驗」觸發主動閱讀，非被動瀏覽 |
| 4 | 閱讀中切到別的 Tab 5 秒 | 計時器自動暫停；切回後無縫接續；後端 tab_switch_count + 1 |
| 5 | 滑完末卡 → 自動進 Quiz | Handoff 狀態機觸發；展示 sprint_id 與 quiz_session_id 橋接 |
| 6 | 答 3 題（故意錯 1 題）| 即時解釋 + 原文卡片回溯（source_seq 連結）|
| 7 | Result 頁 | 本次分數、閱讀時間、分心次數、逐題檢討全部匯整 |
| 8 | 打開 `/ui/brief.html` | 商業論述；適合讓面試官快速掌握產品定位與 MA 跨部門價值 |

---

## Tech Stack

| Layer | 選擇 | 設計理由 |
|---|---|---|
| Backend | FastAPI | 自帶 Swagger 文件；async 架構易擴充；型別驗證減少 bug |
| DB | SQLite | 零外部依賴、一鍵啟動、schema 清晰；企業導入無需額外基礎設施 |
| Frontend | Vanilla HTML/CSS/JS | 無 build step、無 framework、瀏覽器直接打開即可 demo |
| Timer | Browser Visibility API + 後端 timestamp | UX 自然（切走暫停）+ 防前端竄改（timestamp 由 server 蓋章）|
| 推薦算法 | 規則式 `wrong_rate × log(days+1)` | 可解釋性高、易 debug；收集足夠數據後可升級 RL |

---

## 資料庫設計（9 張表）

三層職責分離，對應三個不同部門的使用者：

| 分類 | 資料表 | 使用部門 | 用途 |
|---|---|---|---|
| 核心 | `FlashcardPages` | 教育訓練部 | 6 章 × 5 張閱讀卡內容，版本可控 |
| 核心 | `SprintSessions` | 法遵部 | 每次閱讀行為紀錄（timer、tab 切換），可稽核 |
| 核心 | `LearningJourney_Map` | 資料部 | 閱讀與測驗橋接表，記錄最終分數，供 AI 訓練 |
| 測驗 | `QuizQuestions` | 教育訓練部 | 6 章 × 3 題，含選項、正解、解釋 |
| 測驗 | `QuizResponses` | 資料部 | 每題作答紀錄，分析個人盲點 |
| 推薦 | `ChapterMastery` | 資料部 | 每章答對率 + 距上次複習天數，驅動推薦 |
| 推薦 | `ReviewEvents` | 資料部 | 每次推薦事件觸發紀錄 |
| 支援 | `MicroModules` | 教育訓練部 | 章節 metadata（標題、卡片數、預估時間） |
| 支援 | `Agents` | IT | 系統 agent 設定（預留 AI 推薦擴充） |

---

## 快速驗證指令

```bash
# 確認 DB 建立
sqlite3 data/sprint.db ".tables"

# 確認 seed 資料
curl http://localhost:8000/api/module
curl http://localhost:8000/api/quiz/3        # 六大原則 3 題

# 完整 Sprint → Quiz flow
SPRINT=$(curl -s -X POST http://localhost:8000/api/sprint/start \
  -H "Content-Type: application/json" \
  -d '{"module_id": 3, "agent_id": "demo-agent-001"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['sprint_id'])")

curl -s -X POST http://localhost:8000/api/sprint/telemetry \
  -H "Content-Type: application/json" \
  -d "{\"sprint_id\": \"$SPRINT\"}"

curl -s -X POST http://localhost:8000/api/sprint/complete \
  -H "Content-Type: application/json" \
  -d "{\"sprint_id\": \"$SPRINT\"}"

# 確認 LearningJourney_Map 寫入
sqlite3 data/sprint.db "SELECT * FROM LearningJourney_Map ORDER BY id DESC LIMIT 1;"
```

---

## 資料夾結構

```
sprint-reader/
├── run.sh
├── init_db.py                   ← 建表 + seed 6 章內容與題庫（30 張卡 + 18 題）
├── app/
│   ├── main.py                  ← FastAPI entry + 靜態檔案掛載 /ui/
│   ├── db.py                    ← SQLite connection helper
│   ├── routes/
│   │   ├── module.py            ← GET /api/module, /api/module/{id}
│   │   ├── sprint.py            ← POST /api/sprint/{start,telemetry,complete}
│   │   ├── quiz.py              ← GET /api/quiz/{id}, POST /api/quiz/{submit,finalize}
│   │   └── handoff.py          ← Sprint → Quiz 狀態橋接
│   └── services/
│       └── session_manager.py   ← 狀態機（pre_sprint → reading → handoff）+ tab_switch
├── frontend/
│   ├── index.html               ← 章節選擇 + 今日推薦儀表板
│   ├── splash.html              ← Pre-Sprint 說明頁
│   ├── reader.html              ← 滑卡 + 計時器 + Visibility API
│   ├── quiz.html                ← 即時測驗
│   ├── result.html              ← 分數 + 逐題檢討
│   ├── brief.html               ← 商業論述
│   ├── pitch.html               ← 面試簡報（13 張投影片）
│   └── assets/
│       ├── style.css
│       └── app.js
└── docs/
    ├── schema.md                ← ER 圖 + 5 個設計決策
    └── screenshots/
```

---

Ray Huang · Project 3 of 3
