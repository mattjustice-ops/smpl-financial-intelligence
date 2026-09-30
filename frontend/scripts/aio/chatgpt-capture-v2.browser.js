// ChatGPT AIO capture v2. Runs inside a chatgpt.com tab; processes one queued prompt per call.
//
// Setup (once per run, from DevTools / CDP Runtime.evaluate on chatgpt.com):
//   localStorage.setItem("smpl_aio_v2_src", <this file's text>)
//   localStorage.setItem("smpl_aio_v2_queue", JSON.stringify({ runId, idx: 0, attempts: {}, items: [{ key, id, query, trial, phase }] }))
// Each call:
//   new Function(localStorage.getItem("smpl_aio_v2_src"))()
// The call sends the current prompt in a fresh temporary chat, stores a structured record under
// localStorage "smpl_aio_v2_results"[key], then navigates to the next prompt's URL.
// To run a whole queue unattended, use chatgpt-capture-v2.driver.browser.js instead.
//
// Every prompt gets its own conversation: the prompt URL opens a new temporary chat with web
// search pre-selected (?temporary-chat=true&hints=search&q=...). Personalization must already be
// set to "Unpersonalized" in the account; the script refuses to send otherwise.
return (async () => {
  const QK = "smpl_aio_v2_queue";
  const RK = "smpl_aio_v2_results";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const q = JSON.parse(localStorage.getItem(QK) || "null");
  if (!q) return { error: "no queue" };
  q.attempts = q.attempts || {};
  const item = q.items[q.idx];
  if (!item) return { done: true, total: q.items.length };
  const urlFor = (it) =>
    "https://chatgpt.com/?temporary-chat=true&hints=search&q=" + encodeURIComponent(it.query);
  const saveQueue = () => localStorage.setItem(QK, JSON.stringify(q));
  const goNext = () => {
    const next = q.items[q.idx];
    if (next) setTimeout(() => (location.href = urlFor(next)), 400);
  };

  // ChatGPT strips ?q=&hints= after pre-filling the composer, so readiness is judged by the
  // composer text below; any conversation page (/c/...) means we still need a fresh chat.
  if (location.pathname !== "/") {
    location.href = urlFor(item);
    return { navigating: item.key };
  }

  const bodyText = () => document.body.innerText;
  let send;
  let box;
  let ready = false;
  for (let i = 0; i < 80; i++) {
    send = document.querySelector('button[aria-label="Send"]');
    box = document.querySelector("[contenteditable=true]");
    ready =
      !!send &&
      !send.disabled &&
      !!box &&
      norm(box.innerText) === norm(item.query) &&
      !!document.querySelector('button[aria-label="Remove Web search"]') &&
      /Unpersonalized/.test(bodyText()) &&
      /Temporary chat/.test(bodyText());
    if (ready) break;
    await sleep(500);
  }
  if (!ready) {
    const n = (q.attempts[item.key] = (q.attempts[item.key] || 0) + 1);
    const why = {
      send: !!send && !send.disabled,
      promptMatches: !!box && norm(box.innerText) === norm(item.query),
      webSearch: !!document.querySelector('button[aria-label="Remove Web search"]'),
      unpersonalized: /Unpersonalized/.test(bodyText()),
      temporary: /Temporary chat/.test(bodyText()),
    };
    if (n >= 3) {
      const results = JSON.parse(localStorage.getItem(RK) || "{}");
      results[item.key] = { schema: "aio_capture_v2", runId: q.runId, key: item.key, queryId: item.id, queryText: item.query, trial: item.trial, phase: item.phase, error: "not_ready", why, capturedAt: new Date().toISOString() };
      localStorage.setItem(RK, JSON.stringify(results));
      q.idx += 1;
      saveQueue();
      goNext();
      return { key: item.key, error: "not_ready_skipped", why };
    }
    saveQueue();
    location.href = urlFor(item);
    return { key: item.key, retry: n, why };
  }

  const modelBtn = document.querySelector('button[aria-label="Select ChatGPT model"]');
  const environment = {
    interface: "chatgpt.com web app (Cursor embedded browser, signed-in account)",
    promptUrl: urlFor(item),
    pageUrlAtSend: location.href,
    temporaryChat: /temporary-chat=true/.test(location.search) && /Temporary chat/.test(bodyText()),
    memoryAndInstructionsIgnoredNotice: /ignore memory/i.test(bodyText()),
    personalization: /Unpersonalized/.test(bodyText()) ? "Unpersonalized" : "unknown",
    webSearchSelected: !!document.querySelector('button[aria-label="Remove Web search"]'),
    modelSelectorLabel: modelBtn ? norm(modelBtn.innerText) : null,
    userAgent: navigator.userAgent,
    viewport: `${innerWidth}x${innerHeight}`,
  };
  const promptText = norm(box.innerText);
  const sentAt = new Date();
  send.click();
  await sleep(4000);

  const getUnit = () => {
    const u = [...document.querySelectorAll('[data-chatgpt-search-unit-key$=":assistant"]')];
    return u[u.length - 1];
  };
  const getMd = () => getUnit()?.querySelector('[data-markdown-text-style="assistant-message"]');
  let last = "";
  let stable = 0;
  let timedOut = true;
  for (let i = 0; i < 300; i++) {
    const stop = document.querySelector('button[aria-label*="Stop" i]');
    const txt = getMd()?.innerText || "";
    if (!stop && txt.length > 40 && txt === last) {
      stable += 1;
      if (stable >= 3) {
        timedOut = false;
        break;
      }
    } else stable = 0;
    last = txt;
    await sleep(1000);
  }
  const unit = getUnit();
  const md = getMd();
  const completedAt = new Date();
  if (!md) {
    const results = JSON.parse(localStorage.getItem(RK) || "{}");
    results[item.key] = { schema: "aio_capture_v2", runId: q.runId, key: item.key, queryId: item.id, queryText: item.query, trial: item.trial, phase: item.phase, error: "no_assistant_message", environment, sentAt: sentAt.toISOString(), capturedAt: completedAt.toISOString() };
    localStorage.setItem(RK, JSON.stringify(results));
    q.idx += 1;
    saveQueue();
    goNext();
    return { key: item.key, error: "no_assistant_message" };
  }

  const answerText = md.innerText;
  const PILL = 'a[data-testid="chatgpt-citation"]';
  const parseLabel = (aria) => {
    const m = /^(.*?): (.*), (https?:\/\/\S+?)(?:, (\d+) additional sources?)?$/.exec(aria || "");
    if (!m) return { publisher: null, title: null, url: null, additional: 0 };
    return { publisher: m[1], title: m[2], url: m[3], additional: Number(m[4] || 0) };
  };
  const blockOf = (el) => el.closest("p,li,td,th,h1,h2,h3,h4,h5,h6,blockquote") || el.parentElement;
  const textWithoutPills = (el) => {
    const c = el.cloneNode(true);
    c.querySelectorAll("span[data-search-result-target]," + PILL).forEach((n) => n.remove());
    return norm(c.textContent);
  };
  const tooltipFor = (url) =>
    [...document.querySelectorAll('[role="tooltip"]')].find((t) =>
      [...t.querySelectorAll("a[href]")].some((a) => a.href === url),
    );
  const openTooltip = async (a) => {
    for (const el of [a, a.parentElement]) {
      for (const ev of ["pointerover", "pointerenter", "mouseover", "mouseenter", "focus", "focusin"]) {
        const Ctor = ev.startsWith("pointer") ? PointerEvent : ev.startsWith("focus") ? FocusEvent : MouseEvent;
        el.dispatchEvent(new Ctor(ev, { bubbles: !ev.endsWith("enter"), cancelable: true, pointerType: "mouse" }));
      }
    }
    a.focus();
    for (let i = 0; i < 20; i++) {
      const t = tooltipFor(a.href) || document.querySelector('[role="tooltip"]');
      if (t && t.querySelector("a[href]")) return t;
      await sleep(150);
    }
    return null;
  };
  const closeTooltip = async (a) => {
    for (const el of [a, a.parentElement]) {
      for (const ev of ["pointerleave", "mouseleave", "pointerout", "mouseout", "blur", "focusout"]) {
        const Ctor = ev.startsWith("pointer") ? PointerEvent : ev.startsWith("blur") || ev.startsWith("focus") ? FocusEvent : MouseEvent;
        el.dispatchEvent(new Ctor(ev, { bubbles: !ev.endsWith("leave") && ev !== "blur", cancelable: true, pointerType: "mouse" }));
      }
    }
    a.blur();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    for (let i = 0; i < 10 && document.querySelector('[role="tooltip"] a[href]'); i++) await sleep(150);
  };

  const pills = [];
  const sources = [];
  let expansionFailures = 0;
  const pillEls = [...md.querySelectorAll(PILL)];
  for (let i = 0; i < pillEls.length; i++) {
    const a = pillEls[i];
    const meta = parseLabel(a.getAttribute("aria-label"));
    const url = meta.url || a.href;
    const paragraph = textWithoutPills(blockOf(a)).slice(0, 600);
    const pill = {
      index: i,
      label: norm((a.innerText || "").split("\n")[0]),
      publisher: meta.publisher,
      title: meta.title,
      url,
      additionalCount: meta.additional,
      expanded: [],
      paragraph,
    };
    sources.push({ url, title: meta.title, publisher: meta.publisher, paragraph, pillIndex: i, hidden: false });
    if (meta.additional > 0) {
      const seen = new Set([url]);
      const t = await openTooltip(a);
      if (t) {
        for (let p = 0; p < meta.additional + 1; p++) {
          const tip = document.querySelector('[role="tooltip"]');
          const link = tip && tip.querySelector("a[href]");
          if (link && !seen.has(link.href)) {
            seen.add(link.href);
            const m = parseLabel(link.getAttribute("aria-label") + "");
            const hidden = { url: link.href, title: m.title, publisher: m.publisher };
            pill.expanded.push(hidden);
            sources.push({ ...hidden, paragraph, pillIndex: i, hidden: true });
          }
          const next = tip && tip.querySelector('button[aria-label="Next source"]');
          if (!next) break;
          next.click();
          await sleep(450);
        }
      }
      await closeTooltip(a);
      if (pill.expanded.length < meta.additional) expansionFailures += 1;
    }
    pills.push(pill);
  }

  const inlineLinks = [...md.querySelectorAll("a[href]")]
    .filter((a) => !a.closest(PILL))
    .map((a) => ({ url: a.href, text: norm(a.innerText), paragraph: textWithoutPills(blockOf(a)).slice(0, 600) }));
  for (const l of inlineLinks) {
    sources.push({ url: l.url, title: l.text, publisher: null, paragraph: l.paragraph, pillIndex: null, hidden: false, inline: true });
  }
  const outsideLinks = [...unit.querySelectorAll("a[href]")]
    .filter((a) => !md.contains(a))
    .map((a) => ({ url: a.href, text: norm(a.innerText) }));

  const clone = md.cloneNode(true);
  clone.querySelectorAll("span[data-search-result-target]," + PILL).forEach((n) => n.remove());
  const holder = document.createElement("div");
  holder.style.cssText = `position:fixed;left:-30000px;top:0;width:${md.clientWidth || 700}px;`;
  holder.appendChild(clone);
  document.body.appendChild(holder);
  const proseText = clone.innerText;
  holder.remove();

  const htmlClone = md.cloneNode(true);
  htmlClone.querySelectorAll("svg,img,button").forEach((n) => n.remove());
  htmlClone.querySelectorAll("*").forEach((n) => {
    for (const at of [...n.attributes]) {
      if (!["href", "data-testid", "aria-label"].includes(at.name)) n.removeAttribute(at.name);
    }
  });

  const citationStatus =
    pills.length === 0 && inlineLinks.length === 0
      ? "none_shown"
      : expansionFailures > 0 || timedOut
        ? "partial"
        : "complete";

  const record = {
    schema: "aio_capture_v2",
    runId: q.runId,
    key: item.key,
    queryId: item.id,
    queryText: item.query,
    trial: item.trial,
    phase: item.phase,
    promptText,
    promptMatches: promptText === norm(item.query),
    conversationUrl: location.href,
    sentAt: sentAt.toISOString(),
    completedAt: completedAt.toISOString(),
    durationSec: Math.round((completedAt - sentAt) / 1000),
    responseTimedOut: timedOut,
    environment,
    answerText,
    proseText,
    answerHtml: htmlClone.innerHTML,
    citationLabels: pills.map((p) => p.label),
    pills,
    sources,
    inlineLinks,
    outsideLinks,
    citationStatus,
    expansionFailures,
    capturedAt: new Date().toISOString(),
  };
  const results = JSON.parse(localStorage.getItem(RK) || "{}");
  results[item.key] = record;
  localStorage.setItem(RK, JSON.stringify(results));
  q.idx += 1;
  saveQueue();
  goNext();
  return {
    key: item.key,
    done: q.idx,
    total: q.items.length,
    len: answerText.length,
    pills: pills.length,
    sources: sources.length,
    hidden: sources.filter((s) => s.hidden).length,
    status: citationStatus,
    model: environment.modelSelectorLabel,
    secs: record.durationSec,
    kb: Math.round(JSON.stringify(results).length / 1024),
  };
})();
