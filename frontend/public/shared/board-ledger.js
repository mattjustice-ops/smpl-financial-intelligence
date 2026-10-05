/**
 * Board reporting ledger — the one data source the Income Statement and the
 * Management P&L are both built from.
 *
 * Income Statement basis: ledger rows rolled up by statement line, no allocations.
 * Management basis: the same rows mapped to management lines, then allocation layers
 * applied. Allocations move cost between cost lines only; revenue, total costs and
 * EBITDA are identical on both bases by construction.
 *
 * Today the reporting source carries statement-line rows (TS_DATA.is). When a source
 * provides account-level rows (department / management line per account), they slot
 * into the same row shape and both statements pick them up with no other change.
 */
(function (global) {
  "use strict";

  var SOURCE_ROWS = [
    { id: "sub_rev", name: "Subscription revenue", section: "revenue", isLine: "Subscription Revenue", mgmtLine: "Subscription Revenue", dept: "Revenue" },
    { id: "svc_rev", name: "Implementation & onboarding", section: "revenue", isLine: "Implementation & Onboarding", mgmtLine: "Implementation & Onboarding", dept: "Revenue" },
    { id: "cogs", name: "Cost of revenue", section: "cogs", isLine: "Cost of Revenue", mgmtLine: "Cost of Revenue", dept: "Cost of Revenue" },
    { id: "sm", name: "Sales & marketing", section: "opex", isLine: "Sales & Marketing", mgmtLine: "Sales & Marketing", dept: "Sales & Marketing" },
    { id: "rd", name: "Research & development", section: "opex", isLine: "Research & Development", mgmtLine: "Research & Development", dept: "R&D" },
    { id: "ga", name: "General & administrative", section: "opex", isLine: "General & Administrative", mgmtLine: "General & Administrative", dept: "G&A" },
  ];

  var SECTIONS = [
    { key: "revenue", title: "Revenue", total: "Total Revenue" },
    { key: "cogs", title: "Cost of Revenue", total: "Total Cost of Revenue" },
    { key: "opex", title: "Operating Expenses", total: "Total OpEx" },
  ];

  /** Allocation layers (management basis only). Empty until a customer's allocation policy is configured. */
  if (!Array.isArray(global.SMPL_ALLOCATION_RULES)) global.SMPL_ALLOCATION_RULES = [];

  function tsSource() {
    if (typeof global.boardTsSource === "function") return global.boardTsSource();
    if (global.SMPLBoardData && global.SMPLBoardData.boardTsSource) return global.SMPLBoardData.boardTsSource();
    return global.TS_DATA || null;
  }

  function closeMonth() {
    return String(global.CLOSE_MONTH || "2026-06");
  }

  function isLive() {
    return Boolean(global.SMPL_LIVE_OUTLOOK);
  }

  function sourceInfo() {
    return {
      kind: isLive() ? "warehouse" : "demo",
      label: isLive() ? "Warehouse reporting ledger (live)" : "Embedded demo reporting ledger",
      grain: "statement line",
      table: isLive() ? "income_statement" : "TS_DATA",
      rows: SOURCE_ROWS.length,
    };
  }

  function num(v) {
    return v == null || Number.isNaN(+v) ? null : +v;
  }

  /** Ledger amounts for one scenario / period, keyed by row id. Costs are positive. */
  function rowAmounts(scenario, period) {
    var ts = tsSource();
    var is = ts && ts[scenario] && ts[scenario].is && ts[scenario].is[period];
    if (!is) return null;
    var rev = num(is.revenue);
    var sub = num(is.sub_rev);
    var svc = num(is.svc_rev);
    if (sub == null && svc == null) {
      sub = rev;
      svc = rev == null ? null : 0;
    } else if (sub == null) {
      sub = rev == null ? null : rev - svc;
    } else if (svc == null) {
      svc = rev == null ? 0 : rev - sub;
    }
    return { sub_rev: sub, svc_rev: svc, cogs: num(is.cogs), sm: num(is.sm), rd: num(is.rd), ga: num(is.ga) };
  }

  function periodsFor(scenario, which) {
    var ts = tsSource();
    var all = (ts && ts[scenario] && ts[scenario].periods) || [];
    var cm = closeMonth();
    var year = cm.slice(0, 4);
    if (which === "month") return all.indexOf(cm) >= 0 ? [cm] : [];
    if (which === "ytd") return all.filter(function (p) { return p.slice(0, 4) === year && p <= cm; });
    if (which === "rest_of_year") return all.filter(function (p) { return p.slice(0, 4) === year && p > cm; });
    return all.slice();
  }

  function lineOrder(basis) {
    var key = basis === "is" ? "isLine" : "mgmtLine";
    var seen = {};
    var out = [];
    SOURCE_ROWS.forEach(function (r) {
      if (seen[r[key]]) return;
      seen[r[key]] = true;
      out.push({ label: r[key], section: r.section });
    });
    return out;
  }

  function allocationRules() {
    return (global.SMPL_ALLOCATION_RULES || []).filter(function (rule) {
      return rule && rule.from && rule.to && rule.from !== rule.to;
    });
  }

  /**
   * Roll ledger rows up on one basis for a scenario across periods.
   * Returns lines (with contributing accounts and net allocation), section totals,
   * gross profit, EBITDA and the allocation transfers applied.
   */
  function rollup(basis, scenario, periods) {
    var lineKey = basis === "is" ? "isLine" : "mgmtLine";
    var order = lineOrder(basis);
    var lines = {};
    order.forEach(function (l) {
      lines[l.label] = { label: l.label, section: l.section, amount: 0, alloc: 0, accounts: [], hasData: false };
    });
    var accountTotals = {};
    var transfers = [];
    var rules = basis === "mgmt" ? allocationRules() : [];

    periods.forEach(function (p) {
      var amts = rowAmounts(scenario, p);
      if (!amts) return;
      var periodLine = {};
      SOURCE_ROWS.forEach(function (r) {
        var v = amts[r.id];
        if (v == null) return;
        var line = lines[r[lineKey]];
        line.amount += v;
        line.hasData = true;
        periodLine[r[lineKey]] = (periodLine[r[lineKey]] || 0) + v;
        accountTotals[r.id] = (accountTotals[r.id] || 0) + v;
      });
      rules.forEach(function (rule) {
        var from = lines[rule.from];
        if (!from || from.section === "revenue") return;
        var to = lines[rule.to];
        if (!to) {
          to = lines[rule.to] = { label: rule.to, section: rule.toSection || from.section, amount: 0, alloc: 0, accounts: [], hasData: true };
          order.push({ label: rule.to, section: to.section });
        }
        if (to.section === "revenue") return;
        var fixed = rule.amounts && rule.amounts[scenario] && rule.amounts[scenario][p];
        var fromPeriod = periodLine[rule.from];
        var amt = fixed != null ? +fixed : (rule.pct != null && fromPeriod != null ? fromPeriod * rule.pct : 0);
        if (!amt) return;
        periodLine[rule.from] = (fromPeriod || 0) - amt;
        periodLine[rule.to] = (periodLine[rule.to] || 0) + amt;
        from.amount -= amt;
        from.alloc -= amt;
        to.amount += amt;
        to.alloc += amt;
        transfers.push({ id: rule.id, label: rule.label || (rule.from + " → " + rule.to), from: rule.from, to: rule.to, period: p, amount: amt });
      });
    });

    SOURCE_ROWS.forEach(function (r) {
      if (accountTotals[r.id] == null) return;
      lines[r[lineKey]].accounts.push({ id: r.id, name: r.name, dept: r.dept, amount: accountTotals[r.id] });
    });

    var totals = { revenue: 0, cogs: 0, opex: 0 };
    order.forEach(function (l) {
      totals[lines[l.label].section] += lines[l.label].amount;
    });
    return {
      basis: basis,
      scenario: scenario,
      periods: periods.slice(),
      order: order.map(function (l) { return l.label; }),
      lines: lines,
      totals: {
        revenue: totals.revenue,
        cogs: totals.cogs,
        gross_profit: totals.revenue - totals.cogs,
        opex: totals.opex,
        ebitda: totals.revenue - totals.cogs - totals.opex,
      },
      transfers: transfers,
    };
  }

  /** Income Statement value for one scenario / period / TS_DATA key, from the ledger. */
  function isValue(scenario, period, key) {
    var amts = rowAmounts(scenario, period);
    if (!amts) return null;
    var r = rollup("is", scenario, [period]).totals;
    switch (key) {
      case "sub_rev": return amts.sub_rev;
      case "svc_rev": return amts.svc_rev;
      case "cogs": return amts.cogs;
      case "sm": return amts.sm;
      case "rd": return amts.rd;
      case "ga": return amts.ga;
      case "revenue": return r.revenue;
      case "gross_profit": return r.gross_profit;
      case "gm_pct": return r.revenue ? r.gross_profit / r.revenue : null;
      case "total_opex": return r.opex;
      case "ebitda": return r.ebitda;
      default: return undefined;
    }
  }

  var M = 1e6;
  function toM(v) { return v == null ? null : +(v / M).toFixed(6); }

  function lineCols(label, cols) {
    function amt(key) {
      var line = cols[key].lines[label];
      return line && line.hasData ? toM(line.amount) : null;
    }
    return { a: amt("a"), b: amt("b"), ytdA: amt("ytdA"), ytdB: amt("ytdB"), fc: amt("fc") };
  }

  function totalCols(key, cols) {
    function t(c) { return cols[c].periods.length ? toM(cols[c].totals[key]) : null; }
    return { a: t("a"), b: t("b"), ytdA: t("ytdA"), ytdB: t("ytdB"), fc: t("fc") };
  }

  function columnRollups(basis) {
    return {
      a: rollup(basis, "Actual", periodsFor("Actual", "month")),
      b: rollup(basis, "Budget", periodsFor("Budget", "month")),
      ytdA: rollup(basis, "Actual", periodsFor("Actual", "ytd")),
      ytdB: rollup(basis, "Budget", periodsFor("Budget", "ytd")),
      fc: rollup(basis, "Forecast", periodsFor("Forecast", "rest_of_year")),
    };
  }

  /** Management P&L table rows ($M): close month vs budget, YTD, and rest-of-year forecast. */
  function managementPl() {
    var cols = columnRollups("mgmt");
    var rows = [];
    SECTIONS.forEach(function (sec) {
      rows.push({ type: "sec", label: sec.title, section: sec.key });
      cols.a.order.forEach(function (label) {
        var line = cols.a.lines[label];
        if (line.section !== sec.key) return;
        var r = Object.assign({ label: label, section: sec.key, inv: sec.key !== "revenue" }, lineCols(label, cols));
        r.accounts = line.accounts.map(function (acct) {
          function acctAmt(c) {
            var l = cols[c].lines[label];
            var hit = l && l.accounts.filter(function (x) { return x.id === acct.id; })[0];
            return hit ? toM(hit.amount) : null;
          }
          return { id: acct.id, name: acct.name, dept: acct.dept, a: acctAmt("a"), b: acctAmt("b"), ytdA: acctAmt("ytdA"), ytdB: acctAmt("ytdB"), fc: acctAmt("fc") };
        });
        r.alloc = { a: toM(line.alloc), b: toM(cols.b.lines[label] ? cols.b.lines[label].alloc : 0) };
        rows.push(r);
      });
      rows.push(Object.assign({ type: "sub", label: sec.total, section: sec.key, inv: sec.key !== "revenue" }, totalCols(sec.key === "revenue" ? "revenue" : sec.key, cols)));
      if (sec.key === "cogs") {
        rows.push(Object.assign({ type: "sub", label: "Gross Profit", hi: true }, totalCols("gross_profit", cols)));
      }
    });
    rows.push(Object.assign({ type: "tot", label: "EBITDA" }, totalCols("ebitda", cols)));
    return rows;
  }

  var BRIDGE_METRICS = [
    { key: "revenue", label: "Revenue" },
    { key: "cogs", label: "Cost of revenue" },
    { key: "gross_profit", label: "Gross profit" },
    { key: "opex", label: "Operating expenses" },
    { key: "ebitda", label: "EBITDA" },
  ];

  /**
   * Income Statement → Management P&L bridge for a scenario and period set.
   * Status per metric: "identical" (no allocation moved it), "allocated" (difference equals
   * the allocation transfers), or "break" (difference not explained — should never happen).
   */
  function bridge(scenario, periods) {
    var is = rollup("is", scenario, periods);
    var mg = rollup("mgmt", scenario, periods);
    var allocBySection = { revenue: 0, cogs: 0, opex: 0 };
    mg.order.forEach(function (label) {
      var l = mg.lines[label];
      allocBySection[l.section] += l.alloc;
    });
    var alloc = {
      revenue: allocBySection.revenue,
      cogs: allocBySection.cogs,
      gross_profit: -allocBySection.cogs,
      opex: allocBySection.opex,
      ebitda: -(allocBySection.cogs + allocBySection.opex),
    };
    var rows = BRIDGE_METRICS.map(function (m) {
      var diff = mg.totals[m.key] - is.totals[m.key];
      var explained = Math.abs(diff - alloc[m.key]) < 0.5;
      var status = !explained ? "break" : Math.abs(alloc[m.key]) >= 0.5 ? "allocated" : "identical";
      return { key: m.key, label: m.label, is: is.totals[m.key], alloc: alloc[m.key], mgmt: mg.totals[m.key], status: status };
    });
    return {
      scenario: scenario,
      periods: periods.slice(),
      rows: rows,
      transfers: mg.transfers,
      rules: allocationRules(),
      ok: rows.every(function (r) { return r.status !== "break"; }),
    };
  }

  /** How one management / IS line is built, for provenance popovers. */
  function explain(basis, label, scenario, periods) {
    var r = rollup(basis, scenario, periods);
    var line = r.lines[label];
    var src = sourceInfo();
    if (!line) {
      var key = { "Total Revenue": "revenue", "Total Cost of Revenue": "cogs", "Gross Profit": "gross_profit", "Total OpEx": "opex", "EBITDA": "ebitda" }[label];
      if (!key) return null;
      var formula = {
        revenue: "Sum of revenue lines",
        cogs: "Sum of cost of revenue lines",
        gross_profit: "Total Revenue − Total Cost of Revenue",
        opex: "Sum of operating expense lines",
        ebitda: "Gross Profit − Total OpEx",
      }[key];
      return { label: label, basis: basis, scenario: scenario, periods: periods, total: r.totals[key], formula: formula, accounts: [], transfers: [], source: src };
    }
    return {
      label: label,
      basis: basis,
      scenario: scenario,
      periods: periods,
      total: line.amount,
      accounts: line.accounts.map(function (a) {
        return { name: a.name, dept: a.dept, amount: a.amount, source: src.table + "." + a.id };
      }),
      transfers: r.transfers.filter(function (t) { return t.from === label || t.to === label; }),
      alloc: line.alloc,
      source: src,
    };
  }

  /** Ledger rows grouped by department, for the department and GL drilldown views ($M). */
  function byDepartment() {
    var cols = columnRollups("is");
    var depts = {};
    var order = [];
    SOURCE_ROWS.forEach(function (r) {
      if (r.section === "revenue") return;
      if (!depts[r.dept]) {
        depts[r.dept] = { dept: r.dept, accounts: [] };
        order.push(r.dept);
      }
      function amt(c) {
        var l = cols[c].lines[r.isLine];
        var hit = l && l.accounts.filter(function (x) { return x.id === r.id; })[0];
        return hit ? toM(hit.amount) : null;
      }
      depts[r.dept].accounts.push({ id: r.id, name: r.name, a: amt("a"), b: amt("b"), ytdA: amt("ytdA"), ytdB: amt("ytdB"), fc: amt("fc") });
    });
    return order.map(function (d) {
      var accts = depts[d].accounts;
      function sum(k) {
        var any = false;
        var s = accts.reduce(function (acc, x) { if (x[k] != null) any = true; return acc + (x[k] || 0); }, 0);
        return any ? +s.toFixed(6) : null;
      }
      return { dept: d, accounts: accts, a: sum("a"), b: sum("b"), ytdA: sum("ytdA"), ytdB: sum("ytdB"), fc: sum("fc") };
    });
  }

  global.SMPLLedger = {
    SOURCE_ROWS: SOURCE_ROWS,
    sourceInfo: sourceInfo,
    periodsFor: periodsFor,
    rollup: rollup,
    isValue: isValue,
    managementPl: managementPl,
    bridge: bridge,
    explain: explain,
    byDepartment: byDepartment,
    allocationRules: allocationRules,
  };
})(typeof window !== "undefined" ? window : globalThis);
