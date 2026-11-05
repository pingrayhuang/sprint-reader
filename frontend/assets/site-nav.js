/* Portfolio-wide navigation for sprint-reader side (port 8000) */
(function () {
  const ADVISOR = 'https://rayhuang2.pythonanywhere.com/ui/';
  const INVEST  = 'https://rayhuang3.pythonanywhere.com/ui/';
  const cur     = location.pathname.split('/').pop() || 'index.html';

  const isIntro  = cur === 'intro.html';
  const isAbout  = cur === 'about.html' || cur === 'brief.html';

  const isResearch = cur === 'research.html';

  // Standalone SP1 site (/sp1/): only the 閱讀加速器 tab, no portfolio pages.
  const standalone = location.pathname.startsWith('/sp1/');
  if (standalone && (isIntro || isResearch)) {
    location.replace('about.html');
    return;
  }

  const allLinks = [
    { href: 'intro.html',            label: '自我介紹',   tag: null,      active: isIntro },
    { href: 'about.html',            label: '閱讀加速器', tag: 'SP 1',    active: isAbout },
    { href: ADVISOR + 'brief.html',  label: '業務員助手', tag: 'SP 2',    active: false },
    { href: INVEST  + 'brief.html',  label: '投資 Agent', tag: 'SP 3',    active: false },
    { href: 'research.html',         label: 'AI 研究',    tag: 'RESEARCH',active: isResearch },
  ];
  const links = standalone ? allLinks.filter(l => l.href === 'about.html') : allLinks;

  const css = `
.snav{position:fixed;top:0;left:0;right:0;z-index:9999;height:50px;
  background:#070F1E;border-bottom:1px solid rgba(147,197,253,.15);
  display:flex;align-items:center;padding:0 28px;gap:0;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif;}
.snav-brand{text-decoration:none;display:flex;flex-direction:column;
  justify-content:center;margin-right:36px;line-height:1;}
.snav-brand .sn-title{font-size:13.5px;font-weight:800;
  background:linear-gradient(135deg,#1D4ED8,#60A5FA);
  -webkit-background-clip:text;background-clip:text;color:transparent;}
.snav-brand .sn-sub{font-size:9.5px;color:#4B6180;margin-top:2px;letter-spacing:.04em;}
.snav-divider{width:1px;height:20px;background:rgba(147,197,253,.12);margin-right:20px;}
.snav-links{display:flex;gap:2px;flex:1;}
.snav-link{font-size:12.5px;color:#9FB0CC;text-decoration:none;
  padding:6px 16px;border-radius:6px;transition:.15s;font-weight:500;white-space:nowrap;}
.snav-link:hover{background:rgba(96,165,250,.1);color:#60A5FA;}
.snav-link.sn-active{background:rgba(96,165,250,.14);color:#60A5FA;font-weight:700;}
.snav-right{display:flex;align-items:center;gap:10px;}
.snav-demo{font-size:11.5px;color:#60A5FA;border:1px solid rgba(96,165,250,.3);
  padding:5px 16px;border-radius:999px;text-decoration:none;cursor:pointer;
  transition:.15s;font-weight:600;white-space:nowrap;background:transparent;}
.snav-demo:hover{background:rgba(96,165,250,.1);}
.snav-tag{font-size:10px;color:#4B6180;letter-spacing:.06em;}
.snav-sp{font-size:9px;font-weight:700;color:#4B6180;background:rgba(96,165,250,.08);
  border:1px solid rgba(96,165,250,.15);border-radius:3px;padding:1px 5px;
  margin-right:5px;letter-spacing:.04em;flex-shrink:0;}
.snav-body-pad{padding-top:50px;}

/* ── Demo modal ── */
.sdm-overlay{
  position:fixed;inset:0;z-index:99999;
  background:rgba(4,10,22,.82);backdrop-filter:blur(6px);
  display:flex;align-items:center;justify-content:center;
  opacity:0;transition:opacity .22s;pointer-events:none;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif;
}
.sdm-overlay.sdm-open{opacity:1;pointer-events:all;}
.sdm-card{
  background:#0C1A2E;border:1px solid rgba(147,197,253,.2);
  border-radius:18px;padding:36px 40px;max-width:480px;width:90%;
  box-shadow:0 24px 64px rgba(0,0,0,.6);
  transform:translateY(12px);transition:transform .22s;
}
.sdm-overlay.sdm-open .sdm-card{transform:translateY(0);}
.sdm-eyebrow{
  font-size:10px;letter-spacing:.14em;text-transform:uppercase;
  color:#4B6180;margin-bottom:10px;
}
.sdm-title{
  font-size:20px;font-weight:800;
  background:linear-gradient(135deg,#1D4ED8,#60A5FA);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  line-height:1.25;margin-bottom:14px;
}
.sdm-tags{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:22px;}
.sdm-tag{
  font-size:11.5px;color:#9FB0CC;
  background:rgba(96,165,250,.09);border:1px solid rgba(96,165,250,.2);
  border-radius:999px;padding:3px 11px;
}
.sdm-rule{
  border:none;border-top:1px solid rgba(147,197,253,.1);margin:0 0 22px;
}
.sdm-info{
  background:rgba(96,165,250,.06);border:1px solid rgba(96,165,250,.15);
  border-radius:10px;padding:16px 18px;margin-bottom:24px;
}
.sdm-info-row{
  display:flex;align-items:center;gap:12px;
  font-size:13.5px;color:#9FB0CC;line-height:1.6;
}
.sdm-info-row + .sdm-info-row{margin-top:10px;}
.sdm-info-ico{font-size:18px;flex-shrink:0;width:22px;text-align:center;}
.sdm-info-row strong{color:#E6EEFA;}
.sdm-prompt{
  font-size:14px;font-weight:700;color:#E6EEFA;
  border-left:3px solid #60A5FA;padding-left:14px;
  line-height:1.6;margin-bottom:28px;
}
.sdm-actions{display:flex;align-items:center;gap:12px;}
.sdm-btn{
  flex:1;padding:11px 0;border-radius:10px;font-size:14px;
  font-weight:700;cursor:pointer;border:none;transition:.15s;
  font-family:inherit;
}
.sdm-btn-go{
  background:linear-gradient(135deg,#1D4ED8,#2563EB);
  color:#fff;
}
.sdm-btn-go:hover{background:linear-gradient(135deg,#1e40af,#1D4ED8);}
.sdm-btn-cancel{
  background:transparent;color:#4B6180;
  border:1px solid rgba(147,197,253,.15);flex:0 0 auto;
  padding:11px 20px;
}
.sdm-btn-cancel:hover{color:#9FB0CC;border-color:rgba(147,197,253,.3);}
`;

  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  document.body.classList.add('snav-body-pad');

  /* ── Nav bar ── */
  const nav = document.createElement('nav');
  nav.className = 'snav';
  nav.innerHTML = `
    <a class="snav-brand" href="${standalone ? 'about.html' : 'intro.html'}">
      <span class="sn-title">${standalone ? 'Sprint Reader' : 'Ray Huang'}</span>
      <span class="sn-sub">${standalone ? '7 分鐘考照微學習' : 'Portfolio · 2026'}</span>
    </a>
    <div class="snav-divider"></div>
    <div class="snav-links">
      ${links.map(l => `<a class="snav-link${l.active ? ' sn-active' : ''}" href="${l.href}">${l.tag ? `<span class="snav-sp">${l.tag}</span>` : ''}${l.label}</a>`).join('')}
    </div>
    <div class="snav-right">
      <span class="snav-tag">Ray Huang</span>
      <button class="snav-demo" id="snav-demo-btn">進入 Demo →</button>
    </div>
  `;
  document.body.insertBefore(nav, document.body.firstChild);

  /* ── Modal ── */
  const overlay = document.createElement('div');
  overlay.className = 'sdm-overlay';
  overlay.innerHTML = `
    <div class="sdm-card">
      <div class="sdm-eyebrow">Sprint Reader · 人身保險考照微學習</div>
      <div class="sdm-title">人身保險業務員<br/>資格考照筆記</div>
      <div class="sdm-tags">
        <span class="sdm-tag">#人身保險</span>
        <span class="sdm-tag">#合規考照</span>
        <span class="sdm-tag">#間隔重複</span>
        <span class="sdm-tag">#行為遙測</span>
        <span class="sdm-tag">#微學習</span>
      </div>
      <hr class="sdm-rule"/>
      <div class="sdm-info">
        <div class="sdm-info-row">
          <span class="sdm-info-ico">📚</span>
          <span><strong>6 章節</strong>，各含 5 張閱讀卡，涵蓋人身保險考試核心考點</span>
        </div>
        <div class="sdm-info-row">
          <span class="sdm-info-ico">⏱</span>
          <span>每章限時 <strong>7 分鐘</strong>，計時器由後端蓋章，切分頁自動暫停</span>
        </div>
        <div class="sdm-info-row">
          <span class="sdm-info-ico">✅</span>
          <span>閱讀完成後接 <strong>3 題即時測驗</strong>，附解釋與原文卡片回溯</span>
        </div>
      </div>
      <div class="sdm-prompt">
        你有 7 分鐘閱讀 5 張卡片，<br/>接著會有 3 題測驗。準備好了嗎？
      </div>
      <div class="sdm-actions">
        <button class="sdm-btn sdm-btn-go" id="sdm-go">開始 Demo →</button>
        <button class="sdm-btn sdm-btn-cancel" id="sdm-cancel">取消</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  /* ── Events ── */
  document.getElementById('snav-demo-btn').addEventListener('click', () => {
    overlay.classList.add('sdm-open');
  });
  document.getElementById('sdm-cancel').addEventListener('click', () => {
    overlay.classList.remove('sdm-open');
  });
  document.getElementById('sdm-go').addEventListener('click', () => {
    window.location.href = 'index.html';
  });
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('sdm-open');
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') overlay.classList.remove('sdm-open');
  });
})();
