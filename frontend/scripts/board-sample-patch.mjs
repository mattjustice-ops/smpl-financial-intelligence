/** Patches the static marketing board HTML (no live demo / API). */

const SAMPLE_EXPORTS = {
  boardReview: "/board-sample/exports/SMPL_Board_Review_Q2_2026.pptx",
  mdaPackage: "/board-sample/exports/SMPL_MDA_Package_June2026.xlsx",
};

const TOPBAR_EXPORTS = `    <span class="period-badge" id="periodBadge"></span>
    <button class="ai-global-btn" onclick="globalMDA()">✦ MD&A Deck ↗</button>
    <button class="ai-global-btn" onclick="varComm()">✦ Variance Commentary ↗</button>`;

const FOOTER_SIMPLE = `<div class="footer">
  <div class="footer-note">SMPL · Board sample · Jan–<span id="footerCloseMo"></span> 2026 · Illustrative static data</div>
</div>`;

const EXPORT_BLOCK = `
const BOARD_EXPORTS = {
  boardReview: '${SAMPLE_EXPORTS.boardReview}',
  mdaPackage: '${SAMPLE_EXPORTS.mdaPackage}',
};

function openBoardExport(url) {
  const opened = window.open(url, '_blank', 'noopener,noreferrer');
  if (!opened) window.location.assign(url);
}

function globalMDA() { openBoardExport(BOARD_EXPORTS.boardReview); }
function varComm() { openBoardExport(BOARD_EXPORTS.mdaPackage); }
`;

const STATIC_AI_COMM = `
async function aiComm(slideKey, targetId) {
  if (aiCache[slideKey]) {
    const el = document.getElementById(targetId);
    if (el) el.querySelector('.commentary-text').textContent = aiCache[slideKey];
    return;
  }
  const el = document.getElementById(targetId);
  if (!el) return;
  const txt = el.querySelector('.commentary-text');
  const canned = AI_CTX[slideKey] || 'Sample commentary is illustrative only.';
  txt.textContent = canned;
  aiCache[slideKey] = canned;
}
`;

const STATIC_CP_SEND = `
async function cpSend() {
  if (cpSending) return;
  const input = document.getElementById('cpInput');
  const sendBtn = document.getElementById('cpSendBtn');
  const msgs = document.getElementById('cpMessages');
  if (!input || !msgs) return;
  const q = input.value.trim();
  if (!q) return;

  cpSending = true;
  input.value = '';
  if (sendBtn) sendBtn.disabled = true;

  msgs.innerHTML += '<div class="cp-msg user"><div class="cp-avatar">M</div><div class="cp-bubble">' + q.replace(/</g,'&lt;') + '</div></div>';

  const thinkId = 'cpThink_' + Date.now();
  msgs.innerHTML += '<div class="cp-msg assistant" id="' + thinkId + '"><div class="cp-avatar">S</div><div class="cp-bubble"><div class="cp-thinking"><div class="cp-dot"></div><div class="cp-dot"></div><div class="cp-dot"></div></div></div></div>';
  msgs.scrollTop = msgs.scrollHeight;

  await new Promise(function (r) { setTimeout(r, 450); });

  const seeds = CP_DATA.mda_seeds || {};
  const key = Object.keys(seeds).find(function (k) { return q.toLowerCase().indexOf(k.toLowerCase().split(' ')[0]) >= 0; });
  const reply = key ? seeds[key] : 'June close: ARR $86.1M (+$0.58M vs budget), revenue $7.41M (+$60K), cash $70.6M (+$39.1M vs budget — billing timing). This sample view uses illustrative static data; book a demo for your live operating model.';

  const formatted = '<div class="cp-section">Sample response</div>' + reply.replace(/\\n/g, '<br>') + '<div class="cp-source">Illustrative sample · not connected to live systems</div>';

  const thinkEl = document.getElementById(thinkId);
  if (thinkEl) {
    thinkEl.outerHTML = '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble">' + formatted + '</div></div>';
  }

  cpSending = false;
  if (sendBtn) sendBtn.disabled = false;
  msgs.scrollTop = msgs.scrollHeight;
}
`;

export function patchBoardSampleHtml(html) {
  let out = html;

  out = out.replace(
    /<title>SMPL · We make finance simple · June 2026<\/title>/,
    "<title>SMPL · Board sample · June 2026</title>",
  );

  // Top bar: period badge + MD&A Deck + Variance Commentary (remove single Download MD&A)
  out = out.replace(
    /<span class="period-badge" id="periodBadge"><\/span>\s*<button class="ai-global-btn" onclick="globalMDA\(\)">✦ Download MD&A ↗<\/button>/,
    TOPBAR_EXPORTS,
  );
  out = out.replace(
    /<span class="period-badge" id="periodBadge"><\/span>\s*<button class="ai-global-btn" onclick="globalMDA\(\)">✦ MD&A Deck ↗<\/button>\s*<button class="ai-global-btn" onclick="varComm\(\)">✦ Variance Commentary ↗<\/button>/,
    TOPBAR_EXPORTS,
  );

  // Footer: remove bottom export buttons
  out = out.replace(
    /<div class="footer">[\s\S]*?<\/div>\s*(?=<script src="https:\/\/cdnjs)/,
    FOOTER_SIMPLE + "\n\n",
  );

  // Export handlers → committed public/board-sample/exports paths
  out = out.replace(
    /function globalMDA\(\)\{window\.open\('SMPL_MDA_Package_May2026\.xlsx'\);\}\s*function varComm\(\)\{window\.open\('SMPL_MDA_Package_May2026\.xlsx'\);\}\s*function decBrief\(\)\{window\.open\('SMPL_Board_Review_May2026\.pptx'\);\}/,
    EXPORT_BLOCK.trim(),
  );

  if (!out.includes("const BOARD_EXPORTS")) {
    out = out.replace(
      /function globalMDA\(\)\s*\{[\s\S]*?\}\s*function varComm\(\)\s*\{[\s\S]*?\}(?:\s*function decBrief\(\)\s*\{[\s\S]*?\})?/,
      EXPORT_BLOCK.trim(),
    );
  }

  // Static commentary (no Anthropic API)
  out = out.replace(
    /async function aiComm\([\s\S]*?(?=function globalMDA|function renderThreeStmt|const BOARD_EXPORTS)/,
    `${STATIC_AI_COMM.trim()}\n\n`,
  );

  out = out.replace(
    /async function cpSend\(\)[\s\S]*?(?=function formatCopilotReply)/,
    `${STATIC_CP_SEND.trim()}\n\n`,
  );

  // Footer month label
  if (!out.includes("getElementById('footerCloseMo')")) {
    out = out.replace(
      /document\.getElementById\('periodBadge'\)\.textContent = CLOSE_LABEL \+ ' \\u00b7 YTD Close';/,
      "document.getElementById('periodBadge').textContent = CLOSE_LABEL + ' \\u00b7 YTD Close';\nconst _footerMo = document.getElementById('footerCloseMo');\nif (_footerMo) _footerMo.textContent = CLOSE_MO;",
    );
  }

  return out;
}
