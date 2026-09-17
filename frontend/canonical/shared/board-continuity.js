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
    var path = (global.location && global.location.pathname) || "";
    var base = path.indexOf("/board") >= 0 ? path.split("?")[0] : "/board/";
    if (!/\/$/.test(base) && !/\.html$/i.test(base)) base += "/";
    var q = "view=validation&period=" + encodeURIComponent(period);
    var emb = (global.location && global.location.search) || "";
    if (/[?&]embedded=1(?:&|$)/.test(emb)) q += "&embedded=1";
    return base + (base.indexOf("?") >= 0 ? "&" : "?") + q;
  }

  function openValidationView() {
    if (typeof global.show === "function" && document.getElementById("slideArea")) {
      var btn = Array.from(document.querySelectorAll(".nav-btn")).find(function (b) {
        return (b.getAttribute("onclick") || "").indexOf("show('validation'") >= 0;
      });
      global.show("validation", btn || null);
      try {
        var u = new URL(global.location.href);
        u.searchParams.set("view", "validation");
        u.searchParams.set("period", closeMonth());
        global.history.replaceState({}, "", u.pathname + "?" + u.searchParams.toString() + u.hash);
      } catch (e) {
        /* ignore */
      }
      return;
    }
    global.location.href = validationHref();
  }

  function closeMonth() {
    if (typeof global.CLOSE_MONTH === "string" && global.CLOSE_MONTH) return global.CLOSE_MONTH;
    var badge = document.getElementById("periodBadge");
    if (badge && badge.textContent) {
      var m = String(badge.textContent).match(/20\d{2}-\d{2}/);
      if (m) return m[0];
    }
    var q = (global.location && global.location.search) || "";
    var pm = q.match(/[?&]period=(20\d{2}-\d{2})/);
    if (pm) return pm[1];
    return "2026-06";
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
    var ccFails = (cc.failures && cc.failures.length) || 0;
    var fidelityIssues =
      (pack.narrative_issues || 0) +
      (pack.post_render_failures || 0) +
      (pack.anchor_failures || 0);
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
    return s.failN + (s.ccFails ? "+" + s.ccFails + " cash" : "") + " open";
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
    el.href = validationHref();
    el.setAttribute("aria-label", "Open Validation Engine");
    el.addEventListener("click", function (ev) {
      if (typeof global.show === "function" && document.getElementById("slideArea")) {
        ev.preventDefault();
        openValidationView();
      }
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
    el.href = validationHref();
    if (ready) {
      el.innerHTML =
        '<span class="smpl-trust-dot" style="background:' +
        clr +
        '"></span><strong>Close validated</strong>' +
        '<span class="smpl-trust-meta">' +
        esc(s.closeMonth) +
        (s.allowedBy ? " · by " + esc(s.allowedBy) : "") +
        " · Validation Engine</span>";
    } else {
      el.innerHTML =
        '<span class="smpl-trust-dot" style="background:' +
        clr +
        '"></span><strong>Validation pending</strong>' +
        '<span class="smpl-trust-meta">' +
        esc(s.closeMonth) +
        " · owner Align · Validation Engine</span>";
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
      /^\[([^\]]+)\]\s+(\d{4}-\d{2})\s+(.+?):\s+expected=([-\d.]+)\s+actual=([-\d.]+)\s+diff=([-\d.]+)/,
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
    var soft = tie.soft || [];
    var skipped = tie.skipped || [];
    var chips = cashChipRows(cc);

    var failHtml = fails.length
      ? fails
          .map(function (f, i) {
            return (
              '<details class="smpl-cont-fail" ' +
              (i === 0 ? "open" : "") +
              "><summary><strong>" +
              esc(f.rule || "FAIL") +
              "</strong> · " +
              esc(f.period || "") +
              " · " +
              esc(f.metric || f.message || "") +
              "</summary><div class='smpl-cont-fail-body'>" +
              (f.expected != null
                ? "<div>Expected: <code>" +
                  esc(String(f.expected)) +
                  "</code> · Actual: <code>" +
                  esc(String(f.actual)) +
                  "</code> · Diff: <code>" +
                  esc(String(f.diff)) +
                  "</code></div>"
                : "") +
              "<div class='smpl-cont-msg'>" +
              esc(f.message || "") +
              "</div></div></details>"
            );
          })
          .join("")
      : '<div class="smpl-cont-ok">No client A–F hard failures for this close.</div>';

    var chipHtml = chips
      .map(function (c) {
        var fg = c.ok ? "var(--teal)" : "#c48a3a";
        return (
          '<span class="smpl-cont-chip" style="color:' +
          fg +
          ";border-color:" +
          fg +
          '">' +
          (c.ok ? "✓" : c.count + "×") +
          " " +
          esc(c.label) +
          "</span>"
        );
      })
      .join("");

    area.innerHTML =
      '<div class="card-title" style="margin-bottom:12px">Ties</div>' +
      '<div class="slide-sub" style="margin-top:0">Client A–F + cash spine · TOL_ACTUALS $1 · failures first</div>' +
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
      s.checksRun +
      " checks · " +
      s.failN +
      " fail · " +
      s.softN +
      " soft · " +
      s.ccFails +
      " cash</div></div>" +
      '<div class="card" style="margin-top:14px"><div class="card-title">Cash spine (C1–C5)</div>' +
      '<div class="smpl-cont-chips">' +
      chipHtml +
      "</div>" +
      (cc.summary
        ? '<div style="font-size:11px;color:var(--text3);margin-top:8px">' + esc(cc.summary) + "</div>"
        : "") +
      "</div>" +
      '<div class="card" style="margin-top:14px"><div class="card-title">Failures first (client A–F)</div>' +
      failHtml +
      (soft.length
        ? '<div style="margin-top:12px;font-size:11px;color:#c48a3a"><strong>Soft / advisory</strong><ul style="margin:6px 0 0 16px">' +
          soft
            .slice(0, 12)
            .map(function (x) {
              return "<li>" + esc(x) + "</li>";
            })
            .join("") +
          "</ul></div>"
        : "") +
      (skipped.length
        ? '<div style="margin-top:10px;font-size:10px;color:var(--text3)">Skipped: ' +
          esc(skipped.slice(0, 6).join(" · ")) +
          "</div>"
        : "") +
      "</div>" +
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
    if (!area._veState) area._veState = { panel: "status", status: null };
    return area._veState;
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
      row("Built", s.freeze_built_at || "—") +
      '<div class="smpl-cont-row"><span>Allow</span><strong class="' +
      (allow.allowed ? "ve-ok" : "ve-warn") +
      '">' +
      (allow.allowed ? "Allowed by " + esc(allow.allowed_by || "owner") : "Not yet Allowed") +
      "</strong></div>" +
      row("Mapping open", String(s.mapping_material_open_count || 0) + " material") +
      '<div class="smpl-cont-row"><span>Board ready</span><strong class="' +
      (ready ? "ve-ok" : "ve-warn") +
      '">' +
      (ready ? "Yes — outcomes stamp green" : "No — finish Align") +
      "</strong></div>" +
      "</div></div>" +
      '<p class="ve-foot">Not SOC 2 certified. Hard ID for production actuals is import/close; this Engine is where owners verify and Allow.</p>'
    );
  }

  function renderMappingHtml(status) {
    var s = status || {};
    var queue = s.mapping_queue || [];
    var lines = s.management_lines || [];
    var rows = queue
      .map(function (q) {
        var open = q.status === "open";
        var opts = lines
          .map(function (l) {
            return (
              '<option value="' +
              esc(l) +
              '"' +
              (q.mapped_to === l ? " selected" : "") +
              ">" +
              esc(l) +
              "</option>"
            );
          })
          .join("");
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
          "</td>" +
          "<td>" +
          (open
            ? '<select class="ve-map-sel" data-acct="' +
              esc(q.account_id) +
              '">' +
              opts +
              "</select> " +
              '<button type="button" class="ai-global-btn ve-map-btn" data-acct="' +
              esc(q.account_id) +
              '">Map</button>'
            : "—") +
          "</td></tr>"
        );
      })
      .join("");
    return (
      '<div class="card-title" style="margin-bottom:12px">Mapping</div>' +
      '<div class="slide-sub" style="margin-top:0">New GL / dimension accounts since last Allow — map to management IS / BS / CFS / ARR before they distort statements.</div>' +
      '<div class="card"><div class="card-title">Unmapped / needs review</div>' +
      (queue.length
        ? '<table class="ve-map"><thead><tr><th>Acct</th><th>Name</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>' +
          rows +
          "</tbody></table>"
        : '<div class="smpl-cont-ok">Queue clear — no open material accounts.</div>') +
      "</div>" +
      (s.import_hard_id_blocked
        ? '<p class="ve-bad" style="margin-top:12px;font-size:12px">Import/close hard-ID: material open items will block close lock until mapped.</p>'
        : "")
    );
  }

  function renderAlignHtml(status) {
    var s = status || {};
    var align = s.monthly_align || {};
    var ts = trustSummary();
    var tiesOk = ts.passed;
    var mapOk = !!align.mapping_clear;
    var allowOk = !!align.allow;
    var canAllow =
      tiesOk && mapOk && (s.freeze_status === "COMPLETE" || s.freeze_status === "STALE") && !allowOk;
    return (
      '<div class="card-title" style="margin-bottom:12px">Monthly Align</div>' +
      '<div class="slide-sub" style="margin-top:0">Owner ritual (~15–30 min): ties → mapping → deck fidelity → Allow. Board stamp turns green only after Allow.</div>' +
      '<div class="card"><ul class="ve-checklist">' +
      '<li><span class="ve-check ' +
      (tiesOk ? "ve-ok" : "ve-bad") +
      '">' +
      (tiesOk ? "✓" : "!") +
      "</span><div><strong>Ties</strong><div class=\"ve-check-meta\">" +
      esc(statusLabel(ts)) +
      " — review Ties panel</div></div></li>" +
      '<li><span class="ve-check ' +
      (mapOk ? "ve-ok" : "ve-bad") +
      '">' +
      (mapOk ? "✓" : "!") +
      '</span><div><strong>Mapping queue</strong><div class="ve-check-meta">' +
      (mapOk ? "Clear" : (s.mapping_material_open_count || 0) + " material open") +
      "</div></div></li>" +
      '<li><span class="ve-check ' +
      ((ts.fidelityIssues || 0) === 0 ? "ve-ok" : "ve-warn") +
      '">' +
      ((ts.fidelityIssues || 0) === 0 ? "✓" : "~") +
      '</span><div><strong>Deck fidelity</strong><div class="ve-check-meta">Evidence Pack / post-render — soft-warn OK; review before Allow</div></div></li>' +
      '<li><span class="ve-check ' +
      (allowOk ? "ve-ok" : "ve-warn") +
      '">' +
      (allowOk ? "✓" : "○") +
      '</span><div><strong>Allow for Board</strong><div class="ve-check-meta">' +
      (allowOk
        ? "Recorded " + esc((s.validation_allow && s.validation_allow.allowed_at) || "")
        : "Not recorded") +
      "</div></div></li>" +
      "</ul>" +
      '<div style="margin-top:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">' +
      '<input type="text" class="ve-allow-by" id="veAllowBy" placeholder="Your name" value="FP&amp;A Owner" />' +
      '<button type="button" class="ai-global-btn ve-allow-btn" id="veAllowBtn"' +
      (canAllow ? "" : " disabled") +
      ">Allow close for Board</button>" +
      "</div>" +
      (!canAllow && !allowOk
        ? '<p class="ve-foot" style="margin-top:8px">Resolve ties + mapping + freeze COMPLETE before Allow.</p>'
        : "") +
      "</div>"
    );
  }

  function paintValidationPanel(area) {
    var st = veState(area);
    var body = area.querySelector("#veBoardBody");
    if (!body) return;
    if (st.panel === "ties") {
      renderTiesPanel(body);
      return;
    }
    if (st.panel === "mapping") {
      body.innerHTML = renderMappingHtml(st.status);
      Array.prototype.forEach.call(body.querySelectorAll(".ve-map-btn"), function (btn) {
        btn.onclick = function () {
          var id = btn.getAttribute("data-acct");
          var sel = body.querySelector('select.ve-map-sel[data-acct="' + id + '"]');
          var line = sel && sel.value;
          if (!line) return;
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
      return;
    }
    if (st.panel === "align") {
      body.innerHTML = renderAlignHtml(st.status);
      var allowBtn = body.querySelector("#veAllowBtn");
      if (allowBtn) {
        allowBtn.onclick = function () {
          var who = (body.querySelector("#veAllowBy") || {}).value || "owner";
          allowBtn.disabled = true;
          postAllow(who, "Monthly Align")
            .then(function (next) {
              st.status = next;
              paintValidationPanel(area);
              refreshValidatedStamp();
            })
            .catch(function (err) {
              alert(String(err.message || err));
              allowBtn.disabled = false;
            });
        };
      }
      return;
    }
    body.innerHTML = renderStatusHtml(st.status, closeMonth());
  }

  /** Full Validation Engine inside Board chrome (owner workshop). */
  function renderValidationEngine(area) {
    if (!area) return;
    global.SMPL_VALIDATION_ENGINE = true;
    setOwnerMode(true);
    var st = veState(area);
    area.innerHTML =
      '<div class="slide-title">Validation Engine</div>' +
      '<div class="slide-sub">Owner workshop — ties, mapping, Monthly Align, and Allow. Leadership Board stays outcomes-only.</div>' +
      '<div class="subnav" id="veBoardNav">' +
      '<button type="button" class="snav-btn' +
      (st.panel === "status" ? " on" : "") +
      '" data-panel="status">1 · Close status</button>' +
      '<button type="button" class="snav-btn' +
      (st.panel === "ties" ? " on" : "") +
      '" data-panel="ties">2 · Ties</button>' +
      '<button type="button" class="snav-btn' +
      (st.panel === "mapping" ? " on" : "") +
      '" data-panel="mapping">3 · Mapping</button>' +
      '<button type="button" class="snav-btn' +
      (st.panel === "align" ? " on" : "") +
      '" data-panel="align">4 · Monthly Align</button>' +
      "</div>" +
      '<div id="veBoardBody" style="margin-top:8px"></div>';
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
    postMapAccount: postMapAccount,
    isOwnerMode: isOwnerMode,
    setOwnerMode: setOwnerMode,
    validationHref: validationHref,
    install: install,
  };

  install();
})(typeof window !== "undefined" ? window : globalThis);
