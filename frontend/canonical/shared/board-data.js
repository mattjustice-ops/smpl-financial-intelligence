/**
 * Board Platform — single source for series derived from TS_DATA + ARR waterfall.
 * Call boardRefreshAllSeries() after TS_DATA is available and after warehouse hydrate.
 */
(function (global) {
  "use strict";

  /** Canonical total headcount by month (Jan–Dec). Jun close EOP = 137. */
  var BOARD_WF_TOTAL_HC = [121, 124, 126, 128, 130, 137, 140, 142, 145, 146, 147, 147];
  if (!global.WF_TOTAL_HC) global.WF_TOTAL_HC = BOARD_WF_TOTAL_HC;

  function boardTsSource() {
    var embedded = global.TS_DATA;
    if (global.SMPL_LIVE_OUTLOOK && global.SMPLOutlook && global.SMPLOutlook.getOutlookTsData) {
      var live = global.SMPLOutlook.getOutlookTsData();
      if (live && global.SMPLOutlook.mergeTsData && embedded) {
        return global.SMPLOutlook.mergeTsData(embedded, live);
      }
      if (live) return live;
    }
    return embedded;
  }

  function boardWfTable() {
    if (global.SMPLOutlook && global.SMPLOutlook.getOutlookWfTable) {
      var wf = global.SMPLOutlook.getOutlookWfTable();
      if (wf) return wf;
    }
    return global.SMPL_DEMO_WF_TABLE || global.SMPL_ARR_WATERFALL || null;
  }

  function boardActCount() {
    return global.ACT_MONTHS_COUNT != null
      ? global.ACT_MONTHS_COUNT
      : parseInt((global.CLOSE_MONTH || "2026-06").slice(5), 10);
  }

  function boardCloseIdx() {
    return boardActCount() - 1;
  }

  function boardYear() {
    return (global.CLOSE_MONTH || "2026-06").slice(0, 4);
  }

  function wfRow(wf, key) {
    if (!wf || !wf[key]) return null;
    return wf[key];
  }

  function boardRefreshAllSeries() {
    var ts = boardTsSource();
    var wf = boardWfTable();
    var actN = boardActCount();
    if (!ts || !ts.Actual) return false;

    var actPeriods = (ts.Actual.periods || []).slice(0, actN);
    var isAct = ts.Actual.is || {};
    var bsAct = ts.Actual.bs || {};
    var cfsAct = ts.Actual.cfs || {};
    var isBud = (ts.Budget && ts.Budget.is) || {};
    var bsBud = (ts.Budget && ts.Budget.bs) || {};

    if (wf && wf.Ending) {
      global.ARR_ACT = wf.Ending.slice(0, actN).map(function (v) {
        return +(v / 1e6).toFixed(2);
      });
      var budEnd = wf.Budget_Ending || wf.budget_ending;
      if (budEnd) {
        global.ARR_BUD = budEnd.slice(0, actN).map(function (v) {
          return +(v / 1e6).toFixed(2);
        });
      } else if (global.ARR_BUD && global.ARR_BUD.length >= actN) {
        /* keep embedded budget ARR */
      } else {
        global.ARR_BUD = global.ARR_ACT.map(function (v, i) {
          return +(v * 0.99).toFixed(2);
        });
      }

      global.NN_ACT = [];
      for (var i = 0; i < actN; i++) {
        var nn =
          (wfRow(wf, "New Business")[i] || 0) +
          (wfRow(wf, "Expansion")[i] || 0) +
          (wfRow(wf, "Reactivation")[i] || 0) +
          (wfRow(wf, "Contraction")[i] || 0) +
          (wfRow(wf, "Churn")[i] || 0);
        global.NN_ACT.push(+(nn / 1e6).toFixed(3));
      }

      if (global.ARR_BUD && global.ARR_BUD.length >= actN) {
        global.NN_BUD = [];
        for (var j = 0; j < actN; j++) {
          var dr = boardNnDrivers(wf, j);
          var budSum = dr.reduce(function (s, d) {
            return s + d.bud;
          }, 0);
          global.NN_BUD.push(+(budSum.toFixed(3)));
        }
      } else if (!global.NN_BUD || global.NN_BUD.length < actN) {
        global.NN_BUD = [];
        for (var k = 0; k < actN; k++) {
          var prevArr = k > 0 ? global.ARR_ACT[k - 1] : wfRow(wf, "Beginning")[0] / 1e6;
          global.NN_BUD.push(+((global.ARR_ACT[k] - prevArr).toFixed(3)));
        }
      }
    }

    var mo12 =
      global.MO12 ||
      ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    global.MO12 = mo12;
    global.MO = mo12.slice(0, actN);

    global.REV_ACT = actPeriods.map(function (p) {
      return +((isAct[p] && isAct[p].revenue ? isAct[p].revenue : 0) / 1e6).toFixed(2);
    });
    global.GP_ACT = actPeriods.map(function (p) {
      return +((isAct[p] && isAct[p].gross_profit ? isAct[p].gross_profit : 0) / 1e6).toFixed(2);
    });
    global.SM_ACT = actPeriods.map(function (p) {
      return +((isAct[p] && isAct[p].sm ? isAct[p].sm : 0) / 1e6).toFixed(2);
    });
    global.RD_ACT = actPeriods.map(function (p) {
      return +((isAct[p] && isAct[p].rd ? isAct[p].rd : 0) / 1e6).toFixed(2);
    });
    global.GA_ACT = actPeriods.map(function (p) {
      return +((isAct[p] && isAct[p].ga ? isAct[p].ga : 0) / 1e6).toFixed(2);
    });
    global.EBITDA_ACT = actPeriods.map(function (p) {
      return +((isAct[p] && isAct[p].ebitda != null ? isAct[p].ebitda : 0) / 1e6).toFixed(2);
    });

    if (actPeriods.length) {
      global.REV_BUD = actPeriods.map(function (p, i) {
        var row = isBud[p];
        if (row && row.revenue != null) return +(row.revenue / 1e6).toFixed(2);
        return global.REV_BUD && global.REV_BUD[i] != null ? global.REV_BUD[i] : global.REV_ACT[i];
      });
      /* Keep embedded operational cash budget series; BS budget cash ≠ liquidity plan */
      if (!global.CASH_BUD || global.CASH_BUD.length < actN) {
        global.CASH_BUD = actPeriods.map(function (p) {
          var row = bsBud[p];
          return row && row.cash != null ? +(row.cash / 1e6).toFixed(2) : 0;
        });
      }
    }

    global.CASH_ACT = actPeriods.map(function (p) {
      var cash = bsAct[p] && bsAct[p].cash;
      if (cash == null && cfsAct[p]) cash = cfsAct[p].ending_cash;
      return cash != null ? +(cash / 1e6).toFixed(2) : 0;
    });

    global.COLL = actPeriods.map(function (p, i) {
      var bridge =
        (global.SMPL_CASH_BRIDGE && global.SMPL_CASH_BRIDGE.Actual && global.SMPL_CASH_BRIDGE.Actual[p]) ||
        (global.SMPL_OUTLOOK_PAYLOAD &&
          global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE &&
          global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE.Actual &&
          global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE.Actual[p]);
      if (bridge && bridge.collections != null) {
        return +(bridge.collections / 1e6).toFixed(2);
      }
      var cfs = cfsAct[p];
      if (cfs && cfs.cfo != null && cfs.cfo > 0) return +(cfs.cfo / 1e6).toFixed(2);
      return global.COLL && global.COLL[i] != null ? global.COLL[i] : 0;
    });

    if (global.WF_TOTAL_HC && global.WF_TOTAL_HC.length >= actN) {
      var hc = global.WF_TOTAL_HC;
      global.HC_BY_MO = hc.slice(0, actN);
      global.HC_TOTAL_JAN = hc[0];
      global.HC_TOTAL_MAY = hc[Math.min(4, hc.length - 1)];
      global.HC_TOTAL_JUN = hc[boardCloseIdx()];
      if (global.HC_TOTAL_BUD == null) global.HC_TOTAL_BUD = hc[Math.min(4, hc.length - 1)];
      var arrEop = wf && wf.Ending ? wf.Ending[boardCloseIdx()] : null;
      if (arrEop && global.HC_BY_MO[boardCloseIdx()]) {
        global.ARR_PER_EMP = actPeriods.map(function (p, idx) {
          var h = hc[idx] || global.HC_BY_MO[idx];
          var arr = wf && wf.Ending ? wf.Ending[idx] : null;
          return h && arr ? Math.round(arr / h / 1000) : 0;
        });
      }
    }

    return true;
  }

  function wfBudgetComponent(wf, label, idx) {
    if (!wf) return null;
    var keys = [
      "Budget_" + label.replace(/ /g, "_"),
      "Budget " + label,
      label + "_Budget",
    ];
    for (var i = 0; i < keys.length; i++) {
      var row = wf[keys[i]];
      if (row && row[idx] != null) return row[idx] / 1e6;
    }
    return null;
  }

  function boardWaterfallMonthM(wf, monthIdx) {
    if (!wf) return null;
    var m = function (key) {
      return (wfRow(wf, key)[monthIdx] || 0) / 1e6;
    };
    var bop = m("Beginning");
    var nb = m("New Business");
    var exp = m("Expansion");
    var react = m("Reactivation");
    var con = m("Contraction");
    var churn = m("Churn");
    var eop = m("Ending");
    var afterNB = bop + nb;
    var afterExp = afterNB + exp;
    var afterReact = afterExp + react;
    var afterCon = afterReact + con;
    var afterChurn = afterCon + churn;
    return {
      bop: bop,
      nb: nb,
      exp: exp,
      react: react,
      con: con,
      churn: churn,
      eop: eop,
      afterNB: afterNB,
      afterExp: afterExp,
      afterReact: afterReact,
      afterCon: afterCon,
      afterChurn: afterChurn,
      wfOffsets: [0, bop, afterNB, afterExp, afterCon, afterChurn, 0],
      wfHeights: [bop, nb, exp, react, Math.abs(con), Math.abs(churn), afterChurn],
      wfLabelsTop: [bop, nb, exp, react, con, churn, afterChurn],
    };
  }

  function boardArrTableMeta() {
    var actN = boardActCount();
    var year = boardYear();
    var mo = global.MO12 || ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return mo.map(function (name, i) {
      return {
        label: name + " " + year,
        isFc: i >= actN,
        isAct: i < actN,
      };
    });
  }

  function boardArrPeriodLabel() {
    var actN = boardActCount();
    var mo = global.MO12 || [];
    var year = boardYear();
    var actEnd = mo[actN - 1] || "Jun";
    var fcStart = mo[actN] || "Jul";
    return (
      "Jan through " +
      actEnd +
      " " +
      year +
      " Actual · " +
      fcStart +
      " through Dec " +
      year +
      " Forecast"
    );
  }

  function boardCashBridgeRows(period) {
    period = period || global.CLOSE_MONTH || "2026-06";
    var ts = boardTsSource();
    var cfs = ts && ts.Actual && ts.Actual.cfs && ts.Actual.cfs[period];

    function cfsNetChange(c) {
      if (!c) return null;
      if (c.net_change != null) return c.net_change;
      if (c.net_change_cash != null) return c.net_change_cash;
      if (c.ending_cash != null && c.beginning_cash != null) return c.ending_cash - c.beginning_cash;
      return null;
    }

    function operationalBridgeRows(bridge) {
      var rows = [];
      function push(label, key, invert) {
        if (bridge[key] == null) return;
        var v = bridge[key];
        rows.push({ label: label, value: v, inflow: !invert ? v >= 0 : v <= 0 });
      }
      push("+ Collections", "collections", false);
      push("– Payroll", "payroll", true);
      push("– Vendor / AP", "vendor", true);
      push("– Commissions", "commission", true);
      push("– CapEx", "capex", true);
      var net = cfs ? cfsNetChange(cfs) : bridge.net_change;
      if (net == null) net = bridge.net_change;
      if (net != null) rows.push({ label: "Net change in cash", value: net, total: true, cfsTie: true });
      return rows;
    }

    function cfsBridgeRows(c) {
      if (!c) return [];
      var rows = [];
      if (c.cfo != null) {
        rows.push({ label: "Cash from operations (CFO)", value: c.cfo, inflow: c.cfo >= 0 });
      } else {
        if (c.net_income != null) rows.push({ label: "Net income", value: c.net_income, inflow: c.net_income >= 0 });
        if (c.da != null) rows.push({ label: "D&A (add-back)", value: c.da, inflow: true });
        if (c.sbc != null) rows.push({ label: "Stock-based comp", value: c.sbc, inflow: true });
        if (c.chg_ar != null) rows.push({ label: "Δ Accounts receivable", value: c.chg_ar, inflow: c.chg_ar >= 0 });
        if (c.chg_dr != null) rows.push({ label: "Δ Deferred revenue", value: c.chg_dr, inflow: c.chg_dr >= 0 });
        if (c.chg_ap != null) rows.push({ label: "Δ Accounts payable", value: c.chg_ap, inflow: c.chg_ap >= 0 });
        if (c.chg_prepaids != null) rows.push({ label: "Δ Prepaids", value: c.chg_prepaids, inflow: c.chg_prepaids >= 0 });
      }
      var capex = c.capex != null ? c.capex : c.cfi;
      if (capex != null) rows.push({ label: "Investing (CapEx)", value: capex, inflow: capex >= 0 });
      if (c.cff != null && c.cff !== 0) rows.push({ label: "Financing", value: c.cff, inflow: c.cff >= 0 });
      var net = cfsNetChange(c);
      if (net != null) rows.push({ label: "Net change in cash", value: net, total: true, cfsTie: true });
      return rows;
    }

    var bridge =
      (global.SMPL_CASH_BRIDGE && global.SMPL_CASH_BRIDGE.Actual && global.SMPL_CASH_BRIDGE.Actual[period]) ||
      (global.SMPL_OUTLOOK_PAYLOAD &&
        global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE &&
        global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE.Actual &&
        global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE.Actual[period]);

    if (bridge) return operationalBridgeRows(bridge);
    if (cfs) return cfsBridgeRows(cfs);
    return [];
  }

  function boardFmtM(v, d) {
    d = d == null ? 1 : d;
    if (v == null || Number.isNaN(v)) return "—";
    var abs = Math.abs(v);
    var neg = v < 0;
    var s = abs >= 1 ? abs.toFixed(d) + "M" : Math.round(abs * 1000) + "K";
    return (neg ? "-" : "") + "$" + s;
  }

  function boardFmtM1(v) {
    return boardFmtM(v, 1);
  }

  function boardFmtVarM(v, d) {
    if (v == null || Number.isNaN(v)) return "—";
    var abs = Math.abs(v);
    var prefix = v >= 0 ? "+" : "-";
    var decimals = d != null ? d : abs < 0.1 ? 2 : 1;
    return prefix + "$" + abs.toFixed(decimals) + "M";
  }

  function boardCloseHc() {
    var idx = boardCloseIdx();
    if (global.WF_TOTAL_HC && global.WF_TOTAL_HC[idx] != null) return global.WF_TOTAL_HC[idx];
    if (global.HC_BY_MO && global.HC_BY_MO[idx] != null) return global.HC_BY_MO[idx];
    return BOARD_WF_TOTAL_HC[idx] != null ? BOARD_WF_TOTAL_HC[idx] : null;
  }

  function boardNnDrivers(wf, idx) {
    idx = idx == null ? boardCloseIdx() : idx;
    var w = wf ? boardWaterfallMonthM(wf, idx) : null;
    var budByLabel = {
      "New Business": 1.73,
      Expansion: 0.85,
      Reactivation: 0.07,
      Contraction: -0.28,
      Churn: -0.5,
    };
    if (!w) {
      return [
        { label: "New Business", val: 1.92, bud: 1.73, dir: "pos", pct: 72 },
        { label: "Expansion", val: 0.98, bud: 0.85, dir: "pos", pct: 37 },
        { label: "Reactivation", val: 0.095, bud: 0.07, dir: "pos", pct: 10 },
        { label: "Contraction", val: -0.225, bud: -0.28, dir: "pos", pct: 18 },
        { label: "Churn", val: -0.115, bud: -0.5, dir: "pos", pct: 9 },
      ];
    }
    var rows = [
      { label: "New Business", val: w.nb, bud: wfBudgetComponent(wf, "New Business", idx) },
      { label: "Expansion", val: w.exp, bud: wfBudgetComponent(wf, "Expansion", idx) },
      { label: "Reactivation", val: w.react, bud: wfBudgetComponent(wf, "Reactivation", idx) },
      { label: "Contraction", val: w.con, bud: wfBudgetComponent(wf, "Contraction", idx) },
      { label: "Churn", val: w.churn, bud: wfBudgetComponent(wf, "Churn", idx) },
    ];
    rows.forEach(function (r) {
      if (r.bud == null) r.bud = budByLabel[r.label];
      r.dir = "pos";
    });
    var maxPos = 0.01;
    rows.forEach(function (r) {
      if (r.val > 0) maxPos = Math.max(maxPos, Math.abs(r.val));
    });
    rows.forEach(function (r) {
      r.pct = Math.min(100, Math.round((Math.abs(r.val) / maxPos) * 100));
    });
    return rows;
  }

  function boardExecKpis() {
    var wf = boardWfTable();
    var idx = boardCloseIdx();
    var ts = boardTsSource();
    var cm = global.CLOSE_MONTH || "2026-06";
    var isJun = ts && ts.Actual && ts.Actual.is && ts.Actual.is[cm];
    var isBud = ts && ts.Budget && ts.Budget.is && ts.Budget.is[cm];
    var bsJun = ts && ts.Actual && ts.Actual.bs && ts.Actual.bs[cm];
    var bsBud = ts && ts.Budget && ts.Budget.bs && ts.Budget.bs[cm];

    var drivers = boardNnDrivers(wf, idx);
    var nnFromDrivers = drivers.reduce(function (s, d) {
      return s + d.val;
    }, 0);
    var nnBudFromDrivers = drivers.reduce(function (s, d) {
      return s + d.bud;
    }, 0);
    var nn = global.NN_ACT && global.NN_ACT[idx] != null ? global.NN_ACT[idx] : nnFromDrivers;
    var nnBud = nnBudFromDrivers;
    var nnVar = +(nn - nnBud).toFixed(3);

    var arrEop = global.ARR_ACT && global.ARR_ACT[idx];
    var arrBud = global.ARR_BUD && global.ARR_BUD[idx];

    var revAct = isJun && isJun.revenue != null ? isJun.revenue / 1e6 : global.REV_ACT && global.REV_ACT[idx];
    var revBud = isBud && isBud.revenue != null ? isBud.revenue / 1e6 : global.REV_BUD && global.REV_BUD[idx];
    var gpAct = isJun && isJun.gross_profit != null ? isJun.gross_profit / 1e6 : null;
    var gpBud = isBud && isBud.gross_profit != null ? isBud.gross_profit / 1e6 : null;
    var gmAct = isJun && isJun.gm_pct != null ? isJun.gm_pct * 100 : null;
    var gmBud = isBud && isBud.gm_pct != null ? isBud.gm_pct * 100 : null;
    var ebitdaAct =
      isJun && isJun.ebitda != null ? isJun.ebitda / 1e6 : global.EBITDA_ACT && global.EBITDA_ACT[idx];
    var ebitdaBud = isBud && isBud.ebitda != null ? isBud.ebitda / 1e6 : null;
    var cashAct =
      bsJun && bsJun.cash != null
        ? bsJun.cash / 1e6
        : global.CASH_ACT && global.CASH_ACT[idx];
    var cashBud =
      global.CASH_BUD && global.CASH_BUD[idx] != null
        ? global.CASH_BUD[idx]
        : bsBud && bsBud.cash != null
          ? bsBud.cash / 1e6
          : null;

    var drivers = boardNnDrivers(wf, idx);

    return {
      idx: idx,
      nn: nn,
      nnBud: nnBud,
      nnVar: nnVar,
      nnFromDrivers: nnFromDrivers,
      arrEop: arrEop,
      arrBud: arrBud,
      arrVar: arrEop != null && arrBud != null ? arrEop - arrBud : null,
      revAct: revAct,
      revBud: revBud,
      gpAct: gpAct,
      gpBud: gpBud,
      gmAct: gmAct,
      gmBud: gmBud,
      gmVarPp: gmAct != null && gmBud != null ? gmAct - gmBud : null,
      ebitdaAct: ebitdaAct,
      ebitdaBud: ebitdaBud,
      cashAct: cashAct,
      cashBud: cashBud,
      drivers: drivers,
      closeHc: boardCloseHc(),
      hcBud: global.HC_TOTAL_BUD,
    };
  }

  function boardFmtBridge(v) {
    if (v == null || Number.isNaN(v)) return "—";
    var abs = Math.abs(v);
    var neg = v < 0;
    var s = abs >= 1e6 ? (abs / 1e6).toFixed(2) + "M" : abs >= 1e3 ? (abs / 1e3).toFixed(0) + "K" : abs.toFixed(0);
    return (neg ? "-" : "+") + "$" + s;
  }

  function boardCashBridgeHtml(period) {
    var rows = boardCashBridgeRows(period);
    if (!rows.length) return '<div style="color:var(--text3);font-size:11px">Cash bridge unavailable</div>';
    return rows
      .map(function (r) {
        var cls = r.total ? "tot" : r.inflow !== false && r.value >= 0 ? "in" : "out";
        var color = r.total ? "var(--teal)" : r.inflow !== false && r.value >= 0 ? "var(--teal)" : "var(--red)";
        var prefix = r.total ? "" : r.inflow !== false && r.value >= 0 ? "+ " : "– ";
        var val = boardFmtBridge(r.value);
        if (r.total) {
          return (
            '<div class="cash-row tot" style="margin-top:5px"><span>' +
            r.label +
            '</span><span style="font-family:var(--mono);color:' +
            color +
            '">' +
            val +
            "</span></div>"
          );
        }
        return (
          '<div class="cash-row ' +
          cls +
          '"><span style="color:' +
          color +
          '">' +
          prefix +
          r.label.replace(/^[+\-–]\s*/, "") +
          '</span><span style="font-family:var(--mono)">' +
          val +
          "</span></div>"
        );
      })
      .join("");
  }

  function boardJunArrKpis() {
    var wf = boardWfTable();
    var idx = boardCloseIdx();
    var w = wf ? boardWaterfallMonthM(wf, idx) : null;
    var arrEop = global.ARR_ACT && global.ARR_ACT[idx];
    var arrBud = global.ARR_BUD && global.ARR_BUD[idx];
    var nn = global.NN_ACT && global.NN_ACT[idx];
    var nnBud = global.NN_BUD && global.NN_BUD[idx];
    return {
      eop: arrEop,
      eopVar: arrEop != null && arrBud != null ? arrEop - arrBud : null,
      nn: nn,
      nnVar: nn != null && nnBud != null ? nn - nnBud : null,
      nb: w ? w.nb : null,
      exp: w ? w.exp : null,
      bop: w ? w.bop : null,
      eopChart: w ? w.eop : arrEop,
    };
  }

  function boardRevenueKpis() {
    var idx = boardCloseIdx();
    var cm = global.CLOSE_MONTH || "2026-06";
    var ts = boardTsSource();
    var isJun = ts && ts.Actual && ts.Actual.is && ts.Actual.is[cm];
    var isBud = ts && ts.Budget && ts.Budget.is && ts.Budget.is[cm];
    var rev = isJun && isJun.revenue != null ? isJun.revenue / 1e6 : global.REV_ACT && global.REV_ACT[idx];
    var revBud = isBud && isBud.revenue != null ? isBud.revenue / 1e6 : global.REV_BUD && global.REV_BUD[idx];
    var gm = isJun && isJun.gm_pct != null ? isJun.gm_pct * 100 : null;
    var ytdRev = 0;
    var ytdBud = 0;
    if (ts && ts.Actual && ts.Actual.periods) {
      ts.Actual.periods.slice(0, boardActCount()).forEach(function (p) {
        var a = ts.Actual.is[p];
        var b = ts.Budget.is[p];
        if (a && a.revenue != null) ytdRev += a.revenue;
        if (b && b.revenue != null) ytdBud += b.revenue;
      });
    }
    ytdRev = +(ytdRev / 1e6).toFixed(1);
    ytdBud = +(ytdBud / 1e6).toFixed(1);
    var arrEop = global.ARR_ACT && global.ARR_ACT[idx];
    var arrBud = global.ARR_BUD && global.ARR_BUD[idx];
    return {
      rev: rev,
      revBud: revBud,
      revVar: rev != null && revBud != null ? rev - revBud : null,
      ytdRev: ytdRev,
      ytdBud: ytdBud,
      ytdVar: +(ytdRev - ytdBud).toFixed(1),
      gm: gm,
      arrEop: arrEop,
      arrBud: arrBud,
      arrVar: arrEop != null && arrBud != null ? arrEop - arrBud : null,
      nrr: 100.8,
    };
  }

  function boardPlKpis() {
    var idx = boardCloseIdx();
    var cm = global.CLOSE_MONTH || "2026-06";
    var ts = boardTsSource();
    var isJun = ts && ts.Actual && ts.Actual.is && ts.Actual.is[cm];
    var isBud = ts && ts.Budget && ts.Budget.is && ts.Budget.is[cm];
    if (!isJun) {
      return {
        rev: global.REV_ACT && global.REV_ACT[idx],
        revBud: global.REV_BUD && global.REV_BUD[idx],
        gp: global.GP_ACT && global.GP_ACT[idx],
        gpBud: null,
        gm: null,
        opex: null,
        opexBud: null,
        ebitda: global.EBITDA_ACT && global.EBITDA_ACT[idx],
        ebitdaBud: null,
      };
    }
    var rev = isJun.revenue / 1e6;
    var revBud = isBud && isBud.revenue != null ? isBud.revenue / 1e6 : null;
    var gp = isJun.gross_profit / 1e6;
    var gm = isJun.gm_pct != null ? isJun.gm_pct * 100 : null;
    var opex = isJun.total_opex / 1e6;
    var opexBud = isBud && isBud.total_opex != null ? isBud.total_opex / 1e6 : null;
    var sm = isJun.sm / 1e6;
    var smBud = isBud && isBud.sm != null ? isBud.sm / 1e6 : null;
    var rd = isJun.rd / 1e6;
    var rdBud = isBud && isBud.rd != null ? isBud.rd / 1e6 : null;
    var ga = isJun.ga / 1e6;
    var gaBud = isBud && isBud.ga != null ? isBud.ga / 1e6 : null;
    var ebitda = isJun.ebitda / 1e6;
    var ebitdaBud = isBud && isBud.ebitda != null ? isBud.ebitda / 1e6 : null;
    return {
      rev: rev,
      revBud: revBud,
      gp: gp,
      gpBud: isBud ? isBud.gross_profit / 1e6 : null,
      gm: gm,
      opex: opex,
      opexBud: opexBud,
      sm: sm,
      smBud: smBud,
      rd: rd,
      rdBud: rdBud,
      ga: ga,
      gaBud: gaBud,
      ebitda: ebitda,
      ebitdaBud: ebitdaBud,
    };
  }

  function boardValidate() {
    var errors = [];
    var idx = boardCloseIdx();
    var actN = boardActCount();
    var ts = boardTsSource();
    var cm = global.CLOSE_MONTH || "2026-06";
    var cfs = ts && ts.Actual && ts.Actual.cfs && ts.Actual.cfs[cm];

    ["ARR_ACT", "NN_ACT", "NN_BUD", "CASH_ACT", "CASH_BUD", "REV_ACT", "GP_ACT", "COLL"].forEach(function (key) {
      var arr = global[key];
      if (!arr || arr.length < actN) errors.push(key + " missing or short (len=" + (arr ? arr.length : 0) + ", need " + actN + ")");
    });

    if (global.NN_ACT && global.NN_ACT[idx] <= 0) errors.push("NN_ACT Jun must be > 0");
    if (global.CASH_ACT && global.CASH_ACT[idx] <= 0) errors.push("CASH_ACT Jun must be > 0");

    if (cfs) {
      var net = cfs.net_change != null ? cfs.net_change : cfs.net_change_cash;
      if (net != null && cfs.ending_cash != null && cfs.beginning_cash != null) {
        var diff = Math.abs(cfs.ending_cash - cfs.beginning_cash - net);
        if (diff > 1) errors.push("CFS net_change does not tie beginning→ending (diff $" + diff + ")");
      }
    }

    var fmt = boardFmtM(86.1, 1);
    if (fmt !== "$86.1M") errors.push("boardFmtM broken: got " + fmt);
    if (boardFmtVarM(0.58, 1) !== "+$0.6M" && boardFmtVarM(0.58, 1) !== "+$0.58M") {
      errors.push("boardFmtVarM broken: got " + boardFmtVarM(0.58, 1));
    }

    var bridge = boardCashBridgeRows(cm);
    var netRow = bridge.filter(function (r) {
      return r.cfsTie || (r.label && r.label.indexOf("Net change") >= 0);
    }).pop();
    if (cfs && netRow && cfs.net_change != null && Math.abs(netRow.value - cfs.net_change) > 1) {
      errors.push("Cash bridge net change does not tie CFS ($" + netRow.value + " vs $" + cfs.net_change + ")");
    }

    return { ok: errors.length === 0, errors: errors };
  }

  function boardPatchChart(cfg) {
    return global.SMPLSkin && global.SMPLSkin.patchChartCfg ? global.SMPLSkin.patchChartCfg(cfg) : cfg;
  }

  function boardMkChart(elOrId, cfg) {
    var el = typeof elOrId === "string" ? document.getElementById(elOrId) : elOrId;
    if (!el) return null;
    if (typeof global.Chart !== "function") {
      console.warn("[board] Chart.js not loaded — charts will be empty");
      return null;
    }
    try {
      var existing = global.Chart.getChart(el);
      if (existing) existing.destroy();
      return new global.Chart(el, boardPatchChart(cfg));
    } catch (err) {
      console.error("[board] chart build failed", el.id || el, err);
      return null;
    }
  }

  global.SMPLBoardData = {
    boardTsSource: boardTsSource,
    boardWfTable: boardWfTable,
    boardRefreshAllSeries: boardRefreshAllSeries,
    boardWaterfallMonthM: boardWaterfallMonthM,
    boardArrTableMeta: boardArrTableMeta,
    boardArrPeriodLabel: boardArrPeriodLabel,
    boardCashBridgeRows: boardCashBridgeRows,
    boardCashBridgeHtml: boardCashBridgeHtml,
    boardJunArrKpis: boardJunArrKpis,
    boardExecKpis: boardExecKpis,
    boardNnDrivers: boardNnDrivers,
    boardCloseHc: boardCloseHc,
    boardFmtM: boardFmtM,
    boardFmtM1: boardFmtM1,
    boardFmtVarM: boardFmtVarM,
    boardPlKpis: boardPlKpis,
    boardRevenueKpis: boardRevenueKpis,
    boardValidate: boardValidate,
    boardMkChart: boardMkChart,
    boardPatchChart: boardPatchChart,
    boardActCount: boardActCount,
    BOARD_WF_TOTAL_HC: BOARD_WF_TOTAL_HC,
  };

  global.boardRefreshAllSeries = boardRefreshAllSeries;
  global.boardMkChart = boardMkChart;
  global.boardCashBridgeHtml = boardCashBridgeHtml;
  global.boardJunArrKpis = boardJunArrKpis;
  global.boardExecKpis = boardExecKpis;
  global.boardCloseHc = boardCloseHc;
  global.boardFmtM = boardFmtM;
  global.boardFmtVarM = boardFmtVarM;
  global.boardPlKpis = boardPlKpis;
  global.boardRevenueKpis = boardRevenueKpis;
  global.boardValidate = boardValidate;
  global.boardArrPeriodLabel = boardArrPeriodLabel;
  global.boardArrTableMeta = boardArrTableMeta;
  global.boardWaterfallMonthM = boardWaterfallMonthM;
  global.boardWfTable = boardWfTable;
})(typeof window !== "undefined" ? window : globalThis);
