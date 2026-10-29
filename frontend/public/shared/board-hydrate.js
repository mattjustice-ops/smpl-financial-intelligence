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
    return global.CLOSE_MONTH;
  }

  function boardCloseLabel() {
    var cm = boardActiveCloseMonth();
    return monthNames()[parseInt(cm.slice(5), 10) - 1] + " " + cm.slice(0, 4);
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

  /** Close-month metrics for commentary; the same values the Executive Summary shows. */
  function boardJunMetrics() {
    var k = (global.boardExecKpis && global.boardExecKpis()) || {};
    return {
      arrAct: k.arrEop,
      arrBud: k.arrBud,
      arrYearEnd: k.arrYearEnd,
      arrYearEndBud: k.arrYearEndBud,
      revAct: k.revAct,
      revBud: k.revBud,
      ebitdaAct: k.ebitdaAct,
      ebitdaBud: k.ebitdaBud,
      cashAct: k.cashAct,
      cashBud: k.cashBud,
      gmPct: k.gmAct,
      nrr: k.nrr,
    };
  }

  function boardExecDrivers() {
    var k = (global.boardExecKpis && global.boardExecKpis()) || {};
    return { nnAct: k.nn, nnBud: k.nnBud, drivers: k.drivers || [] };
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
      if (badge) {
        badge.textContent =
          global.SMPLContinuity && typeof global.SMPLContinuity.publicationLabel === "function"
            ? global.SMPLContinuity.publicationLabel()
            : cm + " Prelim";
      }
      var footMo = document.getElementById("footerCloseMo");
      if (footMo) footMo.textContent = global.CLOSE_MO;
      var footYr = document.getElementById("footerCloseYr");
      if (footYr) footYr.textContent = cm.slice(0, 4);
    }

    if (data.ARR_WATERFALL && global.SMPL_DEMO_WF_TABLE && global.SMPLOutlook && global.SMPLOutlook.replaceArrWaterfallTable) {
      global.SMPLOutlook.replaceArrWaterfallTable(global.SMPL_DEMO_WF_TABLE, data.ARR_WATERFALL);
    }

    if (typeof global.boardRefreshAllSeries === "function") {
      global.boardRefreshAllSeries();
    }
    // Rebuild Management P&L from the same TS_DATA Income Statement SoT.
    if (typeof global.schedulePLCharts === "function") {
      try { global.schedulePLCharts(0); } catch (_) { /* non-fatal */ }
    } else if (typeof global.buildPLTable === "function") {
      try { global.buildPLTable(); } catch (_) { /* non-fatal */ }
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

    refreshAllLiveCommentariesFromMetrics();
  }

  function smplBoardRefreshView() {
    var tab = "exec";
    try {
      if (typeof global.SMPL_BOARD_VIEW === "string" && global.SMPL_BOARD_VIEW) {
        tab = global.SMPL_BOARD_VIEW;
      } else if (global.SMPL_VALIDATION_ENGINE) {
        tab = "validation";
      } else {
        var q = (global.location && global.location.search) || "";
        var qm = q.match(/[?&]view=([a-z0-9_]+)/i);
        if (qm) {
          tab = qm[1].toLowerCase();
          if (tab === "continuity") tab = "validation";
        } else {
          var active = document.querySelector(".nav-btn.active");
          if (active) {
            var m = active.getAttribute("onclick");
            if (m) {
              var hit = m.match(/show\('(\w+)'/);
              if (hit) tab = hit[1];
            }
          }
        }
      }
    } catch (_) {
      /* keep default */
    }
    if (tab === "continuity") tab = "validation";
    var btn = null;
    if (tab !== "validation") {
      btn = document.querySelector(".nav-btn.active");
      if (!btn) {
        btn =
          Array.prototype.find.call(document.querySelectorAll(".nav-btn"), function (b) {
            return (b.getAttribute("onclick") || "").indexOf("show('" + tab + "'") >= 0;
          }) || null;
      }
    }
    if (typeof global.show === "function") {
      global.show(tab, btn);
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
      return "http://127.0.0.1:8000";
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
      if (timeoutMs != null && timeoutMs <= 130000) {
        return (
          "Request timed out after " +
          secs +
          "s. Commentary should finish under 2 minutes — hard refresh and retry. " +
          "If this keeps happening, the freeze pack may be missing and the live warehouse path is too slow."
        );
      }
      return (
        "Request timed out after " +
        secs +
        "s. Long exports can take several minutes — confirm Railway API is healthy and ANTHROPIC_API_KEY is set, then retry."
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
    var closeLbl = boardCloseLabel();
    var arrVar = m.arrAct != null && m.arrBud != null ? m.arrAct - m.arrBud : null;
    var revVar = m.revAct != null && m.revBud != null ? m.revAct - m.revBud : null;
    var ebitdaVar = m.ebitdaAct != null && m.ebitdaBud != null ? m.ebitdaAct - m.ebitdaBud : null;
    var cashVar = m.cashAct != null && m.cashBud != null ? m.cashAct - m.cashBud : null;
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
      " vs bud), monthly NRR " +
      nrrPct +
      "."
    );
  }

  function buildLiveArrCommentary() {
    var m = boardJunMetrics();
    var drivers = boardExecDrivers();
    var closeLbl = boardCloseLabel();
    var arrVar = m.arrAct != null && m.arrBud != null ? m.arrAct - m.arrBud : null;
    var closeMonthNum = Number(boardActiveCloseMonth().slice(5, 7));
    var parts = [
      closeLbl +
        " waterfall end ARR " +
        fKpiM(m.arrAct) +
        " (" +
        fKpiVarM(arrVar) +
        " vs bud), net new " +
        fKpiM(drivers.nnAct) +
        " (bud " +
        fKpiM(drivers.nnBud) +
        ").",
    ];
    drivers.drivers.forEach(function (d) {
      if (Math.abs(d.val) < 0.01) return;
      parts.push(d.label + " " + fKpiVarM(d.val) + " (bud " + fKpiM(d.bud) + ").");
    });
    if (closeMonthNum < 12 && m.arrYearEnd != null) {
      parts.push(
        "Year-end ARR forecast " +
          fKpiM(m.arrYearEnd) +
          (m.arrYearEndBud != null
            ? " vs " + fKpiM(m.arrYearEndBud) + " budget (" + fKpiVarM(m.arrYearEnd - m.arrYearEndBud) + ")."
            : " (no budget loaded)."),
      );
    }
    if (m.nrr != null) parts.push("Monthly NRR " + (m.nrr * 100).toFixed(1) + "%.");
    return parts.join(" ");
  }

  function buildLiveCashCommentary() {
    var m = boardJunMetrics();
    var closeLbl = boardCloseLabel();
    var cashVar = m.cashAct != null && m.cashBud != null ? m.cashAct - m.cashBud : null;
    var idx = boardActualPeriods().length - 1;
    var coll = global.COLL && global.COLL[idx] != null ? global.COLL[idx] : null;
    var parts = [
      closeLbl +
        " ending cash " +
        fKpiM(m.cashAct) +
        " (" +
        fKpiVarM(cashVar) +
        " vs bud).",
    ];
    if (coll != null) parts.push("Collections " + fKpiM(coll) + ".");
    return parts.join(" ");
  }

  function buildLiveRevenueCommentary() {
    var m = boardJunMetrics();
    var closeLbl = boardCloseLabel();
    var revVar = m.revAct != null && m.revBud != null ? m.revAct - m.revBud : null;
    var ebitdaVar = m.ebitdaAct != null && m.ebitdaBud != null ? m.ebitdaAct - m.ebitdaBud : null;
    var gm = m.gmPct != null ? m.gmPct.toFixed(1) + "%" : null;
    var parts = [
      closeLbl +
        " revenue " +
        fKpiM(m.revAct) +
        " (" +
        fKpiVarM(revVar) +
        " vs bud), EBITDA " +
        fKpiM(m.ebitdaAct) +
        " (" +
        fKpiVarM(ebitdaVar) +
        " vs bud).",
    ];
    if (gm) parts.push("Gross margin " + gm + ".");
    return parts.join(" ");
  }

  function buildLiveHeadcountCommentary() {
    var closeHc = global.boardCloseHc ? global.boardCloseHc() : null;
    var arrPerEmp =
      global.ARR_PER_EMP && global.ARR_PER_EMP.length
        ? global.ARR_PER_EMP[global.ARR_PER_EMP.length - 1]
        : null;
    var arrPerEmpJan =
      global.ARR_PER_EMP && global.ARR_PER_EMP.length ? global.ARR_PER_EMP[0] : null;
    var closeLbl = boardCloseLabel();
    var parts = [
      closeLbl +
        " headcount " +
        (closeHc != null ? closeHc : "—") +
        " (bud " +
        (global.HC_TOTAL_BUD != null ? global.HC_TOTAL_BUD : "—") +
        ").",
    ];
    if (arrPerEmp != null) {
      parts.push(
        "ARR per employee $" +
          arrPerEmp +
          "K" +
          (arrPerEmpJan != null ? " (Jan $" + arrPerEmpJan + "K)" : "") +
          ".",
      );
    }
    return parts.join(" ");
  }

  function buildLiveRisksCommentary() {
    var m = boardJunMetrics();
    var drivers = boardExecDrivers();
    var closeLbl = boardCloseLabel();
    var arrVar = m.arrAct != null && m.arrBud != null ? m.arrAct - m.arrBud : null;
    var ebitdaVar = m.ebitdaAct != null && m.ebitdaBud != null ? m.ebitdaAct - m.ebitdaBud : null;
    var cashVar = m.cashAct != null && m.cashBud != null ? m.cashAct - m.cashBud : null;
    return (
      closeLbl +
      " confirms ARR " +
      fKpiVarM(arrVar) +
      " vs bud, EBITDA " +
      fKpiVarM(ebitdaVar) +
      ", cash " +
      fKpiVarM(cashVar) +
      ", net new " +
      fKpiM(drivers.nnAct) +
      ". Board priorities should track material unfavorable variances and remaining-year pipeline coverage against the live ARR forecast."
    );
  }

  function discussionPhrase(dollars) {
    if (global.SMPLReportFormat && typeof global.SMPLReportFormat.moneyPhrase === "function") {
      return global.SMPLReportFormat.moneyPhrase(dollars);
    }
    var amount = Number(dollars);
    if (!isFinite(amount)) return "—";
    var abs = Math.abs(amount);
    var body = abs >= 1000000 ? "$" + (abs / 1000000).toFixed(2) + "m" : abs >= 1000 ? "$" + (abs / 1000).toFixed(2) + "k" : "$" + abs.toFixed(2);
    return (amount < 0 ? "−" : "") + body;
  }

  function phraseFromMillions(millions) {
    if (millions == null || !isFinite(Number(millions))) return "";
    return discussionPhrase(Number(millions) * 1e6);
  }

  function discussionSpan(periods, scenario) {
    var names = monthNames();
    if (scenario === "Budget") return "the budget";
    if (scenario === "Forecast") return "the forecast";
    if (!periods || !periods.length) return "";
    var first = String(periods[0]);
    var last = String(periods[periods.length - 1]);
    if (periods.length === 1) return names[parseInt(first.slice(5, 7), 10) - 1] + " " + first.slice(0, 4);
    var quarter = first.slice(0, 4) === last.slice(0, 4) && periods.length === 3 && Math.floor((+first.slice(5, 7) - 1) / 3) === Math.floor((+last.slice(5, 7) - 1) / 3);
    if (quarter) return "Q" + (Math.floor((+last.slice(5, 7) - 1) / 3) + 1) + " " + last.slice(0, 4);
    return names[parseInt(first.slice(5, 7), 10) - 1] + "–" + names[parseInt(last.slice(5, 7), 10) - 1] + " " + last.slice(0, 4);
  }

  function tsSource() {
    var embedded = global.TS_DATA;
    if (global.SMPL_LIVE_OUTLOOK && global.SMPLOutlook && global.SMPLOutlook.getOutlookTsData) {
      var live = global.SMPLOutlook.getOutlookTsData();
      if (live && global.SMPLOutlook.mergeTsData && embedded) return global.SMPLOutlook.mergeTsData(embedded, live);
      if (live) return live;
    }
    return embedded;
  }

  function isDollars(scenario, period, key) {
    var ts = tsSource();
    var row = ts && ts[scenario] && ts[scenario].is && ts[scenario].is[period];
    if (!row || row[key] == null || row[key] === "") return null;
    var amount = Number(row[key]);
    return isFinite(amount) ? amount : null;
  }

  function sumLoadedDollars(periods, scenario, key) {
    var total = 0;
    var any = false;
    (periods || []).forEach(function (period) {
      var amount = isDollars(scenario, period, key);
      if (amount == null) return;
      total += amount;
      any = true;
    });
    return any ? total : null;
  }

  function waterfallAt(period) {
    if (typeof global.boardWaterfallMonthM !== "function" || typeof global.boardWfTable !== "function") return null;
    var close = String(global.CLOSE_MONTH || "");
    if (String(period).slice(0, 4) !== close.slice(0, 4)) return null;
    var index = parseInt(String(period).slice(5, 7), 10) - 1;
    if (index < 0) return null;
    return global.boardWaterfallMonthM(global.boardWfTable(), index);
  }

  function waterfallWindow(periods) {
    var last = null;
    var nb = 0;
    var exp = 0;
    var react = 0;
    var con = 0;
    var churn = 0;
    var any = false;
    var flows = false;
    function add(sum, value) {
      if (value == null) return sum;
      flows = true;
      return sum + value;
    }
    (periods || []).forEach(function (period) {
      var month = waterfallAt(period);
      if (!month) return;
      any = true;
      last = month;
      nb = add(nb, month.nb);
      exp = add(exp, month.exp);
      react = add(react, month.react);
      con = add(con, month.con);
      churn = add(churn, month.churn);
    });
    if (!any || !last || last.eop == null) return null;
    return {
      eop: last.eop,
      nb: nb,
      exp: exp,
      react: react,
      con: Math.abs(con),
      churn: Math.abs(churn),
      net: flows ? nb + exp + react + con + churn : null,
    };
  }

  function movedMillions(label, current, base, baseTitle) {
    if (current == null) return "";
    var text = label + " was " + phraseFromMillions(current);
    if (base == null) return text;
    var gap = current - base;
    var gapPhrase = phraseFromMillions(Math.abs(gap));
    if (phraseFromMillions(current) === phraseFromMillions(base) || gapPhrase === "$0.00") {
      return text + ", unchanged from " + phraseFromMillions(base) + " in " + baseTitle;
    }
    return text + ", " + (gap > 0 ? "up " : "down ") + gapPhrase + " from " + phraseFromMillions(base) + " in " + baseTitle;
  }

  function narrateArr(win) {
    var currentTitle = discussionSpan(win.current, "Actual");
    var baseTitle = discussionSpan(win.base, win.scenario);
    if (win.id === "budget") {
      var kpis = (global.boardExecKpis && global.boardExecKpis()) || {};
      var parts = [];
      if (kpis.arrEop != null) {
        var ending = "Ending ARR was " + phraseFromMillions(kpis.arrEop);
        if (kpis.arrBud != null) {
          var gap = kpis.arrEop - kpis.arrBud;
          ending += Math.abs(gap) < 0.005
            ? ", in line with the budget of " + phraseFromMillions(kpis.arrBud)
            : ", " + phraseFromMillions(Math.abs(gap)) + (gap > 0 ? " above" : " below") + " the budget of " + phraseFromMillions(kpis.arrBud);
        }
        parts.push(ending + ".");
      }
      if (kpis.nn != null) {
        parts.push("Net new ARR was " + phraseFromMillions(kpis.nn) + (kpis.nnBud != null ? " against a budget of " + phraseFromMillions(kpis.nnBud) : "") + ".");
      }
      (kpis.drivers || []).forEach(function (driver) {
        if (driver.val == null || Math.abs(driver.val) < 0.01) return;
        var sentence = driver.label + " was " + phraseFromMillions(Math.abs(driver.val));
        if (driver.bud != null) sentence += " against a budget of " + phraseFromMillions(Math.abs(driver.bud));
        parts.push(sentence + ".");
      });
      if (kpis.nrr != null) parts.push("Monthly net dollar retention was " + (kpis.nrr * 100).toFixed(1) + "%.");
      if (kpis.arrYearEnd != null) {
        var yearEnd = "The year-end ARR forecast is " + phraseFromMillions(kpis.arrYearEnd);
        if (kpis.arrYearEndBud != null) {
          var yearGap = kpis.arrYearEnd - kpis.arrYearEndBud;
          yearEnd += Math.abs(yearGap) < 0.005
            ? ", in line with a budget of " + phraseFromMillions(kpis.arrYearEndBud)
            : ", " + phraseFromMillions(Math.abs(yearGap)) + (yearGap > 0 ? " above" : " below") + " a budget of " + phraseFromMillions(kpis.arrYearEndBud);
        }
        parts.push(yearEnd + ".");
      }
      return parts.join(" ");
    }
    var current = waterfallWindow(win.current);
    var base = win.id === "forecast" ? null : waterfallWindow(win.base);
    if (!current) return "";
    var parts = [movedMillions("Ending ARR", current.eop, base && base.eop, baseTitle) + "."];
    if (current.net != null) parts.push(movedMillions("Net new ARR", current.net, base && base.net, baseTitle) + ".");
    if (current.nb != null) parts.push(movedMillions("New business", current.nb, base && base.nb, baseTitle) + ".");
    if (Math.abs(current.exp) >= 0.01 || (base && Math.abs(base.exp) >= 0.01)) {
      parts.push(movedMillions("Expansion", current.exp, base && base.exp, baseTitle) + ".");
    }
    if (Math.abs(current.con) >= 0.01 || (base && Math.abs(base.con) >= 0.01)) {
      parts.push(movedMillions("Contraction", current.con, base && base.con, baseTitle) + ".");
    }
    if (current.churn >= 0.01 || (base && base.churn >= 0.01)) {
      parts.push(movedMillions("Churn", current.churn, base && base.churn, baseTitle) + ".");
    }
    var metrics = boardJunMetrics();
    if (metrics.nrr != null) {
      parts.push("Net dollar retention in " + boardCloseLabel() + " was " + (metrics.nrr * 100).toFixed(1) + "%.");
    }
    if (!base && win.id === "forecast") {
      parts.push("A forecast ARR bridge is not loaded for " + currentTitle + ", so this is the actual waterfall.");
    } else if (!base) {
      parts.push(baseTitle + " is outside the close-year waterfall, so these are the " + currentTitle + " figures.");
    }
    return parts.join(" ");
  }

  function narrateMargin(win) {
    var scenario = win.scenario || "Actual";
    var revenue = sumLoadedDollars(win.current, "Actual", "revenue");
    var baseRevenue = sumLoadedDollars(win.base, scenario, "revenue");
    var gross = sumLoadedDollars(win.current, "Actual", "gross_profit");
    var baseGross = sumLoadedDollars(win.base, scenario, "gross_profit");
    var ebitda = sumLoadedDollars(win.current, "Actual", "ebitda");
    var baseEbitda = sumLoadedDollars(win.base, scenario, "ebitda");
    var currentTitle = discussionSpan(win.current, "Actual");
    var baseTitle = discussionSpan(win.base, scenario);
    if (revenue == null && ebitda == null) return "";
    var parts = [];
    if (revenue != null && gross != null) {
      var margin = (gross / revenue) * 100;
      var sentence = "Gross margin was " + margin.toFixed(1) + "% in " + currentTitle + " on revenue of " + discussionPhrase(revenue);
      if (baseRevenue != null && baseGross != null && baseRevenue) {
        sentence += ", from " + ((baseGross / baseRevenue) * 100).toFixed(1) + "% on " + discussionPhrase(baseRevenue) + " in " + baseTitle;
      }
      parts.push(sentence + ".");
    } else if (revenue != null) {
      parts.push(movedMillions("Revenue", revenue / 1e6, baseRevenue == null ? null : baseRevenue / 1e6, baseTitle) + ".");
    }
    if (ebitda != null) parts.push(movedMillions("EBITDA", ebitda / 1e6, baseEbitda == null ? null : baseEbitda / 1e6, baseTitle) + ".");
    return parts.join(" ");
  }

  function narrateCash(win) {
    var last = win.current[win.current.length - 1];
    var baseLast = win.base && win.base.length ? win.base[win.base.length - 1] : "";
    var scenario = win.scenario || "Actual";
    var current = typeof global.boardCashM === "function" ? global.boardCashM("Actual", last) : null;
    var base = baseLast && typeof global.boardCashM === "function" ? global.boardCashM(scenario, baseLast) : null;
    var baseTitle = discussionSpan(win.base, scenario);
    if (current == null) return "";
    var parts = [movedMillions("Ending cash", current, base, baseTitle) + "."];
    var bridge = (global.SMPL_CASH_BRIDGE && global.SMPL_CASH_BRIDGE.Actual) ||
      (global.SMPL_OUTLOOK_PAYLOAD && global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE && global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE.Actual) ||
      {};
    var collections = 0;
    var haveCollections = false;
    (win.current || []).forEach(function (period) {
      var row = bridge[period];
      if (!row || row.collections == null) return;
      collections += Number(row.collections);
      haveCollections = true;
    });
    if (haveCollections) parts.push("Collections were " + discussionPhrase(collections) + ".");
    return parts.join(" ");
  }

  function narrateWorkforce(win) {
    var workforce = typeof global.boardWorkforce === "function" ? global.boardWorkforce() : {};
    var heads = workforce.heads_total || [];
    var budgetHeads = workforce.heads_budget_total || [];
    var close = String(global.CLOSE_MONTH || "");
    function headAt(period) {
      if (String(period).slice(0, 4) !== close.slice(0, 4)) return null;
      var index = parseInt(String(period).slice(5, 7), 10) - 1;
      return heads[index] != null ? heads[index] : null;
    }
    var current = headAt(win.current[win.current.length - 1]);
    var base = win.base && win.base.length ? headAt(win.base[win.base.length - 1]) : null;
    var currentTitle = discussionSpan(win.current, "Actual");
    var baseTitle = discussionSpan(win.base, win.scenario);
    if (current == null && win.id !== "budget") return "";
    var parts = [];
    if (win.id === "budget") {
      var budget = budgetHeads[parseInt(close.slice(5, 7), 10) - 1];
      if (current != null) {
        parts.push("Headcount was " + current + " in " + currentTitle + (budget != null ? ", against a budget of " + budget : "") + ".");
      }
    } else if (current != null) {
      parts.push("Headcount was " + current + " in " + currentTitle + (base != null ? ", from " + base + " in " + baseTitle : "") + ".");
    }
    var perEmployee = global.ARR_PER_EMP && global.ARR_PER_EMP.length ? global.ARR_PER_EMP[global.ARR_PER_EMP.length - 1] : null;
    var january = global.ARR_PER_EMP && global.ARR_PER_EMP.length ? global.ARR_PER_EMP[0] : null;
    if (perEmployee != null) {
      parts.push(
        "ARR per employee was " + discussionPhrase(perEmployee * 1000) +
        (january != null ? ", from " + discussionPhrase(january * 1000) + " in January" : "") +
        "."
      );
    }
    return parts.join(" ");
  }

  function narrateTakeaways(win) {
    var currentTitle = discussionSpan(win.current, "Actual");
    var baseTitle = discussionSpan(win.base, win.scenario);
    var scenario = win.scenario || "Actual";
    var revenue = sumLoadedDollars(win.current, "Actual", "revenue");
    var baseRevenue = sumLoadedDollars(win.base, scenario, "revenue");
    var last = win.current[win.current.length - 1];
    var baseLast = win.base && win.base.length ? win.base[win.base.length - 1] : "";
    var cash = typeof global.boardCashM === "function" ? global.boardCashM("Actual", last) : null;
    var baseCash = baseLast && typeof global.boardCashM === "function" ? global.boardCashM(scenario, baseLast) : null;
    var arr = waterfallWindow(win.current);
    var baseArr = win.id === "forecast" ? null : waterfallWindow(win.base);
    var sentences = [];
    if (revenue != null) sentences.push(movedMillions("Revenue", revenue / 1e6, baseRevenue == null ? null : baseRevenue / 1e6, baseTitle) + ".");
    if (arr && arr.eop != null) sentences.push(movedMillions("Ending ARR", arr.eop, baseArr && baseArr.eop, baseTitle) + ".");
    if (cash != null) sentences.push(movedMillions("Ending cash", cash, baseCash, baseTitle) + ".");
    if (!sentences.length) return "";
    return currentTitle + " compared with " + baseTitle + ". " + sentences.join(" ");
  }

  var DISCUSSION_NARRATIVES = {
    arr: narrateArr,
    revenue: narrateMargin,
    cash: narrateCash,
    headcount: narrateWorkforce,
    risks: narrateTakeaways,
  };

  global.boardDiscussionNarrative = function boardDiscussionNarrative(slideKey, win) {
    var builder = DISCUSSION_NARRATIVES[slideKey];
    if (!builder || !win || !win.current || !win.current.length) return "";
    try {
      return builder(win) || "";
    } catch (err) {
      return "";
    }
  };

  var LIVE_COMMENTARY_BUILDERS = {
    exec: buildLiveExecCommentary,
    arr: buildLiveArrCommentary,
    revenue: buildLiveRevenueCommentary,
    cash: buildLiveCashCommentary,
    headcount: buildLiveHeadcountCommentary,
    risks: buildLiveRisksCommentary,
  };

  global.boardDataCommentary = function boardDataCommentary(slideKey) {
    var builder = LIVE_COMMENTARY_BUILDERS[slideKey];
    if (!builder) return "";
    return hasLiveBoardMetrics() ? builder() : "Commentary unavailable: no data loaded.";
  };

  function buildDemoCommentary(slideKey, targetId) {
    var builder = LIVE_COMMENTARY_BUILDERS[slideKey];
    if (builder && hasLiveBoardMetrics()) {
      return builder();
    }
    return readStaticCommentary(slideKey, targetId);
  }

  function refreshLiveCommentaryFromMetrics(slideKey, targetId) {
    if (global.aiCache && global.aiCache[slideKey]) return;
    var builder = LIVE_COMMENTARY_BUILDERS[slideKey];
    if (!builder || !hasLiveBoardMetrics()) return;
    var el = document.getElementById(targetId);
    if (!el) return;
    var txt = el.querySelector(".commentary-text");
    if (txt) txt.textContent = builder();
  }

  function refreshExecCommentaryFromLiveMetrics() {
    refreshLiveCommentaryFromMetrics("exec", "execComm");
  }

  function refreshAllLiveCommentariesFromMetrics() {
    var map = {
      exec: "execComm",
      arr: "arrComm",
      revenue: "revComm",
      cash: "cashComm",
      headcount: "hcComm",
      risks: "riskComm",
    };
    Object.keys(map).forEach(function (key) {
      refreshLiveCommentaryFromMetrics(key, map[key]);
    });
  }

  function shouldFallbackToDemo(status) {
    // Soft fallback for validation 409 only. Usage-limit / entitlement 403s must show
    // the real API message (not a misleading "Claude unavailable" demo string).
    return status === 401 || status === 409;
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
            120000,
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
            txt.textContent = "Commentary request failed: " + boardFetchErrorMessage(err, 120000);
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
          " Warehouse validation notes (e.g. pipeline_waterfall_ties) do not block board review — client A–F at export is advisory (HTML report companion).";
      } else if (!orgId) {
        demoText +=
          " (Built from the demo dataset — sign in at /app/board for live Claude commentary from your warehouse.)";
      } else if (hasLiveBoardMetrics()) {
        demoText += " (Live warehouse metrics — Claude unavailable or API blocked; numbers above match hydrated board data.)";
      } else {
        demoText +=
          " (Live API unavailable and no data loaded. Confirm sign-in and ANTHROPIC_API_KEY on the API server.)";
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
          120000,
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
          var asOfMeta = "";
          if (data.context_as_of || data.as_of_period) {
            var src = data.context_source || "live";
            var staleLbl = data.stale ? " · stale" : "";
            var when = data.context_as_of
              ? new Date(data.context_as_of).toLocaleString()
              : "";
            asOfMeta =
              '<div class="cp-source">Data as of ' +
              (when || data.as_of_period || "") +
              " · close " +
              (data.as_of_period || "") +
              " · " +
              src +
              staleLbl +
              "</div>";
          }
          var thinkEl = document.getElementById(thinkId);
          if (thinkEl) {
            thinkEl.outerHTML =
              '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble">' +
              formatted +
              asOfMeta +
              "</div></div>";
          }
        }
      } catch (err) {
        var failEl = document.getElementById(thinkId);
        if (failEl) {
          failEl.outerHTML =
            '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">' +
            boardFetchErrorMessage(err, 120000).replace(/</g, "&lt;") +
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
    var trustBit =
      '<div class="cp-source">Each answer shows its data-as-of timestamp (freeze pack when available, otherwise live).</div>';
    var trust = global.SMPL_TRUST_SUMMARY;
    if (trust && (trust.passed_count != null || trust.trust_label)) {
      var total = (trust.passed_count || 0) + (trust.warning_count || 0) + (trust.failed_count || 0);
      trustBit =
        '<div class="cp-source">' +
        (trust.trust_label || "Checks") +
        " · " +
        (trust.passed_count || 0) +
        "/" +
        total +
        " checks · as of " +
        (trust.as_of_period || close) +
        ". Each answer also shows its data-as-of timestamp.</div>";
    }
    bubble.innerHTML =
      '<div class="cp-section">Ready</div>I have warehouse data for <strong>' +
      org +
      "</strong> through <strong>" +
      closeLbl +
      "</strong> close. Ask about ARR, revenue, cash, headcount, GTM, or variance vs budget." +
      trustBit;
  }

  function installLiveExec() {
    if (!global.renderExec || global._smplExecLiveInstalled) return;
    global._smplExecLiveInstalled = true;
    var demoRenderExec = global.renderExec;

    global.renderExec = function renderExecLive(area) {
      if (!global.SMPL_LIVE_OUTLOOK) {
        return demoRenderExec(area);
      }
      var closeLbl = boardCloseLabel();

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

    var query;
    if (global.SMPL_REPORTING_ENGINE && global.SMPL_REPORTING_AS_OF) {
      query = { as_of_period: global.SMPL_REPORTING_AS_OF };
    }

    await global.SMPLOutlook.hydrate({
      endpoint: "reporting/outlook",
      query: query,
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
          if (global.SMPLProvenance && typeof global.SMPLProvenance.ingestOutlook === "function") {
            global.SMPLProvenance.ingestOutlook(data);
          }
          syncBoardFromOutlook(data);
          updateCopilotWelcome(data);
          smplBoardRefreshView();
          if (global.SMPLProvenance) {
            try {
              global.SMPLProvenance.annotateDom(document);
              global.SMPLProvenance.runTieOut();
            } catch (provErr) {
              console.warn("[board-hydrate] provenance annotate/tie-out failed", provErr);
            }
          }
        } catch (err) {
          console.error("[board-hydrate] post-hydrate refresh failed", err);
        }
      },
    });
  }

  /** Same-origin Next proxy on prod (session + internal key). Direct Railway only on localhost. */
  function boardExportApiBase() {
    return boardLiveApiBase();
  }

  function isExportUpstreamError(text) {
    return /upstream error|ROUTER_EXTERNAL_TARGET|An error occurred with this application|502|504|503/i.test(
      text || "",
    );
  }

  /** Hidden-iframe download; the proxy passes Railway's Content-Disposition: attachment through. */
  function triggerDirectExportDownload(exportUrl, label, silent) {
    if (!silent) {
      alert(
        label +
          " export started.\n\nGeneration can take 3–8 minutes. Your browser will download when ready — keep this tab open.",
      );
    }
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

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function ensureExportProgressPanel() {
    var existing = document.getElementById("smplExportProgress");
    if (existing) return existing;
    var panel = document.createElement("div");
    panel.id = "smplExportProgress";
    panel.setAttribute("role", "status");
    panel.style.cssText =
      "position:fixed;right:20px;bottom:20px;z-index:99999;width:min(360px,calc(100vw - 32px));" +
      "background:#0f172a;color:#e2e8f0;border:1px solid rgba(255,255,255,0.12);border-radius:12px;" +
      "box-shadow:0 18px 40px rgba(0,0,0,0.35);padding:16px 16px 14px;font:13px/1.45 system-ui,sans-serif;";
    panel.innerHTML =
      '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px;">' +
      '<div><div id="smplExportProgressTitle" style="font-weight:650;color:#fff;font-size:14px;">Preparing Executive Package</div>' +
      '<div id="smplExportProgressMeta" style="color:#94a3b8;margin-top:4px;font-size:12px;">Starting…</div></div>' +
      '<button type="button" id="smplExportProgressClose" style="background:transparent;border:0;color:#94a3b8;cursor:pointer;font-size:18px;line-height:1;" aria-label="Close">×</button></div>' +
      '<ol id="smplExportProgressList" style="list-style:none;margin:0;padding:0;"></ol>';
    document.body.appendChild(panel);
    var closeBtn = document.getElementById("smplExportProgressClose");
    if (closeBtn) {
      closeBtn.onclick = function () {
        panel.style.display = "none";
      };
    }
    return panel;
  }

  function renderExportProgress(label, statusJson) {
    var panel = ensureExportProgressPanel();
    panel.style.display = "block";
    var failed = !!(statusJson && statusJson.status === "failed");
    panel.style.borderColor = failed ? "rgba(248,113,113,0.55)" : "rgba(255,255,255,0.12)";
    var title = document.getElementById("smplExportProgressTitle");
    var meta = document.getElementById("smplExportProgressMeta");
    var list = document.getElementById("smplExportProgressList");
    if (title) {
      title.textContent = failed ? label + " failed" : "Preparing " + label;
      title.style.color = failed ? "#fca5a5" : "#fff";
    }
    var msg = (statusJson && (statusJson.error || statusJson.message)) || "Working…";
    var eta = statusJson && statusJson.eta_seconds;
    var etaLbl = "";
    if (!failed && eta != null) {
      etaLbl =
        eta <= 0
          ? "Ready"
          : "Estimated time remaining: ~" + Math.max(1, Math.round(eta / 60)) + " min";
    }
    if (meta) {
      meta.style.color = failed ? "#fca5a5" : "#94a3b8";
      meta.textContent = failed
        ? "Please try again. " + String(msg).replace(/\s+/g, " ").slice(0, 160)
        : etaLbl
          ? msg + " · " + etaLbl
          : msg;
    }
    var stages =
      statusJson && Array.isArray(statusJson.progress) && statusJson.progress.length
        ? statusJson.progress
        : failed
          ? [{ id: "failed", label: "Export failed — please try again", done: false, current: true, failed: true }]
          : [
              { id: "queued", label: "Export queued", done: true, current: false },
              { id: "work", label: msg || "Working…", done: false, current: true },
            ];
    if (!list) return;
    list.innerHTML = stages
      .map(function (stage) {
        var isFailed = !!(stage.failed || stage.id === "failed" || (failed && stage.current));
        var mark = isFailed ? "✕" : stage.done ? "✓" : stage.current ? "●" : "○";
        var color = isFailed
          ? "#f87171"
          : stage.done
            ? "#4ade80"
            : stage.current
              ? "#fbbf24"
              : "#64748b";
        var textColor = isFailed
          ? "#fecaca"
          : stage.current || stage.done
            ? "#e2e8f0"
            : "#94a3b8";
        return (
          '<li style="display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-top:1px solid rgba(255,255,255,0.06);">' +
          '<span style="color:' +
          color +
          ';min-width:14px;">' +
          mark +
          "</span>" +
          '<span style="color:' +
          textColor +
          ';">' +
          String(stage.label || "").replace(/</g, "&lt;") +
          "</span></li>"
        );
      })
      .join("");
  }

  function renderExportFailed(label, detail) {
    renderExportProgress(label, {
      status: "failed",
      message: detail || "Export failed",
      error: detail || "Export failed",
      progress: [
        { id: "failed", label: "Export failed — please try again", done: false, current: true, failed: true },
      ],
      eta_seconds: null,
    });
  }

  function hideExportProgressSoon() {
    setTimeout(function () {
      var panel = document.getElementById("smplExportProgress");
      if (panel) panel.style.display = "none";
    }, 2500);
  }

  async function pollAndDownloadExport(directBase, exportSpec, format, params) {
    renderExportProgress(exportSpec.label, {
      message: "Queued",
      status: "queued",
      progress: [
        { id: "queued", label: "Export queued", done: false, current: true },
        { id: "validated", label: "Validation complete", done: false, current: false },
        { id: "intelligence", label: "Financial context ready", done: false, current: false },
        {
          id: "narrative",
          label: format === "pptx" ? "Building PowerPoint" : "Building package",
          done: false,
          current: false,
        },
        { id: "complete", label: "Ready to download", done: false, current: false },
      ],
      eta_seconds: format === "pptx" ? 480 : 300,
    });
    var jobPath =
      format === "pptx" ? "/api/v1/export/jobs/mda-deck" : "/api/v1/export/jobs/mda-package";
    var startUrl = boardLiveUrl(directBase, jobPath) + "?" + params.toString();
    try {
      var startRes = await boardFetchWithTimeout(
        startUrl,
        boardLiveFetchInit(directBase, { method: "POST", cache: "no-store" }),
        120000,
      );
      if (!startRes.ok) {
        var startErr = await boardApiErrorMessage(startRes);
        if (startRes.status === 429) {
          renderExportFailed(exportSpec.label, startErr);
          alert(
            exportSpec.label +
              " regenerate limit reached for this close period.\n\n" +
              startErr +
              "\n\nContact SMPL support if you need an exception.",
          );
          return "error";
        }
        if (startRes.status === 409 && /freeze/i.test(startErr)) {
          renderExportFailed(exportSpec.label, startErr);
          alert(
            exportSpec.label +
              " needs a close freeze pack first.\n\n" +
              startErr +
              "\n\nRun board validation (or ask Ops to prewarm freezes), then retry.",
          );
          return "error";
        }
        renderExportFailed(exportSpec.label, startErr);
        alert(exportSpec.label + " export failed:\n" + startErr);
        return "error";
      }
      var startJson = await startRes.json();
      var jobId = startJson && startJson.job_id;
      if (!jobId) {
        renderExportFailed(exportSpec.label, "No job id returned from API.");
        alert(exportSpec.label + " export failed: no job id returned from API.");
        return "error";
      }
      renderExportProgress(exportSpec.label, startJson);
      var deadline = Date.now() + 900000;
      while (Date.now() < deadline) {
        await sleep(5000);
        var statusUrl = boardLiveUrl(directBase, "/api/v1/export/jobs/" + jobId);
        var statusRes = await boardFetchWithTimeout(
          statusUrl,
          boardLiveFetchInit(directBase, { method: "GET", cache: "no-store" }),
          60000,
        );
        if (!statusRes.ok) continue;
        var statusJson = await statusRes.json();
        renderExportProgress(exportSpec.label, statusJson);
        if (statusJson.status === "failed") {
          var failDetail = statusJson.error || statusJson.message || "Unknown error";
          // statusJson.progress already includes "Export failed — please try again"
          alert(exportSpec.label + " export failed:\n" + failDetail + "\n\nPlease try again.");
          return "error";
        }
        if (statusJson.status === "complete") {
          triggerDirectExportDownload(
            boardLiveUrl(directBase, "/api/v1/export/jobs/" + jobId + "/download"),
            exportSpec.label,
            true,
          );
          try {
            if (statusJson.evidence_pack && window.SMPLContinuity) {
              var pack = Object.assign({}, statusJson.evidence_pack);
              if (statusJson.has_evidence_html) {
                // Fetch HTML companion so Continuity can re-download offline
                boardFetchWithTimeout(
                  boardLiveUrl(directBase, "/api/v1/export/jobs/" + jobId + "/evidence.html"),
                  boardLiveFetchInit(directBase, { method: "GET", cache: "no-store" }),
                  60000,
                ).then(function (evRes) {
                  if (!evRes || !evRes.ok) {
                    SMPLContinuity.saveEvidencePack(pack);
                    return;
                  }
                  return evRes.text().then(function (html) {
                    pack.html = html;
                    SMPLContinuity.saveEvidencePack(pack);
                  });
                }).catch(function () {
                  SMPLContinuity.saveEvidencePack(pack);
                });
              } else {
                SMPLContinuity.saveEvidencePack(pack);
              }
            }
          } catch (evErr) {
            console.warn("[board-hydrate] evidence pack save failed", evErr);
          }
          hideExportProgressSoon();
          return "started";
        }
      }
      renderExportFailed(
        exportSpec.label,
        "Timed out after 15 minutes. Please try again.",
      );
      alert(
        exportSpec.label +
          " export timed out after 15 minutes.\n\nPlease try again.",
      );
      return "error";
    } catch (err) {
      var catchDetail = boardFetchErrorMessage(err, 900000);
      renderExportFailed(exportSpec.label, catchDetail);
      alert(exportSpec.label + " export failed:\n" + catchDetail + "\n\nPlease try again.");
      return "error";
    }
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

    // Client A–F is advisory at export: always proceed; companion HTML report on WARN.
    // Hard identification belongs at import/close — not when finance pulls presentations.
    var tieOutGate = null;
    if (global.SMPLProvenance && typeof global.SMPLProvenance.gatePublish === "function") {
      tieOutGate = global.SMPLProvenance.gatePublish({ closeMonth: closeMonth });
      if (tieOutGate.blocked) {
        alert(
          (format === "pptx" ? "MD&A Deck" : "Variance Commentary") +
            " export blocked — tie-out failed (forceBlock).\n\n" +
            (tieOutGate.message || "") +
            "\n\nClient HTML tie-out report downloaded when available.",
        );
        return "tieout-blocked";
      }
      if (tieOutGate.result && !tieOutGate.result.passed && tieOutGate.message) {
        console.warn("[board-hydrate] tie-out advisory (export proceeds)", tieOutGate.message);
      }
    }

    // Board header buttons — must match backend export registry (export_sheet_registry.py).
    // Variance Commentary button → SMPL MD&A Excel package (Prompt 2), NOT month-end-close.xlsx.
    var exportSpec =
      format === "pptx"
        ? {
            path: "/api/v1/export/mda-deck.pptx",
            filename: "mda_deck_" + closeMonth + ".pptx",
            label: "MD&A Deck",
          }
        : {
            path: "/api/v1/export/mda-package.xlsx",
            filename: "SMPL_MDA_Package_" + closeMonth.replace("-", "_") + ".xlsx",
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

    var exportTimeoutMs = 900000;

    try {
      var directBase = await boardExportApiBase();
      var host = global.location && global.location.hostname;
      var isLocal = host === "localhost" || host === "127.0.0.1";
      var exportUrl = boardLiveUrl(directBase, exportSpec.path) + "?" + params.toString();

      if (!isLocal) {
        var pollStatus = await pollAndDownloadExport(directBase, exportSpec, format, params);
        if (
          (pollStatus === "ok" || pollStatus === "started") &&
          tieOutGate &&
          tieOutGate.status === "WARN"
        ) {
          alert(
            exportSpec.label +
              " ready.\n\nClient tie-out report downloaded (advisory). " +
              "Forecast gaps are OK to review; production actuals should be fixed at import/close.\n\n" +
              (tieOutGate.message || ""),
          );
        }
        return pollStatus;
      }

      var exportBase = directBase || "";
      try {
        var result = await fetchBoardExportBlob(exportBase, exportUrl, exportSpec, exportTimeoutMs);
        if (result.ok) {
          if (tieOutGate && tieOutGate.status === "WARN") {
            alert(
              exportSpec.label +
                " ready.\n\nClient tie-out report downloaded (advisory). " +
                "Forecast gaps are OK to review; production actuals should be fixed at import/close.\n\n" +
                (tieOutGate.message || ""),
            );
          }
          return "ok";
        }
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
    refreshAllLiveCommentariesFromMetrics: refreshAllLiveCommentariesFromMetrics,
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
    refreshAllLiveCommentariesFromMetrics();
    // Defer first hydrate so embedded iframe receives smpl:org from parent (Forecast Engine pattern).
    setTimeout(function () {
      void smplBoardHydrate();
    }, 50);
  });
})(window);
