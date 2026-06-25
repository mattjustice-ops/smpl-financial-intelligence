import { existsSync, readFileSync } from "fs";
import { join } from "path";

const SAMPLE_EXPORTS = {
  boardReview: "/board-sample/exports/SMPL_Board_Review_Q2_2026.pptx",
  mdaPackage: "/board-sample/exports/SMPL_MDA_Package_June2026.xlsx",
} as const;

const BOARD_EXEC_NAV = `
/** Executive summary KPI cards → primary nav tabs */
function boardExecNav(tab) {
  const btn = Array.from(document.querySelectorAll('.nav-btn')).find(function (b) {
    return (b.getAttribute('onclick') || '').indexOf("show('" + tab + "'") >= 0;
  });
  show(tab, btn || null);
}
`;

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

/** Static sample only — no live Anthropic calls from the marketing view. */
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

function resolveSampleSourcePath(): string | null {
  const cwd = process.cwd();
  const candidates = [
    join(cwd, "public", "board-sample", "index.html"),
    process.env.SMPL_BOARD_SAMPLE_SRC?.trim(),
    join(cwd, "canonical", "board-sample", "index.html"),
    "C:\\Users\\mattj\\Downloads\\SMPL_Board_Platform_June2026 (10).html",
  ].filter((p): p is string => Boolean(p));

  for (const path of candidates) {
    if (existsSync(path)) return path;
  }
  return null;
}

export function patchBoardSampleHtml(html: string): string {
  let out = html;

  out = out.replace(
    /<title>SMPL · We make finance simple · June 2026<\/title>/,
    "<title>SMPL · Board sample · June 2026</title>",
  );

  out = out.replace(
    /SMPL · Board Intelligence · Jan–<span id="footerCloseMo"><\/span> 2026 Actuals · AI commentary via Claude · Confidential/,
    "SMPL · Board sample · Jan–<span id=\"footerCloseMo\"></span> 2026 · Illustrative static data · MD&A &amp; variance exports only",
  );

  if (!out.includes("function boardExecNav")) {
    out = out.replace("function destroyCharts()", `${BOARD_EXEC_NAV}\nfunction destroyCharts()`);
  }

  out = out.replace(
    /\$\{\[\s*\{lbl:'Ending ARR',\s*val:'\$86\.1M',\s*delta:'\+\$0\.58M vs bud', dir:'pos', because:'Best net new ARR month of H1 — new logos \+ expansion both beat plan', link:'View waterfall →'\},/,
    "${[\n      {lbl:'Ending ARR',     val:'$86.1M',   delta:'+$0.58M vs bud', dir:'pos', because:'Best net new ARR month of H1 — new logos + expansion both beat plan', link:'View waterfall →', tab:'arr'},",
  );
  out = out.replace(
    /\{lbl:'Net New ARR',\s*val:'\$2\.655M',\s*delta:'\+\$0\.47M vs bud', dir:'pos', because:'New business \$1\.92M \(\+\$0\.19M\) and expansion \$0\.98M \(\+\$0\.13M\) drove outperformance', link:'View driver tree →'\},/,
    "{lbl:'Net New ARR',    val:'$2.655M',  delta:'+$0.47M vs bud', dir:'pos', because:'New business $1.92M (+$0.19M) and expansion $0.98M (+$0.13M) drove outperformance', link:'View driver tree →', tab:'arr'},",
  );
  out = out.replace(
    /\{lbl:'EBITDA',\s*val:'-\$1\.30M',\s*delta:'-\$1\.08M vs bud', dir:'neg', because:'Q2 variable comp accrual timing — underlying operating leverage is intact; normalizes Q3', link:'View P&L →'\},/,
    "{lbl:'EBITDA',         val:'-$1.30M',  delta:'-$1.08M vs bud', dir:'neg', because:'Q2 variable comp accrual timing — underlying operating leverage is intact; normalizes Q3', link:'View P&L →', tab:'pl'},",
  );
  out = out.replace(
    /\{lbl:'Cash Balance',\s*val:'\$70\.61M',\s*delta:'\+\$39\.1M vs bud', dir:'pos', because:'Annual billing collection cycle front-loaded; \$39M above budget reflects billing structure', link:'View cash →'\},/,
    "{lbl:'Cash Balance',   val:'$70.61M',  delta:'+$39.1M vs bud', dir:'pos', because:'Annual billing collection cycle front-loaded; $39M above budget reflects billing structure', link:'View cash →', tab:'cash'},",
  );
  out = out.replace(
    /<div style="font-size:10px;color:var\(--accent\);cursor:pointer;font-weight:500">\$\{h\.link\}<\/div>/,
    '<div style="font-size:10px;color:var(--accent);cursor:pointer;font-weight:500" onclick="boardExecNav(\'${h.tab}\')" role="link" tabindex="0">${h.link}</div>',
  );

  out = out.replace(
    /function globalMDA\(\)\{window\.open\('SMPL_MDA_Package_May2026\.xlsx'\);\}\s*function varComm\(\)\{window\.open\('SMPL_MDA_Package_May2026\.xlsx'\);\}\s*function decBrief\(\)\{window\.open\('SMPL_Board_Review_May2026\.pptx'\);\}/,
    EXPORT_BLOCK,
  );

  out = out.replace(/async function aiComm\([\s\S]*?(?=function globalMDA|function renderThreeStmt|const BOARD_EXPORTS)/, STATIC_AI_COMM.trim() + "\n\n");
  out = out.replace(/async function cpSend\(\)[\s\S]*?(?=function formatCopilotReply)/, STATIC_CP_SEND.trim() + "\n\n");

  return out;
}

export function loadBoardSampleHtml(): string | null {
  const path = resolveSampleSourcePath();
  if (!path) return null;
  const raw = readFileSync(path, "utf-8");
  return patchBoardSampleHtml(raw);
}

export function boardSampleSetupMessage(): string {
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Board sample setup</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 24px;line-height:1.6;color:#0f172a}
code{background:#f1f5f9;padding:2px 6px;border-radius:4px}</style></head>
<body>
<h1>Board sample not found</h1>
<p>Restore the static marketing sample from <code>frontend/</code>:</p>
<pre><code>npm run create:board-sample
npm run copy:board-exports</code></pre>
<p>Or set <code>SMPL_BOARD_SAMPLE_SRC</code> to the original HTML board template path.</p>
</body></html>`;
}
