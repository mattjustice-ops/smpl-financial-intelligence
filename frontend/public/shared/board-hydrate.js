/**
 * Board Platform — live warehouse hydration + Claude API (same pattern as Forecast Engine).
 */
(function (global) {
  "use strict";

  var BOARD_SLIDE_API_KEYS = {
    exec: "executive_summary",
    arr: "arr_waterfall",
    revenue: "gaap_revenue",
    gtm: "gtm_performance",
    cash: "cash_forecast",
    headcount: "headcount",
    risks: "risks_opportunities",
  };

  function monthNames() {
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  }

  function boardActiveCloseMonth() {
    return global.CLOSE_MONTH || global.SMPL_CLOSE_MONTH || "2026-06";
  }

  function boardActualPeriods() {
    var cm = boardActiveCloseMonth();
    var y = cm.slice(0, 4);
    var n = parseInt(cm.slice(5), 10);
    var out = [];
    for (var i = 1; i <= n; i++) {
      out.push(y + "-" + String(i).padStart(2, "0"));
    }
    return out;
  }

  function fKpiM(v, d) {
    d = d == null ? 1 : d;
    if (v == null || Number.isNaN(v)) return "—";
    var abs = Math.abs(v);
    if (abs >= 1) return (v < 0 ? "-" : "") + "$" + abs.toFixed(d) + "M";
    if (abs >= 0.001) return (v < 0 ? "-" : "") + "$" + Math.round(abs * 1000) + "k";
    return "$0";
  }

  function fKpiVarM(v) {
    if (v == null || Number.isNaN(v)) return "—";
    return (v >= 0 ? "+" : "") + fKpiM(v);
  }

  function fKpiPct(v) {
    if (v == null || Number.isNaN(v)) return "—";
    return (v * 100).toFixed(1) + "%";
  }

  function boardJunMetrics() {
    var cm = boardActiveCloseMonth();
    var ts = (global.SMPLOutlook && global.SMPLOutlook.getOutlookTsData && global.SMPLOutlook.getOutlookTsData()) || global.TS_DATA || {};
    var isA = (ts.Actual && ts.Actual.is && ts.Actual.is[cm]) || {};
    var isB = (ts.Budget && ts.Budget.is && ts.Budget.is[cm]) || {};
    var bsA = (ts.Actual && ts.Actual.bs && ts.Actual.bs[cm]) || {};
    var bsB = (ts.Budget && ts.Budget.bs && ts.Budget.bs[cm]) || {};
    var src =
      (global.SMPL_OUTLOOK_PAYLOAD &&
        global.SMPL_OUTLOOK_PAYLOAD.SRC &&
        global.SMPL_OUTLOOK_PAYLOAD.SRC.actuals &&
        global.SMPL_OUTLOOK_PAYLOAD.SRC.actuals[cm]) ||
      {};
    var wf = global.SMPL_ARR_WATERFALL || {};
    var idx = boardActualPeriods().length - 1;
    var arrAct =
      wf.Ending && wf.Ending[idx] != null ? wf.Ending[idx] / 1e6 : global.ARR_ACT && global.ARR_ACT[idx];
    var arrBud =
      wf.Budget_Ending && wf.Budget_Ending[idx] != null
        ? wf.Budget_Ending[idx] / 1e6
        : global.ARR_BUD && global.ARR_BUD[idx];
    return {
      arrAct: arrAct,
      arrBud: arrBud,
      revAct: isA.revenue != null ? isA.revenue / 1e6 : null,
      revBud: isB.revenue != null ? isB.revenue / 1e6 : null,
      ebitdaAct: isA.ebitda != null ? isA.ebitda / 1e6 : null,
      ebitdaBud: isB.ebitda != null ? isB.ebitda / 1e6 : null,
      cashAct: bsA.cash != null ? bsA.cash / 1e6 : null,
      cashBud: bsB.cash != null ? bsB.cash / 1e6 : null,
      gmAct: isA.gm_pct,
      gmBud: isB.gm_pct,
      nrr: src.nrr,
    };
  }

  function boardExecDrivers() {
    var cm = boardActiveCloseMonth();
    var wf = global.SMPL_ARR_WATERFALL || {};
    var idx = boardActualPeriods().length - 1;
    function row(key, label) {
      var act = wf[key] && wf[key][idx] != null ? wf[key][idx] / 1e6 : 0;
      var budKey = "Budget_" + key.replace(/ /g, "_");
      var bud =
        wf[budKey] && wf[budKey][idx] != null
          ? wf[budKey][idx] / 1e6
          : wf[key + "_Budget"] && wf[key + "_Budget"][idx] != null
            ? wf[key + "_Budget"][idx] / 1e6
            : 0;
      return { label: label, val: act, bud: bud };
    }
    var drivers = [
      row("New Business", "New Business"),
      row("Expansion", "Expansion"),
      row("Reactivation", "Reactivation"),
      row("Contraction", "Contraction"),
      row("Churn", "Churn"),
    ];
    var nnAct = drivers.reduce(function (s, d) {
      return s + d.val;
    }, 0);
    var nnBud = drivers.reduce(function (s, d) {
      return s + d.bud;
    }, 0);
    var maxAbs = Math.max.apply(
      null,
      drivers.map(function (d) {
        return Math.abs(d.val);
      }).concat([0.01]),
    );
    drivers.forEach(function (d) {
      d.pct = Math.round((Math.abs(d.val) / maxAbs) * 100);
    });
    return { nnAct: nnAct, nnBud: nnBud, drivers: drivers };
  }

  function syncBoardFromOutlook(data) {
    if (!data || !data.meta) return;
    var cm = data.meta.close_month;
    if (cm) {
      global.CLOSE_MONTH = cm;
      global.SMPL_CLOSE_MONTH = cm;
      var names = monthNames();
      var idx = parseInt(cm.slice(5), 10) - 1;
      global.CLOSE_MO = names[idx] || cm.slice(5, 7);
      global.CLOSE_LABEL = global.CLOSE_MO + " " + cm.slice(0, 4);
      global.ACT_MONTHS_COUNT = idx + 1;
      global.CLOSE_MO_IDX = idx;
      var badge = document.getElementById("periodBadge");
      if (badge) badge.textContent = global.CLOSE_LABEL + " \u00b7 YTD Close";
    }

    if (data.ARR_WATERFALL && global.SMPL_DEMO_WF_TABLE && global.SMPLOutlook && global.SMPLOutlook.replaceArrWaterfallTable) {
      global.SMPLOutlook.replaceArrWaterfallTable(global.SMPL_DEMO_WF_TABLE, data.ARR_WATERFALL);
    }

    if (typeof global.boardRefreshAllSeries === "function") {
      global.boardRefreshAllSeries();
    }

    if (data.CASH_BRIDGE && data.CASH_BRIDGE.Actual && global.COLL) {
      var periods = boardActualPeriods();
      periods.forEach(function (period, i) {
        if (i >= global.COLL.length) return;
        var row = data.CASH_BRIDGE.Actual[period];
        if (row && row.collections != null) {
          global.COLL[i] = +(row.collections / 1e6).toFixed(2);
        }
      });
    }

    if (typeof global.tsRender === "function") {
      try {
        global.tsRender();
      } catch (err) {
        console.error("[board-hydrate] tsRender after outlook failed", err);
      }
    }

    if (global.SMPLBoardLive && global.SMPLBoardLive.updateCopilotContext) {
      global.SMPLBoardLive.updateCopilotContext(data);
    }

    refreshExecCommentaryFromLiveMetrics();
  }

  function smplBoardRefreshView() {
    var active = document.querySelector(".nav-btn.active");
    var tab = "exec";
    if (active) {
      var m = active.getAttribute("onclick");
      if (m) {
        var hit = m.match(/show\('(\w+)'/);
        if (hit) tab = hit[1];
      }
    }
    if (typeof global.show === "function") {
      global.show(tab, active);
    }
  }
  global.smplBoardRefreshView = smplBoardRefreshView;

  async function boardSessionOrgs() {
    try {
      var res = await fetch("/api/auth/session", { credentials: "include" });
      if (!res.ok) return null;
      var j = await res.json();
      if (!j || !j.user) return null;
      var orgIds = (j.user.organizations || [])
        .map(function (o) {
          return o.organizationId;
        })
        .filter(Boolean);
      return {
        activeId: j.user.activeOrganizationId || null,
        orgIds: orgIds,
      };
    } catch (_) {
      return null;
    }
  }

  function pickAccessibleOrgId(preferred, sessionOrgs) {
    if (!sessionOrgs || !sessionOrgs.orgIds.length) return preferred || null;
    if (preferred && sessionOrgs.orgIds.indexOf(preferred) >= 0) return preferred;
    if (sessionOrgs.activeId && sessionOrgs.orgIds.indexOf(sessionOrgs.activeId) >= 0) {
      return sessionOrgs.activeId;
    }
    return sessionOrgs.orgIds[0];
  }

  async function boardResolveOrgId() {
    var sessionOrgs = await boardSessionOrgs();
    if (global.SMPL_ORG_ID) {
      return pickAccessibleOrgId(global.SMPL_ORG_ID, sessionOrgs);
    }
    if (global.SMPLOutlook && global.SMPLOutlook.resolveOrgId) {
      var resolved = await global.SMPLOutlook.resolveOrgId({ waitForParent: true, parentWaitMs: 4000 });
      return pickAccessibleOrgId(resolved, sessionOrgs);
    }
    return sessionOrgs ? pickAccessibleOrgId(null, sessionOrgs) : null;
  }

  /** Same-origin Next proxy on prod (session + X-SFI-User-Id). Direct Railway only on localhost. */
  async function boardLiveApiBase() {
    var host = global.location && global.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8001";
    }
    return "";
  }

  function boardLiveFetchInit(apiBase, init) {
    var opts = Object.assign({}, init || {});
    if (apiBase) {
      opts.credentials = "omit";
      opts.mode = "cors";
    } else {
      opts.credentials = "include";
    }
    return opts;
  }

  function boardLiveUrl(apiBase, path) {
    return (apiBase || "") + path;
  }

  function boardFetchWithTimeout(url, init, timeoutMs) {
    timeoutMs = timeoutMs == null ? 295000 : timeoutMs;
    var controller = new AbortController();
    var timer = setTimeout(function () {
      controller.abort("board-request-timeout");
    }, timeoutMs);
    var opts = Object.assign({}, init || {}, { signal: controller.signal });
    return fetch(url, opts).finally(function () {
      clearTimeout(timer);
    });
  }

  function boardFetchErrorMessage(err, timeoutMs) {
    if (!err) return "Request failed.";
    if (err === "board-request-timeout" || err.name === "AbortError") {
      var secs = Math.round((timeoutMs || 295000) / 1000);
      return (
        "Request timed out after " +
        secs +
        "s. Claude exports can take several minutes — confirm Railway API is healthy and ANTHROPIC_API_KEY is set, then retry."
      );
    }
    if (err.message === "Failed to fetch" || (err.message && err.message.indexOf("NetworkError") >= 0)) {
      return (
        "Network error reaching the API. Stay on /app/board (signed in), hard refresh, and retry. " +
        "If exports time out, confirm SFI_BACKEND_URL on Vercel points to Railway."
      );
    }
    return err.message ? err.message : String(err);
  }

  async function boardApiErrorMessage(res) {
    try {
      var text = await res.text();
      if (!text) return "Request failed (" + res.status + ")";
      try {
        var j = JSON.parse(text);
        var detail = j.detail;
        if (typeof detail === "string") return detail;
        if (detail && typeof detail === "object") {
          var msg = detail.message || detail.code || "Request failed (" + res.status + ")";
          var checks = detail.validation && detail.validation.checks;
          if (checks && checks.length) {
            var issues = checks
              .filter(function (c) {
                return c.status === "fail" || c.status === "warning";
              })
              .slice(0, 4)
              .map(function (c) {
                return c.validation_name + " (" + c.period + "): " + c.status;
              });
            if (issues.length) msg += " — " + issues.join("; ");
          }
          return msg;
        }
        return text.slice(0, 500);
      } catch (_) {
        if (/upstream error|ROUTER_EXTERNAL_TARGET|An error occurred with this application/i.test(text)) {
          return (
            "Export timed out on the web proxy (upstream error). Retrying via Railway direct… " +
            "If both attempts fail, confirm SFI_BACKEND_URL on Vercel and Railway /export/ping health."
          );
        }
        return text.slice(0, 500);
      }
    } catch (_) {
      return "Request failed (" + res.status + ")";
    }
  }

  function formatApiCommentary(c) {
    if (!c || typeof c !== "object") return "";
    if (c.narrative) return c.narrative;
    // Single-paragraph Claude output (no rule-based boilerplate fields)
    if (c.what_happened && !c.impact && !c.recommended_actions && !c.leadership_watch) {
      return c.what_happened;
    }
    if (c.what_happened && c.why_it_happened) {
      return (c.what_happened + " " + c.why_it_happened).trim();
    }
    return c.what_happened || "";
  }

  var BOARD_COMMENTARY_SLIDE_FOR_TAB = {
    exec: "exec",
    arr: "arr",
    revenue: "revenue",
    gtm: "gtm",
    cash: "cash",
    workforce: "headcount",
    risks: "risks",
  };

  var BOARD_COMMENTARY_TARGET = {
    exec: "execComm",
    arr: "arrComm",
    revenue: "revComm",
    gtm: "gtmComm",
    cash: "cashComm",
    headcount: "hcComm",
    risks: "riskComm",
  };

  function restoreSlideCommentary(tabName) {
    var slideKey = BOARD_COMMENTARY_SLIDE_FOR_TAB[tabName];
    if (!slideKey || !global.aiCache || !global.aiCache[slideKey]) return;
    var targetId = BOARD_COMMENTARY_TARGET[slideKey];
    if (!targetId) return;
    var el = document.getElementById(targetId);
    if (!el) return;
    var txt = el.querySelector(".commentary-text");
    if (txt) txt.textContent = global.aiCache[slideKey];
  }

  function installCommentaryCacheRestore() {
    if (global._smplCommentaryRestoreInstalled || !global.show) return;
    global._smplCommentaryRestoreInstalled = true;
    var origShow = global.show;
    global.show = function (name, btn) {
      origShow(name, btn);
      setTimeout(function () {
        restoreSlideCommentary(name);
      }, 0);
    };
  }

  function formatDemoFacts(facts) {
    if (!facts) return "";
    var parts = facts.split(/(?<=[.!?])\s+/).filter(Boolean);
    if (parts.length <= 4) return facts;
    return parts.slice(0, 2).join(" ") + " " + parts.slice(2, 4).join(" ") + " " + parts.slice(4).join(" ");
  }

  function readStaticCommentary(slideKey, targetId) {
    global._smplStaticComm = global._smplStaticComm || {};
    if (!global._smplStaticComm[slideKey]) {
      var el = document.getElementById(targetId);
      var node = el && el.querySelector(".commentary-text");
      var text = node && node.textContent ? node.textContent.trim() : "";
      if (!text && global.AI_CTX && global.AI_CTX[slideKey]) {
        text = formatDemoFacts(global.AI_CTX[slideKey]);
      }
      global._smplStaticComm[slideKey] = text || "Commentary unavailable.";
    }
    return global._smplStaticComm[slideKey];
  }

  function hasLiveBoardMetrics() {
    var m = boardJunMetrics();
    return m.arrAct != null || m.revAct != null || m.cashAct != null;
  }

  function buildLiveExecCommentary() {
    var m = boardJunMetrics();
    var drivers = boardExecDrivers();
    var closeLbl = global.CLOSE_LABEL || "Close";
    var arrVar = m.arrAct != null && m.arrBud != null ? m.arrAct - m.arrBud : 0;
    var revVar = m.revAct != null && m.revBud != null ? m.revAct - m.revBud : 0;
    var ebitdaVar = m.ebitdaAct != null && m.ebitdaBud != null ? m.ebitdaAct - m.ebitdaBud : 0;
    var cashVar = m.cashAct != null && m.cashBud != null ? m.cashAct - m.cashBud : 0;
    var nrrPct = m.nrr != null ? (m.nrr * 100).toFixed(1) + "%" : "—";
    return (
      closeLbl +
      " close: ARR " +
      fKpiM(m.arrAct) +
      " (" +
      fKpiVarM(arrVar) +
      " vs bud), net new " +
      fKpiM(drivers.nnAct) +
      ", revenue " +
      fKpiM(m.revAct) +
      " (" +
      fKpiVarM(revVar) +
      " vs bud), EBITDA " +
      fKpiM(m.ebitdaAct) +
      " (" +
      fKpiVarM(ebitdaVar) +
      " vs bud), cash " +
      fKpiM(m.cashAct) +
      " (" +
      fKpiVarM(cashVar) +
      " vs bud), N$R " +
      nrrPct +
      "."
    );
  }

  function buildDemoCommentary(slideKey, targetId) {
    if (slideKey === "exec" && hasLiveBoardMetrics()) {
      return buildLiveExecCommentary();
    }
    return readStaticCommentary(slideKey, targetId);
  }

  function refreshExecCommentaryFromLiveMetrics() {
    if (global.aiCache && global.aiCache.exec) return;
    var execComm = document.getElementById("execComm");
    if (!execComm || !hasLiveBoardMetrics()) return;
    var txt = execComm.querySelector(".commentary-text");
    if (txt) txt.textContent = buildLiveExecCommentary();
  }

  function shouldFallbackToDemo(status) {
    // Auth / org mismatch → embedded demo. API/LLM outages surface explicit errors instead.
    return status === 401 || status === 403 || status === 409;
  }

  function cacheAllStaticCommentary() {
    var map = {
      exec: "execComm",
      arr: "arrComm",
      revenue: "revComm",
      gtm: "gtmComm",
      cash: "cashComm",
      headcount: "hcComm",
      risks: "riskComm",
    };
    Object.keys(map).forEach(function (key) {
      readStaticCommentary(key, map[key]);
    });
  }

  function installLiveAi() {
    if (global._smplBoardAiInstalled) return;
    global._smplBoardAiInstalled = true;
    cacheAllStaticCommentary();

    global.aiComm = async function aiComm(slideKey, targetId) {
      global.aiCache = global.aiCache || {};
      delete global.aiCache[slideKey];

      var el = document.getElementById(targetId);
      if (!el) return;
      var txt = el.querySelector(".commentary-text");
      txt.innerHTML = '<span class="spin"></span> Generating AI commentary...';
      var orgId = await boardResolveOrgId();
      var apiSlideKey = BOARD_SLIDE_API_KEYS[slideKey] || slideKey;
      var lastApiStatus = null;

      if (orgId) {
        try {
          var apiBase = await boardLiveApiBase();
          var res = await boardFetchWithTimeout(
            boardLiveUrl(
              apiBase,
              "/api/v1/board-platform/commentary/regenerate?organization_id=" + encodeURIComponent(orgId),
            ),
            boardLiveFetchInit(apiBase, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ slide_key: apiSlideKey }),
            }),
            295000,
          );
          if (res.ok) {
            var data = await res.json();
            var text = formatApiCommentary(data.commentary) || "Commentary unavailable.";
            if (
              text.indexOf("See section commentary") >= 0 ||
              text.indexOf("Confirm waterfall tie-outs") >= 0
            ) {
              text = readStaticCommentary(slideKey, targetId);
            }
            txt.textContent = text;
            global.aiCache = global.aiCache || {};
            global.aiCache[slideKey] = text;
            return;
          }
          if (!shouldFallbackToDemo(res.status)) {
            txt.textContent = await boardApiErrorMessage(res);
            return;
          }
          lastApiStatus = res.status;
        } catch (err) {
          if (orgId) {
            txt.textContent = "Commentary request failed: " + boardFetchErrorMessage(err, 295000);
            return;
          }
        }
      }

      await new Promise(function (r) {
        setTimeout(r, 350);
      });
      var demoText = buildDemoCommentary(slideKey, targetId);
      if (lastApiStatus === 409) {
        demoText +=
          " Warehouse validation notes (e.g. pipeline_waterfall_ties) do not block board review — export package still requires tie-outs.";
      } else if (!orgId) {
        demoText +=
          " (Embedded narrative — sign in at /app/board for live Claude commentary from your warehouse.)";
      } else if (hasLiveBoardMetrics()) {
        demoText += " (Live warehouse metrics — Claude unavailable or API blocked; numbers above match hydrated board data.)";
      } else {
        demoText +=
          " (Live API unavailable — showing embedded June 2026 narrative. Confirm sign-in and ANTHROPIC_API_KEY on the API server.)";
      }
      txt.textContent = demoText;
      global.aiCache = global.aiCache || {};
      global.aiCache[slideKey] = demoText;
    };

    var origCpSend = global.cpSend;
    global.cpSend = async function cpSendLive() {
      if (global.cpSending) return;
      var input = document.getElementById("cpInput");
      var sendBtn = document.getElementById("cpSendBtn");
      var msgs = document.getElementById("cpMessages");
      if (!input || !msgs) return;
      var q = input.value.trim();
      if (!q) return;

      global.cpSending = true;
      input.value = "";
      if (sendBtn) sendBtn.disabled = true;

      msgs.innerHTML +=
        '<div class="cp-msg user"><div class="cp-avatar">M</div><div class="cp-bubble">' +
        q.replace(/</g, "&lt;") +
        "</div></div>";

      var thinkId = "cpThink_" + Date.now();
      msgs.innerHTML +=
        '<div class="cp-msg assistant" id="' +
        thinkId +
        '"><div class="cp-avatar">S</div><div class="cp-bubble"><div class="cp-thinking"><div class="cp-dot"></div><div class="cp-dot"></div><div class="cp-dot"></div></div></div></div>';
      msgs.scrollTop = msgs.scrollHeight;

      global.cpHistory = global.cpHistory || [];
      global.cpHistory.push({ role: "user", content: q });

      var orgId = await boardResolveOrgId();
      if (!orgId) {
        var el = document.getElementById(thinkId);
        if (el) {
          el.outerHTML =
            '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">Open Board Platform from /app/board (signed in) to use live SMPL Copilot.</div></div>';
        }
        global.cpSending = false;
        if (sendBtn) sendBtn.disabled = false;
        return;
      }

      try {
        var cpApiBase = await boardLiveApiBase();
        var res = await boardFetchWithTimeout(
          boardLiveUrl(
            cpApiBase,
            "/api/v1/board-platform/copilot?organization_id=" + encodeURIComponent(orgId),
          ),
          boardLiveFetchInit(cpApiBase, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q }),
          }),
          295000,
        );
        if (!res.ok) {
          var errText = await boardApiErrorMessage(res);
          var errEl = document.getElementById(thinkId);
          if (errEl) {
            errEl.outerHTML =
              '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">' +
              errText.replace(/</g, "&lt;") +
              "</div></div>";
          }
        } else {
          var data = await res.json();
          var reply = data.answer || "Unable to generate response.";
          global.cpHistory.push({ role: "assistant", content: reply });
          var formatted =
            typeof global.formatCopilotReply === "function"
              ? global.formatCopilotReply(reply)
              : reply.replace(/</g, "&lt;");
          var thinkEl = document.getElementById(thinkId);
          if (thinkEl) {
            thinkEl.outerHTML =
              '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble">' +
              formatted +
              "</div></div>";
          }
        }
      } catch (err) {
        var failEl = document.getElementById(thinkId);
        if (failEl) {
          failEl.outerHTML =
            '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">' +
            boardFetchErrorMessage(err, 295000).replace(/</g, "&lt;") +
            "</div></div>";
        }
      }

      global.cpSending = false;
      if (sendBtn) sendBtn.disabled = false;
      msgs.scrollTop = msgs.scrollHeight;
    };
  }

  function updateCopilotWelcome(data) {
    var bubble = document.querySelector("#cpMessages .cp-msg.assistant .cp-bubble");
    if (!bubble || !data || !data.meta) return;
    var org = data.meta.organization_name || "your organization";
    var close = data.meta.close_month || boardActiveCloseMonth();
    var y = close.slice(0, 4);
    var m = parseInt(close.slice(5), 10) - 1;
    var closeLbl = (monthNames()[m] || "") + " " + y;
    bubble.innerHTML =
      '<div class="cp-section">Ready</div>I have live warehouse data for <strong>' +
      org +
      "</strong> through <strong>" +
      closeLbl +
      "</strong> close. Ask about ARR, revenue, cash, headcount, GTM, or variance vs budget." +
      '<div class="cp-source">Source: reconciled Neon warehouse via /api/v1/reporting/outlook</div>';
  }

  function installLiveExec() {
    if (!global.renderExec || global._smplExecLiveInstalled) return;
    global._smplExecLiveInstalled = true;
    var demoRenderExec = global.renderExec;

    global.renderExec = function renderExecLive(area) {
      if (!global.SMPL_LIVE_OUTLOOK) {
        return demoRenderExec(area);
      }
      var m = boardJunMetrics();
      var drivers = boardExecDrivers();
      var closeLbl = global.CLOSE_LABEL || "Close";
      var cm = boardActiveCloseMonth();
      var arrVar = m.arrAct != null && m.arrBud != null ? m.arrAct - m.arrBud : 0;
      var revVar = m.revAct != null && m.revBud != null ? m.revAct - m.revBud : 0;
      var ebitdaVar = m.ebitdaAct != null && m.ebitdaBud != null ? m.ebitdaAct - m.ebitdaBud : 0;
      var cashVar = m.cashAct != null && m.cashBud != null ? m.cashAct - m.cashBud : 0;
      var nnVar = drivers.nnAct - drivers.nnBud;
      var nrrPct = m.nrr != null ? (m.nrr * 100).toFixed(1) + "%" : "—";
      var gmActPct = m.gmAct != null ? fKpiPct(m.gmAct) : "—";
      var gmBudPct = m.gmBud != null ? fKpiPct(m.gmBud) : "—";

      var heroCards = [
        {
          lbl: "Ending ARR",
          val: fKpiM(m.arrAct),
          delta: fKpiVarM(arrVar) + " vs bud",
          dir: arrVar >= 0 ? "pos" : "neg",
          because: "Sourced from live ARR waterfall ending balance",
          link: "show('arr',null)",
        },
        {
          lbl: "Net New ARR",
          val: fKpiM(drivers.nnAct),
          delta: fKpiVarM(nnVar) + " vs bud",
          dir: nnVar >= 0 ? "pos" : "neg",
          because: "Driver decomposition from warehouse waterfall",
          link: "show('arr',null)",
        },
        {
          lbl: "EBITDA",
          val: fKpiM(m.ebitdaAct),
          delta: fKpiVarM(ebitdaVar) + " vs bud",
          dir: ebitdaVar >= 0 ? "pos" : "neg",
          because: "Income statement actual vs budget at " + cm,
          link: "show('pl',null)",
        },
        {
          lbl: "Cash Balance",
          val: fKpiM(m.cashAct),
          delta: fKpiVarM(cashVar) + " vs bud",
          dir: cashVar >= 0 ? "pos" : "neg",
          because: "Balance sheet cash ties to cash flow bridge",
          link: "show('cash',null)",
        },
      ];

      demoRenderExec(area);

      var root = area.querySelector(".slide");
      if (!root) return;

      var mastheadSub = root.querySelector(".slide div[style*='Prepared for Board']");
      if (mastheadSub) {
        mastheadSub.textContent = "Prepared for Board of Directors · " + closeLbl + " Close";
      }

      /* KPI cards + section 02 NN variance come from boardExecKpis() in renderExec — do not replace hero grid (was causing NN var mismatch). */

      var execComm = document.getElementById("execComm");
      if (execComm) {
        var txt = execComm.querySelector(".commentary-text");
        if (txt) {
          if (global.aiCache && global.aiCache.exec) {
            txt.textContent = global.aiCache.exec;
          } else if (!global.aiCache?.exec) {
            txt.textContent = buildLiveExecCommentary();
          }
        }
      }
    };
  }

  async function smplBoardHydrate() {
    if (!global.SMPLOutlook) {
      var el = document.getElementById("warehouseStatus");
      if (el) {
        el.textContent = "Demo data";
        el.style.color = "var(--amber)";
      }
      return;
    }

    installLiveAi();
    installLiveExec();

    global.SMPL_DEMO_TS_DATA = global.TS_DATA;
    if (global.TS_DATA) {
      global.SMPLOutlook.registerDemoData(global.TS_DATA, global.SMPL_DEMO_WF_TABLE || null);
    }

    await global.SMPLOutlook.hydrate({
      endpoint: "reporting/outlook",
      hooks: {
        TS_DATA: global.TS_DATA,
        WF_TABLE: global.SMPL_DEMO_WF_TABLE,
        ARR_ACT: global.ARR_ACT,
        actMonthsCount: global.ACT_MONTHS_COUNT,
      },
      onStatus: function (text, tone) {
        var el = document.getElementById("warehouseStatus");
        if (!el) return;
        el.textContent = text;
        el.style.color =
          tone === "ok" ? "var(--teal)" : tone === "warn" ? "var(--amber)" : "var(--text2)";
      },
      onApplied: function (data) {
        try {
          syncBoardFromOutlook(data);
          updateCopilotWelcome(data);
          smplBoardRefreshView();
        } catch (err) {
          console.error("[board-hydrate] post-hydrate refresh failed", err);
        }
      },
    });
  }

  function boardExportApiBase() {
    var host = global.location && global.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return Promise.resolve("http://127.0.0.1:8001");
    }
    if (global.SMPL_LONG_RUNNING_API_BASE) {
      return Promise.resolve(global.SMPL_LONG_RUNNING_API_BASE);
    }
    if (!global._boardExportApiBasePromise) {
      global._boardExportApiBasePromise = fetch("/api/smpl/board-config", {
        cache: "no-store",
        credentials: "include",
      })
        .then(function (res) {
          return res.ok ? res.json() : null;
        })
        .then(function (j) {
          var base = j && j.longRunningApiBase ? String(j.longRunningApiBase).replace(/\/$/, "") : "";
          if (base) global.SMPL_LONG_RUNNING_API_BASE = base;
          return base;
        })
        .catch(function () {
          return "";
        });
    }
    return global._boardExportApiBasePromise;
  }

  function isExportUpstreamError(text) {
    return /upstream error|ROUTER_EXTERNAL_TARGET|An error occurred with this application|502|504|503/i.test(
      text || "",
    );
  }

  /** Cross-origin file downloads bypass CORS (unlike fetch). Railway serves Content-Disposition: attachment. */
  function triggerDirectExportDownload(exportUrl, label) {
    alert(
      label +
        " export started.\n\nGeneration can take 3–8 minutes. Your browser will download when ready — keep this tab open.",
    );
    var frame = document.getElementById("smpl-export-download-frame");
    if (!frame) {
      frame = document.createElement("iframe");
      frame.id = "smpl-export-download-frame";
      frame.setAttribute("aria-hidden", "true");
      frame.style.display = "none";
      document.body.appendChild(frame);
    }
    frame.src = exportUrl;
  }

  async function fetchBoardExportBlob(exportBase, exportUrl, exportSpec, exportTimeoutMs) {
    var res = await boardFetchWithTimeout(
      exportUrl,
      boardLiveFetchInit(exportBase, { method: "GET", cache: "no-store" }),
      exportTimeoutMs,
    );
    if (!res.ok) {
      return { ok: false, message: await boardApiErrorMessage(res) };
    }
    var blob = await res.blob();
    if (!blob || blob.size < 100) {
      return { ok: false, message: exportSpec.label + " export returned an empty file. Check backend logs and retry." };
    }
    var objectUrl = URL.createObjectURL(blob);
    var anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = exportSpec.filename;
    anchor.click();
    URL.revokeObjectURL(objectUrl);
    return { ok: true };
  }

  async function openLiveBoardExport(format) {
    var orgId = await boardResolveOrgId();
    var closeMonth = boardActiveCloseMonth();
    var year = closeMonth.slice(0, 4);
    if (!orgId) {
      return "no-org";
    }

    // Board header buttons — must match backend export registry (output_requirements.py).
    // Variance Commentary button → full MD&A Excel package (month-end-close), NOT 2-tab variance-only.
    var exportSpec =
      format === "pptx"
        ? {
            path: "/api/v1/export/board-presentation.pptx",
            filename: "board_mda_deck_" + closeMonth + ".pptx",
            label: "MD&A Deck",
          }
        : {
            path: "/api/v1/export/month-end-close.xlsx",
            filename: "mda_package_" + closeMonth + ".xlsx",
            label: "Variance Commentary",
          };

    var params = new URLSearchParams({
      organization_id: orgId,
      scenario: "Combined",
      start_period: year + "-01",
      end_period: year + "-12",
      as_of_period: closeMonth,
      include_ai_commentary: "true",
      include_commentary: "true",
      include_appendix: "true",
      include_validation: "true",
      block_on_failure: "false",
      package_mode: "full_board",
    });

    var exportTimeoutMs = 600000;

    try {
      var directBase = await boardExportApiBase();
      var host = global.location && global.location.hostname;
      var isLocal = host === "localhost" || host === "127.0.0.1";
      var exportUrl = boardLiveUrl(directBase, exportSpec.path) + "?" + params.toString();

      if (directBase && !isLocal) {
        triggerDirectExportDownload(exportUrl, exportSpec.label);
        return "started";
      }

      if (!directBase && !isLocal) {
        alert(
          exportSpec.label +
            " export failed: Railway API URL is not configured.\n\n" +
            "Set SFI_BACKEND_URL and NEXT_PUBLIC_API_URL on Vercel to https://sfi-api-production.up.railway.app, redeploy, then hard refresh /app/board.",
        );
        return "error";
      }

      var exportBase = directBase || "";
      try {
        var result = await fetchBoardExportBlob(exportBase, exportUrl, exportSpec, exportTimeoutMs);
        if (result.ok) return "ok";
        alert(exportSpec.label + " export failed:\n" + (result.message || "Unknown error"));
        return "error";
      } catch (err) {
        alert(exportSpec.label + " export failed:\n" + boardFetchErrorMessage(err, exportTimeoutMs));
        return "error";
      }
    } catch (err) {
      alert(
        exportSpec.label +
          " export failed: " +
          boardFetchErrorMessage(err, exportTimeoutMs),
      );
      return "error";
    }
  }

  global.SMPLBoardLive = {
    hydrate: smplBoardHydrate,
    syncBoardFromOutlook: syncBoardFromOutlook,
    updateCopilotContext: updateCopilotWelcome,
    boardJunMetrics: boardJunMetrics,
    refreshExecCommentaryFromLiveMetrics: refreshExecCommentaryFromLiveMetrics,
    openBoardExport: openLiveBoardExport,
  };

  global.SMPL_ON_ORG_READY = function () {
    void smplBoardHydrate();
  };

  // Install live handlers as soon as this script parses (before window "load").
  installLiveAi();
  installCommentaryCacheRestore();

  global.addEventListener("load", function () {
    if (global.SMPLSkin) {
      global.SMPLSkin.init("skinSelect", smplBoardRefreshView);
    } else if (typeof global.applySkin === "function") {
      var sel = document.getElementById("skinSelect");
      var saved = "canvas";
      try {
        saved = localStorage.getItem("smpl-skin") || "canvas";
      } catch (_) {}
      if (sel) sel.value = saved;
      global.applySkin(saved);
    }
    // Defer first hydrate so embedded iframe receives smpl:org from parent (Forecast Engine pattern).
    setTimeout(function () {
      void smplBoardHydrate();
    }, 50);
  });
})(window);
