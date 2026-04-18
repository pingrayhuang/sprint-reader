"""Initialize SQLite DB.

Schema:
  - MicroModules     : one row per chapter (mock P1 output)
  - FlashcardPages   : 5 cards per chapter
  - QuizQuestions    : 3 MCQ per chapter (mock P2 content)
  - SprintSessions   : reading telemetry (P3 core)
  - QuizResponses    : answer submissions
  - LearningJourney_Map : P3 ↔ P2 bridge

Seed data: 6 chapters extracted from 人身保險.pdf (JY 價值筆記, 人身保險業務員證照).
All cards are manually curated summaries of the PDF content.
Quiz questions are real past-exam questions copied from the PDF's own 題庫 section.
"""
import sqlite3
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "sprint.db"
DB_PATH.parent.mkdir(exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS MicroModules (
    module_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL,
    source_doc     TEXT    NOT NULL,
    domain_tags    TEXT    NOT NULL,
    description    TEXT    NOT NULL,
    duration_sec   INTEGER NOT NULL DEFAULT 420,
    page_count     INTEGER NOT NULL DEFAULT 5,
    quiz_count     INTEGER NOT NULL DEFAULT 3,
    sort_order     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS FlashcardPages (
    page_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id         INTEGER NOT NULL,
    sequence_number   INTEGER NOT NULL,
    page_content_json TEXT    NOT NULL,
    UNIQUE (module_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS QuizQuestions (
    question_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id        INTEGER NOT NULL,
    sequence_number  INTEGER NOT NULL,
    stem             TEXT    NOT NULL,
    options_json     TEXT    NOT NULL,
    correct_index    INTEGER NOT NULL,
    explanation      TEXT,
    source_page_seq  INTEGER,
    UNIQUE (module_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS SprintSessions (
    sprint_id         TEXT    PRIMARY KEY,
    agent_id          TEXT    NOT NULL,
    module_id         INTEGER NOT NULL,
    start_timestamp   TEXT    NOT NULL,
    end_timestamp     TEXT,
    tab_switch_count  INTEGER DEFAULT 0,
    completion_status TEXT    DEFAULT 'in_progress'
);

CREATE TABLE IF NOT EXISTS QuizResponses (
    response_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_session_id  TEXT    NOT NULL,
    question_id      INTEGER NOT NULL,
    chosen_index     INTEGER NOT NULL,
    is_correct       INTEGER NOT NULL,
    answered_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS LearningJourney_Map (
    journey_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id        TEXT    NOT NULL,
    quiz_session_id  TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    score            INTEGER,
    total_questions  INTEGER,
    FOREIGN KEY (sprint_id) REFERENCES SprintSessions(sprint_id)
);
"""

CHAPTERS = [
    {
        "title": "保險角色與受益人",
        "description": "保險人、要保人、被保險人、受益人 — 誰是誰、誰有什麼權利。",
        "tags": ["#保險法規", "#基本概念"],
        "pages": [
            {
                "title": "契約當事人 vs. 關係人",
                "body": "保險人（保險公司）與要保人（付錢的人）是契約的「當事人」；被保險人與受益人是「關係人」。要保人繳保費、保險人負賠償責任。主管機關為金管會。",
                "highlight": "記住：當事人＝保險人＋要保人。",
            },
            {
                "title": "要保人的權利義務",
                "body": "權利：申請契約變更、指定／變更受益人（需被保險人書面同意）、申請保單借款或自動墊繳、終止契約、行使撤銷權。義務：繳保險費、告知、通知。",
                "highlight": "要保人最重要的權利 = 終止契約、申領解約金。",
            },
            {
                "title": "受益人五大規定",
                "body": "1. 無人數限制。2. 可透過約定／指定／法定產生。3. 以請求保險金時仍生存者為限（胎兒以將來非死產者為限）。4. 有疑義時推定要保人為受益人。5. 未指定死亡受益人時，保險金視為被保險人遺產。",
                "highlight": "「殘廢、醫療、年金」保險金限給被保險人本人，不得指定他人。",
            },
            {
                "title": "行為能力與契約效力",
                "body": "未滿 7 歲或意思表示時精神錯亂者無行為能力，所簽契約無效。限制行為能力者（7–20 歲未婚者）簽訂人身保險契約，須經法定代理人事前允許、事後承認，或限制原因消滅後自己承認，始生效力。",
                "highlight": "未成年人「已結婚」屬於有行為能力人。",
            },
            {
                "title": "代理人 vs. 經紀人",
                "body": "保險代理人：代表保險公司、向保險人收取費用。保險經紀人：站在被保險人立場、代客戶向保險公司洽訂契約，向客戶收取佣金。兩者立場完全相反。",
                "highlight": "口訣：代理人＝幫公司、經紀人＝幫客戶。",
            },
        ],
        "questions": [
            {"stem": "人壽保險契約的「當事人」是指下列何者？", "options": ["保險人及受益人","被保險人及受益人","要保人及保險人","保險人及被保險人"], "correct": 2, "explanation": "契約當事人是『出錢的』跟『收錢的』，即要保人與保險人。被保險人與受益人屬於契約關係人。", "source_seq": 1},
            {"stem": "下列何者不是限制行為能力人訂定保險契約之生效方式？", "options": ["於限制原因消滅後自己承認","經其法定代理人事後承認","經其法定代理人事前允許","經被保險人同意"], "correct": 3, "explanation": "限制行為能力者訂約生效方式只有三種：法代事前允許、事後承認、限制原因消滅後本人承認。被保險人同意不算。", "source_seq": 4},
            {"stem": "按我國保險法規定，受益人有疑義時，推定誰為受益人？", "options": ["被保險人之法定繼承人","要保人","被保險人","以上皆可"], "correct": 1, "explanation": "保險法推定『要保人為自己利益而訂立』，故推定要保人為受益人。", "source_seq": 3},
            {"stem": "人壽保險契約的告知義務人是下列何者？", "options": ["要保人及受益人","要保人","被保險人","要保人及被保險人"], "correct": 3, "explanation": "告知義務人為要保人及被保險人，兩者對投保事項均須據實告知。", "source_seq": 2},
            {"stem": "何人具有向保險公司請求終止契約、領回解約金之權利？", "options": ["被保險人","要保人","受益人","保險人"], "correct": 1, "explanation": "終止契約、領解約金屬於要保人的權利，因為要保人是繳保費的人。", "source_seq": 2},
            {"stem": "保險經紀人係基於何者之利益，代向保險公司洽訂保險契約或提供服務而收取佣金？", "options": ["要保人","保險人","承保的保險業","被保險人"], "correct": 3, "explanation": "經紀人站在被保險人立場為其利益洽訂契約；代理人則是代表保險公司。", "source_seq": 5},
            {"stem": "受益人的產生方式包括下列何者？A.約定 B.指定 C.法定", "options": ["僅A","僅B","ABC","僅AB"], "correct": 2, "explanation": "受益人可透過約定、指定、法定三種方式產生，這是保險法第 110 條與 113 條的規定。", "source_seq": 3},
            {"stem": "下列何者得為保險契約的受益人？A.自然人 B.法人 C.胎兒（以將來非死產者為限）", "options": ["僅A","AB","BC","ABC"], "correct": 3, "explanation": "自然人、法人、胎兒（非死產者）均可為受益人。", "source_seq": 3},
            {"stem": "要保人對下列何者具有保險利益？", "options": ["本人或其家屬","生活費或教育費所仰給之人","債務人","以上皆是"], "correct": 3, "explanation": "保險法第 16 條：要保人對本人或家屬、生活費或教育費所仰給之人、債務人、為本人管理財產或利益之人均有保險利益。", "source_seq": 1},
            {"stem": "以下關於行為能力何者為非？", "options": ["未滿 7 歲者無行為能力","未滿 7 歲之未成年人須由法代代為意思","滿 7 歲以上未成年人為限制行為能力","未成年人已結婚者仍為限制行為能力"], "correct": 3, "explanation": "未成年人已結婚者屬於『有行為能力人』，此為保險法與民法重點。", "source_seq": 4},
        ],
    },
    {
        "title": "保險契約（撤銷、繳費、停復效）",
        "description": "契約怎麼開始、怎麼撤銷、繳不出保費怎麼辦。",
        "tags": ["#保險法規", "#契約實務"],
        "pages": [
            {
                "title": "契約撤銷權：10 天猶豫期",
                "body": "要保人可在收到保險單翌日起 10 日內，親自或書面向保險人撤銷契約，不需任何理由。撤銷效力自書面到達翌日零時起，契約自始無效。體檢與否都可撤銷。",
                "highlight": "10 天猶豫期是要保人最重要的保護機制。",
            },
            {
                "title": "誰可以繳保費？",
                "body": "不是只有要保人能繳。被保險人、受益人、信託業都可代繳。長期險（人壽、年金）不得訴訟請求交付保費；短期險（傷害、健康）可以訴訟請求。",
                "highlight": "長期險繳不出來 → 停效；不會被告。",
            },
            {
                "title": "保單展期 vs. 減額繳清",
                "body": "兩者都用保單價值準備金處理繳不出保費的困境。保單展期：保額不變、保險期間縮短。減額繳清：保險期間不變、保險金額減少。要保人依需求二選一。",
                "highlight": "展期保期限縮短、繳清保額縮水 — 選錯賠不到。",
            },
            {
                "title": "自動墊繳與催告",
                "body": "自動墊繳：從保單價值準備金借錢繳保費。催告後逾 30 日未繳，契約停效。季／月繳不催告，自應繳日翌日起 30 日內為寬限期；半年／年繳需催告，催告到達翌日起 30 日內為寬限期。",
                "highlight": "月繳逾期 → 直接停效；年繳逾期 → 先催告。",
            },
            {
                "title": "停效與復效（最常考！）",
                "body": "申請復效期間：自停效日起至少 2 年內。停效 6 個月內：清償欠繳保費＋利息後翌日零時起復效。停效 6 個月後：需保險公司同意，可要求可保證明。復效期限屆滿前至少 3 個月，保險公司須通知要保人有復效權利。",
                "highlight": "記住關鍵數字：2 年申請期 / 6 個月是分水嶺 / 3 個月通知義務。",
            },
        ],
        "questions": [
            {"stem": "人壽保險契約的撤銷權，要保人應於收到保單後幾日內行使？", "options": ["7 日","10 日","14 日","30 日"], "correct": 1, "explanation": "保險法規定要保人收到保單「翌日起 10 日內」可撤銷契約。", "source_seq": 1},
            {"stem": "保戶使用「保單展期」處理繳不出保費的情形，下列何者正確？", "options": ["保險期間不變、保額減少","保額不變、保險期間縮短","保額與保險期間皆減少","保額增加、保險期間縮短"], "correct": 1, "explanation": "保單展期 = 保額不變，但保險期間縮短，展延期不得超過原契約滿期日。", "source_seq": 3},
            {"stem": "保險契約停效後，要保人申請復效的期間，自保單停效日起至少不得少於？", "options": ["6 個月","1 年","2 年","3 年"], "correct": 2, "explanation": "保險公司給保戶申請復效的期間，自停效日起不得低於 2 年。", "source_seq": 5},
            {"stem": "契約撤銷的效力，自要保人書面意思表示到達保險公司何時起生效？", "options": ["當日零時","送達當時立刻","翌日零時","下月 1 日"], "correct": 2, "explanation": "現行示範條款規定：撤銷效力自書面意思表示到達翌日零時起生效，該契約自始無效。", "source_seq": 1},
            {"stem": "減額繳清保險的特性為何？", "options": ["保額不變、保險期間縮短","保額減少、保險期間縮短","保額減少、保險期間不變","保額與期間皆不變"], "correct": 2, "explanation": "減額繳清保險：保險金額減少、保險期間不變。與展期定期保險（保額不變、期間縮短）相對。", "source_seq": 3},
            {"stem": "半年繳或年繳保費逾期未繳，寬限期間起算日為？", "options": ["應繳日當日","應繳日翌日","催告到達當日","催告到達翌日"], "correct": 3, "explanation": "半年繳與年繳需先催告，寬限期自催告到達翌日起 30 日。月繳季繳則不催告，自應繳日翌日起算。", "source_seq": 4},
            {"stem": "保險契約停效日起 6 個月內申請復效，需具備何種條件？", "options": ["需重新體檢核保","清償欠費及利息後翌日零時起復效","需保險公司另行同意","無法復效"], "correct": 1, "explanation": "停效 6 個月內申請復效僅需清償欠費及利息，翌日零時起即恢復效力，不需另外核保。", "source_seq": 5},
            {"stem": "復效期限屆滿前多久，保險公司須以書面等方式通知要保人復效權利？", "options": ["1 個月","2 個月","3 個月","6 個月"], "correct": 2, "explanation": "復效期滿前至少 3 個月，保險公司須通知要保人申請復效的權利。", "source_seq": 5},
            {"stem": "保險費自動墊繳的利息計算基準為？", "options": ["銀行短期放款利率","保險公司公告利率","主管機關核定利率","國庫券利率"], "correct": 1, "explanation": "自動墊繳保險費的利息依保險公司當時公告的利率計算。", "source_seq": 4},
            {"stem": "下列何者不可代要保人繳交保險費？", "options": ["被保險人","受益人","信託業","保險業務員"], "correct": 3, "explanation": "被保險人、受益人、信託業皆可代繳保費；業務員不屬於法定可代繳人。", "source_seq": 2},
        ],
    },
    {
        "title": "保險契約六大原則",
        "description": "保險利益、最大誠信、主力近因、損害填補、分攤、代位 — 金融證照必考。",
        "tags": ["#保險法規", "#六大原則"],
        "pages": [
            {
                "title": "保險利益原則",
                "body": "存在目的：避免賭博行為、防止道德風險。要保人對下列對象具有保險利益：①本人或家屬 ②生活費／教育費所仰給之人 ③債務人 ④為本人管理財產或利益之人。",
                "highlight": "債權人對債務人有保險利益，反之不必然。",
            },
            {
                "title": "最大誠信原則",
                "body": "要保人若有隱匿或不實告知，造成保險人對危險的估計有所影響時，保險人得解除契約。訂約時要保人或被保險人已知保險事故發生者，契約無效。",
                "highlight": "告知不實 = 保險公司可解約、拒賠。",
            },
            {
                "title": "主力近因原則",
                "body": "導致被保險人死亡或受傷的「最主要、最有效」原因，而非最接近的原因。當死亡原因有 2 個以上且彼此有因果關係時，最先發生且造成一連串事故的才是主力近因。",
                "highlight": "注意：是「最主要」不是「最接近」— 容易考錯。",
            },
            {
                "title": "損害填補 & 分攤原則",
                "body": "損害填補：讓被保險人經濟上恰能恢復至事故前情況，不得因保險而獲利。分攤原則：重複投保時，各保險人按比例分攤理賠。兩原則「原則上只適用產險」，例外：實支實付型健康保險適用。",
                "highlight": "人壽保險以生命為標的 → 無法估價 → 不適用此兩原則。",
            },
            {
                "title": "保險代位原則",
                "body": "保險人給付理賠後，可直接向加害第三人求償。保險法第 103 條：人壽保險不得代位行使請求權；健康、傷害、年金保險亦同。因此「代位原則僅適用於財產保險」。",
                "highlight": "人身保險四兄弟（壽／健／傷／年）都不適用代位。",
            },
        ],
        "questions": [
            {"stem": "關於保險代位原則，下列敘述何者正確？", "options": ["適用於人壽保險","適用於健康保險","僅適用於財產保險","適用於所有保險"], "correct": 2, "explanation": "保險法第 103 條明定人壽保險不得代位；健康、傷害、年金亦同。故僅適用財產保險。", "source_seq": 5},
            {"stem": "保險利益原則的主要存在目的為何？", "options": ["增加保險公司收益","方便理賠計算","避免賭博行為、防止道德危險","簡化核保流程"], "correct": 2, "explanation": "保險利益原則是為了避免把保險變成賭博工具，並防止道德風險發生。", "source_seq": 1},
            {"stem": "下列何者「不」適用損害填補原則？", "options": ["汽車險","火險","實支實付健康保險","人壽保險"], "correct": 3, "explanation": "損害填補原則原則上只適用產險，例外為實支實付健康保險。人壽保險因標的為生命，無法估價，不適用。", "source_seq": 4},
            {"stem": "訂約時要保人已知保險事故已發生，該契約效力為？", "options": ["有效","保險人得解除契約","契約無效","由法院判決"], "correct": 2, "explanation": "最大誠信原則下，訂約時事故已發生者契約無效（保險法第 51 條）。", "source_seq": 2},
            {"stem": "主力近因原則是指？", "options": ["最接近被保險人死亡的原因","最主要或最有效導致事故的原因","最後發生的原因","首先被送醫的原因"], "correct": 1, "explanation": "主力近因 = 最主要、最有效導致事故的原因，不是最接近的原因，容易考錯。", "source_seq": 3},
            {"stem": "要保人對於下列何者「不」具有保險利益？", "options": ["本人或家屬","生活費仰給之人","路人甲","債務人"], "correct": 2, "explanation": "對毫無利害關係的路人無保險利益；否則會變成賭博行為。", "source_seq": 1},
            {"stem": "分攤原則（攤派原則）主要適用於哪一類保險？", "options": ["人壽保險","年金保險","財產保險及實支實付型健康保險","傷害保險"], "correct": 2, "explanation": "分攤原則由損害填補原則衍生，原則上適用於財產保險，例外為實支實付型健康保險。", "source_seq": 4},
            {"stem": "要保人如有所隱匿造成保險人對危險估計有所影響時，保險人得？", "options": ["無任何處置","解除契約","僅調整保費","通知主管機關"], "correct": 1, "explanation": "最大誠信原則：隱匿或不實告知影響危險估計時，保險人得解除契約。", "source_seq": 2},
            {"stem": "保險法第 103 條規定，下列何種保險不得代位行使請求權？", "options": ["火險","人壽、健康、傷害、年金保險","汽車險","海上保險"], "correct": 1, "explanation": "保險法 103 條明定人身四類保險（壽、健、傷、年）皆不得代位。", "source_seq": 5},
            {"stem": "債權人對債務人是否有保險利益？", "options": ["沒有","有","依金額大小決定","僅限 100 萬以上"], "correct": 1, "explanation": "債權人對債務人有保險利益；反之則不必然成立。", "source_seq": 1},
        ],
    },
    {
        "title": "契約效力：解除、無效、失效、停效、復效",
        "description": "五種效力狀態的差異 — 最容易搞混的考點。",
        "tags": ["#保險法規", "#契約效力"],
        "pages": [
            {
                "title": "解除：保險公司說了算",
                "body": "保險公司（保險人）有契約解除權。效力自始不存在。自保險人知有解除原因後 1 個月內、或自契約開始日起經過 2 年不行使而告消滅。典型情境：要保人告知不實被抓包。",
                "highlight": "解除權行使期限：知悉後 1 個月 / 契約起 2 年。",
            },
            {
                "title": "無效：從一開始就不算",
                "body": "屬於自始無效：由第三人訂立的「死亡保險」契約；以精神障礙或心智缺陷者為被保險人投保人壽／傷害保險（除喪葬費用外，其餘死亡給付無效）。",
                "highlight": "失公平、違反平等互惠 → 契約無效。",
            },
            {
                "title": "失效 vs. 停效",
                "body": "失效：原本有效的契約因特定事由（如對保險標的物無保險利益），自原因發生時起失去效力。停效：契約暫時停止效力（如逾期未繳保費）。停效可復效，失效通常不可。",
                "highlight": "停效是暫停、失效是陣亡。",
            },
            {
                "title": "復效的兩段時間",
                "body": "停效日起 6 個月內：清償欠費＋利息，翌日零時起復效。6 個月後：需保險公司同意，得要求可保證明（5 天內提交），除非危險程度重大變更至拒絕承保。保險公司須於復效期屆滿前 3 個月以書面／電子郵件／簡訊通知。",
                "highlight": "6 個月是分水嶺：內部從寬、外部從嚴。",
            },
            {
                "title": "失蹤與死亡宣告",
                "body": "失蹤滿 7 年 → 宣告死亡。80 歲以上失蹤滿 3 年 → 宣告死亡。遭遇特別災難者，災難終了滿 1 年 → 宣告死亡。二人以上同時遇難不能證明先後時，推定同時死亡，相互不繼承。",
                "highlight": "7 / 3 / 1 年 — 與年齡、災難有關的差別。",
            },
        ],
        "questions": [
            {"stem": "保險公司行使契約解除權，應於知有解除原因後多久內行使？", "options": ["1 個月","3 個月","6 個月","1 年"], "correct": 0, "explanation": "自保險人知有解除原因後 1 個月內不行使而消滅（另自契約起算 2 年也會消滅）。", "source_seq": 1},
            {"stem": "被保險人於停效期間辦理復效，停效日起 6 個月內申請者，復效條件為？", "options": ["需保險公司同意並提交可保證明","清償欠繳保費及利息即可復效","需重新核保","無法復效"], "correct": 1, "explanation": "停效 6 個月內申請復效，只要清償欠費＋利息，翌日零時起即恢復效力。", "source_seq": 4},
            {"stem": "失蹤人為 80 歲以上者，失蹤滿幾年後可宣告死亡？", "options": ["1 年","3 年","5 年","7 年"], "correct": 1, "explanation": "一般人失蹤滿 7 年宣告死亡；80 歲以上縮短為 3 年；遭遇特別災難者災後 1 年即可。", "source_seq": 5},
            {"stem": "契約『解除』的法律效果為何？", "options": ["自解除日起失效","契約效力自始不存在","暫停效力","視為不作為"], "correct": 1, "explanation": "解除 = 溯及自始無效，契約效力自始不存在。", "source_seq": 1},
            {"stem": "下列何者屬於保險契約『自始無效』的情況？", "options": ["逾期未繳保費","由第三人訂立的死亡保險契約（未經被保險人書面承認）","要保人住所變更","保險金額不足"], "correct": 1, "explanation": "第三人為他人投保死亡保險須經被保險人書面同意，否則契約無效。", "source_seq": 2},
            {"stem": "投保年齡錯誤於事故發生後才被發現且為溢繳，保險公司如何處理？", "options": ["全額退還溢繳保費","按比例提高保險金額，不退還溢繳部分","依原金額給付","契約無效"], "correct": 1, "explanation": "事故發生後發現投保年齡錯誤且溢繳者：按原保費與應繳保費比例提高保險金額，不退還溢繳部分。", "source_seq": 4},
            {"stem": "下列何者為『失效』（非停效）的典型情況？", "options": ["月繳逾期未繳","對保險標的物無保險利益","要保人住所變更","被保險人出國"], "correct": 1, "explanation": "失效是原本有效的契約因特定事由（如對標的物無保險利益）自原因發生時起失效。", "source_seq": 3},
            {"stem": "遭遇特別災難而失蹤者，於特別災難終了滿幾年後可宣告死亡？", "options": ["1 年","3 年","5 年","7 年"], "correct": 0, "explanation": "遭遇特別災難終了滿 1 年即可宣告死亡（加速宣告）。", "source_seq": 5},
            {"stem": "二人以上同時遇難而不能證明死亡先後時，法律推定為？", "options": ["年長者先死亡","年幼者先死亡","同時死亡，相互不繼承","待法院認定"], "correct": 2, "explanation": "推定同時死亡 → 相互不繼承，這是民法第 11 條的規定。", "source_seq": 5},
            {"stem": "保險人行使契約解除權的最長期限，自契約開始日起算為？", "options": ["1 年","2 年","3 年","5 年"], "correct": 1, "explanation": "自契約開始日起經過 2 年不行使即告消滅（除斥期間）。", "source_seq": 1},
        ],
    },
    {
        "title": "保險金、解約金與繼承",
        "description": "保險金怎麼付、解約金怎麼算、保險金跟遺產的關係。",
        "tags": ["#保險法規", "#給付實務"],
        "pages": [
            {
                "title": "保險金給付期限",
                "body": "事故發生後申請保險金：保險人接到通知後 15 日內給付。超過要付遲延利息（年利一分）。解約金：要保人已付足 1 年以上保費後可解約，保險人應於接到通知後 1 個月內給付，金額不得少於應得保單價值準備金之 3/4。",
                "highlight": "15 日給付保險金、1 個月給付解約金、3/4 是最低門檻。",
            },
            {
                "title": "除外責任：四種不賠情況",
                "body": "①要保人故意致被保險人於死 ②被保險人故意自殺或自成失能 ③被保險人因犯罪處死 ④拒捕或越獄致死。上述情況免給付保險金，但契約累積有保單價值準備金者，依約給付保單價值準備金予應得之人。",
                "highlight": "故意 = 不賠，但保價金仍會返還。",
            },
            {
                "title": "未成年被保險人的特別限制",
                "body": "被保險人未滿 15 歲：死亡給付於滿 15 歲時才生效力。滿 15 歲前死亡者，僅給付喪葬費用，且金額不得超過遺產稅喪葬費扣除額（123 萬）的一半，即 61.5 萬。",
                "highlight": "未滿 15 歲死亡 → 頂多賠 61.5 萬。",
            },
            {
                "title": "保險金 vs. 遺產",
                "body": "死亡保險金「未指定受益人」→ 視為被保險人遺產，需課遺產稅。「已指定受益人」→ 不計入遺產，但要保人與被保險人非同一人時仍可能有稅務問題。被保險人與受益人同時死亡 → 保險金為被保險人遺產。",
                "highlight": "指定受益人 = 節稅；未指定 = 併入遺產。",
            },
            {
                "title": "繼承與拋棄繼承",
                "body": "胎兒為繼承人時，非保留其應繼分，其他繼承人不得分割遺產。拋棄繼承：知悉得繼承之時起 3 個月內，以書面向法院為之。拋棄後應以書面通知因其拋棄而應為繼承之人。",
                "highlight": "拋棄繼承關鍵字：3 個月內、書面、向法院。",
            },
        ],
        "questions": [
            {"stem": "保險事故發生後，保險人接到通知後應於幾日內給付保險金？", "options": ["7 日","15 日","30 日","1 個月"], "correct": 1, "explanation": "保險人接到通知後 15 日內給付保險金；逾期要付遲延利息年利一分。", "source_seq": 1},
            {"stem": "被保險人為未滿 15 歲之未成年人者，若於滿 15 歲前死亡，保險公司：", "options": ["全額給付身故保險金","僅給付喪葬費用，不得超過遺產稅扣除額的一半","給付保單價值準備金","不賠任何費用"], "correct": 1, "explanation": "保險法第 107 條：未滿 15 歲前死亡者僅給付喪葬費用，且不得超過遺產稅喪葬費扣除額（123 萬）的一半即 61.5 萬。", "source_seq": 3},
            {"stem": "拋棄繼承應於知悉得繼承之時起幾個月內以書面向法院為之？", "options": ["1 個月","2 個月","3 個月","6 個月"], "correct": 2, "explanation": "拋棄繼承期限為知悉得繼承時起 3 個月內，以書面向法院提出。", "source_seq": 5},
            {"stem": "要保人已付足幾年以上保費後可申請終止契約、領取解約金？", "options": ["半年","1 年","2 年","3 年"], "correct": 1, "explanation": "付足 1 年以上保費即可解約，解約金不得少於保單價值準備金之 3/4。", "source_seq": 1},
            {"stem": "解約金金額不得少於要保人應得保單價值準備金之幾分之幾？", "options": ["1/2","2/3","3/4","全數"], "correct": 2, "explanation": "解約金不得少於應得保單價值準備金之 3/4。", "source_seq": 1},
            {"stem": "下列何種情況保險公司『免』給付保險金（但應返還保單價值準備金）？", "options": ["被保險人疾病身故","被保險人意外身故","要保人故意致被保險人於死","被保險人自然老死"], "correct": 2, "explanation": "要保人故意致被保險人於死屬除外責任，免給付保險金但應返還保單價值準備金予應得之人。", "source_seq": 2},
            {"stem": "死亡保險金未指定受益人時，保險金如何處理？", "options": ["由保險公司保留","視為要保人遺產","視為被保險人遺產","由法院分配"], "correct": 2, "explanation": "未指定受益人 → 保險金視為被保險人遺產，須課徵遺產稅。", "source_seq": 4},
            {"stem": "超過保險金給付期限，保險公司應付遲延利息，利率為？", "options": ["年利 5%","年利一分（10%）","市場利率","銀行定存利率"], "correct": 1, "explanation": "接到通知後 15 日內未給付者，要付年利一分（10%）遲延利息。", "source_seq": 1},
            {"stem": "胎兒為繼承人時，其他繼承人分割遺產須？", "options": ["可直接分割不予保留","保留其應繼分才能分割","完全不能分割","由法院裁定"], "correct": 1, "explanation": "胎兒為繼承人時，非保留其應繼分，其他繼承人不得分割遺產。", "source_seq": 5},
            {"stem": "被保險人與受益人同時死亡時，保險金如何歸屬？", "options": ["為受益人遺產","為被保險人遺產","為要保人所有","平均分配"], "correct": 1, "explanation": "同時死亡時保險金為被保險人遺產（保險法第 112 條類推）。", "source_seq": 4},
        ],
    },
    {
        "title": "遺產稅、贈與稅與所得稅",
        "description": "保險與稅 — 業務員最會被客戶問、也最容易答錯。",
        "tags": ["#保險法規", "#稅務實務"],
        "pages": [
            {
                "title": "誰要繳遺產稅？",
                "body": "經常居住中華民國境內之國民：就境內境外全部遺產課遺產稅。經常居住境外之國民 + 非國民：僅就境內遺產課稅。計算公式：遺產總額 − 免稅額（1,333 萬）− 扣除額 = 課稅遺產淨額。",
                "highlight": "境內國民＝全球課稅；其他＝境內課稅。",
            },
            {
                "title": "遺產稅扣除額（現行法規）",
                "body": "配偶 493 萬；父母 123 萬／人；喪葬費 123 萬；重度身心障礙 618 萬／人；成年子女、受扶養兄弟姐妹、受扶養祖父母 50 萬／人；未成年子女每年加扣 50 萬（到 20 歲）。",
                "highlight": "喪葬費 123 萬 → 記住這是遺產稅專用。",
            },
            {
                "title": "繳不出遺產稅怎麼辦？",
                "body": "遺產稅或贈與稅應納稅額在 30 萬元以上，且納稅義務人有困難不能一次繳納現金時，可在納稅期限內申請分期繳納，最多 18 期，每期間隔不超過 2 個月。",
                "highlight": "30 萬門檻 / 18 期 / 每期 2 個月。",
            },
            {
                "title": "贈與稅",
                "body": "夫妻贈與免課稅。其他贈與每年自總額中減除免稅額 244 萬元（111 年新制）。父母於子女婚嫁時所贈財物，總金額 100 萬元內不計入贈與總額。納稅義務人為贈與人（30 天內申報）。",
                "highlight": "夫妻互贈免稅；婚嫁 100 萬內不計。",
            },
            {
                "title": "所得稅：保險相關優惠",
                "body": "人身保險、勞保、軍公教保險給付免納所得稅。納稅義務人本人、配偶或受扶養直系親屬之人身保險費等，每人每年扣除額上限 24,000 元。全民健保保費不受金額限制。綜合所得稅免稅額每人全年 6 萬元。",
                "highlight": "保險費列舉扣除每人每年上限 24,000 元。",
            },
        ],
        "questions": [
            {"stem": "現行遺產稅法規定，喪葬費扣除額為多少？", "options": ["100 萬元","111 萬元","123 萬元","200 萬元"], "correct": 2, "explanation": "現行法規（第 12-1 條）喪葬費扣除額為 123 萬元。舊法第 17 條為 100 萬元。", "source_seq": 2},
            {"stem": "遺產稅應納稅額達多少元以上，納稅義務人可申請分期繳納？", "options": ["10 萬元","20 萬元","30 萬元","50 萬元"], "correct": 2, "explanation": "應納稅額 30 萬元以上且有繳納困難時，可申請 18 期以內分期，每期間隔不超過 2 個月。", "source_seq": 3},
            {"stem": "納稅義務人每人每年可列舉扣除之人身保險費上限為新台幣多少？", "options": ["2,400 元","24,000 元","240,000 元","無上限"], "correct": 1, "explanation": "人身保險費列舉扣除每人每年上限 24,000 元。但全民健保保費不受金額限制。", "source_seq": 5},
            {"stem": "現行遺產稅的免稅額為多少？", "options": ["800 萬元","1,200 萬元","1,333 萬元","2,000 萬元"], "correct": 2, "explanation": "現行遺產稅免稅額為 1,333 萬元。", "source_seq": 1},
            {"stem": "現行遺產稅配偶扣除額為多少？", "options": ["400 萬元","445 萬元","493 萬元","500 萬元"], "correct": 2, "explanation": "現行配偶扣除額為 493 萬元（舊法第 17 條為 400 萬）。", "source_seq": 2},
            {"stem": "遺產稅分期繳納最多可分幾期？每期間隔不超過多久？", "options": ["12 期／3 個月","18 期／2 個月","24 期／1 個月","36 期／3 個月"], "correct": 1, "explanation": "最多分 18 期，每期間隔不超過 2 個月。", "source_seq": 3},
            {"stem": "現行贈與稅每年免稅額為多少（111 年新制）？", "options": ["220 萬元","244 萬元","300 萬元","400 萬元"], "correct": 1, "explanation": "111 年起贈與稅每年免稅額調高至 244 萬元。", "source_seq": 4},
            {"stem": "父母於子女婚嫁時贈與之財物，總金額多少元內不計入贈與總額？", "options": ["50 萬","100 萬","200 萬","244 萬"], "correct": 1, "explanation": "父母於子女婚嫁時所贈財物，100 萬元以內不計入贈與總額。", "source_seq": 4},
            {"stem": "下列保險給付何者免納所得稅？", "options": ["投資型保險投資收益","人身保險給付","定期儲蓄險利息","強制責任險給付"], "correct": 1, "explanation": "人身保險、勞保、軍公教保險之保險給付免納所得稅。", "source_seq": 5},
            {"stem": "遺產稅之課稅對象，『經常居住境內之中華民國國民』採何標準？", "options": ["僅境內遺產","僅境外遺產","境內境外全部遺產","由繼承人選擇"], "correct": 2, "explanation": "經常居住境內國民就『境內境外全部遺產』課遺產稅。境外國民或非國民則僅就境內遺產課稅。", "source_seq": 1},
        ],
    },
]


def init():
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"[init] removed old DB at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    source_doc = "人身保險業務員考照筆記（JY 價值筆記）"
    for idx, ch in enumerate(CHAPTERS, start=1):
        cur.execute(
            "INSERT INTO MicroModules (title, source_doc, domain_tags, description, "
            "duration_sec, page_count, quiz_count, sort_order) VALUES (?,?,?,?,?,?,?,?)",
            (ch["title"], source_doc, json.dumps(ch["tags"], ensure_ascii=False),
             ch["description"], 420, len(ch["pages"]), len(ch["questions"]), idx),
        )
        module_id = cur.lastrowid
        for i, page in enumerate(ch["pages"], start=1):
            cur.execute(
                "INSERT INTO FlashcardPages (module_id, sequence_number, page_content_json) VALUES (?,?,?)",
                (module_id, i, json.dumps(page, ensure_ascii=False)),
            )
        for i, q in enumerate(ch["questions"], start=1):
            cur.execute(
                "INSERT INTO QuizQuestions (module_id, sequence_number, stem, options_json, "
                "correct_index, explanation, source_page_seq) VALUES (?,?,?,?,?,?,?)",
                (module_id, i, q["stem"], json.dumps(q["options"], ensure_ascii=False),
                 q["correct"], q.get("explanation"), q.get("source_seq")),
            )

    conn.commit()
    conn.close()
    print(f"[init] DB ready at {DB_PATH}")
    print(f"[init] seeded {len(CHAPTERS)} chapters, {sum(len(c['pages']) for c in CHAPTERS)} pages, "
          f"{sum(len(c['questions']) for c in CHAPTERS)} quiz questions")


if __name__ == "__main__":
    init()
