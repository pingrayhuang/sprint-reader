// Sprint Reader — frontend logic
// Chapters → Splash → Reader (timer + Visibility API + swipe) → Handoff → Quiz → Result

const API = ""; // same origin

async function api(method, path, body) {
  const res = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function fmtMMSS(sec) {
  sec = Math.max(0, Math.round(sec));
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function qs(key) {
  return new URLSearchParams(location.search).get(key);
}

// ---------- Shared: font zoom control ----------
const ZOOM_STEPS = [0.85, 0.95, 1.0, 1.15, 1.3, 1.5];
function getZoomIdx() {
  const saved = parseFloat(localStorage.getItem("fs_scale") || "1");
  let i = ZOOM_STEPS.indexOf(saved);
  return i >= 0 ? i : 2;
}
function applyZoom(rootEl) {
  const v = ZOOM_STEPS[getZoomIdx()];
  if (rootEl) rootEl.style.setProperty("--fs-scale", v);
  const label = document.getElementById("zoom-label");
  if (label) label.textContent = Math.round(v * 100) + "%";
  const down = document.getElementById("zoom-down");
  const up = document.getElementById("zoom-up");
  if (down) down.disabled = getZoomIdx() === 0;
  if (up) up.disabled = getZoomIdx() === ZOOM_STEPS.length - 1;
}
function bindZoom(rootEl) {
  applyZoom(rootEl);
  const down = document.getElementById("zoom-down");
  const up = document.getElementById("zoom-up");
  if (down) down.addEventListener("click", () => {
    const i = Math.max(0, getZoomIdx() - 1);
    localStorage.setItem("fs_scale", ZOOM_STEPS[i]);
    applyZoom(rootEl);
  });
  if (up) up.addEventListener("click", () => {
    const i = Math.min(ZOOM_STEPS.length - 1, getZoomIdx() + 1);
    localStorage.setItem("fs_scale", ZOOM_STEPS[i]);
    applyZoom(rootEl);
  });
  // Keyboard +/-
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea")) return;
    if (e.key === "+" || e.key === "=") { if (up) { up.click(); e.preventDefault(); } }
    else if (e.key === "-" || e.key === "_") { if (down) { down.click(); e.preventDefault(); } }
  });
}

// ---------- Splash ----------
async function initSplash() {
  const moduleId = Number(qs("module_id"));
  if (!moduleId) { location.href = "index.html"; return; }

  let mod;
  try {
    mod = await api("GET", `/api/module/${moduleId}`);
  } catch (e) {
    document.querySelector(".splash-title").textContent = "章節不存在";
    return;
  }

  document.querySelector(".splash-title").textContent = mod.title;
  document.querySelector(".splash-doc").textContent = `Source: ${mod.source_doc}`;
  const tags = document.querySelector(".splash-tags");
  tags.innerHTML = "";
  mod.domain_tags.forEach((t) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = t;
    tags.appendChild(span);
  });
  document.getElementById("warning-time").textContent = `${Math.floor(mod.duration_sec / 60)} 分鐘`;
  document.getElementById("warning-pages").textContent = `${mod.page_count} 張卡片`;
  document.getElementById("warning-quiz").textContent = `${mod.quiz_count} 題即時測驗`;

  document.getElementById("start-btn").addEventListener("click", async () => {
    const start = await api("POST", "/api/sprint/start", {
      agent_id: "demo-agent-001",
      module_id: moduleId,
    });
    sessionStorage.setItem("sprint_id", start.sprint_id);
    sessionStorage.setItem("module_id", String(moduleId));
    sessionStorage.setItem("start_ts", String(Date.now()));
    sessionStorage.setItem("duration_sec", String(mod.duration_sec));
    location.href = "reader.html";
  });
}

