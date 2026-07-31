/**
 * DOM data-source provenance + client tie-out gate (P15 / framework Part 3–4).
 * Prefers hydrate payload `_sources` when present; falls back to field catalog.
 * Demo path stays usable — tags still apply from catalog; publish gate only hard-blocks
 * on live hydrate FAIL (customer export / final forecast promote).
 *
 * Client Rule Sets A–F run when local Board/FE data exists (SRC, TS_DATA, WF_TABLE,
 * baseline_engine, display arrays). Skips D/E (and bank B2) when structures absent.
 * HTML report is client-side from those checks — not live warehouse SQL.
 * Not SOC 2 certified.
 */
(function (global) {
  "use strict";

  var TOL_ACTUALS = 1.0;
  var TOL_EXACT = 0;
  var TOL_DISPLAY_M = 0.001; // million-scale UI display_precision (~$1K)
  var TOL_BANK_SOFT = 1000; // bank timing soft — not statement rounding

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
  var _lastTieOutHtml = null;
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

  function periodMonthIndex(period) {
    if (!period || String(period).length < 7) return -1;
    return parseInt(String(period).slice(5, 7), 10) - 1;
  }

  function resolveWfTable() {
    return (
      global.SMPL_ARR_WATERFALL ||
      global.SMPL_DEMO_WF_TABLE ||
      (global.SMPLOutlook &&
        typeof global.SMPLOutlook.getArrWaterfall === "function" &&
        global.SMPLOutlook.getArrWaterfall()) ||
      null
    );
  }

  function resolveEngineResults(engineResults, tsData, closeMo) {
    if (engineResults && typeof engineResults === "object") return engineResults;
    if (global.SMPL_BASELINE_ENGINE && typeof global.SMPL_BASELINE_ENGINE === "object") {
      return global.SMPL_BASELINE_ENGINE;
    }
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    if (payload && payload.baseline_engine) return payload.baseline_engine;
    if (typeof global.getResults === "function") {
      try {
        return global.getResults();
      } catch (err) {
        /* ignore */
      }
    }
    if (typeof global.compute === "function") {
      try {
        return global.compute();
      } catch (err2) {
        /* ignore */
      }
    }
    void tsData;
    void closeMo;
    return null;
  }

  /** A2: accept signed (neg cont/churn) or magnitude (positive cont/churn) conventions. */
  function arrNetNewFromComponents(nb, exp, react, cont, churn) {
    var signed =
      (nb || 0) + (exp || 0) + (react || 0) + (cont || 0) + (churn || 0);
    var mag =
      (nb || 0) +
      (exp || 0) +
      (react || 0) -
      Math.abs(cont || 0) -
      Math.abs(churn || 0);
    return { signed: signed, mag: mag };
  }

  function arrComponentsMatchNn(nb, exp, react, cont, churn, nn, tol) {
    if (nn == null || nb == null || exp == null) return null;
    var parts = arrNetNewFromComponents(nb, exp, react, cont, churn);
    if (Math.abs(parts.signed - nn) <= tol) return parts.signed;
    if (Math.abs(parts.mag - nn) <= tol) return parts.mag;
    return parts.signed; // prefer signed for failure message (framework A2)
  }

  function softChk(rule, period, metric, expected, actual, softs, tol) {
    if (actual == null || expected == null) return;
    var diff = Math.abs(expected - actual);
    if (diff > tol) {
      softs.push(
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
          diff.toFixed(0) +
          " (soft)",
      );
    }
  }

  /**
   * Client Rule Sets A–F when local Board/FE structures exist.
   * Hard fails use TOL_ACTUALS=$1. Soft bank/display go to warnings.
   * D/E skipped when headcount/sales structures absent (honest skip notes).
   */
  function runTieOut(srcActuals, tsData, engineResults, closeMo) {
    var fails = [];
    var softs = [];
    var skipped = [];
    var checksRun = [];
    var tol = TOL_ACTUALS;
    closeMo = closeMo || closeMonth();

    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    if (!srcActuals && payload && payload.SRC) srcActuals = payload.SRC.actuals || payload.SRC;
    if (!tsData && payload) tsData = payload.TS_DATA;
    if (!tsData && global.TS_DATA) tsData = global.TS_DATA;
    if (!srcActuals && global.SRC && global.SRC.actuals) srcActuals = global.SRC.actuals;

    if (srcActuals && srcActuals.actuals && typeof srcActuals.actuals === "object") {
      srcActuals = srcActuals.actuals;
    }

    var actual = (tsData && tsData.Actual) || {};
    var forecast = (tsData && tsData.Forecast) || {};
    var engine = resolveEngineResults(engineResults, tsData, closeMo);
    var wf = resolveWfTable();

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

    var fcPeriods = [];
    if (forecast.is && typeof forecast.is === "object") {
      fcPeriods = Object.keys(forecast.is).sort();
    } else if (forecast.periods && forecast.periods.length) {
      fcPeriods = forecast.periods.slice().sort();
    }

    // ── Rule A: ARR ────────────────────────────────────────────────────
    if (wf && Array.isArray(wf.Ending) && Array.isArray(wf.Beginning)) {
      checksRun.push("A1");
      for (var i = 0; i < wf.Ending.length - 1; i++) {
        var endN = num(wf.Ending[i]);
        var begNext = num(wf.Beginning[i + 1]);
        if (endN == null || begNext == null) continue;
        chk("A1", "idx" + i + "→" + (i + 1), "arr chain ending=next beginning", endN, begNext, fails, TOL_EXACT);
      }
    } else {
      skipped.push("A1: no WF_TABLE / ARR_WATERFALL");
    }

    periodList.forEach(function (p) {
      var srcRow = (srcActuals && srcActuals[p]) || {};
      var nb = num(srcRow.arr_nb);
      var exp = num(srcRow.arr_exp);
      var react = num(srcRow.arr_react);
      var cont = num(srcRow.arr_cont);
      var churn = num(srcRow.arr_churn != null ? srcRow.arr_churn : srcRow.arr_nr_churn);
      var nn = num(srcRow.arr_nn);
      var bop = num(srcRow.arr_bop);
      var eop = num(srcRow.arr_eop);

      if (nn != null && nb != null && exp != null) {
        checksRun.push("A2");
        var matched = arrComponentsMatchNn(nb, exp, react, cont, churn, nn, tol);
        chk("A2", p, "arr net_new components", matched, nn, fails, tol);
      }

      if (eop != null && bop != null && nn != null) {
        checksRun.push("A3");
        chk("A3", p, "arr ending=bop+nn", bop + nn, eop, fails, tol);
      }

      // A4/A5: WF_TABLE ↔ SRC arr_* for close-year months
      if (wf && Array.isArray(wf.Ending)) {
        var mi = periodMonthIndex(p);
        if (mi >= 0 && mi < wf.Ending.length) {
          var wfEnd = num(wf.Ending[mi]);
          var wfBeg = num(wf.Beginning && wf.Beginning[mi]);
          if (eop != null && wfEnd != null) {
            checksRun.push("A4");
            chk("A4", p, "WF Ending ↔ SRC arr_eop", wfEnd, eop, fails, tol);
          }
          if (bop != null && wfBeg != null) {
            checksRun.push("A4");
            chk("A4", p, "WF Beginning ↔ SRC arr_bop", wfBeg, bop, fails, tol);
          }
          if (nn != null && wf.Ending && wf.Beginning) {
            var wfNn =
              (num(wf["New Business"] && wf["New Business"][mi]) || 0) +
              (num(wf.Expansion && wf.Expansion[mi]) || 0) +
              (num(wf.Reactivation && wf.Reactivation[mi]) || 0) +
              (num(wf.Contraction && wf.Contraction[mi]) || 0) +
              (num(wf.Churn && wf.Churn[mi]) || 0);
            checksRun.push("A5");
            chk("A5", p, "WF component nn ↔ SRC arr_nn", wfNn, nn, fails, tol);
            if (wfEnd != null) {
              chk("A5", p, "SRC arr_eop ↔ WF Ending", eop, wfEnd, fails, tol);
            }
          }
        }
      }
    });

    // A2/A3 from WF alone when SRC lacks arr_*
    if (wf && Array.isArray(wf.Ending)) {
      var yearPrefix = closeMo ? String(closeMo).slice(0, 4) : null;
      for (var wi = 0; wi < wf.Ending.length; wi++) {
        var wNb = num(wf["New Business"] && wf["New Business"][wi]);
        var wExp = num(wf.Expansion && wf.Expansion[wi]);
        var wReact = num(wf.Reactivation && wf.Reactivation[wi]);
        var wCont = num(wf.Contraction && wf.Contraction[wi]);
        var wChurn = num(wf.Churn && wf.Churn[wi]);
        var wBeg = num(wf.Beginning && wf.Beginning[wi]);
        var wEnd = num(wf.Ending[wi]);
        if (wNb == null || wExp == null || wEnd == null || wBeg == null) continue;
        var wNn =
          (wNb || 0) + (wExp || 0) + (wReact || 0) + (wCont || 0) + (wChurn || 0);
        var label =
          (yearPrefix || "yr") + "-" + String(wi + 1).padStart(2, "0");
        if (closeMo && label > closeMo) continue;
        checksRun.push("A2-wf");
        chk("A2", label, "WF arr net_new components", wNn, wEnd - wBeg, fails, tol);
        checksRun.push("A3-wf");
        chk("A3", label, "WF ending=bop+nn", wBeg + wNn, wEnd, fails, tol);
      }
    }

    if (fcPeriods.length && closeMo) {
      var actEndArr =
        (srcActuals && srcActuals[closeMo] && num(srcActuals[closeMo].arr_eop)) ||
        (wf &&
          Array.isArray(wf.Ending) &&
          num(wf.Ending[periodMonthIndex(closeMo)]));
      var firstFC = fcPeriods[0];
      var engBop =
        engine &&
        engine[firstFC] &&
        engine[firstFC].arr &&
        num(engine[firstFC].arr.arr_bop);
      if (actEndArr != null && engBop != null) {
        checksRun.push("A6");
        chk("A6", firstFC, "forecast arr_bop == actual arr_eop", actEndArr, engBop, fails, tol);
      } else if (actEndArr != null && engBop == null) {
        skipped.push("A6: no engineResults/baseline_engine arr_bop for " + firstFC);
      }
    }

    // ── Rule B: Cash ───────────────────────────────────────────────────
    var cashPeriods = periodList.slice();
    if (actual.cfs) {
      Object.keys(actual.cfs).forEach(function (p) {
        if (!closeMo || p <= closeMo) cashPeriods.push(p);
      });
    }
    cashPeriods = cashPeriods
      .filter(function (p, idx, arr) {
        return arr.indexOf(p) === idx;
      })
      .sort();

    for (var ci = 0; ci < cashPeriods.length - 1; ci++) {
      var pN = cashPeriods[ci];
      var pN1 = cashPeriods[ci + 1];
      var endCash =
        num((actual.cfs && actual.cfs[pN] && actual.cfs[pN].ending_cash)) ||
        num(srcActuals && srcActuals[pN] && srcActuals[pN].ending_cash);
      var begNextCash =
        num((actual.cfs && actual.cfs[pN1] && actual.cfs[pN1].beginning_cash)) ||
        num(srcActuals && srcActuals[pN1] && srcActuals[pN1].beginning_cash);
      if (endCash == null || begNextCash == null) continue;
      checksRun.push("B1");
      chk("B1", pN + "→" + pN1, "cash chain ending=next beginning", endCash, begNextCash, fails, tol);
    }
    if (!checksRun.some(function (x) { return x === "B1"; })) {
      skipped.push("B1: insufficient CFS/SRC cash chain periods");
    }

    skipped.push("B2: bank_account_balances not in Board/FE client payload (warehouse-only soft check)");

    if (fcPeriods.length && closeMo) {
      var actEndCash =
        num(srcActuals && srcActuals[closeMo] && srcActuals[closeMo].ending_cash) ||
        num(actual.cfs && actual.cfs[closeMo] && actual.cfs[closeMo].ending_cash);
      var firstFc = fcPeriods[0];
      var tsBeg = num(forecast.cfs && forecast.cfs[firstFc] && forecast.cfs[firstFc].beginning_cash);
      var engBeg =
        engine &&
        engine[firstFc] &&
        engine[firstFc].cfs &&
        num(engine[firstFc].cfs.beg_cash != null ? engine[firstFc].cfs.beg_cash : engine[firstFc].cfs.beginning_cash);
      if (actEndCash != null && tsBeg != null) {
        checksRun.push("B3");
        chk("B3a", firstFc, "TS forecast beg_cash == actual ending", actEndCash, tsBeg, fails, tol);
      }
      if (actEndCash != null && engBeg != null) {
        checksRun.push("B3");
        chk("B3b", firstFc, "Engine forecast beg_cash == actual ending", actEndCash, engBeg, fails, tol);
      }
      if (actEndCash != null && tsBeg == null && engBeg == null) {
        skipped.push("B3: no Forecast CFS / engine beg_cash for " + firstFc);
      }
    }

    // B4: CASH_ACT display array (soft display_precision)
    if (typeof global.CASH_ACT !== "undefined" && Array.isArray(global.CASH_ACT) && closeMo) {
      var cmi = periodMonthIndex(closeMo);
      var cashDisp = num(global.CASH_ACT[cmi]);
      var cashWh =
        num(actual.cfs && actual.cfs[closeMo] && actual.cfs[closeMo].ending_cash) ||
        num(srcActuals && srcActuals[closeMo] && srcActuals[closeMo].ending_cash);
      if (cashDisp != null && cashWh != null) {
        checksRun.push("B4");
        softChk("B4", closeMo, "CASH_ACT vs ending_cash/1e6", cashWh / 1e6, cashDisp, softs, TOL_DISPLAY_M);
      }
    } else {
      skipped.push("B4: CASH_ACT display array absent");
    }

    // B5: CFO identity from CFS row when components present
    cashPeriods.forEach(function (p) {
      var cfsRow = (actual.cfs && actual.cfs[p]) || {};
      var cfo = num(cfsRow.cfo);
      var ni = num(cfsRow.net_income);
      var da = num(cfsRow.da);
      var sbc = num(cfsRow.sbc);
      var car = num(cfsRow.chg_ar);
      var cdr = num(cfsRow.chg_dr);
      var cap = num(cfsRow.chg_ap);
      var pre = num(cfsRow.chg_prepaids);
      if (cfo == null || ni == null || da == null) return;
      var compCfo =
        (ni || 0) +
        (da || 0) +
        (sbc || 0) +
        (car || 0) +
        (cdr || 0) +
        (cap || 0) +
        (pre || 0);
      checksRun.push("B5");
      chk("B5", p, "CFO identity", compCfo, cfo, fails, tol);
    });

    // ── Rule C: IS identities + TS↔SRC ─────────────────────────────────
    periodList.forEach(function (p) {
      var srcRow = (srcActuals && srcActuals[p]) || {};
      var isRow = (actual.is && actual.is[p]) || {};

      // C1 / C2 from whichever side has full IS
      var rev = num(isRow.revenue != null ? isRow.revenue : srcRow.revenue);
      var cogs = num(isRow.cogs != null ? isRow.cogs : srcRow.cogs);
      var gp = num(isRow.gross_profit != null ? isRow.gross_profit : srcRow.gross_profit);
      var sm = num(isRow.sm != null ? isRow.sm : srcRow.sm);
      var rd = num(isRow.rd != null ? isRow.rd : srcRow.rd);
      var ga = num(isRow.ga != null ? isRow.ga : srcRow.ga);
      var ebitda = num(isRow.ebitda != null ? isRow.ebitda : srcRow.ebitda);

      if (rev != null && cogs != null && gp != null) {
        checksRun.push("C1");
        chk("C1", p, "gross_profit = revenue - cogs", rev - cogs, gp, fails, tol);
      }
      if (gp != null && sm != null && rd != null && ga != null && ebitda != null) {
        checksRun.push("C2");
        chk("C2", p, "ebitda = gp - sm - rd - ga", gp - sm - rd - ga, ebitda, fails, tol);
      }

      // C3 TS↔SRC: only when period exists on both sides (chain-only periods skip).
      var srcHas = srcActuals && srcActuals[p] && typeof srcActuals[p] === "object";
      var tsHas =
        (actual.is && actual.is[p]) ||
        (actual.bs && actual.bs[p]) ||
        (actual.cfs && actual.cfs[p]);
      if (srcHas && tsHas) {
        TS_SRC_FIELDS.forEach(function (triple) {
          var field = triple[0];
          var stmt = triple[1];
          var srcKey = triple[2];
          var tsRow = ((actual[stmt] || {})[p]) || {};
          var tsVal = num(tsRow[field]);
          var srcVal = num(srcRow[srcKey]);
          if (srcVal == null && srcKey === "deferred_rev") srcVal = num(srcRow.dr);
          if (tsVal == null && srcVal == null) return;
          checksRun.push("C3");
          chk("C3", p, field, srcVal, tsVal, fails, tol);
        });
      }
    });

    // C3 soft: REV_ACT / EBITDA_ACT display vs TS (million scale)
    if (typeof global.REV_ACT !== "undefined" && Array.isArray(global.REV_ACT) && closeMo) {
      var rmi = periodMonthIndex(closeMo);
      var revDisp = num(global.REV_ACT[rmi]);
      var revWh = num(actual.is && actual.is[closeMo] && actual.is[closeMo].revenue);
      if (revDisp != null && revWh != null) {
        checksRun.push("C3-disp");
        softChk("C3-disp", closeMo, "REV_ACT vs revenue/1e6", revWh / 1e6, revDisp, softs, TOL_DISPLAY_M);
      }
    }

    fcPeriods.forEach(function (p) {
      var eng = engine && engine[p];
      var tsIs = forecast.is && forecast.is[p];
      if (!eng || !eng.is || !tsIs) return;
      checksRun.push("C4");
      chk("C4", p, "revenue", num(eng.is.revenue), num(tsIs.revenue), fails, tol);
      chk("C4", p, "gross_profit", num(eng.is.gross_profit), num(tsIs.gross_profit), fails, tol);
      chk("C4", p, "ebitda", num(eng.is.ebitda), num(tsIs.ebitda), fails, tol);
      chk("C4", p, "net_income", num(eng.is.net_income), num(tsIs.net_income), fails, tol);
      // C5: revenue ≈ arr_eop / 12
      var arrEop = eng.arr && num(eng.arr.arr_eop);
      if (arrEop != null && num(eng.is.revenue) != null) {
        checksRun.push("C5");
        chk("C5", p, "revenue ≈ arr_eop/12", arrEop / 12, num(eng.is.revenue), fails, tol);
      }
    });
    if (fcPeriods.length && !engine) {
      skipped.push("C4/C5/F: no engineResults / baseline_engine / compute()");
    }

    // ── Rule D: Headcount (exact) when WF_HC_ALL present ────────────────
    var wfHc = global.WF_HC_ALL;
    if (wfHc && typeof wfHc === "object") {
      checksRun.push("D1");
      // Internal consistency: department columns same length; no warehouse plan → skip D2–D4
      var depts = Object.keys(wfHc);
      var lengths = depts.map(function (d) {
        return Array.isArray(wfHc[d]) ? wfHc[d].length : 0;
      });
      var len0 = lengths[0] || 0;
      if (!depts.length || lengths.some(function (l) { return l !== len0; })) {
        fails.push("[D1] WF_HC_ALL department column lengths mismatch");
      }
      skipped.push("D2–D4: headcount_plan / open_requisitions warehouse tables not in client payload");
    } else {
      skipped.push("D: WF_HC_ALL absent");
    }

    // ── Rule E: Sales when SD present ──────────────────────────────────
    var sd = global.SD || (payload && payload.SD) || null;
    if (sd && sd.monthly && typeof sd.monthly === "object") {
      checksRun.push("E1");
      Object.keys(sd.monthly).forEach(function (p) {
        if (closeMo && p > closeMo) return;
        var row = sd.monthly[p] || {};
        // Internal non-null sanity only — warehouse quota_assignments not in client
        if (row.quota == null && row.attained == null) {
          softs.push("[E1] " + p + " SD.monthly missing quota/attained (soft)");
        }
      });
      skipped.push("E1–E3 warehouse quota_assignments / opportunities not in client — SD present for display only");
    } else {
      skipped.push("E: SD.monthly absent");
    }

    // ── Rule F: Engine ↔ TS Forecast cross-tie ─────────────────────────
    if (engine && fcPeriods.length) {
      fcPeriods.forEach(function (p) {
        var eng = engine[p];
        var tsIs = forecast.is && forecast.is[p];
        var tsCfs = forecast.cfs && forecast.cfs[p];
        if (!eng || !tsIs) {
          fails.push("[F] missing data for " + p);
          return;
        }
        checksRun.push("F2");
        chk("F2", p, "revenue", num(eng.is && eng.is.revenue), num(tsIs.revenue), fails, tol);
        checksRun.push("F3");
        chk("F3", p, "ebitda", num(eng.is && eng.is.ebitda), num(tsIs.ebitda), fails, tol);
        if (eng.cfs && tsCfs) {
          checksRun.push("F4");
          chk(
            "F4a",
            p,
            "beg_cash",
            num(eng.cfs.beg_cash != null ? eng.cfs.beg_cash : eng.cfs.beginning_cash),
            num(tsCfs.beginning_cash),
            fails,
            tol,
          );
          chk(
            "F4b",
            p,
            "end_cash",
            num(eng.cfs.end_cash != null ? eng.cfs.end_cash : eng.cfs.ending_cash),
            num(tsCfs.ending_cash),
            fails,
            tol,
          );
        }
        var engArr = eng.arr && num(eng.arr.arr_eop);
        if (engArr != null && wf && Array.isArray(wf.Ending)) {
          var fmi = periodMonthIndex(p);
          var wfFcEnd = num(wf.Ending[fmi]);
          if (wfFcEnd != null) {
            checksRun.push("F1");
            chk("F1", p, "engine arr_eop ↔ WF Ending", engArr, wfFcEnd, fails, tol);
          }
        }
      });
      skipped.push("F5: payroll lever soft check not automated (requires SRC.open_reqs vs WF_PAYROLL)");
    }

    if (!periodList.length && !checksRun.length) {
      _lastTieOut = {
        passed: true,
        failures: [],
        warnings: ["tie-out skipped: no overlapping Actual periods / WF / engine data"],
        skipped: skipped,
        soft: softs,
        checksRun: checksRun,
        scope: "empty",
        live: isLive(),
        closeMonth: closeMo,
      };
      _lastTieOutHtml = renderTieOutReportHtml(_lastTieOut);
      global.SMPL_LAST_TIEOUT = _lastTieOut;
      global.SMPL_LAST_TIEOUT_HTML = _lastTieOutHtml;
      return _lastTieOut;
    }

    var passed = fails.length === 0;
    var uniqueChecks = checksRun.filter(function (x, i, a) {
      return a.indexOf(x) === i;
    });
    if (passed) {
      console.info(
        "[smpl-provenance] ✓ TIE-OUT PASSED (client A–F subset: " +
          uniqueChecks.join(",") +
          ")",
      );
    } else {
      console.error("[smpl-provenance] ✗ TIE-OUT FAILED (" + fails.length + " issues)");
      fails.forEach(function (f) {
        console.error(" " + f);
      });
    }

    _lastTieOut = {
      passed: passed,
      failures: fails,
      warnings: softs.concat(
        skipped.map(function (s) {
          return "skip: " + s;
        }),
      ),
      skipped: skipped,
      soft: softs,
      checksRun: uniqueChecks,
      scope: "client-A-F",
      live: isLive(),
      closeMonth: closeMo,
      note:
        "Client A–F from Board/FE structures. Not live warehouse SQL. " +
        "D2–D4 / E warehouse / B2 bank / F5 payroll remain skipped when data absent. " +
        "TOL_ACTUALS=$" +
        TOL_ACTUALS.toFixed(2) +
        ".",
    };
    _lastTieOutHtml = renderTieOutReportHtml(_lastTieOut);
    global.SMPL_LAST_TIEOUT = _lastTieOut;
    global.SMPL_LAST_TIEOUT_HTML = _lastTieOutHtml;
    return _lastTieOut;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Client-side HTML tie-out report (not warehouse SQL Part 5). */
  function renderTieOutReportHtml(result) {
    result = result || _lastTieOut || {};
    var fails = result.failures || [];
    var soft = result.soft || [];
    var skipped = result.skipped || [];
    var checks = result.checksRun || [];
    var status = result.passed
      ? "APPROVED FOR DEPLOYMENT (client checks)"
      : "BLOCKED — tie-out failures";
    var rows = fails
      .map(function (f) {
        return "<tr class='fail'><td>FAIL</td><td>" + escapeHtml(f) + "</td></tr>";
      })
      .concat(
        soft.map(function (f) {
          return "<tr class='soft'><td>SOFT</td><td>" + escapeHtml(f) + "</td></tr>";
        }),
      )
      .concat(
        skipped.map(function (f) {
          return "<tr class='skip'><td>SKIP</td><td>" + escapeHtml(f) + "</td></tr>";
        }),
      )
      .join("");
    return (
      "<!DOCTYPE html><html><head><meta charset='utf-8'><title>SMPL Tie-Out Report</title>" +
      "<style>body{font-family:ui-monospace,Consolas,monospace;padding:24px;background:#0f1410;color:#dde8d6}" +
      "h1{font-size:18px}table{border-collapse:collapse;width:100%;margin-top:16px}" +
      "td,th{border:1px solid #2e3f31;padding:6px 8px;font-size:12px;text-align:left}" +
      ".fail td{color:#b8705f}.soft td{color:#b89060}.skip td{color:#72826a}" +
      ".ok{color:#5fa878}.bad{color:#b8705f}</style></head><body>" +
      "<h1>SMPL.ai — Client Data Tie-Out Report</h1>" +
      "<p>Close: " +
      escapeHtml(result.closeMonth || "") +
      " · Live: " +
      (result.live ? "yes" : "no") +
      " · Scope: " +
      escapeHtml(result.scope || "") +
      "</p>" +
      "<p>Checks run: " +
      escapeHtml(checks.join(", ") || "(none)") +
      "</p>" +
      "<p class='" +
      (result.passed ? "ok" : "bad") +
      "'>STATUS: " +
      escapeHtml(status) +
      "</p>" +
      "<p>Hard failures: " +
      fails.length +
      " · Soft: " +
      soft.length +
      " · Skipped: " +
      skipped.length +
      "</p>" +
      "<p>TOL_ACTUALS=$" +
      TOL_ACTUALS.toFixed(2) +
      ". Not SOC 2 certified. Not live warehouse SQL.</p>" +
      "<table><thead><tr><th>Kind</th><th>Detail</th></tr></thead><tbody>" +
      (rows || "<tr><td>OK</td><td>No failures, soft flags, or skips recorded.</td></tr>") +
      "</tbody></table>" +
      "<p style='margin-top:24px;color:#72826a'>Finance sign-off boxes are intentionally blank — " +
      "do not treat this auto-report as founder Allow.</p>" +
      "</body></html>"
    );
  }

  function downloadTieOutReport(result) {
    var html = renderTieOutReportHtml(result || _lastTieOut);
    _lastTieOutHtml = html;
    global.SMPL_LAST_TIEOUT_HTML = html;
    if (typeof document === "undefined") return html;
    try {
      var blob = new Blob([html], { type: "text/html;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      var cm = (result && result.closeMonth) || closeMonth() || "unknown";
      a.href = url;
      a.download = "tieout_report_client_" + cm + ".html";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () {
        URL.revokeObjectURL(url);
      }, 2000);
    } catch (err) {
      console.warn("[smpl-provenance] HTML report download failed", err);
    }
    return html;
  }

  /**
   * Customer publish gate. Returns { ok, blocked, result, message, reportHtml }.
   * - Live + FAIL → block (ok=false, blocked=true); HTML report attached
   * - Demo / no live → warn only (ok=true, blocked=false) unless forceBlock
   */
  function gatePublish(options) {
    options = options || {};
    var result = runTieOut(options.srcActuals, options.tsData, options.engineResults, options.closeMonth);
    var live = options.forceLive != null ? options.forceLive : isLive();
    var forceBlock = Boolean(options.forceBlock);
    var blocked = (!result.passed && live) || (!result.passed && forceBlock);
    var reportHtml = _lastTieOutHtml || renderTieOutReportHtml(result);
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
        ". Client Rule Sets A–F (skips when data absent). HTML report attached.";
      if (blocked) {
        message += "\n\nCustomer publish/export blocked until resolved.";
        if (options.downloadReport !== false) {
          try {
            downloadTieOutReport(result);
          } catch (err) {
            /* ignore */
          }
        }
      } else {
        message += "\n\nDemo/offline path: warning only (not hard-blocked).";
      }
    }
    return {
      ok: !blocked,
      blocked: blocked,
      result: result,
      message: message,
      reportHtml: reportHtml,
    };
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
    TOL_DISPLAY_M: TOL_DISPLAY_M,
    TOL_BANK_SOFT: TOL_BANK_SOFT,
    FIELD_CATALOG: FIELD_CATALOG,
    ingestOutlook: ingestOutlook,
    resolveRecord: resolveRecord,
    formatSourceTag: formatSourceTag,
    attrString: attrString,
    annotateDom: annotateDom,
    applyAttrsToEl: applyAttrsToEl,
    runTieOut: runTieOut,
    gatePublish: gatePublish,
    renderTieOutReportHtml: renderTieOutReportHtml,
    downloadTieOutReport: downloadTieOutReport,
    toggleAuditOverlay: toggleAuditOverlay,
    clearAuditTags: clearAuditTags,
    install: install,
    getLastTieOut: function () {
      return _lastTieOut;
    },
    getLastTieOutHtml: function () {
      return _lastTieOutHtml;
    },
    getPayloadSources: function () {
      return _payloadSources;
    },
  };

  // Global alias matching framework Part 4 naming
  global.runTieOut = runTieOut;

  install();
})(typeof window !== "undefined" ? window : globalThis);
