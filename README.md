# Sprint Reader

> 7 分鐘微學習 App — 利用零碎時間複習人身保險考照重點，透過「即將測驗」機制強化主動閱讀與認知留存。

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
| `http://localhost:8000/ui/` | Demo 起點（章節選擇） |
| `http://localhost:8000/ui/brief.html` | 完整商業論述 |
| `http://localhost:8000/docs` | FastAPI 自動產生的 API 文件 |

## What it solves

傳統保險考照備考方式以大量 PDF 與長時間集中複習為主，但業務員日常難以空出完整時間，導致學習斷斷續續、遺忘率高。

**Sprint Reader 的設計邏輯**：
- ⏱ **7 分鐘限時** — 通勤、等候的零碎時間就能完成一章複習
- 🎯 **「即將測驗」觸發** — 每章閱讀完立即接 3 題 quiz，強迫主動提取記憶（Active Recall）
- 🔁 **間隔重複推薦** — 根據答錯率與距上次複習天數，推薦優先複習的章節
- 📊 **行為遙測** — 記錄 `tab_switch_count`、閱讀時間、完成狀態，作為個人弱點分析基礎

## 資料庫設計（SQLite）

共 9 張表，分三個層次：

| 分類 | 資料表 | 用途 |
|---|---|---|
| **核心** | `FlashcardPages` | 6 章 × 5 張閱讀卡內容 |
| **核心** | `SprintSessions` | 每次 7 分鐘閱讀的行為紀錄（timer、tab 切換、完成狀態） |
| **核心** | `LearningJourney_Map` | 閱讀 session 與 quiz session 的橋接表，記錄最終分數 |
| **Quiz** | `QuizQuestions` | 6 章 × 3 題，含選項、正解、解釋 |
| **Quiz** | `QuizResponses` | 每題作答紀錄，可分析使用者盲點 |
| **推薦** | `ChapterMastery` | 每章答對率 + 距上次複習天數，驅動推薦邏輯 |
| **推薦** | `ReviewEvents` | 每次間隔重複推薦的觸發紀錄 |
| **支援** | `MicroModules` | 章節 metadata（標題、卡片數、預估時間） |
| **支援** | `Agents` | 系統 agent 設定（預留 AI 推薦擴充用） |

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI | 自帶 OpenAPI 文件；async 架構好擴充 |
| DB | SQLite | demo 易啟動、schema 清晰、零依賴 |
| Frontend | Vanilla HTML/CSS/JS | 無 build step、無 framework、快速啟動零摩擦 |
| Timer | Browser Visibility API + 後端 timestamp | UX 自然 + 防前端竄改 |

## 資料夾結構

```
sprint-reader/
├── run.sh                       ← 一鍵啟動
├── requirements.txt
├── init_db.py                   ← 建表 + seed 6 章內容與題庫
├── app/
│   ├── main.py                  ← FastAPI entry + /ui 靜態掛載
│   ├── db.py                    ← sqlite3 connection helper
│   ├── routes/
│   │   ├── module.py            ← GET /api/module, GET /api/module/{id}
│   │   ├── sprint.py            ← POST /api/sprint/{start,telemetry,complete}
│   │   ├── quiz.py              ← GET /api/quiz/{module_id}, POST /api/quiz/submit, /finalize
│   │   └── handoff.py           ← POST /api/handoff/to-quiz
│   └── services/
│       └── session_manager.py   ← 狀態機 + sprint_id 生成 + tab_switch
├── frontend/
│   ├── index.html               ← 章節選擇 TOC
│   ├── splash.html              ← Pre-Sprint 說明頁
│   ├── reader.html              ← 滑卡 + 計時器 + Visibility API
│   ├── handoff.html             ← 閱讀完成過場
│   ├── quiz.html                ← 3 題即時測驗
│   ├── result.html              ← 分數 + 逐題檢討
│   ├── brief.html               ← 商業論述頁
│   └── assets/
│       ├── style.css
│       └── app.js
├── data/
│   └── sprint.db                ← 啟動後生成
└── docs/
    └── schema.md                ← ER 圖 + 設計決策
```

## End-to-end 驗證

```bash
# 看所有表是否建立
sqlite3 data/sprint.db ".tables"

# 看章節清單
sqlite3 data/sprint.db "SELECT module_id, title FROM MicroModules;"

# 跑完一個 sprint 後，看橋接表
sqlite3 data/sprint.db "SELECT * FROM LearningJourney_Map;"

# 看 tab 切換次數與完成狀態
sqlite3 data/sprint.db "SELECT sprint_id, tab_switch_count, completion_status FROM SprintSessions;"

# 看各章掌握度
sqlite3 data/sprint.db "SELECT * FROM ChapterMastery;"
```

---

Ray Huang · Project 3 of 3