// ---------- Reader ----------
async function initReader() {
  const sprintId = sessionStorage.getItem("sprint_id");
  const moduleId = Number(sessionStorage.getItem("module_id"));
  const startTs = Number(sessionStorage.getItem("start_ts"));
  const durationSec = Number(sessionStorage.getItem("duration_sec"));
  if (!sprintId) { location.href = "index.html"; return; }

  const mod = await api("GET", `/api/module/${moduleId}`);
  renderCards(mod);
  renderProgressBars(mod.pages.length);
  document.getElementById("meta-tags").textContent = mod.domain_tags.join(" ");
  document.getElementById("meta-source").textContent = mod.title;
  bindZoom(document.querySelector(".reader"));

  let currentIdx = 0;
  const cardsEl = document.getElementById("cards");
  const cardEls = () => [...cardsEl.querySelectorAll(".card")];

  function showCard(i) {
    cardEls().forEach((c, j) => {
      c.classList.remove("is-gone-left", "is-gone-right", "is-below", "swipe-next", "swipe-prev", "snap-back");
      c.style.removeProperty("--swipe-intensity");
      c.style.transform = "";
      c.style.opacity = "";
      c.style.pointerEvents = "";
      if (j < i) {
        c.classList.add("is-gone-right");
        c.style.pointerEvents = "none";   // passed cards must not block active card hits
      }
      else if (j === i) {/* active — keep default pointer-events */}
      else if (j === i + 1) c.classList.add("is-below");    // peek behind (is-below has pointer-events: none in CSS)
      else { c.style.opacity = "0"; c.style.pointerEvents = "none"; }
    });
    currentIdx = i;
    updateProgress(i, mod.pages.length);
    document.getElementById("card-num").textContent = `${i + 1} / ${mod.pages.length}`;
    const footBtn = document.getElementById("foot-complete-btn");
    if (footBtn) footBtn.hidden = i !== mod.pages.length - 1;
    const prevBtn = document.getElementById("nav-prev");
    const nextBtn = document.getElementById("nav-next");
    if (prevBtn) prevBtn.disabled = i === 0;
    if (nextBtn) nextBtn.disabled = i === mod.pages.length - 1;
  }

  function goNext() {
    if (currentIdx < mod.pages.length - 1) showCard(currentIdx + 1);
    updateNavArrows();
  }
  function goPrev() {
    if (currentIdx > 0) showCard(currentIdx - 1);
    updateNavArrows();
  }
  function updateNavArrows() {
    const prevBtn = document.getElementById("nav-prev");
    const nextBtn = document.getElementById("nav-next");
    if (prevBtn) prevBtn.disabled = currentIdx === 0;
    if (nextBtn) nextBtn.disabled = currentIdx === mod.pages.length - 1;
  }
  function animateOutThenGo(direction) {
    if (completed) return;
    const card = cardEls()[currentIdx];
    if (!card) return;
    if (direction === "next" && currentIdx >= mod.pages.length - 1) return;
    if (direction === "prev" && currentIdx <= 0) return;
    card.classList.remove("swipe-next", "swipe-prev");
    card.style.removeProperty("--swipe-intensity");
    card.classList.add(direction === "next" ? "is-gone-left" : "is-gone-right");
    setTimeout(() => (direction === "next" ? goNext() : goPrev()), 520);
  }
  const navPrevBtn = document.getElementById("nav-prev");
  const navNextBtn = document.getElementById("nav-next");
  if (navPrevBtn) navPrevBtn.addEventListener("click", () => animateOutThenGo("prev"));
  if (navNextBtn) navNextBtn.addEventListener("click", () => animateOutThenGo("next"));

  // ---- Swipe gesture (pointer events work for mouse + touch) ----
  const THRESHOLD_RATIO = 0.28; // must drag 28% of card width to trigger
  const MAX_ROTATE = 14;
  let drag = null;

  cardsEl.addEventListener("pointerdown", (e) => {
    if (completed) return;
    const active = cardEls()[currentIdx];
    if (!active || !active.contains(e.target)) return;
    // Don't start drag on interactive children (e.g. complete button)
    if (e.target.closest(".card-complete-btn")) return;
    drag = { x0: e.clientX, y0: e.clientY, card: active, width: active.clientWidth };
    active.setPointerCapture(e.pointerId);
    active.classList.add("is-dragging");
  });

  cardsEl.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x0;
    const dy = e.clientY - drag.y0;
    // If vertical dominates, abort drag (let scroll)
    if (Math.abs(dy) > Math.abs(dx) * 1.5 && Math.abs(dx) < 10) return;
    const rot = (dx / drag.width) * MAX_ROTATE;
    drag.card.style.transform = `translateX(${dx}px) rotate(${rot}deg)`;
    drag.card.classList.remove("swipe-next", "swipe-prev");
    const threshold = drag.width * THRESHOLD_RATIO;
    const intensity = Math.min(1, Math.abs(dx) / threshold);
    if (dx < -20 && currentIdx < mod.pages.length - 1) {
      drag.card.classList.add("swipe-next");
      drag.card.style.setProperty("--swipe-intensity", intensity);
    } else if (dx > 20 && currentIdx > 0) {
      drag.card.classList.add("swipe-prev");
      drag.card.style.setProperty("--swipe-intensity", intensity);
    } else {
      drag.card.style.setProperty("--swipe-intensity", 0);
    }
  });

  function endDrag(e) {
    if (!drag) return;
    const dx = (e ? e.clientX : drag.x0) - drag.x0;
    const card = drag.card;
    card.classList.remove("is-dragging");
    card.style.opacity = "";
    const threshold = drag.width * THRESHOLD_RATIO;
    if (dx < -threshold && currentIdx < mod.pages.length - 1) {
      card.classList.remove("swipe-next", "swipe-prev");
      card.style.removeProperty("--swipe-intensity");
      card.classList.add("is-gone-left");
      card.style.transform = "";
      setTimeout(() => goNext(), 520);
    } else if (dx > threshold && currentIdx > 0) {
      card.classList.remove("swipe-next", "swipe-prev");
      card.style.removeProperty("--swipe-intensity");
      card.classList.add("is-gone-right");
      card.style.transform = "";
      setTimeout(() => goPrev(), 520);
    } else {
      // Snap back with bounce
      card.classList.remove("swipe-next", "swipe-prev");
      card.style.removeProperty("--swipe-intensity");
      card.style.transform = "";
      card.classList.add("snap-back");
      const cleanup = () => { card.classList.remove("snap-back"); card.removeEventListener("animationend", cleanup); };
      card.addEventListener("animationend", cleanup);
    }
    drag = null;
  }
  cardsEl.addEventListener("pointerup", endDrag);
  cardsEl.addEventListener("pointercancel", endDrag);

  showCard(0);

  let pausedMs = 0;
  let pausedAt = null;
  let completed = false;
  const timerEl = document.getElementById("timer");
  const pauseBanner = document.getElementById("pause-banner");

  function elapsed() { return (Date.now() - startTs - pausedMs) / 1000; }
  function remaining() { return durationSec - elapsed(); }
  function tick() {
    if (completed || pausedAt !== null) return;
    const r = remaining();
    timerEl.textContent = fmtMMSS(r);
    timerEl.classList.toggle("danger", r <= 30 && r > 0);
    if (r <= 0) handleTimeout();
  }
  setInterval(tick, 250);

  async function handleTimeout() {
    if (completed) return;
    completed = true;
    timerEl.textContent = "00:00";
    timerEl.classList.remove("danger");
    try {
      await api("POST", "/api/sprint/complete", { sprint_id: sprintId, status: "timed_out" });
    } catch (e) { /* continue to modal even if API fails */ }
    const modal = document.getElementById("timeout-modal");
    const meta = document.getElementById("timeout-meta");
    if (meta) meta.textContent = `sprint_id: ${sprintId.slice(0, 8)}… · 本次紀錄 status = timed_out`;
    if (modal) modal.hidden = false;
    const homeBtn = document.getElementById("timeout-home");
    if (homeBtn) {
      homeBtn.addEventListener("click", () => { location.href = "index.html"; });
    }
  }

  // Bind persistent footer "進入測驗" button (shown on last card)
  const footBtn = document.getElementById("foot-complete-btn");
  if (footBtn) {
    footBtn.addEventListener("click", () => complete("finished_early"));
  }

  document.addEventListener("visibilitychange", async () => {
    if (completed) return;
    if (document.hidden) {
      pausedAt = Date.now();
      timerEl.classList.add("paused");
      pauseBanner.classList.add("show");
      try {
        const r = await api("POST", "/api/sprint/telemetry", { sprint_id: sprintId, event: "tab_switch" });
        document.getElementById("tab-switch-count").textContent = `分心 ${r.tab_switch_count} 次`;
      } catch (e) { /* ignore */ }
    } else if (pausedAt !== null) {
      pausedMs += Date.now() - pausedAt;
      pausedAt = null;
      timerEl.classList.remove("paused");
      pauseBanner.classList.remove("show");
    }
  });

  // Keyboard: keep standard desktop meaning (→ next, ← prev)
  document.addEventListener("keydown", (e) => {
    if (completed) return;
    if (e.target.matches("input, textarea, button")) return;
    if (e.key === "ArrowRight") { e.preventDefault(); goNext(); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); goPrev(); }
  });

  // Expose complete for the last-card button (attached in renderCards)
  window.__readerComplete = () => complete("finished_early");

  async function complete(status) {
    if (completed) return;
    completed = true;
    document.getElementById("lock").classList.add("show");
    try {
      await api("POST", "/api/sprint/complete", { sprint_id: sprintId, status });
      const handoff = await api("POST", "/api/handoff/to-quiz", { sprint_id: sprintId });
      sessionStorage.setItem("handoff", JSON.stringify(handoff));
      sessionStorage.setItem("quiz_session_id", handoff.quiz_session_id);
      setTimeout(() => { location.href = "handoff.html"; }, 1400);
    } catch (e) {
      document.querySelector(".lock-text").textContent = "Handoff failed";
      document.querySelector(".lock-sub").textContent = String(e);
    }
  }

  window.addEventListener("beforeunload", (e) => {
    if (completed) return;
    navigator.sendBeacon &&
      navigator.sendBeacon("/api/sprint/complete",
        new Blob([JSON.stringify({ sprint_id: sprintId, status: "abandoned" })], { type: "application/json" }));
    // Trigger browser confirm dialog so user doesn't accidentally discard their sprint
    e.preventDefault();
    e.returnValue = "離開會結束本次 Sprint，本章進度會記錄為「中途離開」。確定要離開嗎？";
    return e.returnValue;
  });
}

