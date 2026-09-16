/**
 * Board Continuity / Trust UX — always-on strip, Continuity tab, cite-to-calc.
 *
 * Productizes SMPLProvenance + CASH_CONTINUITY + export fidelity metadata so
 * customers can prove material numbers without Ctrl+Shift+A or Railway logs.
 * Not SOC 2 certified.
 */
(function (global) {
  "use strict";

  var STRIP_ID = "smpl-trust-strip";
  var DRAWER_ID = "smpl-cite-drawer";
  var FIDELITY_KEY = "smpl_last_evidence_pack";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function closeMonth() {
    if (typeof global.CLOSE_MONTH === "string" && global.CLOSE_MONTH) return global.CLOSE_MONTH;
    var badge = document.getElementById("periodBadge");
    if (badge && badge.textContent) {
      var m = String(badge.textContent).match(/20\d{2}-\d{2}/);
      if (m) return m[0];
    }
    return "2026-06";
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
    refreshTrustStrip();
  }

  function trustSummary() {
    var tie = getTieOut() || {};
    var cc = getCashContinuity() || {};
    var pack = getEvidencePack() || {};
    var failN = (tie.failures && tie.failures.length) || 0;
    var softN = (tie.soft && tie.soft.length) || 0;
    var ccFails = (cc.failures && cc.failures.length) || 0;
    var fidelityIssues =
      (pack.narrative_issues || 0) +
      (pack.post_render_failures || 0) +
      (pack.anchor_failures || 0);
    var passed = failN === 0 && ccFails === 0;
    var status = passed ? (softN || fidelityIssues ? "warn" : "ok") : "fail";
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
    return s.failN + ccPart(s) + " open";
  }

  function ccPart(s) {
    return s.ccFails ? "+" + s.ccFails + " cash" : "";
  }

  function ensureStrip() {
    var el = document.getElementById(STRIP_ID);
    if (el) return el;
    var top = document.querySelector(".topbar-right");
    if (!top) return null;
    el = document.createElement("button");
    el.id = STRIP_ID;
    el.type = "button";
    el.className = "smpl-trust-strip";
    el.setAttribute("aria-label", "Open Continuity trust checks");
    el.onclick = function () {
      openContinuityTab();
    };
    top.insertBefore(el, top.firstChild);
    return el;
  }

  function refreshTrustStrip() {
    var el = ensureStrip();
    if (!el) return;
    var s = trustSummary();
    var clr = statusColor(s.status);
    el.style.borderColor = clr;
    el.style.color = clr;
    el.innerHTML =
      '<span class="smpl-trust-dot" style="background:' +
      clr +
      '"></span>' +
      "<strong>" +
      esc(statusLabel(s)) +
      "</strong>" +
      '<span class="smpl-trust-meta">' +
      esc(s.closeMonth) +
      " · " +
      s.checksRun +
      " checks" +
      (s.freezeStatus ? " · freeze " + esc(s.freezeStatus) : "") +
      " · Continuity</span>";
  }

  function openContinuityTab() {
    var btn = Array.prototype.find.call(document.querySelectorAll(".nav-btn"), function (b) {
      return (b.getAttribute("onclick") || "").indexOf("show('continuity'") >= 0;
    });
    if (typeof global.show === "function") {
      global.show("continuity", btn || null);
    }
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
    var m2 = s.match(/^\[([^\]]+)\]\s+(\d{4}-\d{2})\s+(.+):\s+missing/);
    if (m2) {
      return {
        rule: m2[1],
        period: m2[2],
        metric: m2[3],
        expected: null,
        actual: null,
        diff: null,
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
      return {
        code: c.code,
        label: c.label,
        ok: n === 0,
        count: n,
      };
    });
  }

  function renderContinuity(area) {
    if (!area) return;
    if (global.SMPLProvenance && typeof global.SMPLProvenance.runTieOut === "function") {
      try {
        global.SMPLProvenance.runTieOut();
      } catch (e) {
        /* non-fatal */
      }
    }
    refreshTrustStrip();

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
              ">" +
              "<summary><strong>" +
              esc(f.rule || "FAIL") +
              "</strong> · " +
              esc(f.period || "") +
              " · " +
              esc(f.metric || f.message || "") +
              "</summary>" +
              '<div class="smpl-cont-fail-body">' +
              (f.expected != null
                ? "<div>Expected: <code>" +
                  esc(String(f.expected)) +
                  "</code> · Actual: <code>" +
                  esc(String(f.actual)) +
                  "</code> · Diff: <code>" +
                  esc(String(f.diff)) +
                  "</code> · Tol $1.00</div>"
                : "") +
              "<div class='smpl-cont-msg'>" +
              esc(f.message || "") +
              "</div>" +
              "</div></details>"
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

    var fidelityHtml =
      '<div class="smpl-cont-grid">' +
      row("Last export", pack.export_kind || "—") +
      row("Freeze", pack.freeze_status || s.freezeStatus || "—") +
      row("PPTX source", pack.pptx_source || "—") +
      row("Post-render cells", pack.post_render_ok === false ? "soft-warn" : pack.post_render_ok ? "pass" : "—") +
      row("Anchor coverage", pack.anchor_failures != null ? String(pack.anchor_failures) + " miss" : "—") +
      row("Narrative issues", pack.narrative_issues != null ? String(pack.narrative_issues) : "—") +
      row("Summary", pack.summary || "No export Evidence Pack yet — run MD&A Deck or Variance Commentary.") +
      "</div>";

    area.innerHTML =
      '<div class="slide-title">Continuity</div>' +
      '<div class="slide-sub">Named ties at $1 on closed actuals · material KPIs cite warehouse / computed sources · AI narrates from the evidence pack — it does not invent the dollars. Not SOC 2 certified.</div>' +
      '<div class="smpl-cont-banner" style="border-color:' +
      statusColor(s.status) +
      '">' +
      '<div style="font-size:13px;font-weight:600;color:' +
      statusColor(s.status) +
      '">' +
      esc(statusLabel(s)) +
      " · " +
      esc(s.closeMonth) +
      "</div>" +
      '<div style="font-size:11px;color:var(--text3);margin-top:4px">' +
      s.checksRun +
      " client checks · " +
      s.failN +
      " fail · " +
      s.softN +
      " soft · " +
      s.ccFails +
      " cash continuity · click any KPI with a source tag to open cite-to-calc</div>" +
      "</div>" +
      '<div class="card" style="margin-top:18px">' +
      '<div class="card-title">Stamps</div>' +
      '<div class="smpl-cont-grid">' +
      row("As-of period", s.closeMonth) +
      row("Live hydrate", tie.live ? "yes" : "demo / offline") +
      row("Scope", tie.scope || "client-A-F") +
      row("Org sources", global.SMPL_OUTLOOK_SOURCES ? Object.keys(global.SMPL_OUTLOOK_SOURCES).length + " keys" : "catalog fallback") +
      row("Tolerance", "TOL_ACTUALS = $1.00") +
      "</div></div>" +
      '<div class="card" style="margin-top:14px">' +
      '<div class="card-title">Cash spine (C1–C5)</div>' +
      '<div class="smpl-cont-chips">' +
      chipHtml +
      "</div>" +
      (cc.summary
        ? '<div style="font-size:11px;color:var(--text3);margin-top:8px">' + esc(cc.summary) + "</div>"
        : "") +
      "</div>" +
      '<div class="card" style="margin-top:14px">' +
      '<div class="card-title">Failures first (client A–F)</div>' +
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
        ? '<div style="margin-top:10px;font-size:10px;color:var(--text3)">Skipped when data absent: ' +
          esc(skipped.slice(0, 6).join(" · ")) +
          "</div>"
        : "") +
      "</div>" +
      '<div class="card" style="margin-top:14px">' +
      '<div class="card-title">AI fidelity (last Evidence Pack)</div>' +
      fidelityHtml +
      '<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">' +
      '<button type="button" class="ai-global-btn" onclick="if(window.SMPLProvenance)SMPLProvenance.downloadTieOutReport()">Download client tie-out HTML</button>' +
      (pack.html
        ? '<button type="button" class="ai-global-btn" onclick="window.SMPLContinuity.downloadStoredEvidenceHtml()">Download Evidence Pack HTML</button>'
        : "") +
      "</div></div>" +
      '<div class="card" style="margin-top:14px">' +
      '<div class="card-title">How to prove a number</div>' +
      '<ol style="margin:8px 0 0 18px;font-size:12px;color:var(--text2);line-height:1.55">' +
      "<li>Click a KPI value (ending ARR, revenue, cash, EBITDA, net new) — cite-to-calc opens.</li>" +
      "<li>Confirm period, scenario, and warehouse table.column or COMPUTED formula.</li>" +
      "<li>Export MD&A Deck / Variance Commentary — Evidence Pack travels with the file (same check IDs).</li>" +
      "</ol></div>";
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
    el.addEventListener("click", function (ev) {
      if (ev.target === el) closeCiteDrawer();
    });
    return el;
  }

  function closeCiteDrawer() {
    var el = document.getElementById(DRAWER_ID);
    if (!el) return;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
  }

  function openCiteDrawer(detail) {
    ensureDrawer();
    var body = document.getElementById("smpl-cite-body");
    var el = document.getElementById(DRAWER_ID);
    if (!body || !el) return;
    var rec = detail.record || {};
    var value = detail.displayValue || rec.value || "—";
    body.innerHTML =
      '<div class="smpl-cite-value">' +
      esc(value) +
      "</div>" +
      '<div class="smpl-cont-grid">' +
      row("Metric", detail.metric || rec.field || "—") +
      row("Period", detail.period || rec.period || closeMonth()) +
      row("Scenario", detail.scenario || rec.series_kind || "Actual (closed ≤ as-of)") +
      row("Source type", rec.source_type || "—") +
      row("Table.column", rec.table && rec.column ? rec.table + "." + rec.column : rec.path || "—") +
      row("Formula", rec.formula || rec.formula_id || "—") +
      row("Org", rec.org_id || "—") +
      row("Loaded at", rec.loaded_at || "—") +
      row("Final", rec.is_final == null ? "—" : String(rec.is_final)) +
      row("Tag", detail.sourceTag || "—") +
      "</div>" +
      '<p class="smpl-cite-note">Closed-period material KPIs are engine-computed and tagged to _sources. AI narrates from this package — it does not invent the dollars. Chart datapoints and import hard-ID are Phase 4.</p>';
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
    var t = ev.target;
    if (!t || !t.closest) return;
    var val = t.closest("[data-source], [data-metric].kpi-val, .kpi-val[data-metric]");
    if (!val) {
      var kpi = t.closest(".kpi");
      if (kpi) val = kpi.querySelector(".kpi-val[data-source], .kpi-val[data-metric]");
    }
    if (!val) return;
    // Ignore plain clicks on buttons / links inside KPIs
    if (t.closest("button, a, .nav-btn")) return;
    var metric = val.getAttribute("data-metric");
    if (!metric) return;
    ev.preventDefault();
    ev.stopPropagation();
    var period = val.getAttribute("data-period") || closeMonth();
    var rec = resolveRecord(metric, period);
    openCiteDrawer({
      metric: metric,
      period: period,
      displayValue: (val.textContent || "").trim(),
      sourceTag: val.getAttribute("data-source") || "",
      record: rec,
      scenario: rec.series_kind || "Actual",
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

  function install() {
    if (typeof document === "undefined") return;
    function boot() {
      ensureStrip();
      ensureDrawer();
      refreshTrustStrip();
      document.addEventListener("click", onCiteClick, true);
      // Refresh strip after hydrate / tie-out
      var obs = new MutationObserver(function () {
        refreshTrustStrip();
      });
      var badge = document.getElementById("warehouseStatus");
      if (badge) obs.observe(badge, { childList: true, characterData: true, subtree: true });
      setInterval(refreshTrustStrip, 15000);
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", boot);
    } else {
      boot();
    }
  }

  global.SMPLContinuity = {
    renderContinuity: renderContinuity,
    refreshTrustStrip: refreshTrustStrip,
    openContinuityTab: openContinuityTab,
    openCiteDrawer: openCiteDrawer,
    closeCiteDrawer: closeCiteDrawer,
    saveEvidencePack: saveEvidencePack,
    getEvidencePack: getEvidencePack,
    downloadStoredEvidenceHtml: downloadStoredEvidenceHtml,
    trustSummary: trustSummary,
    install: install,
  };

  install();
})(typeof window !== "undefined" ? window : globalThis);
