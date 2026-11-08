/**
 * Validation Engine + Board validated stamp.
 *
 * Board (exec): one-line stamp → in-Board Validation view (same skins/topbar).
 * Validation Engine (owner): Ties, cash spine, Evidence Pack, Monthly Align, mapping.
 * Cite-to-calc: owner mode only (?owner=1, Validation view, or Ctrl+Shift+V).
 * Not SOC 2 certified.
 */
(function (global) {
  "use strict";

  var STRIP_ID = "smpl-trust-strip";
  var STAMP_ID = "smpl-validated-stamp";
  var DRAWER_ID = "smpl-cite-drawer";
  var FIDELITY_KEY = "smpl_last_evidence_pack";
  var OWNER_KEY = "smpl_owner_mode";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isValidationEnginePage() {
    if (global.SMPL_VALIDATION_ENGINE === true) return true;
    var path = (global.location && global.location.pathname) || "";
    return path.indexOf("/validation") >= 0;
  }

  function isOwnerMode() {
    if (global.SMPL_OWNER_MODE === true) return true;
    try {
      if (global.sessionStorage && global.sessionStorage.getItem(OWNER_KEY) === "1") return true;
    } catch (e) {
      /* ignore */
    }
    var q = (global.location && global.location.search) || "";
    return /[?&]owner=1(?:&|$)/.test(q);
  }

  function setOwnerMode(on) {
    global.SMPL_OWNER_MODE = !!on;
    try {
      if (on) global.sessionStorage.setItem(OWNER_KEY, "1");
      else global.sessionStorage.removeItem(OWNER_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  function validationHref() {
    var period = closeMonth();
    return "/app/board?view=validation&period=" + encodeURIComponent(period);
  }

  function reportingHref() {
    return "/reporting-engine";
  }

  function publicationLabel() {
    var period = closeMonth() || "";
    var status = global.SMPL_VALIDATION_STATUS || {};
    var allow = status.validation_allow || {};
    var final = !!(status.allowed || allow.allowed);
    return period ? period + (final ? " Final" : " Prelim") : "";
  }

  function openValidationView() {
    // Prefer leaving the Board iframe for the top-chrome Validation Engine route.
    try {
      if (global.top && global.top !== global && global.top.location) {
        var period = closeMonth();
        global.top.location.href =
          "/app/board?view=validation&period=" + encodeURIComponent(period);
        return;
      }
    } catch (e) {
      /* cross-origin — fall through */
    }
    if (typeof global.show === "function" && document.getElementById("slideArea")) {
      global.show("validation", null);
      try {
        var u = new URL(global.location.href);
        u.searchParams.set("view", "validation");
        u.searchParams.set("period", closeMonth());
        global.history.replaceState({}, "", u.pathname + "?" + u.searchParams.toString() + u.hash);
      } catch (err) {
        /* ignore */
      }
      return;
    }
    global.location.href = validationHref();
  }

  function closeMonth() {
    return global.CLOSE_MONTH;
  }

  function apiBase() {
    return (global.SMPL_API_BASE || "/api/v1").replace(/\/$/, "");
  }

  function orgId() {
    return (
      global.SMPL_ORG_ID ||
      (global.SMPL_OUTLOOK_PAYLOAD && global.SMPL_OUTLOOK_PAYLOAD.organization_id) ||
      null
    );
  }

  function getTieOut() {
    if (global.SMPLProvenance && typeof global.SMPLProvenance.getLastTieOut === "function") {
      return global.SMPLProvenance.getLastTieOut() || global.SMPL_LAST_TIEOUT || null;
    }
    return global.SMPL_LAST_TIEOUT || null;
  }

  function getCashContinuity() {
    var p = global.SMPL_OUTLOOK_PAYLOAD;
    return (p && p.CASH_CONTINUITY) || null;
  }

  function getEvidencePack() {
    try {
      var raw = global.SMPL_LAST_EVIDENCE_PACK || localStorage.getItem(FIDELITY_KEY);
      if (!raw) return null;
      return typeof raw === "string" ? JSON.parse(raw) : raw;
    } catch (e) {
      return null;
    }
  }

  function saveEvidencePack(pack) {
    if (!pack || typeof pack !== "object") return;
    global.SMPL_LAST_EVIDENCE_PACK = pack;
    try {
      localStorage.setItem(FIDELITY_KEY, JSON.stringify(pack));
    } catch (e) {
      /* quota */
    }
    refreshValidatedStamp();
  }

  function trustSummary() {
    var tie = getTieOut() || {};
    var cc = getCashContinuity() || {};
    var pack = getEvidencePack() || {};
    var allow = global.SMPL_VALIDATION_STATUS && global.SMPL_VALIDATION_STATUS.validation_allow;
    var failN = (tie.failures && tie.failures.length) || 0;
    var softN = (tie.soft && tie.soft.length) || 0;
    var cashFails = closeCashFailures(cc && cc.failures);
    var ccFails = cashFails.length;
    var fidelityIssues =
      (pack.narrative_issues || 0) +
      (pack.post_render_failures || 0) +
      (pack.anchor_failures || 0);
    var clearance = tieClearance(
      (tie.failures || []).map(parseFailString),
      cashFails,
      openMappingRows(),
    );
    var passed = failN === 0 && ccFails === 0;
    var status = passed ? (softN || fidelityIssues ? "warn" : "ok") : "fail";
    var allowed = !!(allow && allow.allowed);
    return {
      status: status,
      closeMonth: tie.closeMonth || cc.as_of || closeMonth(),
      failN: failN,
      softN: softN,
      ccFails: ccFails,
      checksRun: (tie.checksRun && tie.checksRun.length) || 0,
      fidelityIssues: fidelityIssues,
      freezeStatus: pack.freeze_status || (global.SMPL_FREEZE_STATUS || ""),
      passed: passed,
      allowed: allowed,
      allowedBy: allow && allow.allowed_by,
      allowedAt: allow && allow.allowed_at,
      youN: clearance.you.length,
      calcN: clearance.calc.length,
      mappingOpen: (global.SMPL_VALIDATION_STATUS && global.SMPL_VALIDATION_STATUS.mapping_material_open_count) || 0,
      readyForBoard: !!(
        global.SMPL_VALIDATION_STATUS &&
        global.SMPL_VALIDATION_STATUS.monthly_align &&
        global.SMPL_VALIDATION_STATUS.monthly_align.ready_for_board
      ),
    };
  }

  function statusColor(status) {
    if (status === "ok") return "var(--teal, #5fa878)";
    if (status === "warn") return "#c48a3a";
    return "var(--red, #b8705f)";
  }

  function statusLabel(s) {
    if (s.status === "ok") return "Ties pass";
    if (s.status === "warn") return "Ties pass · advisories";
    if (s.youN && s.calcN) return s.youN + " for you · " + s.calcN + " in the calculation";
    if (s.youN) return s.youN + " for you to clear";
    if (s.calcN) return "In the calculation";
    return s.failN + " open";
  }

  function ensureValidatedStamp() {
    if (isValidationEnginePage()) return null;
    var el = document.getElementById(STAMP_ID);
    if (el) return el;
    var top = document.querySelector(".topbar-right");
    if (!top) return null;
    // Remove legacy trust strip if present
    var legacy = document.getElementById(STRIP_ID);
    if (legacy && legacy.parentNode) legacy.parentNode.removeChild(legacy);
    el = document.createElement("a");
    el.id = STAMP_ID;
    el.className = "smpl-validated-stamp";
    el.href = reportingHref();
    el.setAttribute("aria-label", "Open Reporting Engine");
    el.addEventListener("click", function (ev) {
      ev.preventDefault();
      try {
        if (global.top && global.top.location) {
          global.top.location.href = reportingHref();
          return;
        }
      } catch (e) { /* stay in frame */ }
      global.location.href = reportingHref();
    });
    top.insertBefore(el, top.firstChild);
    return el;
  }

  function refreshValidatedStamp() {
    if (isValidationEnginePage()) {
      var existing = document.getElementById(STAMP_ID);
      if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
      return;
    }
    var el = ensureValidatedStamp();
    if (!el) return;
    var s = trustSummary();
    var ready = s.readyForBoard || s.allowed;
    var clr = ready ? statusColor("ok") : statusColor(s.status === "fail" ? "fail" : "warn");
    el.style.borderColor = clr;
    el.style.color = clr;
    el.href = reportingHref();
    var published = publicationLabel();
    var badge = document.getElementById("periodBadge");
    if (badge && published) badge.textContent = published;
    if (ready) {
      el.innerHTML =
        '<span class="smpl-trust-dot" style="background:' +
        clr +
        '"></span><strong>' +
        esc(published) +
        "</strong>" +
        '<span class="smpl-trust-meta">' +
        (s.allowedBy ? "by " + esc(s.allowedBy) : "Reporting Engine") +
        "</span>";
    } else {
      el.innerHTML =
        '<span class="smpl-trust-dot" style="background:' +
        clr +
        '"></span><strong>' +
        esc(published) +
        '</strong><span class="smpl-trust-meta">Reporting Engine</span>';
    }
  }

  /** @deprecated Board Continuity tab removed — use Validation Engine. */
  function refreshTrustStrip() {
    refreshValidatedStamp();
  }

  function openContinuityTab() {
    openValidationView();
  }

  function parseFailString(f) {
    if (f && typeof f === "object") return f;
    var s = String(f || "");
    var m = s.match(
      /^\[([^\]]+)\]\s+(\S+)\s+(.+?):\s+expected=([-\d.]+)\s+actual=([-\d.]+)\s+diff=([-\d.]+)/,
    );
    if (m) {
      return {
        rule: m[1],
        period: m[2],
        metric: m[3],
        expected: Number(m[4]),
        actual: Number(m[5]),
        diff: Number(m[6]),
        message: s,
      };
    }
    return { rule: "?", period: "", metric: "", message: s };
  }

  function openMappingRows() {
    var status = global.SMPL_VALIDATION_STATUS || {};
    var queue = status.mapping_queue || [];
    return queue.filter(function (row) {
      return row && row.status === "open";
    });
  }

  function signedMoney(n) {
    var v = Number(n);
    if (!isFinite(v)) return "—";
    var body = "$" + Math.abs(Math.round(v)).toLocaleString();
    return v < 0 ? "−" + body : body;
  }

  function tieHoldSide(source, rule, metric) {
    if (source === "cash") return rule === "C3" || rule === "C4" || rule === "C5" ? "actual" : "expected";
    if (rule === "C3" || rule === "C4" || rule === "F1" || rule === "F2" || rule === "F3" || rule === "F4a" || rule === "F4b") {
      return "actual";
    }
    if (rule === "A5" && metric && metric.indexOf("SRC") === 0) return "actual";
    return "expected";
  }

  function tieItemGuide(source, rule, metric, openCount) {
    var calcHow =
      "This is in the calculation. The statements are built from the books. There is no amount on this step to edit.";
    var mapHow =
      "Map the open accounts. They are not on a statement line yet, so the calculated statements are missing them.";
    var viaMap = openCount > 0;
    function calc(title, holdLabel, otherLabel) {
      return { yours: false, go: null, title: title, holdLabel: holdLabel, otherLabel: otherLabel, how: calcHow };
    }
    function mapped(title, holdLabel, otherLabel) {
      if (viaMap) {
        return { yours: true, go: "mapping", title: title, holdLabel: holdLabel, otherLabel: otherLabel, how: mapHow };
      }
      return calc(title, holdLabel, otherLabel);
    }
    if (source === "cash" && rule === "C5") {
      return calc("The forecast does not open on this close's cash", "Last closed cash", "Forecast opening cash");
    }
    if (source === "cash" && rule === "C4") {
      return {
        yours: false,
        go: null,
        title: "The cash bridge does not add up to ending cash",
        holdLabel: "Ending cash",
        otherLabel: "Bridge total",
        how:
          "Ending cash is the cash-flow statement. The bridge total is beginning cash plus collections, minus outflows, plus financing. The difference is the part of ending cash those lines do not explain. The accounts on Mapping are a separate list, and their amounts are not this difference.",
      };
    }
    if (source === "cash") {
      var cashTitle = {
        C1: "Cash-flow ending cash and the balance sheet do not match",
        C2: "The cash-flow total does not match the balance-sheet movement",
        C3: "The cash bridge ending cash does not match the statement",
      };
      return calc(cashTitle[rule] || "The cash calculation does not foot", "Cash-flow statement", "The other cash total");
    }
    if (rule === "A1" || rule === "A2" || rule === "A3") {
      return {
        yours: true,
        go: "import",
        title: "The ARR waterfall does not add up",
        holdLabel: "Beginning plus the movements",
        otherLabel: "Ending ARR on the file",
        how: "Replace the billing waterfall on Import. Ending ARR has to equal beginning ARR plus the movements.",
      };
    }
    if (rule === "A4" || rule === "A5") {
      return {
        yours: true,
        go: "import",
        title: "The billing waterfall and the imported ARR do not match",
        holdLabel: "ARR waterfall",
        otherLabel: "Imported ARR",
        how: "Replace the billing import. The close uses one waterfall, and the imported ARR has to match it.",
      };
    }
    if (rule === "A6" || rule === "B3a" || rule === "B3b" || rule === "C4" || (rule && rule.charAt(0) === "F")) {
      return calc("The forecast does not match this close", "This close", "Forecast");
    }
    if (rule === "B1") return mapped("Cash does not carry into the next month", "Ending cash", "Next month's beginning cash");
    if (rule === "B5") {
      return mapped(
        "Operating cash does not equal the lines on the cash-flow statement",
        "Sum of the operating lines",
        "Operating cash on the statement",
      );
    }
    if (rule === "C1") return mapped("Gross profit does not equal revenue minus cost", "Revenue minus cost", "Gross profit");
    if (rule === "C2") {
      return mapped(
        "EBITDA does not equal gross profit minus operating expenses",
        "Gross profit minus operating expenses",
        "EBITDA",
      );
    }
    if (rule === "C3") {
      return {
        yours: true,
        go: viaMap ? "both" : "import",
        title: "An imported amount does not match the calculated statement",
        holdLabel: "Statement",
        otherLabel: "Imported file",
        how: viaMap
          ? "The statement is calculated from the books. Map the open accounts, or replace the import that brought the other amount."
          : "The statement is calculated from the books. Replace the import that brought the other amount.",
      };
    }
    if (rule === "D1") {
      return {
        yours: true,
        go: "import",
        title: "The headcount file is not consistent",
        holdLabel: "Department columns",
        otherLabel: "The same file",
        how: "Replace the workforce import. Each department column has to cover the same months.",
      };
    }
    return mapped("A figure does not match the calculated statement", "Calculated statement", "The other figure");
  }

  function closeCashFailures(fails) {
    return (fails || []).filter(function (row) {
      return String((row && row.scenario) || "") !== "Budget";
    });
  }

  function tieClearance(clientFails, cashFails, openRows) {
    var openCount = (openRows || []).length;
    var groups = {};
    function add(source, row) {
      var rule = row.rule || row.code || "?";
      var metric = row.metric || row.label || "";
      var guide = tieItemGuide(source, rule, metric, openCount);
      var key = (guide.yours ? "you:" : "calc:") + guide.title;
      if (!groups[key]) {
        groups[key] = {
          yours: guide.yours,
          go: guide.go,
          title: guide.title,
          how: guide.how,
          holdLabel: guide.holdLabel,
          otherLabel: guide.otherLabel,
          rows: [],
        };
      }
      var side = tieHoldSide(source, rule, metric);
      var first = row.expected;
      var second = row.actual;
      if (source === "cash") {
        first = row.left;
        second = row.right;
      }
      groups[key].rows.push({
        when: [row.scenario, row.period].filter(Boolean).join(" "),
        hold: side === "actual" ? second : first,
        other: side === "actual" ? first : second,
      });
    }
    (clientFails || []).forEach(function (row) {
      add("client", row);
    });
    closeCashFailures(cashFails).forEach(function (row) {
      add("cash", row);
    });
    var you = [];
    var calc = [];
    Object.keys(groups).forEach(function (key) {
      (groups[key].yours ? you : calc).push(groups[key]);
    });
    return { you: you, calc: calc };
  }

  function cashChipRows(cc) {
    var fails = (cc && cc.failures) || [];
    var byCode = {};
    fails.forEach(function (f) {
      var code = f.code || f.rule || "?";
      byCode[code] = (byCode[code] || 0) + 1;
    });
    return [
      { code: "C1", label: "CFS ↔ BS cash" },
      { code: "C2", label: "CFS ↔ IS+BS spine" },
      { code: "C3", label: "Bridge ↔ CFS" },
      { code: "C4", label: "Bridge foots" },
      { code: "C5", label: "Forecast opens on close" },
    ].map(function (c) {
      var n = byCode[c.code] || 0;
      return { code: c.code, label: c.label, ok: n === 0, count: n };
    });
  }

  function row(label, value) {
    return (
      '<div class="smpl-cont-row"><span>' +
      esc(label) +
      "</span><strong>" +
      esc(value) +
      "</strong></div>"
    );
  }

  function renderTiesPanel(area) {
    if (!area) return;
    if (global.SMPLProvenance && typeof global.SMPLProvenance.runTieOut === "function") {
      try {
        global.SMPLProvenance.runTieOut();
      } catch (e) {
        /* non-fatal */
      }
    }
    var s = trustSummary();
    var tie = getTieOut() || {};
    var cc = getCashContinuity() || {};
    var pack = getEvidencePack() || {};
    var fails = (tie.failures || []).map(parseFailString);
    var clearance = tieClearance(fails, closeCashFailures(cc && cc.failures), openMappingRows());
    var openRows = openMappingRows();

    function tieCards(groups) {
      return groups
        .map(function (g) {
          var lines = g.rows
            .slice(0, 8)
            .map(function (r) {
              return (
                "<div style='margin-top:6px'>" +
                esc(r.when || "") +
                " · " +
                esc(g.holdLabel) +
                " <code>" +
                esc(signedMoney(r.hold)) +
                "</code> · " +
                esc(g.otherLabel) +
                " <code>" +
                esc(signedMoney(r.other)) +
                "</code>" +
                (isFinite(Number(r.hold)) && isFinite(Number(r.other))
                  ? " · Difference " + esc(signedMoney(Number(r.hold) - Number(r.other)))
                  : "") +
                "</div>"
              );
            })
            .join("");
          var more = g.rows.length > 8 ? "<div style='margin-top:6px'>" + (g.rows.length - 8) + " more months</div>" : "";
          var accts =
            g.go === "mapping" || g.go === "both"
              ? "<div style='margin-top:8px'>" +
                openRows
                  .map(function (q) {
                    return esc((q.account_number || q.account_id || "") + " " + (q.name || "") + " · " + signedMoney(q.amount));
                  })
                  .join("<br>") +
                "</div>"
              : "";
          var buttons = [];
          if (g.go === "mapping" || g.go === "both") buttons.push({ go: "mapping", label: "Map the accounts" });
          if (g.go === "import" || g.go === "both") buttons.push({ go: "import", label: "Replace the import" });
          var btn = buttons.length
            ? "<div style='margin-top:10px;display:flex;gap:8px;flex-wrap:wrap'>" +
              buttons
                .map(function (b) {
                  return (
                    '<button type="button" class="ai-global-btn" data-go="' +
                    esc(b.go) +
                    '" data-how="' +
                    esc(g.how) +
                    '">' +
                    esc(b.label) +
                    "</button>"
                  );
                })
                .join("") +
              "</div>"
            : "";
          return (
            '<div class="card" style="margin-top:14px"><div class="card-title">' +
            esc(g.title) +
            "</div><div class='slide-sub' style='margin-top:0'>" +
            esc(g.how) +
            "</div>" +
            lines +
            more +
            accts +
            btn +
            "</div>"
          );
        })
        .join("");
    }

    var youHtml = clearance.you.length
      ? tieCards(clearance.you)
      : '<div class="smpl-cont-ok" style="margin-top:14px">Nothing for you to change on this close.</div>';
    var calcHtml = clearance.calc.length
      ? '<div class="slide-sub" style="margin-top:16px">In the calculation. Allow waits. Mapping and Import do not clear these.</div>' +
        tieCards(clearance.calc)
      : "";
    var cashOk = closeCashFailures(cc && cc.failures).length === 0;

    area.innerHTML =
      '<div class="card-title" style="margin-bottom:12px">Tie-out</div>' +
      '<div class="slide-sub" style="margin-top:0">' +
      (clearance.you.length
        ? "The statement is the number that has to hold. Each item below names the step that changes the other number."
        : clearance.calc.length
          ? "The statement is calculated from the books. Nothing on this step edits it."
          : "The calculated statements tie.") +
      "</div>" +
      '<div class="smpl-cont-banner" style="border-color:' +
      statusColor(s.status) +
      '"><div style="font-weight:600;color:' +
      statusColor(s.status) +
      '">' +
      esc(statusLabel(s)) +
      " · " +
      esc(s.closeMonth) +
      "</div>" +
      '<div style="font-size:11px;color:var(--text3);margin-top:4px">' +
      (cashOk ? "Cash spine ties." : "Cash is in the items below.") +
      "</div></div>" +
      '<div class="card-title" style="margin-top:14px">What you clear</div>' +
      youHtml +
      calcHtml +
      '<div class="card" style="margin-top:14px"><div class="card-title">AI fidelity (Evidence Pack)</div>' +
      '<div class="smpl-cont-grid">' +
      row("Last export", pack.export_kind || "—") +
      row("Freeze", pack.freeze_status || s.freezeStatus || "—") +
      row("Post-render", pack.post_render_ok === false ? "soft-warn" : pack.post_render_ok ? "pass" : "—") +
      row("Anchors", pack.anchor_failures != null ? String(pack.anchor_failures) + " miss" : "—") +
      row("Narrative", pack.narrative_issues != null ? String(pack.narrative_issues) : "—") +
      row("Summary", pack.summary || "No Evidence Pack yet — export MD&A Deck or Variance.") +
      "</div>" +
      '<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">' +
      '<button type="button" class="ai-global-btn" onclick="if(window.SMPLProvenance)SMPLProvenance.downloadTieOutReport()">Download tie-out HTML</button>' +
      (pack.html
        ? '<button type="button" class="ai-global-btn" onclick="window.SMPLContinuity.downloadStoredEvidenceHtml()">Download Evidence Pack</button>'
        : "") +
      "</div></div>";
  }

  function money(n) {
    var v = Number(n) || 0;
    return "$" + Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function veState(area) {
    if (!area._veState) area._veState = { panel: "import", status: null, books: null };
    return area._veState;
  }

  function commentaryOpenCount() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    var book = payload && payload.COMMENTARY;
    var loaded = !!(book && book.comparisons && book.comparisons.length);
    if (!loaded || typeof global.boardStatementReviewOpenCount !== "function") return null;
    return global.boardStatementReviewOpenCount();
  }

  function loadCloseBooks(area) {
    var oid = orgId();
    if (!oid || !area) return Promise.resolve(null);
    return fetch("/api/workspace/summary?organization_id=" + encodeURIComponent(oid), {
      credentials: "include",
      cache: "no-store",
    })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        var st = veState(area);
        st.books = data || null;
        if (st.panel === "import") paintValidationPanel(area);
        return data;
      })
      .catch(function () { return null; });
  }

  var IMPORT_DOMAINS = [
    { id: "erp_gl", label: "ERP / General ledger", description: "Actual GL, income statement, balance sheet, cash flow", entity_types: ["gl_actuals", "forecast_gl_detail", "forecast_income_statement", "forecast_balance_sheet", "forecast_cash_flow_statement"], typical_systems: ["NetSuite", "QuickBooks", "Xero", "Sage"] },
    { id: "crm", label: "CRM / Pipeline", description: "Opportunities, closed-won, bookings", entity_types: ["opportunities", "forecast_opportunities", "forecast_bookings_summary", "forecast_marketing_pipeline"], typical_systems: ["Salesforce", "HubSpot"] },
    { id: "billing_arr", label: "Billing / ARR", description: "MRR waterfall, subscriptions, invoices, deferred revenue", entity_types: ["mrr_waterfall", "forecast_mrr_waterfall", "subscriptions", "invoices", "payments", "forecast_deferred_revenue_waterfall", "forecast_revenue_schedule", "customers"], typical_systems: ["Stripe", "Chargebee", "Maxio", "Salesforce CPQ"] },
    { id: "cash", label: "Cash / Treasury", description: "Collections and operating cash bridge inputs", entity_types: ["forecast_cash_collections", "forecast_operating_cash_flow_bridge", "forecast_working_capital_metrics"], typical_systems: ["Treasury system", "Bank CSV via API"] },
    { id: "workforce", label: "Workforce / HRIS", description: "Headcount plan and workforce feeds", entity_types: ["headcount_plan", "forecast_headcount_plan", "workforce_employees", "workforce_open_requisitions", "workforce_hiring_ramp_assumptions", "workforce_compensation_bands", "workforce_department_allocation_rules"], typical_systems: ["BambooHR", "Workday", "ADP"] },
  ];

  function importDomains(books) {
    var live = books && books.load_domains && books.load_domains.domains;
    if (live && live.length) return live;
    return IMPORT_DOMAINS.map(function (d) {
      return {
        id: d.id, label: d.label, description: d.description, entity_types: d.entity_types, typical_systems: d.typical_systems,
        status: "not_loaded", rows_imported: 0, rows_rejected: 0, source_system: null,
      };
    });
  }

  function importSystems(domains) {
    var seen = {};
    var systems = [];
    (domains || []).forEach(function (domain) {
      (domain.typical_systems || []).forEach(function (name) {
        if (!name || seen[name]) return;
        seen[name] = true;
        systems.push(name);
      });
    });
    return systems;
  }

  function importStatusLabel(status) {
    if (status === "loaded") return "Loaded";
    if (status === "partial") return "Partial — row errors";
    if (status === "failed") return "Failed";
    if (status === "in_progress") return "In progress";
    if (!status || status === "not_loaded") return "Not loaded";
    return String(status);
  }

  function importStatusClass(status) {
    if (status === "loaded") return "ve-ok";
    if (status === "failed") return "ve-bad";
    if (status === "not_loaded") return "ve-check-meta";
    return "ve-warn";
  }

  function describeLoad(ok, payload) {
    if (!ok || (payload && (payload.header_error || payload.integrity_error))) {
      var detail = payload && (payload.detail || (payload.header_error && payload.header_error.message) || payload.integrity_error);
      return { ok: false, text: typeof detail === "string" && detail ? detail : "Load failed." };
    }
    var batch = (payload && payload.batch) || {};
    var receipt = (payload && payload.load_receipt) || {};
    var applied = receipt.rows_applied != null ? receipt.rows_applied : (batch.rows_imported || 0);
    var rejected = receipt.rows_rejected != null ? receipt.rows_rejected : (batch.rows_rejected || 0);
    var status = String(receipt.status || batch.status || "");
    var succeeded = status !== "failed" && status !== "partial" && !rejected;
    var dest = payload && payload.destination && payload.destination.destination_table;
    var live = payload && (payload.reporting_live || payload.destination_live);
    var periods = live && live.periods;
    var text = (succeeded ? "Load succeeded" : "Load finished with row errors") + " — " + applied + " applied";
    if (rejected) text += ", " + rejected + " rejected";
    if (payload && (payload.entity_type || payload.csv_kind)) text += " · " + (payload.entity_type || payload.csv_kind);
    if (dest) text += ". Wrote " + dest;
    if (payload && payload.destination && payload.destination.reporting_reads_this_table === false) {
      text += ". Reporting does not read that table. The file name has to match a template";
    }
    if (periods && periods.length) text += ". Periods in table: " + periods.join(", ");
    text += ".";
    var warnings = payload && payload.warnings;
    if (warnings && warnings.length) text += " " + warnings.slice(0, 3).join(" ");
    return { ok: succeeded, text: text };
  }

  function renderImportHtml(books, st) {
    var ledger = books && books.close_ledger;
    var sources = (ledger && ledger.ingest_by_source) || {};
    var batches = (ledger && ledger.recent_batches) || [];
    var domains = importDomains(books);
    var systems = importSystems(domains);
    var sourceSystem = (st && st.importSource) || "";
    var note = st && st.importNote;
    var period = books && books.load_domains && books.load_domains.as_of_period;
    var domainRows = domains.map(function (d) {
      return "<tr><td><strong>" + esc(d.label) + "</strong><div class=\"ve-check-meta\">" + esc(d.description) +
        "</div></td><td class=\"" + importStatusClass(d.status) + "\">" + esc(importStatusLabel(d.status)) +
        "</td><td>" + esc(String(d.rows_imported || 0)) + "</td><td>" + esc(String(d.rows_rejected || 0)) +
        "</td><td>" + esc(d.source_system || "—") + "</td></tr>";
    }).join("");
    var systemOpts = ['<option value="">Choose a system</option>'].concat(systems.map(function (name) {
      return '<option value="' + esc(name) + '"' + (name === sourceSystem ? " selected" : "") + ">" + esc(name) + "</option>";
    })).join("");
    var sourceRows = Object.keys(sources).map(function (key) {
      var row = sources[key] || {};
      return "<tr><td>" + esc(key) + "</td><td>" + esc(String(row.batches || 0)) +
        "</td><td>" + esc(String(row.rows_imported || 0)) + "</td><td>" + esc(String(row.rows_rejected || 0)) + "</td></tr>";
    }).join("");
    var batchRows = batches.slice(0, 8).map(function (b) {
      var batchStatus = b.status || "—";
      var batchClass = batchStatus === "complete" || batchStatus === "loaded" ? "ve-ok" : (batchStatus === "failed" ? "ve-bad" : "ve-warn");
      return "<tr><td>" + esc(b.filename || b.entity_type || b.source || "—") + "</td><td>" + esc(b.source || "—") +
        "</td><td class=\"" + batchClass + "\">" + esc(importStatusLabel(batchStatus === "complete" ? "loaded" : batchStatus)) +
        "</td><td>" + esc(String(b.rows_imported || 0)) + "</td><td>" + esc(String(b.rows_rejected || 0)) + "</td></tr>";
    }).join("");
    var csv = sources.csv_upload;
    return (
      '<div class="card-title" style="margin-bottom:12px">Import</div>' +
      '<div class="slide-sub" style="margin-top:0">Upload a template, or choose the system this month comes from. Which datasets that system loads is already mapped for the customer.</div>' +
      (st && st.tieNote
        ? '<div class="card" style="margin-bottom:12px">' + esc(st.tieNote) + "</div>"
        : "") +
      (note
        ? '<div class="card" style="margin-bottom:12px"><strong class="' + (note.ok === true ? "ve-ok" : note.ok === false ? "ve-bad" : "ve-warn") + '">' + esc(note.text) + "</strong></div>"
        : "") +
      '<div class="card"><div class="card-title">Load status' + (period ? " · " + esc(period) : "") + "</div>" +
      '<table class="ve-map"><thead><tr><th>Option</th><th>Load</th><th>Applied</th><th>Rejected</th><th>System</th></tr></thead><tbody>' +
      domainRows + "</tbody></table></div>" +
      '<div class="card" style="margin-top:12px"><div class="card-title">Upload a template</div>' +
      '<div class="ve-check-meta">Use the exact template name, for example Actual_MRR_Waterfall.csv. A renamed file lands in a table reporting does not read.</div>' +
      '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px">' +
      '<input type="file" id="veImportFile" accept=".csv,text/csv" />' +
      '<button type="button" class="ai-global-btn" id="veImportBtn"' + (st && st.importBusy ? " disabled" : "") + '>Upload and import</button></div>' +
      '<div class="ve-check-meta" style="margin-top:8px">' +
      (csv
        ? "This period: " + esc(String(csv.batches || 0)) + " CSV batches · " + esc(String(csv.rows_imported || 0)) + " imported" + (csv.rows_rejected ? " · " + esc(String(csv.rows_rejected)) + " rejected" : "")
        : "No CSV batches yet this period.") +
      "</div></div>" +
      '<div class="card" style="margin-top:12px"><div class="card-title">Import from a system</div>' +
      '<div class="ve-check-meta">Choose the system. This step does not ask which dataset to load.</div>' +
      '<div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:10px">' +
      '<label class="ve-check-meta">System<select id="vePushSource" class="ve-map-sel" style="display:block;margin-top:4px;min-width:220px">' + systemOpts + "</select></label>" +
      '<button type="button" class="ai-global-btn" id="vePushBtn"' + (st && st.importBusy ? " disabled" : "") + '>Use this system</button></div></div>' +
      '<div class="card" style="margin-top:12px"><div class="card-title">This period</div>' +
      (ledger
        ? (sourceRows
          ? '<table class="ve-map"><thead><tr><th>Source</th><th>Batches</th><th>Imported</th><th>Rejected</th></tr></thead><tbody>' + sourceRows + "</tbody></table>"
          : '<div class="ve-check-meta">No batches yet this period.</div>')
        : '<div class="ve-check-meta">Loading imports…</div>') +
      "</div>" +
      (batchRows
        ? '<div class="card" style="margin-top:12px"><div class="card-title">Recent loads</div><table class="ve-map"><thead><tr><th>File</th><th>Source</th><th>Result</th><th>Imported</th><th>Rejected</th></tr></thead><tbody>' + batchRows + "</tbody></table></div>"
        : "")
    );
  }

  function renderLedgerHtml(books) {
    var ledger = books && books.close_ledger;
    var batches = (ledger && ledger.recent_batches) || [];
    var errors = (ledger && ledger.recent_row_errors) || [];
    var batchRows = batches.slice(0, 12).map(function (b) {
      return "<tr><td>" + esc(b.filename || b.entity_type || "—") + "</td><td>" + esc(b.source || "—") +
        "</td><td>" + esc(b.status || "—") + "</td><td>" + esc(String(b.rows_imported || 0)) +
        "</td><td>" + esc(String(b.rows_rejected || 0)) + "</td></tr>";
    }).join("");
    var errorRows = errors.slice(0, 8).map(function (row) {
      return "<tr><td>" + esc(row.source || "—") + "</td><td>" + esc(row.entity_type || "—") +
        "</td><td>" + esc(row.message || row.error_code || "—") + "</td></tr>";
    }).join("");
    return (
      '<div class="card" style="margin-top:12px"><div class="card-title">Close ledger</div>' +
      (ledger
        ? (batchRows
          ? '<table class="ve-map"><thead><tr><th>Load</th><th>Source</th><th>Status</th><th>Imported</th><th>Rejected</th></tr></thead><tbody>' + batchRows + "</tbody></table>"
          : '<div class="ve-check-meta">No loads recorded for this period.</div>') +
          (errorRows
            ? '<div class="card-title" style="margin-top:12px">Row errors</div><table class="ve-map"><thead><tr><th>Source</th><th>Entity</th><th>Message</th></tr></thead><tbody>' + errorRows + "</tbody></table>"
            : "")
        : '<div class="ve-check-meta">Loading the close ledger…</div>') +
      "</div>"
    );
  }

  var COMMENTARY_COMPARISONS = { mom: "MoM", qoq: "QoQ", yoy: "YoY", ytd: "YTD", budget: "vs Budget", forecast: "vs Forecast" };

  function commentaryBook() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    var book = payload && payload.COMMENTARY;
    if (book && book.comparisons && book.comparisons.length) return book;
    return null;
  }

  function commentaryReviewMap() {
    var status = global.SMPL_VALIDATION_STATUS;
    var saved = (status && status.commentary && status.commentary.reviews) || {};
    var out = {};
    Object.keys(saved).forEach(function (key) {
      var record = saved[key];
      if (record === true || (record && record.reviewed)) out[key] = true;
    });
    return out;
  }

  function commentarySections() {
    var book = commentaryBook();
    if (!book) return null;
    var reviews = commentaryReviewMap();
    var sections = [];
    (book.comparisons || []).forEach(function (item) {
      if (item.available === false) return;
      (item.statements || []).forEach(function (statement) {
        var required = 0;
        var reviewed = 0;
        var openLabels = [];
        []
          .concat(statement.lines || [])
          .concat(statement.departments || [])
          .concat(statement.accounts || [])
          .forEach(function (row) {
            if (!row.review_required) return;
            required += 1;
            if (reviews[row.key]) reviewed += 1;
            else openLabels.push(row.label || row.id || "Line");
          });
        if (!required) return;
        sections.push({
          comparison: COMMENTARY_COMPARISONS[item.id] || item.label || item.id,
          section: statement.title || statement.id,
          required: required,
          reviewed: reviewed,
          openLabels: openLabels,
        });
      });
    });
    return sections;
  }

  function commentaryChecked() {
    var sections = commentarySections();
    if (!sections) return false;
    return sections.every(function (section) { return section.reviewed >= section.required; });
  }

  function renderCommentaryHtml() {
    var open = commentaryOpenCount();
    var sections = commentarySections();
    if (open == null || !sections) {
      return (
        '<div class="card-title" style="margin-bottom:12px">Commentary reviewed</div>' +
        '<div class="slide-sub" style="margin-top:0">This step checks off once every required section has been reviewed.</div>' +
        '<div class="card"><div class="ve-check-meta">Variance commentary for this month is not loaded yet.</div></div>'
      );
    }
    var openSections = sections.filter(function (section) { return section.reviewed < section.required; }).length;
    var checked = commentaryChecked();
    var rows = sections.map(function (section) {
      var done = section.reviewed >= section.required;
      var waiting = section.openLabels.slice(0, 3).join(", ");
      if (section.openLabels.length > 3) waiting += " +" + (section.openLabels.length - 3) + " more";
      return (
        "<tr><td>" + esc(section.comparison) + "</td><td>" + esc(section.section) + "</td><td>" +
        esc(String(section.reviewed)) + " of " + esc(String(section.required)) + "</td><td class=\"" +
        (done ? "ve-ok" : "ve-bad") + "\">" +
        (done ? "✓ Reviewed" : "Not reviewed" + (waiting ? " — " + esc(waiting) : "")) +
        "</td></tr>"
      );
    }).join("");
    return (
      '<div class="card-title" style="margin-bottom:12px">Commentary reviewed</div>' +
      '<div class="slide-sub" style="margin-top:0">Each required section is listed here. The step is checked off only when every one of them has been reviewed.</div>' +
      '<div class="card"><ul class="ve-checklist">' +
      '<li><span class="ve-check ' + (checked ? "ve-ok" : "ve-bad") + '">' + (checked ? "✓" : "!") +
      '</span><div><strong>' + (checked ? "Checked off" : "Not checked off") + '</strong><div class="ve-check-meta">' +
      (checked
        ? "Every required section has been reviewed."
        : openSections + (openSections === 1 ? " section still needs a review." : " sections still need a review.")) +
      "</div></div></li></ul>" +
      (rows
        ? '<table class="ve-map" style="margin-top:12px"><thead><tr><th>Comparison</th><th>Section</th><th>Reviewed</th><th>Status</th></tr></thead><tbody>' + rows + "</tbody></table>"
        : '<div class="ve-check-meta" style="margin-top:12px">No section requires a review this month.</div>') +
      "</div>"
    );
  }

  function renderStatusHtml(status, period) {
    var s = status || {};
    var allow = s.validation_allow || {};
    var align = s.monthly_align || {};
    var ready = !!align.ready_for_board;
    return (
      '<div class="card-title" style="margin-bottom:12px">Close status</div>' +
      '<div class="slide-sub" style="margin-top:0">Freeze pack + last Allow. Leadership Board reads this as a one-line stamp.</div>' +
      '<div class="card"><div class="card-title">Stamps</div><div class="smpl-cont-grid">' +
      row("As-of", s.as_of_period || period) +
      row("Freeze", s.freeze_status || "—") +
      row("Built", datasetBuilt(s.freeze_built_at)) +
      '<div class="smpl-cont-row"><span>Allow</span><strong class="' +
      (allow.allowed ? "ve-ok" : "ve-warn") +
      '">' +
      (allow.allowed ? "Allowed by " + esc(allow.allowed_by || "owner") : "Not yet Allowed") +
      "</strong></div>" +
      row("Mapping open", String(s.mapping_material_open_count || 0) + " material") +
      '<div class="smpl-cont-row"><span>Board ready</span><strong class="' +
      (ready ? "ve-ok" : "ve-warn") +
      '">' +
      (ready ? "Yes — outcomes stamp green" : "No — finish Approval") +
      "</strong></div>" +
      "</div></div>" +
      '<p class="ve-foot">Not SOC 2 certified. Hard ID for production actuals is import/close; this Engine is where owners verify and Allow.</p>'
    );
  }

  function renderMappingHtml(status, tieNote) {
    var s = status || {};
    var queue = s.mapping_queue || [];
    var lines = s.management_lines || [];
    var rows = queue
      .map(function (q) {
        var open = q.status === "open";
        var selected = open ? q.statement_hint || q.mapped_to || "ga" : q.mapped_to;
        var opts = lines
          .map(function (l) {
            return (
              '<option value="' +
              esc(l) +
              '"' +
              (selected === l ? " selected" : "") +
              ">" +
              esc(l) +
              "</option>"
            );
          })
          .join("");
        var action = open
          ? '<select class="ve-map-sel" data-acct="' +
            esc(q.account_id) +
            '">' +
            opts +
            "</select> " +
            '<button type="button" class="ai-global-btn ve-map-btn" data-acct="' +
            esc(q.account_id) +
            '" data-name="' +
            esc(q.name) +
            '" data-acct-num="' +
            esc(q.account_number || q.account_id) +
            '" data-amount="' +
            esc(String(q.amount || 0)) +
            '">Map</button>'
          : '<button type="button" class="ai-global-btn ve-unmap-btn" data-acct="' +
            esc(q.account_id) +
            '" data-name="' +
            esc(q.name) +
            '" data-acct-num="' +
            esc(q.account_number || q.account_id) +
            '" data-mapped-to="' +
            esc(q.mapped_to || "") +
            '">Undo map</button>';
        return (
          "<tr>" +
          "<td><code>" +
          esc(q.account_number || q.account_id) +
          "</code></td>" +
          "<td>" +
          esc(q.name) +
          "</td>" +
          "<td>" +
          money(q.amount) +
          "</td>" +
          "<td>" +
          esc(q.status) +
          (q.mapped_to ? " → " + esc(q.mapped_to) : "") +
          (open && q.statement_hint ? ' <span class="ve-check-meta">(hint: ' + esc(q.statement_hint) + ")</span>" : "") +
          "</td>" +
          "<td>" +
          action +
          "</td></tr>"
        );
      })
      .join("");
    return (
      '<div class="card-title" style="margin-bottom:12px">Mapping</div>' +
      '<div class="slide-sub" style="margin-top:0">New GL / dimension accounts since last Allow — map each account to a management line (IS / BS / CFS / ARR). You will confirm before it saves.</div>' +
      (tieNote ? '<div class="card" style="margin-bottom:12px">' + esc(tieNote) + "</div>" : "") +
      mappingCheckHtml(status) +
      '<div class="card"><div class="card-title">Unmapped / needs review</div>' +
      '<table class="ve-map"><thead><tr><th>Acct</th><th>Name</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>' +
      rows +
      "</tbody></table></div>" +
      (s.import_hard_id_blocked
        ? '<p class="ve-bad" style="margin-top:12px;font-size:12px">Import/close hard-ID: material open items will block close lock until mapped.</p>'
        : "")
    );
  }

  function mappingAccountsMapped(status) {
    if (!status) return null;
    var align = status.monthly_align || {};
    var openN = Number(status.mapping_material_open_count);
    if (!isFinite(openN) || openN < 0) openN = 0;
    var ok = align.mapping_clear != null ? !!align.mapping_clear : openN === 0;
    return { ok: ok, openN: openN };
  }

  function mappingCheckHtml(status) {
    var mapped = mappingAccountsMapped(status);
    if (!mapped) return "";
    var detail = mapped.ok
      ? "Every account is mapped."
      : mapped.openN === 1
        ? "1 account still needs a map."
        : mapped.openN > 1
          ? mapped.openN + " accounts still need a map."
          : "Accounts still need a map.";
    return (
      '<div class="card" style="margin-bottom:12px"><ul class="ve-checklist">' +
      '<li><span class="ve-check ' +
      (mapped.ok ? "ve-ok" : "ve-bad") +
      '">' +
      (mapped.ok ? "✓" : "!") +
      '</span><div><strong>Accounts Mapped</strong><div class="ve-check-meta">' +
      detail +
      "</div></div></li></ul></div>"
    );
  }

  function datasetBuilt(stamp) {
    var parsed = new Date(stamp);
    if (!stamp || isNaN(parsed.getTime())) return "—";
    var shifted = new Date(parsed.getTime() - 8 * 60 * 60 * 1000);
    var names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var hour = shifted.getUTCHours();
    var minute = shifted.getUTCMinutes();
    var clockHour = hour % 12;
    if (clockHour === 0) clockHour = 12;
    var minutes = minute < 10 ? "0" + minute : String(minute);
    return (
      names[shifted.getUTCMonth()] +
      " " +
      shifted.getUTCDate() +
      ", " +
      shifted.getUTCFullYear() +
      ", " +
      clockHour +
      ":" +
      minutes +
      " " +
      (hour >= 12 ? "PM" : "AM")
    );
  }

  function renderAlignHtml(status, ve) {
    var s = status || {};
    ve = ve || {};
    var align = s.monthly_align || {};
    var ts = trustSummary();
    var tiesOk = ts.passed;
    var mapOk = !!align.mapping_clear;
    var allowOk = !!align.allow;
    var commentaryOpen =
      typeof global.boardStatementReviewOpenCount === "function" ? global.boardStatementReviewOpenCount() : 0;
    var commentaryOk = commentaryOpen === 0;
    var freezeOk = s.freeze_status === "COMPLETE" || s.freeze_status === "STALE";
    var freezeWhen = freezeOk ? "Built " + datasetBuilt(s.freeze_built_at) : "Not built yet";
    var canAllow =
      tiesOk &&
      mapOk &&
      commentaryOk &&
      (s.freeze_status === "COMPLETE" || s.freeze_status === "STALE") &&
      !allowOk;
    var reviewer = (s.validation_allow && s.validation_allow.allowed_by) || "";
    var finalizedAt = s.validation_allow && s.validation_allow.allowed_at;
    var finalizedWhen = finalizedAt ? datasetBuilt(finalizedAt) : "";
    var finalizedDetail = allowOk
      ? "Finalized by " + (reviewer || "the reviewer") + (finalizedWhen && finalizedWhen !== "—" ? " · " + finalizedWhen : "")
      : "Not finalized";
    return (
      '<div class="card-title" style="margin-bottom:12px">' +
      (global.SMPL_REPORTING_ENGINE ? "Finalize" : "Approval") +
      "</div>" +
      '<div class="slide-sub" style="margin-top:0">' +
      (global.SMPL_REPORTING_ENGINE
        ? "The reporting stamp stays Prelim until this month is finalized. After that it reads Final."
        : "The last step. Ties, mapping, the commentary review, and the freeze have to be finished. The final reviewer then records the month as finalized.") +
      "</div>" +
      '<div class="card"><ul class="ve-checklist">' +
      '<li><span class="ve-check ' +
      (tiesOk ? "ve-ok" : "ve-bad") +
      '">' +
      (tiesOk ? "✓" : "!") +
      "</span><div><strong>Ties</strong><div class=\"ve-check-meta\">" +
      esc(statusLabel(ts)) +
      (global.SMPL_REPORTING_ENGINE
        ? ""
        : ts.youN
          ? " — clear these on Tie-out"
          : ts.calcN
            ? " — in the calculation, not edited here"
            : "") +
      "</div></div></li>" +
      '<li><span class="ve-check ' +
      (mapOk ? "ve-ok" : "ve-bad") +
      '">' +
      (mapOk ? "✓" : "!") +
      '</span><div><strong>Mapping queue</strong><div class="ve-check-meta">' +
      (mapOk ? "Clear" : (s.mapping_material_open_count || 0) + " material open") +
      "</div></div></li>" +
      '<li><span class="ve-check ' +
      (commentaryOk ? "ve-ok" : "ve-bad") +
      '">' +
      (commentaryOk ? "✓" : "!") +
      '</span><div><strong>Commentary</strong><div class="ve-check-meta">' +
      (commentaryOk ? "Reviewed" : commentaryOpen + " lines still need a check") +
      "</div></div></li>" +
      '<li><span class="ve-check ' +
      (freezeOk ? "ve-ok" : "ve-bad") +
      '">' +
      (freezeOk ? "✓" : "!") +
      '</span><div style="flex:1;min-width:0"><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap"><strong>Freeze</strong><span class="ve-check-meta" style="margin:0">' +
      esc(freezeWhen) +
      '</span><button type="button" class="ai-global-btn ve-allow-btn" id="veRefreezeBtn"' +
      (ve.freezeBusy ? " disabled" : "") +
      ">" +
      (ve.freezeBusy ? "Updating the dataset…" : "Update dataset") +
      "</button></div></div></li>" +
      '<li><span class="ve-check ' +
      ((ts.fidelityIssues || 0) === 0 ? "ve-ok" : "ve-warn") +
      '">' +
      ((ts.fidelityIssues || 0) === 0 ? "✓" : "~") +
      '</span><div><strong>Deck fidelity</strong><div class="ve-check-meta">Evidence Pack / post-render — soft-warn OK; review before the month is finalized</div></div></li>' +
      '<li><span class="ve-check ' +
      (allowOk ? "ve-ok" : "ve-warn") +
      '">' +
      (allowOk ? "✓" : "○") +
      '</span><div><strong>Month Finalized</strong><div class="ve-check-meta">' +
      esc(finalizedDetail) +
      "</div></div></li>" +
      "</ul>" +
      '<div style="margin-top:16px;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">' +
      '<label class="ve-check-meta" style="display:flex;flex-direction:column;gap:4px">Final reviewer' +
      '<input type="text" class="ve-allow-by" id="veAllowBy" placeholder="Name" value="' +
      esc(allowOk ? reviewer : "") +
      '" /></label>' +
      '<button type="button" class="ai-global-btn ve-allow-btn" id="veAllowBtn"' +
      (canAllow ? "" : " disabled") +
      ">Finalize month</button>" +
      (allowOk
        ? '<button type="button" class="ai-global-btn ve-allow-btn" id="veUncloseBtn">Unclose month</button>'
        : "") +
      "</div>" +
      '<p class="ve-foot" style="margin-top:8px">The MD&amp;A deck reads this dataset. Update it when the books change. Line reviews are cleared because the amounts change. The wording stays.</p>' +
      (ve.freezeNote ? '<p class="ve-foot" style="margin-top:8px">' + esc(ve.freezeNote) + "</p>" : "") +
      (!canAllow && !allowOk
        ? '<p class="ve-foot" style="margin-top:8px">' +
          esc(
            (ts.youN
              ? "Clear the Tie-out items. Each one names the step that changes it. "
              : ts.calcN
                ? "A calculation gap is holding this. Import and Mapping do not change it. "
                : "") +
              (!mapOk ? "Map the open accounts. " : "") +
              (!commentaryOk ? "Finish the commentary review. " : "") +
              (!freezeOk ? "The freeze has to be built. " : "") +
              "Then finalize the month.",
          ) +
          "</p>"
        : "") +
      "</div>"
    );
  }

  function paintValidationPanel(area) {
    var st = veState(area);
    var body = area.querySelector("#veBoardBody");
    if (!body) return;
    if (st.panel === "status") st.panel = "align";
    var commentaryBtn = area.querySelector('#veBoardNav button[data-panel="commentary"]');
    if (commentaryBtn) {
      commentaryBtn.textContent = commentaryChecked() ? "4 · Commentary reviewed ✓" : "4 · Commentary reviewed";
    }
    var mappingBtn = area.querySelector('#veBoardNav button[data-panel="mapping"]');
    if (mappingBtn) {
      var mapped = mappingAccountsMapped(st.status);
      mappingBtn.textContent = mapped && mapped.ok ? "2 · Mapping ✓" : "2 · Mapping";
    }
    if (st.panel === "import") {
      body.innerHTML = renderImportHtml(st.books, st);
      var importBtn = body.querySelector("#veImportBtn");
      if (importBtn) {
        importBtn.onclick = function () {
          var input = body.querySelector("#veImportFile");
          var file = input && input.files && input.files[0];
          var oid = orgId();
          if (st.importBusy) return;
          if (!file) {
            st.importNote = { ok: false, text: "Choose a CSV first." };
            paintValidationPanel(area);
            return;
          }
          if (!oid) {
            st.importNote = { ok: false, text: "No organization is loaded." };
            paintValidationPanel(area);
            return;
          }
          st.importBusy = true;
          st.importNote = { ok: "wait", text: "Importing " + file.name + "…" };
          paintValidationPanel(area);
          var fd = new FormData();
          fd.append("organization_id", oid);
          fd.append("file", file);
          fetch("/api/ingest/csv", { method: "POST", credentials: "include", body: fd })
            .then(function (res) {
              return res.json().then(function (payload) { return { ok: res.ok, payload: payload }; });
            })
            .then(function (result) {
              st.importBusy = false;
              st.importNote = describeLoad(result.ok, result.payload);
              return loadCloseBooks(area);
            })
            .catch(function (err) {
              st.importBusy = false;
              st.importNote = { ok: false, text: String((err && err.message) || err) };
              paintValidationPanel(area);
            });
        };
      }
      var pushBtn = body.querySelector("#vePushBtn");
      if (pushBtn) {
        pushBtn.onclick = function () {
          var sourceEl = body.querySelector("#vePushSource");
          var sourceSystem = sourceEl && sourceEl.value;
          st.importSource = sourceSystem || "";
          if (st.importBusy) return;
          if (!sourceSystem) {
            st.importNote = { ok: false, text: "Choose a system first." };
            paintValidationPanel(area);
            return;
          }
          st.importNote = {
            ok: true,
            text: sourceSystem + " is the system for this import. Datasets for that system are mapped for this customer.",
          };
          paintValidationPanel(area);
        };
      }
      return;
    }
    if (st.panel === "commentary") {
      body.innerHTML = renderCommentaryHtml();
      return;
    }
    if (st.panel === "ties") {
      renderTiesPanel(body);
      Array.prototype.forEach.call(body.querySelectorAll("button[data-go]"), function (btn) {
        btn.onclick = function () {
          st.panel = btn.getAttribute("data-go");
          st.tieNote = btn.getAttribute("data-how") || "";
          var nav = area.querySelector("#veBoardNav");
          if (nav) {
            Array.prototype.forEach.call(nav.querySelectorAll("button[data-panel]"), function (b) {
              b.classList.toggle("on", b.getAttribute("data-panel") === st.panel);
            });
          }
          paintValidationPanel(area);
        };
      });
      return;
    }
    if (st.panel === "mapping" || st.panel === "reporting") {
      body.innerHTML =
        renderMappingHtml(st.status, st.tieNote) + (st.panel === "reporting" ? renderAlignHtml(st.status, st) : "");
      Array.prototype.forEach.call(body.querySelectorAll(".ve-map-btn"), function (btn) {
        btn.onclick = function () {
          var id = btn.getAttribute("data-acct");
          var sel = body.querySelector('select.ve-map-sel[data-acct="' + id + '"]');
          var line = sel && sel.value;
          if (!line) return;
          var acctNum = btn.getAttribute("data-acct-num") || id;
          var name = btn.getAttribute("data-name") || id;
          var amount = money(btn.getAttribute("data-amount"));
          var ok = global.confirm(
            "Map this GL account?\n\n" +
              "Account: " +
              acctNum +
              " — " +
              name +
              "\nAmount: " +
              amount +
              "\nManagement line: " +
              line +
              "\n\nThis changes how the account rolls into Board statements. You can Undo map afterward."
          );
          if (!ok) return;
          btn.disabled = true;
          postMapAccount(id, line, "FP&A Owner")
            .then(function (next) {
              st.status = next;
              paintValidationPanel(area);
            })
            .catch(function (err) {
              alert(String(err.message || err));
              btn.disabled = false;
            });
        };
      });
      Array.prototype.forEach.call(body.querySelectorAll(".ve-unmap-btn"), function (btn) {
        btn.onclick = function () {
          var id = btn.getAttribute("data-acct");
          var acctNum = btn.getAttribute("data-acct-num") || id;
          var name = btn.getAttribute("data-name") || id;
          var mappedTo = btn.getAttribute("data-mapped-to") || "";
          var ok = global.confirm(
            "Undo this mapping and re-open the queue item?\n\n" +
              "Account: " +
              acctNum +
              " — " +
              name +
              (mappedTo ? "\nCurrently mapped to: " + mappedTo : "")
          );
          if (!ok) return;
          btn.disabled = true;
          postUnmapAccount(id, "FP&A Owner")
            .then(function (next) {
              st.status = next;
              paintValidationPanel(area);
            })
            .catch(function (err) {
              alert(String(err.message || err));
              btn.disabled = false;
            });
        };
      });
      if (st.panel !== "reporting") return;
    }
    if (st.panel === "align" || st.panel === "reporting") {
      if (st.panel === "align") body.innerHTML = renderAlignHtml(st.status, st);
      var refreezeBtn = body.querySelector("#veRefreezeBtn");
      if (refreezeBtn) {
        refreezeBtn.onclick = function () {
          if (st.freezeBusy) return;
          st.freezeBusy = true;
          st.freezeNote = "";
          paintValidationPanel(area);
          postRefreeze()
            .then(function (next) {
              st.freezeBusy = false;
              st.status = next;
              st.freezeNote = "Dataset updated from the current books. Line reviews were cleared because the amounts changed. The wording stays.";
              paintValidationPanel(area);
            })
            .catch(function (err) {
              st.freezeBusy = false;
              st.freezeNote = String((err && err.message) || err);
              paintValidationPanel(area);
            });
        };
      }
      var allowBtn = body.querySelector("#veAllowBtn");
      if (allowBtn) {
        allowBtn.onclick = function () {
          var who = ((body.querySelector("#veAllowBy") || {}).value || "").trim();
          if (!who) {
            alert("Enter the final reviewer.");
            return;
          }
          allowBtn.disabled = true;
          postAllow(who, "Finalize month")
            .then(function (next) {
              st.status = next;
              paintValidationPanel(area);
              refreshValidatedStamp();
            })
            .catch(function (err) {
              var msg = String(err.message || err);
              if (msg.indexOf("commentary_review_open") >= 0) {
                msg = "Commentary still has lines that need a check.";
              }
              alert(msg);
              allowBtn.disabled = false;
            });
        };
      }
      var uncloseBtn = body.querySelector("#veUncloseBtn");
      if (uncloseBtn) {
        uncloseBtn.onclick = function () {
          var who = ((body.querySelector("#veAllowBy") || {}).value || "").trim() || "owner";
          uncloseBtn.disabled = true;
          postUnclose(who)
            .then(function (next) {
              st.status = next;
              paintValidationPanel(area);
              refreshValidatedStamp();
            })
            .catch(function (err) {
              alert(String((err && err.message) || err));
              uncloseBtn.disabled = false;
            });
        };
      }
      return;
    }
  }

  /** Mapping and Finalize for the Reporting Engine. The month story sits above this. */
  function renderReportingClose(area) {
    if (!area) return;
    global.SMPL_VALIDATION_ENGINE = true;
    setOwnerMode(true);
    var st = veState(area);
    st.panel = "reporting";
    area.innerHTML = '<div id="veBoardBody"></div>';
    paintValidationPanel(area);
    fetchValidationStatus({ seedDemoQueue: true }).then(function (s) {
      st.status = s || global.SMPL_VALIDATION_STATUS;
      paintValidationPanel(area);
    });
  }

  /** Full Validation Engine inside Board chrome (owner workshop). */
  function renderValidationEngine(area) {
    if (!area) return;
    if (global.SMPL_REPORTING_ENGINE) {
      renderReportingClose(area);
      return;
    }
    global.SMPL_VALIDATION_ENGINE = true;
    setOwnerMode(true);
    var st = veState(area);
    if (st.panel === "status") st.panel = "align";
    area.innerHTML =
      '<div class="slide" style="padding:20px 24px 32px">' +
      '<div class="slide-title">' +
      (global.SMPL_REPORTING_ENGINE ? "Finalize" : "Close Engine") +
      "</div>" +
      '<div class="slide-sub">' +
      (global.SMPL_REPORTING_ENGINE
        ? "Map this month’s new accounts, finish the commentary checks, then finalize. The Board Platform reads Prelim until then, and Final after."
        : "Import the month, map the accounts, tie it out, confirm the variance commentary was reviewed, then approve.") +
      "</div>" +
      '<div class="subnav" id="veBoardNav">' +
      '<button type="button" class="snav-btn' + (st.panel === "import" ? " on" : "") + '" data-panel="import">1 · Import</button>' +
      '<button type="button" class="snav-btn' + (st.panel === "mapping" ? " on" : "") + '" data-panel="mapping">2 · Mapping</button>' +
      '<button type="button" class="snav-btn' + (st.panel === "ties" ? " on" : "") + '" data-panel="ties">3 · Tie-out</button>' +
      '<button type="button" class="snav-btn' + (st.panel === "commentary" ? " on" : "") + '" data-panel="commentary">4 · Commentary reviewed</button>' +
      '<button type="button" class="snav-btn' + (st.panel === "align" ? " on" : "") + '" data-panel="align">5 · Approval</button>' +
      "</div>" +
      '<div id="veBoardBody" style="margin-top:8px"></div>' +
      "</div>";
    var nav = area.querySelector("#veBoardNav");
    if (nav) {
      nav.addEventListener("click", function (ev) {
        var btn = ev.target.closest("button[data-panel]");
        if (!btn) return;
        st.panel = btn.getAttribute("data-panel");
        Array.prototype.forEach.call(nav.querySelectorAll("button[data-panel]"), function (b) {
          b.classList.toggle("on", b === btn);
        });
        paintValidationPanel(area);
      });
    }
    paintValidationPanel(area);
    fetchValidationStatus({ seedDemoQueue: true }).then(function (s) {
      st.status = s || global.SMPL_VALIDATION_STATUS;
      paintValidationPanel(area);
    });
    loadCloseBooks(area);
  }

  /** Legacy Continuity tab renderer — opens full Validation Engine panels. */
  function renderContinuity(area) {
    renderValidationEngine(area);
  }

  function ensureDrawer() {
    var el = document.getElementById(DRAWER_ID);
    if (el) return el;
    el = document.createElement("aside");
    el.id = DRAWER_ID;
    el.className = "smpl-cite-drawer";
    el.setAttribute("aria-hidden", "true");
    el.innerHTML =
      '<div class="smpl-cite-head"><strong>Cite to source</strong>' +
      '<button type="button" class="smpl-cite-close" aria-label="Close">&times;</button></div>' +
      '<div class="smpl-cite-body" id="smpl-cite-body"></div>';
    document.body.appendChild(el);
    el.querySelector(".smpl-cite-close").onclick = closeCiteDrawer;
    return el;
  }

  function closeCiteDrawer() {
    var el = document.getElementById(DRAWER_ID);
    if (!el) return;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
  }

  function openCiteDrawer(detail) {
    if (!isOwnerMode() && !isValidationEnginePage()) return;
    ensureDrawer();
    var body = document.getElementById("smpl-cite-body");
    var el = document.getElementById(DRAWER_ID);
    if (!body || !el) return;
    var rec = detail.record || {};
    body.innerHTML =
      '<div class="smpl-cite-value">' +
      esc(detail.displayValue || rec.value || "—") +
      "</div>" +
      '<div class="smpl-cont-grid">' +
      row("Metric", detail.metric || rec.field || "—") +
      row("Period", detail.period || rec.period || closeMonth()) +
      row("Scenario", detail.scenario || rec.series_kind || "Actual") +
      row("Source type", rec.source_type || "—") +
      row("Table.column", rec.table && rec.column ? rec.table + "." + rec.column : rec.path || "—") +
      row("Formula", rec.formula || rec.formula_id || "—") +
      row("Org", rec.org_id || "—") +
      row("Loaded at", rec.loaded_at || "—") +
      row("Final", rec.is_final == null ? "—" : String(rec.is_final)) +
      "</div>" +
      '<p class="smpl-cite-note">Owner cite-to-calc. AI narrates from _sources — it does not invent the dollars.</p>';
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
  }

  function resolveRecord(metric, period) {
    if (global.SMPLProvenance && typeof global.SMPLProvenance.resolveRecord === "function") {
      return global.SMPLProvenance.resolveRecord(metric, period) || {};
    }
    return {};
  }

  function onCiteClick(ev) {
    if (!isOwnerMode() && !isValidationEnginePage()) return;
    var t = ev.target;
    if (!t || !t.closest) return;
    var val = t.closest("[data-source], [data-metric].kpi-val, .kpi-val[data-metric]");
    if (!val) {
      var kpi = t.closest(".kpi");
      if (kpi) val = kpi.querySelector(".kpi-val[data-source], .kpi-val[data-metric]");
    }
    if (!val) return;
    if (t.closest("button, a, .nav-btn")) return;
    var metric = val.getAttribute("data-metric");
    if (!metric) return;
    ev.preventDefault();
    ev.stopPropagation();
    var period = val.getAttribute("data-period") || closeMonth();
    openCiteDrawer({
      metric: metric,
      period: period,
      displayValue: (val.textContent || "").trim(),
      sourceTag: val.getAttribute("data-source") || "",
      record: resolveRecord(metric, period),
      scenario: "Actual",
    });
  }

  function downloadStoredEvidenceHtml() {
    var pack = getEvidencePack();
    if (!pack || !pack.html) return;
    var blob = new Blob([pack.html], { type: "text/html;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "smpl_evidence_pack_" + (pack.as_of_period || closeMonth()) + ".html";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 2000);
  }

  function fetchValidationStatus(opts) {
    opts = opts || {};
    var oid = orgId();
    var period = closeMonth();
    if (!oid) {
      return Promise.resolve(null);
    }
    var url =
      apiBase() +
      "/validation-engine/status?organization_id=" +
      encodeURIComponent(oid) +
      "&as_of_period=" +
      encodeURIComponent(period) +
      (opts.seedDemoQueue ? "&seed_demo_queue=true" : "");
    return fetch(url, { credentials: "include" })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (data) {
          global.SMPL_VALIDATION_STATUS = data;
          refreshValidatedStamp();
        }
        return data;
      })
      .catch(function () {
        return null;
      });
  }

  function postRefreeze() {
    var oid = orgId();
    if (!oid) return Promise.reject(new Error("No organization is loaded."));
    var url =
      apiBase() +
      "/validation-engine/freeze?organization_id=" +
      encodeURIComponent(oid) +
      "&as_of_period=" +
      encodeURIComponent(closeMonth());
    return fetch(url, { method: "POST", credentials: "include" }).then(function (response) {
      return response.text().then(function (raw) {
        var body = {};
        if (raw) {
          try {
            body = JSON.parse(raw);
          } catch (err) {
            throw new Error(String(raw).replace(/\s+/g, " ").slice(0, 180));
          }
        }
        if (!response.ok) {
          var detail = body && body.detail;
          throw new Error(typeof detail === "string" && detail ? detail : "The dataset could not be updated.");
        }
        global.SMPL_VALIDATION_STATUS = body;
        refreshValidatedStamp();
        return body;
      });
    });
  }

  function postAllow(allowedBy, notes) {
    var oid = orgId();
    if (!oid) return Promise.reject(new Error("no_org"));
    var url =
      apiBase() +
      "/validation-engine/allow?organization_id=" +
      encodeURIComponent(oid) +
      "&as_of_period=" +
      encodeURIComponent(closeMonth());
    return fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allowed_by: allowedBy || "owner", notes: notes || null }),
    }).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.detail || body.message || "allow_failed");
        global.SMPL_VALIDATION_STATUS = body;
        refreshValidatedStamp();
        return body;
      });
    });
  }

  function postUnclose(revokedBy) {
    var oid = orgId();
    if (!oid) return Promise.reject(new Error("no_org"));
    var url =
      apiBase() +
      "/validation-engine/revoke-allow?organization_id=" +
      encodeURIComponent(oid) +
      "&as_of_period=" +
      encodeURIComponent(closeMonth());
    return fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ revoked_by: revokedBy || "owner" }),
    }).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.detail || body.message || "unclose_failed");
        global.SMPL_VALIDATION_STATUS = body;
        refreshValidatedStamp();
        return body;
      });
    });
  }

  function postMapAccount(accountId, mappedTo, mappedBy) {
    var oid = orgId();
    if (!oid) return Promise.reject(new Error("no_org"));
    var url =
      apiBase() +
      "/validation-engine/mapping/map?organization_id=" +
      encodeURIComponent(oid) +
      "&as_of_period=" +
      encodeURIComponent(closeMonth());
    return fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: accountId,
        mapped_to: mappedTo,
        mapped_by: mappedBy || "owner",
      }),
    }).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.detail || "map_failed");
        global.SMPL_VALIDATION_STATUS = body;
        return body;
      });
    });
  }

  function postUnmapAccount(accountId, unmappedBy) {
    var oid = orgId();
    if (!oid) return Promise.reject(new Error("no_org"));
    var url =
      apiBase() +
      "/validation-engine/mapping/unmap?organization_id=" +
      encodeURIComponent(oid) +
      "&as_of_period=" +
      encodeURIComponent(closeMonth());
    return fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: accountId,
        unmapped_by: unmappedBy || "owner",
      }),
    }).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.detail || "unmap_failed");
        global.SMPL_VALIDATION_STATUS = body;
        return body;
      });
    });
  }

  function install() {
    if (typeof document === "undefined") return;
    function boot() {
      var q = (global.location && global.location.search) || "";
      if (/[?&]owner=1(?:&|$)/.test(q)) setOwnerMode(true);
      if (!isValidationEnginePage()) {
        ensureValidatedStamp();
        refreshValidatedStamp();
        fetchValidationStatus();
      }
      if (isOwnerMode() || isValidationEnginePage()) {
        ensureDrawer();
        document.addEventListener("click", onCiteClick, true);
      }
      document.addEventListener("keydown", function (ev) {
        if (ev.ctrlKey && ev.shiftKey && (ev.key === "V" || ev.key === "v")) {
          setOwnerMode(!isOwnerMode());
          ensureDrawer();
          if (isOwnerMode()) document.addEventListener("click", onCiteClick, true);
          refreshValidatedStamp();
        }
      });
      setInterval(refreshValidatedStamp, 20000);
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", boot);
    } else {
      boot();
    }
  }

  global.SMPLContinuity = {
    renderContinuity: renderContinuity,
    renderValidationEngine: renderValidationEngine,
    renderReportingClose: renderReportingClose,
    renderTiesPanel: renderTiesPanel,
    refreshTrustStrip: refreshTrustStrip,
    refreshValidatedStamp: refreshValidatedStamp,
    openContinuityTab: openContinuityTab,
    openValidationView: openValidationView,
    openCiteDrawer: openCiteDrawer,
    closeCiteDrawer: closeCiteDrawer,
    saveEvidencePack: saveEvidencePack,
    getEvidencePack: getEvidencePack,
    downloadStoredEvidenceHtml: downloadStoredEvidenceHtml,
    trustSummary: trustSummary,
    fetchValidationStatus: fetchValidationStatus,
    postAllow: postAllow,
    postUnclose: postUnclose,
    renderAlignHtml: renderAlignHtml,
    postRefreeze: postRefreeze,
    datasetBuilt: datasetBuilt,
    mappingAccountsMapped: mappingAccountsMapped,
    renderMappingHtml: renderMappingHtml,
    postMapAccount: postMapAccount,
    postUnmapAccount: postUnmapAccount,
    tieClearance: tieClearance,
    isOwnerMode: isOwnerMode,
    setOwnerMode: setOwnerMode,
    validationHref: validationHref,
    reportingHref: reportingHref,
    publicationLabel: publicationLabel,
    install: install,
  };

  install();
})(typeof window !== "undefined" ? window : globalThis);