function renderCards(mod) {
  const wrap = document.getElementById("cards");
  wrap.innerHTML = "";
  const total = mod.pages.length;
  mod.pages.forEach((p, i) => {
    const isLast = i === total - 1;
    const card = document.createElement("section");
    card.className = "card";
    // Higher z for earlier cards so they stack on top initially
    card.style.zIndex = String(total - i);
    card.innerHTML = `
      <span class="swipe-stamp prev">↩ 回上一張</span>
      <span class="swipe-stamp next">✓ 下一張</span>
      <div class="card-num">${String(i + 1).padStart(2, "0")} / ${String(total).padStart(2, "0")}</div>
      <h2 class="card-title">${p.title}</h2>
      <p class="card-body">${p.body}</p>
      ${p.highlight ? `<div class="card-highlight">${p.highlight}</div>` : ""}
      ${isLast ? `<button class="card-complete-btn" onclick="window.__readerComplete && window.__readerComplete()">✅ 完成 Sprint · 進入 Quiz</button>` : ""}
    `;
    wrap.appendChild(card);
  });
  document.getElementById("card-num").textContent = `1 / ${total}`;
}

function renderProgressBars(n) {
  const wrap = document.getElementById("progress");
  wrap.innerHTML = "";
  for (let i = 0; i < n; i++) {
    const b = document.createElement("div");
    b.className = "progress-bar" + (i === 0 ? " active" : "");
    b.dataset.idx = i;
    wrap.appendChild(b);
  }
}

