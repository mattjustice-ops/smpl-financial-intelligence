/**
 * DOM data-source provenance + client tie-out gate (P15 / framework Part 3–4).
 * Prefers hydrate payload `_sources` when present; falls back to field catalog.
 * Demo path stays usable — tags still apply from catalog; publish gate only hard-blocks
 * on live hydrate FAIL (customer export / final forecast promote).
 *
 * Not SOC 2 certified. Rule Sets A–F are only partially implemented (see docs).
 */
(function (global) {
  "use strict";

  var TOL_ACTUALS = 1.0;

  /** Leaf field → WAREHOUSE / COMPUTED tag (mirrors claim_verify._SOURCE_FIELD_CATALOG). */
  var FIELD_CATALOG = {
    revenue: { source_type: "WAREHOUSE", table: "income_statement", column: "revenue" },
    cogs: { source_type: "WAREHOUSE", table: "income_statement", column: "cogs" },
    gross_profit: { source_type: "WAREHOUSE", table: "income_statement", column: "gross_profit" },
    sm: { source_type: "WAREHOUSE", table: "income_statement", column: "sm" },
    rd: { source_type: "WAREHOUSE", table: "income_statement", column: "rd" },
    ga: { source_type: "WAREHOUSE", table: "income_statement", column: "ga" },
    ebitda: { source_type: "WAREHOUSE", table: "income_statement", column: "ebitda" },
    net_income: { source_type: "WAREHOUSE", table: "income_statement", column: "net_income" },
    total_opex: {
      source_type: "COMPUTED",
      formula_id: "total_opex_sm_rd_ga",
      formula: "sm + rd + ga",
    },
    gm_pct: {
      source_type: "COMPUTED",
      formula_id: "gross_profit_div_revenue",
      formula: "gross_profit / revenue",
    },
    gross_margin_pct: {
      source_type: "COMPUTED",
      formula_id: "gross_profit_div_revenue",
      formula: "gross_profit / revenue",
    },
    cash: { source_type: "WAREHOUSE", table: "balance_sheet", column: "cash" },
    ar: { source_type: "WAREHOUSE", table: "balance_sheet", column: "ar" },
    deferred_rev: { source_type: "WAREHOUSE", table: "balance_sheet", column: "deferred_rev" },
    ending_cash: { source_type: "WAREHOUSE", table: "cash_flow_statement", column: "ending_cash" },
    beginning_cash: { source_type: "WAREHOUSE", table: "cash_flow_statement", column: "beginning_cash" },
    cfo: { source_type: "WAREHOUSE", table: "cash_flow_statement", column: "cfo" },
    ending_arr: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "ending_arr" },
    beginning_arr: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "beginning_arr" },
    expansion: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "expansion" },
    new_business: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "new_business" },
    churn: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "churn" },
    contraction: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "contraction" },
    reactivation: { source_type: "WAREHOUSE", table: "arr_waterfall", column: "reactivation" },
    net_new: {
      source_type: "COMPUTED",
      formula_id: "arr_net_new",
      formula: "new_business + expansion + reactivation + contraction + churn",
    },
    net_new_arr: {
      source_type: "COMPUTED",
      formula_id: "arr_net_new",
      formula: "new_business + expansion + reactivation + contraction + churn",
    },
    nrr: {
      source_type: "COMPUTED",
      formula_id: "nrr_arr_bridge",
      formula: "(beginning_arr + expansion + reactivation - contraction - churn) / beginning_arr",
    },
    grr: {
      source_type: "COMPUTED",
      formula_id: "grr_arr_bridge",
      formula: "(beginning_arr - contraction - churn) / beginning_arr",
    },
  };

  /** Visible KPI label → metric leaf (board + forecast strips). */
  var LABEL_TO_METRIC = {
    "ending arr": "ending_arr",
    "arr (ending)": "ending_arr",
    "net new arr": "net_new_arr",
    "new business": "new_business",
    "expansion arr": "expansion",
    "beginning arr": "beginning_arr",
    "jun revenue": "revenue",
    revenue: "revenue",
    "ytd revenue": "revenue",
    "forecast revenue": "revenue",
    "gross margin": "gross_margin_pct",
    "gross profit": "gross_profit",
    nrr: "nrr",
    "g$r / n$r": "nrr",
    ebitda: "ebitda",
    "forecast ebitda": "ebitda",
    "cash balance": "cash",
    cash: "cash",
    "ending cash": "ending_cash",
    "dec cash": "ending_cash",
    "dec arr": "ending_arr",
    "total opex": "total_opex",
  };

  /** TS_DATA.Actual ↔ SRC.actuals fields (Rule C / production single-source). */
  var TS_SRC_FIELDS = [
    ["revenue", "is", "revenue"],
    ["cogs", "is", "cogs"],
    ["gross_profit", "is", "gross_profit"],
    ["sm", "is", "sm"],
    ["rd", "is", "rd"],
    ["ga", "is", "ga"],
    ["ebitda", "is", "ebitda"],
    ["net_income", "is", "net_income"],
    ["cash", "bs", "cash"],
    ["ar", "bs", "ar"],
    ["deferred_rev", "bs", "deferred_rev"],
    ["beginning_cash", "cfs", "beginning_cash"],
    ["ending_cash", "cfs", "ending_cash"],
    ["cfo", "cfs", "cfo"],
  ];

  var _payloadSources = null;
  var _lastTieOut = null;
  var _auditBound = false;

  function closeMonth() {
    return (
      global.SMPL_CLOSE_MONTH ||
      global.CLOSE_MONTH ||
      (global.SMPL_OUTLOOK_PAYLOAD &&
        global.SMPL_OUTLOOK_PAYLOAD.meta &&
        global.SMPL_OUTLOOK_PAYLOAD.meta.close_month) ||
      null
    );
  }

  function isLive() {
    return Boolean(global.SMPL_LIVE_OUTLOOK);
  }

  function formatSourceTag(record, key) {
    if (!record) return key || "";
    if (record.source_type === "COMPUTED") {
      return "COMPUTED:" + (record.formula_id || record.formula || key || "derived");
    }
    if (record.source_type === "WAREHOUSE" && record.table && record.column) {
      return record.table + "." + record.column;
    }
    if (record.path) return String(record.path);
    if (record.source_type === "ENGINE_PATH") return "ENGINE_PATH:" + (record.path || key || "");
    return key || "";
  }

  function resolveRecord(metricKey, period) {
    var key = String(metricKey || "").trim();
    if (!key) return null;
    var periodKey = period || closeMonth();

    if (_payloadSources && typeof _payloadSources === "object") {
      if (_payloadSources[key]) return _payloadSources[key];
      var dotted = Object.keys(_payloadSources).find(function (k) {
        return k === key || k.endsWith("." + key) || k.indexOf("." + key + ".") !== -1;
      });
      if (dotted) return _payloadSources[dotted];
      if (periodKey) {
        var withPeriod = Object.keys(_payloadSources).find(function (k) {
          return k.indexOf(periodKey) !== -1 && k.endsWith("." + key);
        });
        if (withPeriod) return _payloadSources[withPeriod];
      }
    }

    var cat = FIELD_CATALOG[key];
    if (cat) {
      var rec = Object.assign({}, cat);
      rec.path = key;
      if (periodKey) rec.period = periodKey;
      return rec;
    }
    return {
      source_type: "ENGINE_PATH",
      path: key,
      field: key,
      period: periodKey || undefined,
      note: "No catalog hit — ENGINE_PATH fallback",
    };
  }

  function attrString(metricKey, period) {
    var rec = resolveRecord(metricKey, period);
    if (!rec) return "";
    var src = formatSourceTag(rec, metricKey);
    var p = rec.period || period || closeMonth() || "";
    var title = src + (p ? " · " + p : "");
    var parts = [
      'data-source="' + escapeAttr(src) + '"',
      'data-metric="' + escapeAttr(metricKey) + '"',
      'title="' + escapeAttr(title) + '"',
      'aria-label="' + escapeAttr(title) + '"',
    ];
    if (p) parts.push('data-period="' + escapeAttr(p) + '"');
    if (rec.source_type === "COMPUTED" && rec.formula) {
      parts.push('data-inputs="' + escapeAttr(rec.formula) + '"');
    }
    return parts.join(" ");
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  /**
   * Ingest hydrate / evidence `_sources`. Accepts:
   * - payload._sources
   * - payload.meta._sources
   * - payload.evidence_package._sources
   */
  function ingestOutlook(payload) {
    _payloadSources = null;
    if (!payload || typeof payload !== "object") return;
    var sources =
      payload._sources ||
      (payload.meta && payload.meta._sources) ||
      (payload.evidence_package && payload.evidence_package._sources) ||
      null;
    if (sources && typeof sources === "object") {
      _payloadSources = sources;
      global.SMPL_OUTLOOK_SOURCES = sources;
    }
    if (typeof document !== "undefined") {
      try {
        annotateDom(document);
      } catch (err) {
        console.warn("[smpl-provenance] annotate after ingest failed", err);
      }
    }
  }

  function normalizeLabel(lbl) {
    return String(lbl || "")
      .replace(/\s+/g, " ")
      .replace(/\(.*?\)/g, "")
      .trim()
      .toLowerCase();
  }

  function metricFromLabel(lbl) {
    var n = normalizeLabel(lbl);
    if (LABEL_TO_METRIC[n]) return LABEL_TO_METRIC[n];
    // Strip leading month tokens e.g. "Jun Revenue"
    var stripped = n.replace(/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+/, "");
    if (LABEL_TO_METRIC[stripped]) return LABEL_TO_METRIC[stripped];
    return null;
  }

  function applyAttrsToEl(el, metricKey, period) {
    if (!el || !metricKey) return;
    var rec = resolveRecord(metricKey, period);
    if (!rec) return;
    var src = formatSourceTag(rec, metricKey);
    var p = rec.period || period || closeMonth() || "";
    var title = src + (p ? " · " + p : "");
    el.setAttribute("data-source", src);
    el.setAttribute("data-metric", metricKey);
    if (p) el.setAttribute("data-period", p);
    el.setAttribute("title", title);
    if (!el.getAttribute("aria-label")) el.setAttribute("aria-label", title);
    if (rec.source_type === "COMPUTED" && rec.formula) {
      el.setAttribute("data-inputs", rec.formula);
    }
  }

  /** Tag .kpi-val / [data-metric] under root from labels or existing data-metric. */
  function annotateDom(root) {
    root = root || (typeof document !== "undefined" ? document : null);
    if (!root || !root.querySelectorAll) return 0;
    var period = closeMonth();
    var count = 0;

    root.querySelectorAll("[data-metric]").forEach(function (el) {
      var key = el.getAttribute("data-metric");
      if (!key) return;
      applyAttrsToEl(el, key, el.getAttribute("data-period") || period);
      count++;
    });

    root.querySelectorAll(".kpi").forEach(function (kpi) {
      var lbl = kpi.querySelector(".kpi-lbl");
      var val = kpi.querySelector(".kpi-val");
      if (!lbl || !val) return;
      if (val.getAttribute("data-source")) return;
      var metric = metricFromLabel(lbl.textContent);
      if (!metric) return;
      applyAttrsToEl(val, metric, period);
      count++;
    });

    return count;
  }

  function num(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function chk(rule, period, metric, expected, actual, fails, tol) {
    if (actual == null && expected == null) return;
    if (actual == null || expected == null) {
      fails.push("[" + rule + "] " + period + " " + metric + ": missing");
      return;
    }
    var diff = Math.abs(expected - actual);
    if (diff > tol) {
      fails.push(
        "[" +
          rule +
          "] " +
          period +
          " " +
          metric +
          ": expected=" +
          expected.toFixed(0) +
          " actual=" +
          actual.toFixed(0) +
          " diff=" +
          diff.toFixed(0),
      );
    }
  }

  /**
   * Client tie-out — Rule C (TS↔SRC actuals) + ARR identities when SRC has arr_*.
   * Full Rule Sets A–F are NOT claimed live; see docs limitation.
   */
  function runTieOut(srcActuals, tsData, engineResults, closeMo) {
    var fails = [];
    var tol = TOL_ACTUALS;
    closeMo = closeMo || closeMonth();

    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    if (!srcActuals && payload && payload.SRC) srcActuals = payload.SRC.actuals || payload.SRC;
    if (!tsData && payload) tsData = payload.TS_DATA;
    if (!tsData && global.TS_DATA) tsData = global.TS_DATA;
    if (!srcActuals && global.SRC && global.SRC.actuals) srcActuals = global.SRC.actuals;

    // Normalize: SRC may be { actuals: {...} } or flat period map
    if (srcActuals && srcActuals.actuals && typeof srcActuals.actuals === "object") {
      srcActuals = srcActuals.actuals;
    }

    var actual = (tsData && tsData.Actual) || {};
    var periods = {};
    if (srcActuals && typeof srcActuals === "object") {
      Object.keys(srcActuals).forEach(function (p) {
        periods[p] = true;
      });
    }
    ["is", "bs", "cfs"].forEach(function (stmt) {
      var block = actual[stmt];
      if (!block) return;
      Object.keys(block).forEach(function (p) {
        periods[p] = true;
      });
    });

    var periodList = Object.keys(periods)
      .filter(function (p) {
        return !closeMo || p <= closeMo;
      })
      .sort();

    if (!periodList.length) {
      // No comparable actuals — pass with note (demo offline / empty warehouse)
      _lastTieOut = {
        passed: true,
        failures: [],
        warnings: ["tie-out skipped: no overlapping Actual periods"],
        scope: "partial-C",
        live: isLive(),
      };
      return _lastTieOut;
    }

    periodList.forEach(function (p) {
      var srcRow = (srcActuals && srcActuals[p]) || {};
      TS_SRC_FIELDS.forEach(function (triple) {
        var field = triple[0];
        var stmt = triple[1];
        var srcKey = triple[2];
        var tsRow = ((actual[stmt] || {})[p]) || {};
        var tsVal = num(tsRow[field]);
        var srcVal = num(srcRow[srcKey]);
        if (srcVal == null && srcKey === "deferred_rev") srcVal = num(srcRow.dr);
        if (tsVal == null && srcVal == null) return;
        chk("C", p, field, srcVal, tsVal, fails, tol);
      });

      // ARR identities when SRC carries arr_* (Rule A2/A3 subset)
      var nb = num(srcRow.arr_nb);
      var exp = num(srcRow.arr_exp);
      var react = num(srcRow.arr_react);
      var cont = num(srcRow.arr_cont);
      var churn = num(srcRow.arr_churn != null ? srcRow.arr_churn : srcRow.arr_nr_churn);
      var nn = num(srcRow.arr_nn);
      var bop = num(srcRow.arr_bop);
      var eop = num(srcRow.arr_eop);
      if (nn != null && nb != null && exp != null) {
        var comp =
          (nb || 0) +
          (exp || 0) +
          (react || 0) +
          (cont || 0) +
          (churn || 0);
        chk("A2", p, "arr net_new components", comp, nn, fails, tol);
      }
      if (eop != null && bop != null && nn != null) {
        chk("A3", p, "arr ending=bop+nn", bop + nn, eop, fails, tol);
      }
    });

    // Soft: engineResults / forecast Rule F not required for v1 gate
    void engineResults;

    var passed = fails.length === 0;
    if (passed) console.info("[smpl-provenance] ✓ TIE-OUT PASSED (partial Rule C/A)");
    else {
      console.error("[smpl-provenance] ✗ TIE-OUT FAILED (" + fails.length + " issues)");
      fails.forEach(function (f) {
        console.error(" " + f);
      });
    }

    _lastTieOut = {
      passed: passed,
      failures: fails,
      warnings: [
        "Partial client gate only (Rule C TS↔SRC + ARR A2/A3 when present). Full Rule Sets A–F not live.",
      ],
      scope: "partial-C-A",
      live: isLive(),
      closeMonth: closeMo,
    };
    global.SMPL_LAST_TIEOUT = _lastTieOut;
    return _lastTieOut;
  }

  /**
   * Customer publish gate. Returns { ok, blocked, result, message }.
   * - Live + FAIL → block (ok=false, blocked=true)
   * - Demo / no live → warn only (ok=true, blocked=false) unless forceBlock
   */
  function gatePublish(options) {
    options = options || {};
    var result = runTieOut(options.srcActuals, options.tsData, options.engineResults, options.closeMonth);
    var live = options.forceLive != null ? options.forceLive : isLive();
    var forceBlock = Boolean(options.forceBlock);
    var blocked = (!result.passed && live) || (!result.passed && forceBlock);
    var message = "";
    if (!result.passed) {
      message =
        "Tie-out FAILED (" +
        result.failures.length +
        " issue" +
        (result.failures.length === 1 ? "" : "s") +
        ").\n\n" +
        result.failures.slice(0, 12).join("\n") +
        (result.failures.length > 12 ? "\n…" : "") +
        "\n\nClosed-actuals bar: $" +
        TOL_ACTUALS.toFixed(2) +
        ". Partial Rule C/A only — not full A–F.";
      if (blocked) {
        message += "\n\nCustomer publish/export blocked until resolved.";
      } else {
        message += "\n\nDemo/offline path: warning only (not hard-blocked).";
      }
    }
    return { ok: !blocked, blocked: blocked, result: result, message: message };
  }

  function clearAuditTags() {
    if (typeof document === "undefined") return;
    document.querySelectorAll(".smpl-audit-tag").forEach(function (t) {
      t.remove();
    });
    document.body.classList.remove("audit-mode");
  }

  function toggleAuditOverlay() {
    if (typeof document === "undefined") return false;
    annotateDom(document);
    var active = document.body.classList.toggle("audit-mode");
    if (active) {
      document.querySelectorAll("[data-source]").forEach(function (el) {
        if (el.nextSibling && el.nextSibling.classList && el.nextSibling.classList.contains("smpl-audit-tag")) {
          return;
        }
        var tag = document.createElement("span");
        tag.className = "smpl-audit-tag";
        var period = el.getAttribute("data-period") || "";
        tag.textContent = "[" + el.getAttribute("data-source") + (period ? " · " + period : "") + "]";
        tag.style.cssText =
          "font-size:8px;color:#BA7517;margin-left:4px;font-family:ui-monospace,monospace;white-space:nowrap;";
        if (el.parentNode) el.parentNode.insertBefore(tag, el.nextSibling);
      });
    } else {
      clearAuditTags();
    }
    return active;
  }

  function bindAuditHotkey() {
    if (_auditBound || typeof document === "undefined") return;
    _auditBound = true;
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "A" || e.key === "a")) {
        e.preventDefault();
        toggleAuditOverlay();
      }
    });
  }

  function install() {
    bindAuditHotkey();
    if (typeof document !== "undefined") {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
          annotateDom(document);
        });
      } else {
        annotateDom(document);
      }
    }
  }

  global.SMPLProvenance = {
    TOL_ACTUALS: TOL_ACTUALS,
    FIELD_CATALOG: FIELD_CATALOG,
    ingestOutlook: ingestOutlook,
    resolveRecord: resolveRecord,
    formatSourceTag: formatSourceTag,
    attrString: attrString,
    annotateDom: annotateDom,
    applyAttrsToEl: applyAttrsToEl,
    runTieOut: runTieOut,
    gatePublish: gatePublish,
    toggleAuditOverlay: toggleAuditOverlay,
    clearAuditTags: clearAuditTags,
    install: install,
    getLastTieOut: function () {
      return _lastTieOut;
    },
    getPayloadSources: function () {
      return _payloadSources;
    },
  };

  // Global alias matching framework Part 4 naming
  global.runTieOut = runTieOut;

  install();
})(typeof window !== "undefined" ? window : globalThis);
