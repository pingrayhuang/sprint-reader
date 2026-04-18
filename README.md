# Sprint Reader 🏃‍♂️📖

> **凱基金 MA 面試 Project 3** — 7 分鐘限時微學習，把合規訓練從「成本中心」變成「風險預警資產」。

## 🔗 Live Demo

| | 連結 |
|---|---|
| **主 Demo** | https://rayhuang.pythonanywhere.com/ui/ |
| **商業論述** | https://rayhuang.pythonanywhere.com/ui/brief.html |
| **資料模型** | https://rayhuang.pythonanywhere.com/ui/architecture-data-model.html |

## Quick Start

```bash
bash run.sh
```

開瀏覽器：`http://localhost:8000/ui/`

第一次執行會自動建 venv、裝套件、建 DB。約 30 秒後 server 啟動。

## 三個必看 URL

| URL | 用途 |
|---|---|
| `http://localhost:8000/ui/` | Demo 起點（Pre-Sprint Splash） |
| `http://localhost:8000/ui/brief.html` | 完整商業論述 |
| `http://localhost:8000/docs` | FastAPI 自動產生的 API 文件 |

## What it solves

金管會 2025 Q4 對保險業逾 6 成裁罰案來自「業務員未確實閱讀法規／商品說明」。傳統 e-learning 完訓率高、有效吸收率 < 30%。

**Sprint Reader 的不同**：
- ⏱ **7 分鐘限時** — 業務員碎片時間就能完訓
- 🎯 **「即將測驗」觸發** — 從被動瀏覽轉成主動閱讀（Active Reading Mode）
- 📊 **行為遙測** — `tab_switch_count`、reading time、completion_status，餵 AI 做個人化推薦

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI | 與 sibling `secure-data-gateway` 對齊；自帶 OpenAPI |
| DB | SQLite × 1 | demo 易啟動、schema 清晰、4 張表夠用 |
| Frontend | Vanilla HTML/CSS/JS | 無 build step、無 framework、快速啟動零摩擦 |
| Timer | Browser Visibility API + 後端 timestamp | UX 自然 + 防前端竄改 |

## 資料夾結構

```
sprint-reader/
├── CLAUDE.md                    ← 開發進度紀錄（跨 session 接續用）
├── README.md                    ← 你正在讀的這份
├── run.sh                       ← 一鍵啟動
├── requirements.txt
├── init_db.py                   ← 建表 + seed mock MicroModule
├── app/
│   ├── main.py                  ← FastAPI entry + /ui 靜態掛載
│   ├── db.py                    ← sqlite3 connection helper
│   ├── routes/
│   │   ├── module.py            ← GET /api/module/{id}
│   │   ├── sprint.py            ← POST /api/sprint/{start,telemetry,complete}
│   │   └── handoff.py           ← POST /api/handoff/to-quiz（mock P2）
│   └── services/
│       └── session_manager.py   ← 狀態機 + sprint_id 生成 + tab_switch
├── frontend/
│   ├── index.html               ← Pre-Sprint Splash
│   ├── reader.html              ← 滑卡 + 計時器 + Visibility API
│   ├── handoff.html             ← Time's Up 交接畫面
│   ├── brief.html               ← 商業論述頁
│   └── assets/
│       ├── style.css
│       └── app.js
├── data/
│   └── sprint.db                ← 啟動後生成
└── docs/
    └── schema.md                ← ER 圖 + 設計決策
```

## 3 分鐘現場 Demo Script

| 步驟 | 操作 | 講點 |
|---|---|---|
| ① | 開 `/ui/` Splash | 「7 分鐘 / 5 卡 / 3 題 quiz — 設計時就告訴使用者規則，觸發 Active Reading」 |
| ② | 點「開始 7 分鐘 Sprint」 | 「Server 端產生 sprint_id（UUID）並蓋 start_timestamp」 |
| ③ | 滑兩張卡 | 「mobile-first，CSS scroll-snap，無 framework」 |
| ④ | **切到別的 tab，停 5 秒** | 「Visibility API 觸發 — timer 暫停、tab_switch_count POST 到後端。這是核心遙測訊號」 |
| ⑤ | 切回，看 timer 從原處接續 | 「業務員的真實使用情境就是會被 Line 打斷，我們不該懲罰他，但要記錄」 |
| ⑥ | 點「下一張」直到末卡 | 「滑到末卡 → 自動 complete」 |
| ⑦ | Handoff 頁顯示 sprint_id + quiz_session_id | 「LearningJourney_Map 現在有一筆 record，未來 P2 quiz 結果可以 join 回來」 |
| ⑧ | 開 `/ui/brief.html` | 「跨部門價值、Roadmap、技術亮點」 |

## End-to-end 驗證

```bash
# 1. 看三張表都建立
sqlite3 data/sprint.db ".tables"

# 2. 看 seed 資料
sqlite3 data/sprint.db "SELECT module_id, title FROM MicroModules;"

# 3. 跑完一個 sprint 後，看橋接表
sqlite3 data/sprint.db "SELECT * FROM LearningJourney_Map;"

# 4. 看 tab 切換次數
sqlite3 data/sprint.db "SELECT sprint_id, tab_switch_count, completion_status FROM SprintSessions;"
```

## 與 sibling `secure-data-gateway` 的關係

兩個專案完全獨立（不同 DB、不同 venv、不共用模組），但敘事上互補：

- **secure-data-gateway**：保證使用者敏感資訊在 LLM 流程中被 tokenization、不外洩
- **sprint-reader**（本專案）：在 identity-safe 前提下，收集員工學習行為，為 AI 個人化推薦鋪路

詳細論述見 `frontend/brief.html`。

---

開發進度與接手指引：見 [`CLAUDE.md`](CLAUDE.md)