function updateProgress(idx, total) {
  document.querySelectorAll(".progress-bar").forEach((b, i) => {
    b.classList.remove("active", "done");
    if (i < idx) b.classList.add("done");
    else if (i === idx) b.classList.add("active");
  });
}

// ---------- Handoff (transition screen → quiz) ----------
function initHandoff() {
  const raw = sessionStorage.getItem("handoff");
  if (!raw) { location.href = "index.html"; return; }
  setTimeout(() => {
    location.href = "quiz.html";
  }, 1400);
}

// ---------- Quiz (v2: answer all, then reveal) ----------
async function initQuiz() {
  const quizSessionId = sessionStorage.getItem("quiz_session_id");
  const sprintId = sessionStorage.getItem("sprint_id");
  const moduleId = Number(sessionStorage.getItem("module_id"));
  if (!quizSessionId) { location.href = "index.html"; return; }

  const data = await api("GET", `/api/quiz/${moduleId}`);
  const questions = data.questions;
  const total = questions.length;
  const answers = Array(total).fill(null); // chosen_index or null
  let idx = 0;

  bindZoom(document.querySelector(".quiz"));

  const stemEl = document.getElementById("quiz-stem");
  const optionsEl = document.getElementById("quiz-options");
  const progressEl = document.getElementById("quiz-progress");
  const dotsEl = document.getElementById("quiz-dots");
  const prevBtn = document.getElementById("quiz-prev");
  const nextBtn = document.getElementById("quiz-next");
  const finishBtn = document.getElementById("quiz-finish");
  const answeredCountEl = document.getElementById("answered-count");
  document.getElementById("total-count").textContent = total;

  function renderDots() {
    dotsEl.innerHTML = "";
    for (let i = 0; i < total; i++) {
      const b = document.createElement("button");
      b.className = "qdot";
      b.textContent = i + 1;
      if (answers[i] !== null) b.classList.add("answered");
      if (i === idx) b.classList.add("current");
      b.addEventListener("click", () => { idx = i; render(); });
      dotsEl.appendChild(b);
    }
  }

  function render() {
    const q = questions[idx];
    progressEl.textContent = `題 ${idx + 1} / ${total}`;
    stemEl.textContent = q.stem;
    optionsEl.innerHTML = "";
    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.className = "quiz-option" + (answers[idx] === i ? " selected" : "");
      btn.innerHTML = `<span class="letter">${String.fromCharCode(65 + i)}</span><span>${opt}</span>`;
      btn.addEventListener("click", () => {
        answers[idx] = i;
        render();
      });
      optionsEl.appendChild(btn);
    });
    renderDots();
    const answeredN = answers.filter((a) => a !== null).length;
    answeredCountEl.textContent = answeredN;
    prevBtn.disabled = idx === 0;
    nextBtn.disabled = idx === total - 1;
    finishBtn.disabled = answeredN < total;
  }

  prevBtn.addEventListener("click", () => { if (idx > 0) { idx--; render(); } });
  nextBtn.addEventListener("click", () => { if (idx < total - 1) { idx++; render(); } });

  // Keyboard: Left/Right nav, 1-4 pick option
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, button")) return;
    if (e.key === "ArrowLeft" && idx > 0) { e.preventDefault(); idx--; render(); }
    else if (e.key === "ArrowRight" && idx < total - 1) { e.preventDefault(); idx++; render(); }
    else if (/^[1-4]$/.test(e.key)) {
      const i = Number(e.key) - 1;
      const q = questions[idx];
      if (i < q.options.length) { answers[idx] = i; render(); }
    }
  });

  let quizSubmitted = false;
  finishBtn.addEventListener("click", async () => {
    finishBtn.disabled = true;
    finishBtn.textContent = "提交中…";
    try {
      await api("POST", "/api/quiz/submit-batch", {
        quiz_session_id: quizSessionId,
        answers: answers.map((a, i) => ({ question_id: questions[i].question_id, chosen_index: a })),
      });
      const final = await api("POST", "/api/quiz/finalize", {
        quiz_session_id: quizSessionId, sprint_id: sprintId, module_id: moduleId,
      });
      sessionStorage.setItem("result", JSON.stringify(final));
      quizSubmitted = true;
      location.href = "result.html";
    } catch (e) {
      alert("提交失敗：" + e);
      finishBtn.disabled = false;
      finishBtn.textContent = "✅ 提交並公布解答";
    }
  });

  window.addEventListener("beforeunload", (e) => {
    if (quizSubmitted) return;
    const answered = answers.filter((a) => a !== null).length;
    if (answered === 0) return;
    e.preventDefault();
    e.returnValue = "離開會放棄本次測驗答案，確定要離開嗎？";
    return e.returnValue;
  });

  render();
}

// ---------- Result ----------
async function initResult() {
  const raw = sessionStorage.getItem("result");
  if (!raw) { location.href = "index.html"; return; }
  const r = JSON.parse(raw);
  const moduleId = Number(sessionStorage.getItem("module_id"));

  const pct = r.total ? Math.round((r.score / r.total) * 100) : 0;
  document.getElementById("result-score").textContent = `答對率（${r.score} / ${r.total} 題）`;
  document.getElementById("result-pct").textContent = `${pct}%`;
  document.getElementById("result-reading").textContent = r.reading_sec != null ? `${r.reading_sec} 秒` : "—";
  document.getElementById("result-tabs").textContent = `${r.tab_switch_count ?? 0} 次`;
  document.getElementById("result-status").textContent = r.completion_status || "—";
  document.getElementById("result-ids").innerHTML = `
    <div class="handoff-row"><span class="k">sprint_id</span><span class="v">${r.sprint_id}</span></div>
    <div class="handoff-row"><span class="k">quiz_session_id</span><span class="v">${r.quiz_session_id}</span></div>
  `;

  // Load module pages once for the card-review modal
  let pagesBySeq = {};
  try {
    const mod = await api("GET", `/api/module/${moduleId}`);
    mod.pages.forEach((p) => { pagesBySeq[p.sequence_number] = p; });
  } catch (e) { /* no-op */ }

  const list = document.getElementById("result-breakdown");
  list.innerHTML = "";
  r.responses.forEach((resp) => {
    const item = document.createElement("div");
    item.className = "review-item " + (resp.is_correct ? "ok" : "ng");
    item.innerHTML = `
      <div class="review-head">
        <span class="review-badge">${resp.is_correct ? "✓" : "✗"}</span>
        <span class="review-seq">Q${resp.sequence_number}</span>
        <span class="review-stem">${resp.stem}</span>
      </div>
      <div class="review-body">
        <div>你的答案：<b>${String.fromCharCode(65 + resp.chosen_index)}. ${resp.options[resp.chosen_index]}</b></div>
        ${!resp.is_correct
          ? `<div>正確答案：<b class="ok-text">${String.fromCharCode(65 + resp.correct_index)}. ${resp.options[resp.correct_index]}</b></div>`
          : ""}
        ${resp.explanation ? `<div class="review-exp">💡 ${resp.explanation}</div>` : ""}
        ${resp.source_page_seq
          ? `<button class="review-src-btn" data-seq="${resp.source_page_seq}">📖 參考原文卡片 #${resp.source_page_seq} →</button>`
          : ""}
      </div>
    `;
    list.appendChild(item);
  });

  // Bind card-review modal
  const modal = document.getElementById("card-modal");
  document.querySelectorAll(".review-src-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const seq = Number(btn.dataset.seq);
      const page = pagesBySeq[seq];
      if (!page) { alert("卡片載入中或找不到"); return; }
      document.getElementById("modal-kicker").textContent = `卡片 ${String(seq).padStart(2, "0")} / ${String(Object.keys(pagesBySeq).length).padStart(2, "0")}`;
      document.getElementById("modal-title").textContent = page.title;
      document.getElementById("modal-body").textContent = page.body;
      const hl = document.getElementById("modal-highlight");
      if (page.highlight) { hl.textContent = page.highlight; hl.style.display = "block"; }
      else { hl.style.display = "none"; }
      modal.hidden = false;
    });
  });
  document.getElementById("modal-close").addEventListener("click", () => { modal.hidden = true; });
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") modal.hidden = true; });
}

// ---------- Review (challenge flow) ----------
async function initReview() {
  const raw = sessionStorage.getItem("review_session");
  if (!raw) { location.href = "review-setup.html"; return; }
  const sess = JSON.parse(raw);
  const quizSessionId = sess.quiz_session_id;
  const questions = sess.questions;
  const total = questions.length;
  const answers = Array(total).fill(null);
  let idx = 0;

  bindZoom(document.querySelector(".quiz"));

  const stemEl = document.getElementById("quiz-stem");
  const optionsEl = document.getElementById("quiz-options");
  const progressEl = document.getElementById("quiz-progress");
  const dotsEl = document.getElementById("quiz-dots");
  const prevBtn = document.getElementById("quiz-prev");
  const nextBtn = document.getElementById("quiz-next");
  const finishBtn = document.getElementById("quiz-finish");
  const answeredCountEl = document.getElementById("answered-count");
  document.getElementById("total-count").textContent = total;

  function renderDots() {
    dotsEl.innerHTML = "";
    for (let i = 0; i < total; i++) {
      const b = document.createElement("button");
      b.className = "qdot";
      b.textContent = i + 1;
      if (answers[i] !== null) b.classList.add("answered");
      if (i === idx) b.classList.add("current");
      b.addEventListener("click", () => { idx = i; render(); });
      dotsEl.appendChild(b);
    }
  }

  function render() {
    const q = questions[idx];
    progressEl.textContent = `題 ${idx + 1} / ${total} · ${q.module_title}`;
    stemEl.textContent = q.stem;
    optionsEl.innerHTML = "";
    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.className = "quiz-option" + (answers[idx] === i ? " selected" : "");
      btn.innerHTML = `<span class="letter">${String.fromCharCode(65 + i)}</span><span>${opt}</span>`;
      btn.addEventListener("click", () => { answers[idx] = i; render(); });
      optionsEl.appendChild(btn);
    });
    renderDots();
    const answeredN = answers.filter((a) => a !== null).length;
    answeredCountEl.textContent = answeredN;
    prevBtn.disabled = idx === 0;
    nextBtn.disabled = idx === total - 1;
    finishBtn.disabled = answeredN < total;
  }

  prevBtn.addEventListener("click", () => { if (idx > 0) { idx--; render(); } });
  nextBtn.addEventListener("click", () => { if (idx < total - 1) { idx++; render(); } });

  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, button")) return;
    if (e.key === "ArrowLeft" && idx > 0) { e.preventDefault(); idx--; render(); }
    else if (e.key === "ArrowRight" && idx < total - 1) { e.preventDefault(); idx++; render(); }
    else if (/^[1-4]$/.test(e.key)) {
      const i = Number(e.key) - 1;
      const q = questions[idx];
      if (i < q.options.length) { answers[idx] = i; render(); }
    }
  });

  finishBtn.addEventListener("click", async () => {
    finishBtn.disabled = true;
    finishBtn.textContent = "提交中…";
    try {
      await api("POST", "/api/review/submit-batch", {
        quiz_session_id: quizSessionId,
        answers: answers.map((a, i) => ({ question_id: questions[i].question_id, chosen_index: a })),
      });
      const final = await api("POST", "/api/review/finalize", { quiz_session_id: quizSessionId });
      renderResults(final, questions);
    } catch (e) {
      finishBtn.disabled = false;
      finishBtn.textContent = "✅ 提交並公布解答";
      alert("提交失敗：" + e);
    }
  });

  function renderResults(final, origQuestions) {
    document.getElementById("quiz-pane").hidden = true;
    document.getElementById("nav-bar").hidden = true;
    const pane = document.getElementById("result-pane");
    pane.hidden = false;
    const pct = final.total ? Math.round(final.score / final.total * 100) : 0;
    // Count "rescued" (previously wrong, now correct)
    // In review flow, ALL questions were previously wrong, so rescued = correct this time
    const rescued = final.score;
    const stillWrong = final.total - final.score;

    let html = `
      <div class="result">
        <div class="result-hero">
          <div class="result-kicker">挑戰結果</div>
          <div class="result-score-wrap">
            <div class="result-score">${final.score} / ${final.total}</div>
            <div class="result-pct">${pct}%</div>
          </div>
        </div>
        <div class="result-stats">
          <div class="stat"><div class="stat-label">🎯 從錯變對</div><div class="stat-value" style="color: var(--success);">${rescued} 題</div></div>
          <div class="stat"><div class="stat-label">😩 還是答錯</div><div class="stat-value" style="color: var(--danger);">${stillWrong} 題</div></div>
          <div class="stat"><div class="stat-label">本次正確率</div><div class="stat-value">${pct}%</div></div>
        </div>
        <h3 class="section-title">逐題檢討</h3>
        <div class="result-breakdown">
    `;
    final.responses.forEach((resp) => {
      html += `
        <div class="review-item ${resp.is_correct ? "ok" : "ng"}">
          <div class="review-head">
            <span class="review-badge">${resp.is_correct ? "✓" : "✗"}</span>
            <span class="review-seq">${resp.module_title} · Q${resp.sequence_number}</span>
            <span class="review-stem">${resp.stem}</span>
          </div>
          <div class="review-body">
            <div>你的答案：<b>${String.fromCharCode(65 + resp.chosen_index)}. ${resp.options[resp.chosen_index]}</b></div>
            ${!resp.is_correct
              ? `<div>正確答案：<b class="ok-text">${String.fromCharCode(65 + resp.correct_index)}. ${resp.options[resp.correct_index]}</b></div>`
              : ""}
            ${resp.explanation ? `<div class="review-exp">💡 ${resp.explanation}</div>` : ""}
          </div>
        </div>
      `;
    });
    html += `
        </div>
        <div class="result-foot">
          <a href="index.html" class="btn-primary" style="text-decoration: none; display: inline-block; padding: 14px 28px; width: auto;">↻ 回首頁</a>
          <br/><br/>
          <a href="review-setup.html" style="color: var(--accent);">再挑戰一次</a>
        </div>
      </div>
    `;
    pane.innerHTML = html;
    window.scrollTo(0, 0);
  }

  render();
}

// ---------- bootstrap ----------
document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "splash") initSplash();
  else if (page === "reader") initReader();
  else if (page === "handoff") initHandoff();
  else if (page === "quiz") initQuiz();
  else if (page === "result") initResult();
  else if (page === "review") initReview();
});
