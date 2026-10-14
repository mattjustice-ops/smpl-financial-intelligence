/**
 * Shared warehouse outlook hydration for Board Platform + Forecast Engine iframes.
 * Both surfaces must apply the same payload shape from build_unified_outlook_payload().
 */
(function (global) {
  "use strict";

  var _hydrateSeq = 0;
  var _hydrateAbort = null;
  var _pendingOrgWait = null;

  function monthLabel(period) {
    if (!period || period.length < 7) return period || "";
    var names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var m = parseInt(period.slice(5, 7), 10) - 1;
    return (names[m] || period.slice(5, 7)) + " " + period.slice(0, 4);
  }

  function resolveOrgIdFromQuery() {
    var q = new URLSearchParams(global.location.search);
    return q.get("organization_id") || null;
  }

  async function resolveOrgId(options) {
    options = options || {};
    var fromQuery = resolveOrgIdFromQuery();
    var sessionOrgs = null;
    var signedOut = false;
    try {
      var res = await fetch("/api/auth/session", { credentials: "include" });
      if (res.ok) {
        var j = await res.json();
        if (!j || !j.user) signedOut = true;
        if (j && j.user) {
          sessionOrgs = {
            activeId: j.user.activeOrganizationId || null,
            orgIds: (j.user.organizations || [])
              .map(function (o) {
                return o.organizationId;
              })
              .filter(Boolean),
          };
        }
      }
    } catch (_) {}

    function pick(preferred) {
      if (!sessionOrgs || !sessionOrgs.orgIds.length) return preferred || null;
      if (preferred && sessionOrgs.orgIds.indexOf(preferred) >= 0) return preferred;
      if (sessionOrgs.activeId && sessionOrgs.orgIds.indexOf(sessionOrgs.activeId) >= 0) {
        return sessionOrgs.activeId;
      }
      return sessionOrgs.orgIds[0];
    }

    if (fromQuery) return pick(fromQuery);
    if (global.SMPL_ORG_ID) return pick(global.SMPL_ORG_ID);
    if (signedOut) return null;

    if (options.waitForParent !== false) {
      var waited = await waitForParentOrg(options.parentWaitMs || 4000);
      if (waited) return pick(waited);
    }

    return pick(null);
  }

  function waitForParentOrg(timeoutMs) {
    if (global.SMPL_ORG_ID) return Promise.resolve(global.SMPL_ORG_ID);
    if (_pendingOrgWait) return _pendingOrgWait;

    _pendingOrgWait = new Promise(function (resolve) {
      var done = false;
      function finish(value) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        global.removeEventListener("message", onMessage);
        _pendingOrgWait = null;
        resolve(value || null);
      }

      function onMessage(event) {
        if (event.origin !== global.location.origin) return;
        var data = event.data;
        if (!data || data.type !== "smpl:org" || !data.organizationId) return;
        global.SMPL_ORG_ID = data.organizationId;
        finish(data.organizationId);
      }

      var timer = setTimeout(function () {
        finish(global.SMPL_ORG_ID || null);
      }, timeoutMs);

      global.addEventListener("message", onMessage);
      if (global.parent && global.parent !== global) {
        global.parent.postMessage({ type: "smpl:iframe-ready" }, global.location.origin);
      }
    });

    return _pendingOrgWait;
  }

  global.addEventListener("message", function (event) {
    if (event.origin !== global.location.origin) return;
    var data = event.data;
    if (!data || !data.type) return;
    if (data.type === "smpl:org" && data.organizationId) {
      global.SMPL_ORG_ID = data.organizationId;
      if (typeof global.SMPL_ON_ORG_READY === "function") {
        global.SMPL_ON_ORG_READY(data.organizationId);
      }
    }
  });

  function outlookPayloadValid(data) {
    if (!data || !data.meta || !data.meta.close_month) return false;
    var wf = data.ARR_WATERFALL;
    if (!wf || !Array.isArray(wf.Ending)) return false;
    var year = data.meta.close_month.slice(0, 4);
    var idx = parseInt(data.meta.close_month.slice(5, 7), 10) - 1;
    if (idx < 0 || idx >= wf.Ending.length) return true;
    var ending = wf.Ending[idx];
    if (ending == null) {
      console.warn("[smpl-outlook] Rejected payload: close month ending ARR missing", data.meta.close_month);
      return false;
    }
    if (String(data.meta.start_period || "").slice(0, 4) === year && wf.Beginning && wf.Beginning[0] == null) {
      console.warn("[smpl-outlook] Rejected payload: missing Jan beginning ARR");
      return false;
    }
    return true;
  }

  function buildOutlookFetchUrl(endpoint, params) {
    var path =
      endpoint.slice(-7) === "/outlook" || endpoint.slice(-7) === "outlook"
        ? "/api/v1/" + endpoint.replace(/\/$/, "")
        : "/api/v1/" + endpoint + "/payload";
    return path + "?" + params.toString();
  }

  function getArrFromWaterfall(wf, period, allPeriods) {
    if (!wf || !wf.Ending || !allPeriods) return null;
    var i = allPeriods.indexOf(period);
    if (i < 0) return null;
    var bop = wf.Beginning[i];
    var nb = wf["New Business"][i];
    var exp = wf.Expansion[i];
    var react = wf.Reactivation[i];
    var cont = wf.Contraction[i];
    var churn = wf.Churn[i];
    var eop = wf.Ending[i];
    if (bop == null && eop == null) return null;
    var retained = [exp, react, cont, churn].every(function (v) { return v != null; });
    return {
      arr_bop: bop,
      arr_nb: nb,
      arr_exp: exp,
      arr_react: react,
      arr_cont: cont == null ? null : Math.abs(cont),
      arr_nr_churn: churn == null ? null : Math.abs(churn),
      ren_churn: null,
      arr_eop: eop,
      nrr: bop && retained ? (bop + exp + react + cont + churn) / bop : null,
      grr: bop && cont != null && churn != null ? (bop + cont + churn) / bop : null,
    };
  }

  /**
   * Per-scenario period blocks: statements, GL opex detail ("line|department|account" → amount), opex and
   * cost of revenue by GL expense type ("line|department|expense_type" → amount) and the marketing program
   * accounts (expense type "Marketing Programs").
   */
  var TS_BLOCKS = ["is", "cfs", "bs", "gl_opex", "gl_expense_types", "gl_programs"];

  /** Live replace: demo keys the warehouse did not send are removed, never kept. */
  function replaceArrWaterfallTable(WF_TABLE, incoming) {
    if (!incoming || !WF_TABLE) return;
    Object.keys(WF_TABLE).forEach(function (key) {
      if (!Array.isArray(incoming[key])) delete WF_TABLE[key];
    });
    Object.keys(incoming).forEach(function (key) {
      if (Array.isArray(incoming[key])) {
        WF_TABLE[key] = incoming[key].slice();
      }
    });
  }

  /** Live replace: every demo scenario/period is cleared before the warehouse rows land. */
  function replaceTsData(target, incoming, closeMonth) {
    if (!incoming || !target) return;
    Object.keys(target).forEach(function (sc) {
      delete target[sc];
    });
    ["Actual", "Forecast", "Budget"].forEach(function (sc) {
      target[sc] = { periods: [], is: {}, bs: {}, cfs: {}, gl_opex: {}, gl_expense_types: {}, gl_programs: {} };
    });
    mergeTsData(target, incoming, closeMonth);
  }

  function replaceSrcBlock(target, incoming) {
    Object.keys(target).forEach(function (k) {
      delete target[k];
    });
    if (incoming) Object.assign(target, JSON.parse(JSON.stringify(incoming)));
  }

  /**
   * Merge warehouse payload into embedded demo TS_DATA.
   * Periods present in the live payload replace the whole row (no field-level
   * Object.assign) so demo cells cannot survive a partial production hydrate.
   */
  function mergeTsData(target, incoming, closeMonth) {
    if (!incoming || !target) return target;
    ["Actual", "Forecast", "Budget"].forEach(function (sc) {
      if (!incoming[sc]) return;
      if (!target[sc]) target[sc] = {};
      if (Array.isArray(incoming[sc].periods) && incoming[sc].periods.length) {
        target[sc].periods = incoming[sc].periods.slice();
      }
      TS_BLOCKS.forEach(function (stmt) {
        if (!incoming[sc][stmt]) return;
        if (!target[sc][stmt]) target[sc][stmt] = {};
        Object.keys(incoming[sc][stmt]).forEach(function (period) {
          var row = incoming[sc][stmt][period];
          if (!row || typeof row !== "object") return;
          var hasValue = Object.keys(row).some(function (k) {
            return row[k] != null;
          });
          if (!hasValue) return;
          // Full row replace — never merge demo fields into live period rows.
          target[sc][stmt][period] = JSON.parse(JSON.stringify(row));
        });
      });
    });
    var asOf = closeMonth || getActiveCloseMonth(null);
    pruneDemoActualResidue(target, incoming, asOf);
    pruneDemoPlanResidue(target, incoming, asOf);
    return target;
  }

  /** Collect period keys that have at least one non-null cell across IS/BS/CFS. */
  function collectPopulatedScenarioPeriods(scenarioBlock) {
    var livePeriods = {};
    if (!scenarioBlock) return livePeriods;
    ["is", "cfs", "bs"].forEach(function (stmt) {
      var block = scenarioBlock[stmt];
      if (!block) return;
      Object.keys(block).forEach(function (period) {
        var row = block[period];
        if (!row || typeof row !== "object") return;
        var hasValue = Object.keys(row).some(function (k) {
          return row[k] != null;
        });
        if (hasValue) livePeriods[period] = true;
      });
    });
    return livePeriods;
  }

  /**
   * When live Actual has at least one populated closed period, drop demo Actual
   * rows for other closed periods that the warehouse did not send. Prevents
   * demo residue after a successful (even partial) production hydrate.
   * Does not reseed demo; only deletes stale closed Actual cells.
   */
  function pruneDemoActualResidue(target, incoming, closeMonth) {
    if (!target || !incoming || !closeMonth) return;
    var livePeriods = collectPopulatedScenarioPeriods(incoming.Actual);
    if (!Object.keys(livePeriods).length) return;
    if (!target.Actual) return;
    TS_BLOCKS.forEach(function (stmt) {
      var block = target.Actual[stmt];
      if (!block) return;
      Object.keys(block).forEach(function (period) {
        if (period <= closeMonth && !livePeriods[period]) {
          delete block[period];
        }
      });
    });
  }

  /**
   * Forecast / Budget forward-period residue prune (conservative).
   *
   * When live Forecast (resp. Budget) has ≥1 populated period, drop target
   * periods for that scenario with period > closeMonth that the warehouse
   * omitted. Empty live Forecast/Budget does not wipe demo scaffolding.
   *
   * Closed-month (≤ closeMonth) plan cells are left alone — warehouse often
   * omits historical Budget/Forecast for closed months; pruning those would
   * risk wiping valid demo overlays incorrectly.
   */
  function pruneDemoPlanResidue(target, incoming, closeMonth) {
    if (!target || !incoming || !closeMonth) return;
    ["Forecast", "Budget"].forEach(function (sc) {
      var livePeriods = collectPopulatedScenarioPeriods(incoming[sc]);
      if (!Object.keys(livePeriods).length) return;
      if (!target[sc]) return;
      TS_BLOCKS.forEach(function (stmt) {
        var block = target[sc][stmt];
        if (!block) return;
        Object.keys(block).forEach(function (period) {
          if (period > closeMonth && !livePeriods[period]) {
            delete block[period];
          }
        });
      });
    });
  }

  /** Hydrated close; before hydrate, the last Actual period of the loaded data. */
  function getActiveCloseMonth(fallback) {
    return global.SMPL_CLOSE_MONTH || global.CLOSE_MONTH || dataCloseMonth() || fallback || null;
  }

  function dataCloseMonth() {
    var ts = getOutlookTsData();
    var periods = ts && ts.Actual && ts.Actual.periods;
    return periods && periods.length ? periods[periods.length - 1] : null;
  }

  function isLiveOutlook() {
    return Boolean(global.SMPL_LIVE_OUTLOOK && global.SMPL_TS_DATA);
  }

  function registerDemoData(tsData, wfTable) {
    if (tsData) global.SMPL_DEMO_TS_DATA = tsData;
    if (wfTable) global.SMPL_DEMO_WF_TABLE = wfTable;
  }

  /** Live warehouse payload when hydrated; otherwise shared demo seed (Board + Forecast). */
  function getOutlookTsData() {
    // After live hydrate, demo object is the merge target but closed Actual
    // residue is pruned — prefer it so Board/FE share one post-hydrate object.
    // Before hydrate (or offline), fall back to embedded demo / live snapshot.
    if (global.SMPL_DEMO_TS_DATA) return global.SMPL_DEMO_TS_DATA;
    if (isLiveOutlook()) return global.SMPL_TS_DATA;
    return null;
  }

  function getOutlookWfTable() {
    if (isLiveOutlook() && global.SMPL_ARR_WATERFALL) return global.SMPL_ARR_WATERFALL;
    return global.SMPL_DEMO_WF_TABLE || null;
  }

  function scenarioForPeriod(period, closeMonth) {
    return period > closeMonth ? "Forecast" : "Actual";
  }

  function tsGetRow(period, stmt, closeMonth) {
    return getCombinedTsRow(period, stmt, closeMonth);
  }

  function getCombinedTsRow(period, stmt, closeMonth) {
    var ts = getOutlookTsData();
    if (!ts) return null;
    var asOf = closeMonth || getActiveCloseMonth(period);
    if (!asOf) return null;
    var scenario = scenarioForPeriod(period, asOf);
    return (ts[scenario] && ts[scenario][stmt] && ts[scenario][stmt][period]) || null;
  }

  function getCashBridgeRow(period, scenario, closeMonth) {
    var bridge = global.SMPL_CASH_BRIDGE || (global.SMPL_OUTLOOK_PAYLOAD && global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE);
    if (!bridge) return null;
    var asOf = closeMonth || getActiveCloseMonth();
    if (!scenario && !asOf) return null;
    var sc = scenario || scenarioForPeriod(period, asOf);
    return (bridge[sc] && bridge[sc][period]) || null;
  }

  function getCombinedArr(period, allPeriods, closeMonth) {
    var wf = getOutlookWfTable();
    if (!wf || !allPeriods) return null;
    return getArrFromWaterfall(wf, period, allPeriods);
  }

  function tsGetValue(period, stmt, key, closeMonth) {
    var row = tsGetRow(period, stmt, closeMonth);
    if (!row || row[key] == null) return null;
    return row[key];
  }

  function enrichIsRow(row) {
    if (!row) return null;
    var out = Object.assign({}, row);
    if (out.total_opex == null && out.sm != null && out.rd != null && out.ga != null) {
      out.total_opex = out.sm + out.rd + out.ga;
    }
    return out;
  }

  function getWarehouseIS(period, allPeriods, closeMonth) {
    void allPeriods;
    return enrichIsRow(getCombinedTsRow(period, "is", closeMonth));
  }

  /** GL opex detail for the period (Actual through close, Forecast after): {"line|department|account": amount}. */
  function getWarehouseGlOpex(period, closeMonth) {
    return getCombinedTsRow(period, "gl_opex", closeMonth);
  }

  /** GL opex and cost of revenue by expense type (Actual through close, Forecast after): {"line|department|expense_type": amount}. */
  function getWarehouseGlExpenseTypes(period, closeMonth) {
    return getCombinedTsRow(period, "gl_expense_types", closeMonth);
  }

  /** GL marketing program accounts for the period: {"line|department|account": amount}. */
  function getWarehouseGlPrograms(period, closeMonth) {
    return getCombinedTsRow(period, "gl_programs", closeMonth);
  }

  /** A loaded statement row ("is", "bs", "cfs") for any month: the HISTORY block, then Actual through close / Forecast after. */
  function getLoadedStatementRow(period, stmt, closeMonth) {
    var h = global.SMPL_HISTORY;
    if (h && h[stmt] && h[stmt][period]) return h[stmt][period];
    return getCombinedTsRow(period, stmt, closeMonth);
  }

  function mapCfsForForecast(row) {
    if (!row) return null;
    return {
      beg_cash: row.beginning_cash,
      ni: row.net_income,
      da: row.da,
      sbc: row.sbc,
      chg_ar: row.chg_ar,
      chg_dr: row.chg_dr,
      chg_ap: row.chg_ap,
      chg_pre: row.chg_prepaids,
      cfo: row.cfo,
      capex: row.capex,
      cfi: row.cfi,
      cff: row.cff,
      net_change: row.net_change,
      end_cash: row.ending_cash,
    };
  }

  function getWarehouseCFS(period, allPeriods, closeMonth) {
    void allPeriods;
    return mapCfsForForecast(getCombinedTsRow(period, "cfs", closeMonth));
  }

  /** Sum of the loaded liability lines; null when any line is missing. */
  function sumBsLiabilities(row, deferredRev, otherLiab) {
    var parts = [row.ap, deferredRev, row.debt, otherLiab];
    if (parts.some(function (v) { return v == null; })) return null;
    return parts.reduce(function (s, v) { return s + v; }, 0);
  }

  function getWarehouseBS(period, allPeriods, closeMonth) {
    void allPeriods;
    var row = getCombinedTsRow(period, "bs", closeMonth);
    if (!row) return null;
    var deferredRev = row.deferred_rev != null ? row.deferred_rev : row.dr;
    var otherLiab = row.other_liabilities != null ? row.other_liabilities : row.other_liab;
    var totalLiab = row.total_liabilities != null ? row.total_liabilities : row.total_liab;
    if (totalLiab == null) {
      totalLiab = sumBsLiabilities(row, deferredRev, otherLiab);
    }
    var totalLe = row.total_le;
    if (totalLe == null && totalLiab != null && row.equity != null) {
      totalLe = totalLiab + row.equity;
    }
    return {
      cash: row.cash,
      ar: row.ar,
      ppe: row.ppe != null ? row.ppe : row.property_and_equipment_net,
      prepaids: row.prepaids != null ? row.prepaids : row.prepaids_and_other_current_assets,
      prepaids_and_other_current_assets: row.prepaids_and_other_current_assets != null
        ? row.prepaids_and_other_current_assets
        : row.prepaids,
      property_and_equipment_net: row.property_and_equipment_net != null
        ? row.property_and_equipment_net
        : row.ppe,
      total_assets: row.total_assets,
      ap: row.ap,
      deferred_rev: deferredRev,
      dr: deferredRev,
      debt: row.debt,
      other_liab: otherLiab,
      total_liab: totalLiab,
      total_liabilities: totalLiab,
      total_le: totalLe,
      equity: row.equity,
    };
  }

  function mergeTsScenario(target, incoming) {
    if (!incoming) return;
    if (Array.isArray(incoming.periods) && incoming.periods.length) {
      target.periods = incoming.periods.slice();
    }
    TS_BLOCKS.forEach(function (stmt) {
      if (!incoming[stmt]) return;
      target[stmt] = target[stmt] || {};
      Object.keys(incoming[stmt]).forEach(function (period) {
        var row = incoming[stmt][period];
        if (!row) return;
        var hasValue = Object.keys(row).some(function (k) {
          return row[k] != null;
        });
        if (!hasValue) return;
        // Full row replace (same contract as mergeTsData).
        target[stmt][period] = JSON.parse(JSON.stringify(row));
      });
    });
  }

  function replaceActuals(target, incoming) {
    if (!incoming) return;
    Object.keys(incoming).forEach(function (period) {
      var row = incoming[period];
      if (!row) return;
      target[period] = JSON.parse(JSON.stringify(row));
    });
  }

  /** Replace whole SRC.actuals period rows; prune closed periods warehouse omitted. */
  function mergeActuals(target, incoming, closeMonth) {
    if (!incoming) return;
    Object.keys(incoming).forEach(function (period) {
      var row = incoming[period];
      if (!row) return;
      var hasValue = Object.keys(row).some(function (k) {
        return row[k] != null;
      });
      if (!hasValue) return;
      // Full replace — do not Object.assign demo fields onto live periods.
      target[period] = JSON.parse(JSON.stringify(row));
    });
    pruneSrcActualResidue(target, incoming, closeMonth || getActiveCloseMonth(null));
  }

  function pruneSrcActualResidue(target, incoming, closeMonth) {
    if (!target || !incoming || !closeMonth) return;
    var livePeriods = {};
    Object.keys(incoming).forEach(function (period) {
      var row = incoming[period];
      if (!row) return;
      var hasValue = Object.keys(row).some(function (k) {
        return row[k] != null;
      });
      if (hasValue) livePeriods[period] = true;
    });
    if (!Object.keys(livePeriods).length) return;
    Object.keys(target).forEach(function (period) {
      if (period <= closeMonth && !livePeriods[period]) {
        delete target[period];
      }
    });
  }

  function getOutlookYearPeriods(data) {
    var close = (data.meta && data.meta.close_month) || getActiveCloseMonth();
    if (!close) return [];
    var year = String(close).slice(0, 4);
    return Array.from({ length: 12 }, function (_, i) {
      return year + "-" + String(i + 1).padStart(2, "0");
    });
  }

  function getDecemberSnapshot(allPeriods) {
    if (!allPeriods || !allPeriods.length || !getOutlookTsData()) return null;
    var dec = allPeriods[allPeriods.length - 1];
    var closeMonth = getActiveCloseMonth();
    if (!closeMonth) return null;
    var arr = getCombinedArr(dec, allPeriods, closeMonth);
    var is = getCombinedTsRow(dec, "is", closeMonth);
    var cfs = mapCfsForForecast(getCombinedTsRow(dec, "cfs", closeMonth));
    var bs = getCombinedTsRow(dec, "bs", closeMonth);
    return {
      period: dec,
      arr_eop: arr && arr.arr_eop,
      revenue: is && is.revenue,
      ending_cash: cfs && cfs.end_cash,
      total_assets: bs && bs.total_assets,
      cash: bs && bs.cash,
      total_liabilities: bs && (bs.total_liabilities != null ? bs.total_liabilities : bs.total_liab),
      equity: bs && bs.equity,
    };
  }

  function logDecemberAlignment(allPeriods) {
    var snap = getDecemberSnapshot(allPeriods);
    if (!snap) return;
    console.info("[smpl-outlook] December warehouse snapshot (Board + Forecast should match):", snap);
  }

  function buildAlignmentReport(allPeriods, closeMonth) {
    allPeriods = allPeriods || getOutlookYearPeriods({ meta: { close_month: closeMonth } });
    closeMonth = closeMonth || getActiveCloseMonth();
    if (!closeMonth || !allPeriods.length) return null;
    var dec = allPeriods[allPeriods.length - 1];
    var decArr = getCombinedArr(dec, allPeriods, closeMonth);
    var mismatches = [];
    allPeriods.forEach(function (p) {
      var is = getCombinedTsRow(p, "is", closeMonth);
      if (!is || is.net_income == null) {
        mismatches.push({ period: p, field: "net_income", issue: "missing" });
      }
    });
    return {
      closeMonth: closeMonth,
      live: isLiveOutlook(),
      dec: {
        arr_eop: decArr && decArr.arr_eop,
        revenue: (getCombinedTsRow(dec, "is", closeMonth) || {}).revenue,
        net_income: (getCombinedTsRow(dec, "is", closeMonth) || {}).net_income,
        ending_cash: (mapCfsForForecast(getCombinedTsRow(dec, "cfs", closeMonth)) || {}).end_cash,
        total_assets: (getCombinedTsRow(dec, "bs", closeMonth) || {}).total_assets,
      },
      actualNetIncome: allPeriods
        .filter(function (p) {
          return p <= closeMonth;
        })
        .map(function (p) {
          var row = getCombinedTsRow(p, "is", closeMonth) || {};
          return { period: p, net_income: row.net_income };
        }),
      mismatches: mismatches,
    };
  }

  function applyOutlook(data, hooks) {
    hooks = hooks || {};
    if (!outlookPayloadValid(data)) return false;

    if (data.meta && data.meta.close_month) {
      global.SMPL_CLOSE_MONTH = data.meta.close_month;
      global.CLOSE_MONTH = data.meta.close_month;
    }

    global.SMPL_OUTLOOK_PAYLOAD = data;
    global.SMPL_ARR_WATERFALL = data.ARR_WATERFALL || null;
    // Stamp period labels onto the waterfall so consumers index Beginning[i] correctly
    // even when the array spans a fiscal range that is not "Jan..Dec of close year".
    if (global.SMPL_ARR_WATERFALL && data.meta && data.meta.start_period && data.meta.end_period) {
      var stamped = [];
      var sp = String(data.meta.start_period).split("-");
      var ep = String(data.meta.end_period).split("-");
      var y = parseInt(sp[0], 10);
      var m = parseInt(sp[1], 10);
      var ey = parseInt(ep[0], 10);
      var em = parseInt(ep[1], 10);
      while (y < ey || (y === ey && m <= em)) {
        stamped.push(y + "-" + String(m).padStart(2, "0"));
        m += 1;
        if (m > 12) {
          m = 1;
          y += 1;
        }
        if (stamped.length > 36) break;
      }
      if (stamped.length && (!global.SMPL_ARR_WATERFALL.periods || !global.SMPL_ARR_WATERFALL.periods.length)) {
        global.SMPL_ARR_WATERFALL.periods = stamped;
      }
    }
    global.SMPL_BASELINE_ENGINE = data.baseline_engine || null;
    global.SMPL_HISTORY = data.HISTORY || null;
    global.SMPL_TS_DATA = data.TS_DATA || null;
    global.SMPL_CASH_BRIDGE = data.CASH_BRIDGE || null;
    global.SMPL_RISK_POLICY = data.RISK_POLICY || null;
    global.SMPL_LIVE_OUTLOOK = true;

    var closeMonth =
      (data.meta && data.meta.close_month) || getActiveCloseMonth(null);

    if (hooks.TS_DATA && data.TS_DATA) {
      replaceTsData(hooks.TS_DATA, data.TS_DATA, closeMonth);
    }

    if (hooks.WF_TABLE && data.ARR_WATERFALL) {
      replaceArrWaterfallTable(hooks.WF_TABLE, data.ARR_WATERFALL);
    }

    if (hooks.SRC) {
      var src = data.SRC || {};
      hooks.SRC.actuals = hooks.SRC.actuals || {};
      replaceSrcBlock(hooks.SRC.actuals, src.actuals);
      hooks.SRC.opp_pipeline = src.opp_pipeline ? JSON.parse(JSON.stringify(src.opp_pipeline)) : {};
      hooks.SRC.gtm = src.gtm || null;
      hooks.SRC.pipeline_book = src.pipeline_book ? JSON.parse(JSON.stringify(src.pipeline_book)) : {};
      hooks.SRC.implementation_fees = src.implementation_fees ? Object.assign({}, src.implementation_fees) : {};
      // Signed-out demo blocks must not survive a live load.
      ["renewals", "dr_waterfall", "opening_bs"].forEach(function (key) {
        hooks.SRC[key] = src[key] ? JSON.parse(JSON.stringify(src[key])) : {};
      });
    }

    if (hooks.TS_DATA && global.SMPL_DEMO_TS_DATA === hooks.TS_DATA) {
      registerDemoData(hooks.TS_DATA, global.SMPL_DEMO_WF_TABLE);
    }

    if (hooks.ARR_ACT && data.ARR_WATERFALL && data.ARR_WATERFALL.Ending && hooks.actMonthsCount) {
      data.ARR_WATERFALL.Ending.forEach(function (v, i) {
        if (i < hooks.actMonthsCount && v != null) {
          hooks.ARR_ACT[i] = +(v / 1e6).toFixed(2);
        }
      });
    }

    return true;
  }

  async function fetchOutlook(orgId, endpoint, query) {
    if (_hydrateAbort) _hydrateAbort.abort();
    _hydrateAbort = new AbortController();
    var seq = ++_hydrateSeq;

    var params = new URLSearchParams(query || {});
    params.set("organization_id", orgId);
    var url = buildOutlookFetchUrl(endpoint, params);
    var res = await fetch(url, {
      credentials: "include",
      signal: _hydrateAbort.signal,
    });

    if (seq !== _hydrateSeq) {
      return { stale: true, data: null, ok: false };
    }

    if (!res.ok) {
      return { stale: false, data: null, ok: false, status: res.status, body: await res.text() };
    }

    return { stale: false, data: await res.json(), ok: true, url: url };
  }

  /**
   * Signed-in users must only ever see warehouse numbers. While the warehouse
   * loads, or when it cannot be loaded, the page body is covered so embedded
   * demo values are never visible to an organization.
   */
  function setLiveCover(state, detail) {
    if (!global.document || !global.document.body) return;
    var doc = global.document;
    var el = doc.getElementById("smpl-live-cover");
    if (state === "hidden") {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = doc.createElement("div");
      el.id = "smpl-live-cover";
      el.setAttribute("role", "status");
      el.style.cssText =
        "position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;" +
        "background:var(--bg,#0b0f14);color:var(--text,#e6edf3);font:14px/1.5 system-ui,sans-serif;text-align:center;padding:24px";
      doc.body.appendChild(el);
    }
    if (state === "loading") {
      el.innerHTML = '<div><div style="font-weight:600">Loading live data…</div></div>';
      return;
    }
    el.innerHTML =
      '<div style="max-width:440px"><div style="font-weight:600;font-size:16px;margin-bottom:6px">Live data unavailable</div>' +
      "<div>We couldn't load your organization's data from the warehouse, so no numbers are shown. " +
      "Nothing here is estimated or filled in.</div>" +
      (detail ? '<div style="opacity:.7;margin-top:8px;font-size:12px">' + detail + "</div>" : "") +
      '<button type="button" style="margin-top:14px;padding:6px 14px;cursor:pointer" onclick="location.reload()">Retry</button></div>';
  }

  function liveFailed(config, statusText, detail) {
    global.SMPL_LIVE_OUTLOOK = false;
    global.SMPL_LIVE_FAILED = true;
    setLiveCover("error", detail);
    if (config.onStatus) config.onStatus(statusText, "warn");
    return false;
  }

  async function hydrate(config) {
    config = config || {};
    setLiveCover("loading");
    var orgId = await resolveOrgId(config);
    if (!orgId) {
      setLiveCover("hidden");
      if (config.onStatus) config.onStatus("Demo data (sign in for live)", "warn");
      return false;
    }

    if (config.onStatus) config.onStatus("Syncing live warehouse…", "warn");

    try {
      var result = await fetchOutlook(orgId, config.endpoint, config.query);
      if (result.stale) return false;
      if (!result.ok) {
        console.warn("[smpl-outlook] hydrate failed", result.status, result.body);
        return liveFailed(
          config,
          "Live data unavailable (API " + (result.status || "?") + ")",
          "Warehouse request failed (HTTP " + (result.status || "?") + ").",
        );
      }

      var applied = applyOutlook(result.data, config.hooks || {});
      if (!applied) {
        return liveFailed(
          config,
          "Live data unavailable (incomplete warehouse)",
          "The warehouse response was missing required data (close month or ARR waterfall).",
        );
      }

      if (config.onApplied) {
        try {
          config.onApplied(result.data);
        } catch (applyErr) {
          console.warn("[smpl-outlook] onApplied error", applyErr);
        }
      }
      if (result.url) console.info("[smpl-outlook] live data loaded from", result.url);
      var periods = getOutlookYearPeriods(result.data);
      logDecemberAlignment(periods);
      console.info("[smpl-outlook] alignment report", buildAlignmentReport(periods, result.data.meta && result.data.meta.close_month));
      if (config.onStatus) {
        var orgName = result.data.meta && result.data.meta.organization_name;
        var forecastLabel = result.data.meta && result.data.meta.active_forecast_version_name;
        var label = orgName
          ? "Live · " + orgName + (forecastLabel ? " · " + forecastLabel : "")
          : "Live warehouse";
        config.onStatus(label, "ok");
      }
      setLiveCover("hidden");
      return true;
    } catch (err) {
      if (err && err.name === "AbortError") return false;
      console.warn("[smpl-outlook] hydrate error", err);
      return liveFailed(config, "Live data unavailable (offline)", "The warehouse could not be reached.");
    }
  }

  /**
   * One prior calendar year from the loaded HISTORY block: twelve monthly values per metric,
   * null where nothing is loaded. Null when the year is outside the block.
   */
  function getHistoryYear(year) {
    var h = global.SMPL_HISTORY;
    if (!h || !h.start_period || !h.end_period) return null;
    var periods = [];
    for (var i = 1; i <= 12; i++) periods.push(year + "-" + String(i).padStart(2, "0"));
    if (periods[11] < h.start_period || periods[0] > h.end_period) return null;
    function row(block, p) {
      return h[block] && h[block][p] ? h[block][p] : null;
    }
    function num(v) {
      return v == null || v === "" ? null : Number(v);
    }
    function field(block, key) {
      return periods.map(function (p) {
        var r = row(block, p);
        return r ? num(r[key]) : null;
      });
    }
    return {
      periods: periods,
      eop: field("arr", "arr_eop"),
      nn: field("arr", "arr_nn"),
      nb: field("arr", "arr_nb"),
      exp: field("arr", "arr_exp"),
      react: field("arr", "arr_react"),
      cont: field("arr", "arr_cont"),
      churn: field("arr", "arr_churn"),
      rev: field("is", "revenue"),
      ebitda: field("is", "ebitda"),
      opex: periods.map(function (p) {
        var r = row("is", p);
        if (!r) return null;
        if (r.total_opex != null) return Number(r.total_opex);
        if (r.sm == null && r.rd == null && r.ga == null) return null;
        return (Number(r.sm) || 0) + (Number(r.rd) || 0) + (Number(r.ga) || 0);
      }),
      mkt: periods.map(function (p) {
        var r = row("gl_programs", p);
        var keys = r ? Object.keys(r) : [];
        if (!keys.length) return null;
        return keys.reduce(function (s, k) { return s + (Number(r[k]) || 0); }, 0);
      }),
      mqls: field("funnel", "mqls"),
      cash: periods.map(function (p) {
        var cfs = row("cfs", p);
        if (cfs && cfs.ending_cash != null) return Number(cfs.ending_cash);
        var bs = row("bs", p);
        return bs && bs.cash != null ? Number(bs.cash) : null;
      }),
      hc: periods.map(function (p) {
        return h.heads && h.heads[p] != null ? Number(h.heads[p]) : null;
      }),
    };
  }

  /** Loaded marketing funnel totals for a month (history block, then outlook Actual / Forecast). */
  /** Outlook FUNNEL block: the live payload's once loaded (even when it has none), else the demo seed's. */
  function outlookFunnelBlock() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    return (payload ? payload.FUNNEL : global.SMPL_DEMO_FUNNEL) || null;
  }

  /** Average new logo ACV from the live payload once loaded, else the demo seed; null when not loaded. */
  function getLoadedAvgAcv() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    var gtm = payload ? payload.SRC && payload.SRC.gtm : global.SMPL_DEMO_GTM_RATES;
    var acv = gtm && Number(gtm.avg_acv);
    return acv > 0 ? acv : null;
  }

  /** Monthly pipeline book (begin, created, won, lost, slipped, end) from the live payload once loaded, else the demo seed. */
  function getLoadedPipelineBook() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    var book = payload ? payload.SRC && payload.SRC.pipeline_book : global.SMPL_DEMO_PIPELINE_BOOK;
    return book && Object.keys(book).length ? book : null;
  }

  var MIN_HISTORY_QUARTERS = 4;

  /**
   * Stress severities and trip-wires measured from closed months. months: [{p, bop, nb, exp, out, nn}] with out =
   * churn + contraction; book: period -> {won, lost, begin}. A value is null unless MIN_HISTORY_QUARTERS observations
   * back it. Severities are the worst observation as a share below the mean (1 − min/mean); trip-wires are one
   * standard deviation (win rate in points, churn as 1 + coefficient of variation, coverage as a share).
   */
  function measureHistory(months, book) {
    var sorted = (months || []).filter(function (m) { return m && m.p && m.bop > 0; })
      .sort(function (a, b) { return a.p < b.p ? -1 : a.p > b.p ? 1 : 0; });
    var byQ = {};
    sorted.forEach(function (m) {
      var k = m.p.slice(0, 4) + "Q" + Math.ceil(Number(m.p.slice(5)) / 3);
      (byQ[k] = byQ[k] || []).push(m);
    });
    var qKeys = Object.keys(byQ).sort().filter(function (k) { return byQ[k].length === 3; });
    function sum(ms, f) { return ms.reduce(function (s, m) { return s + (Number(m[f]) || 0); }, 0); }
    function mean(xs) { return xs.reduce(function (s, v) { return s + v; }, 0) / xs.length; }
    function sd(xs) {
      var mu = mean(xs);
      return Math.sqrt(xs.reduce(function (s, v) { return s + (v - mu) * (v - mu); }, 0) / (xs.length - 1));
    }
    function enough(xs) { return xs.length >= MIN_HISTORY_QUARTERS; }
    function worstShare(xs) {
      if (!enough(xs) || !(mean(xs) > 0)) return null;
      return Math.max(0, 1 - Math.min.apply(null, xs) / mean(xs));
    }
    var win = [], cover = [];
    qKeys.forEach(function (k) {
      var b = byQ[k].map(function (m) { return book && book[m.p]; }).filter(Boolean);
      if (b.length !== 3) return;
      var won = sum(b, "won");
      var lost = sum(b, "lost");
      if (won + lost > 0) win.push(won / (won + lost));
      if (won > 0 && Number(b[0].begin) > 0) cover.push(Number(b[0].begin) / won);
    });
    var expRate = qKeys.map(function (k) { return sum(byQ[k], "exp") / byQ[k][0].bop; });
    var outRate = qKeys.map(function (k) { return sum(byQ[k], "out") / byQ[k][0].bop; });
    var nnYoy = [];
    qKeys.forEach(function (k) {
      var prior = byQ[(Number(k.slice(0, 4)) - 1) + k.slice(4)];
      if (!prior || prior.length !== 3) return;
      var was = sum(prior, "nn");
      if (was > 0) nnYoy.push(sum(byQ[k], "nn") / was);
    });
    var worstMonth = null;
    for (var i = 3; i < sorted.length; i++) {
      var avg = (sorted[i - 1].nb + sorted[i - 2].nb + sorted[i - 3].nb) / 3;
      if (avg > 0) worstMonth = Math.min(worstMonth == null ? Infinity : worstMonth, sorted[i].nb / avg);
    }
    return {
      span: qKeys.length ? byQ[qKeys[0]][0].p + " to " + byQ[qKeys[qKeys.length - 1]][2].p : null,
      quarters: qKeys.length,
      minQuarters: MIN_HISTORY_QUARTERS,
      nbShare: worstShare(win),
      expShare: worstShare(expRate),
      nnShare: worstShare(nnYoy),
      peakShare: enough(qKeys) && worstMonth != null ? Math.max(0, Math.min(1, 1 - worstMonth)) : null,
      coverShare: worstShare(cover),
      winTripPp: enough(win) ? sd(win) * 100 : null,
      churnTripX: enough(outRate) && mean(outRate) > 0 ? 1 + sd(outRate) / mean(outRate) : null,
      coverTripShare: enough(cover) && mean(cover) > 0 ? sd(cover) / mean(cover) : null,
    };
  }

  function getLoadedFunnel(period, closeMonth) {
    var h = global.SMPL_HISTORY;
    if (h && h.funnel && h.funnel[period]) return h.funnel[period];
    var f = outlookFunnelBlock();
    if (!f) return null;
    var asOf = closeMonth || getActiveCloseMonth(null);
    var block = asOf && period > asOf ? f.Forecast : f.Actual;
    return (block && block[period]) || null;
  }

  /** GL marketing program row ("line|department|type" → $) for a month (history block, then outlook); null when not loaded. */
  function getLoadedProgramRow(period, closeMonth) {
    var h = global.SMPL_HISTORY;
    var row = h && h.gl_programs && h.gl_programs[period];
    if (!row || !Object.keys(row).length) row = getWarehouseGlPrograms(period, closeMonth);
    return row && Object.keys(row).length ? row : null;
  }

  /** GL marketing program spend for a month (history block, then outlook); null when not loaded. */
  function getLoadedProgramSpend(period, closeMonth) {
    var row = getLoadedProgramRow(period, closeMonth);
    if (!row) return null;
    return Object.keys(row).reduce(function (s, k) { return s + (Number(row[k]) || 0); }, 0);
  }

  /**
   * Sample sd of (Actual − Budget) monthly cash from operations over closed months
   * that carry both; null below 3 months — too few to estimate a spread.
   */
  function getCfoPlanErrorSd(closeMonth) {
    var ts = getOutlookTsData();
    var actual = ts && ts.Actual && ts.Actual.cfs;
    var budget = ts && ts.Budget && ts.Budget.cfs;
    if (!actual || !budget) return null;
    var asOf = closeMonth || getActiveCloseMonth(null);
    var errs = [];
    Object.keys(actual).sort().forEach(function (p) {
      if (asOf && p > asOf) return;
      var a = actual[p], b = budget[p];
      if (!a || !b || a.cfo == null || b.cfo == null) return;
      var d = Number(a.cfo) - Number(b.cfo);
      if (isFinite(d)) errs.push(d);
    });
    if (errs.length < 3) return null;
    var mu = errs.reduce(function (s, v) { return s + v; }, 0) / errs.length;
    var ss = errs.reduce(function (s, v) { return s + (v - mu) * (v - mu); }, 0);
    return Math.sqrt(ss / (errs.length - 1));
  }

  /**
   * Closed-month GTM history for Monte Carlo prior fitting:
   *  - cpl_log_ratios: log(CPL / CPL in the same month a year earlier), CPL = program spend / MQLs;
   *  - pipeline_cover: pipeline created / closed-won per fully loaded quarter.
   * Months missing either input are skipped, never filled.
   */
  function getGtmPriorHistory(closeMonth) {
    var asOf = closeMonth || getActiveCloseMonth(null);
    if (!asOf) return null;
    var keys = {};
    var h = global.SMPL_HISTORY;
    if (h && h.funnel) Object.keys(h.funnel).forEach(function (k) { keys[k] = 1; });
    var f = outlookFunnelBlock();
    if (f && f.Actual) Object.keys(f.Actual).forEach(function (k) { keys[k] = 1; });
    var periods = Object.keys(keys).filter(function (p) { return p <= asOf; }).sort();
    function month(p) {
      var r = getLoadedFunnel(p, asOf);
      if (!r) return null;
      var spend = getLoadedProgramSpend(p, asOf);
      var mqls = Number(r.mqls);
      return {
        cpl: spend != null && spend > 0 && mqls > 0 ? spend / mqls : null,
        pipe: r.pipeline_arr_created != null ? Number(r.pipeline_arr_created) : null,
        won: r.closed_won_arr != null ? Number(r.closed_won_arr) : null,
      };
    }
    var out = { cpl_log_ratios: [], cpl_periods: [], pipeline_cover: [], pipeline_cover_periods: [] };
    var byQuarter = {};
    periods.forEach(function (p) {
      var cur = month(p);
      if (!cur) return;
      var prior = month((parseInt(p.slice(0, 4), 10) - 1) + p.slice(4));
      if (cur.cpl != null && prior && prior.cpl != null) {
        out.cpl_log_ratios.push(Math.log(cur.cpl / prior.cpl));
        out.cpl_periods.push(p);
      }
      var q = p.slice(0, 4) + "-Q" + Math.ceil(parseInt(p.slice(5, 7), 10) / 3);
      var b = byQuarter[q] || (byQuarter[q] = { n: 0, pipe: 0, won: 0 });
      if (cur.pipe != null && cur.won != null) {
        b.n += 1;
        b.pipe += cur.pipe;
        b.won += cur.won;
      }
    });
    Object.keys(byQuarter).sort().forEach(function (q) {
      var b = byQuarter[q];
      if (b.n === 3 && b.won > 0) {
        out.pipeline_cover.push(b.pipe / b.won);
        out.pipeline_cover_periods.push(q);
      }
    });
    return out;
  }

  /**
   * The company's plan risk policy (outlook RISK_POLICY, onboarding 7.43–7.58): shares as fractions,
   * amounts in dollars, counts as integers. An unanswered or conflicting cutoff is null — never defaulted.
   */
  function getRiskPolicyValue(key) {
    var p = global.SMPL_RISK_POLICY;
    var v = p && p.values ? p.values[key] : null;
    if (v == null) return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function riskPolicyNotSet(key) {
    var p = global.SMPL_RISK_POLICY;
    var q = p && p.questions ? p.questions[key] : null;
    return "Risk policy not set" + (q ? " (onboarding " + q + ")" : "");
  }

  global.SMPLOutlook = {
    getCfoPlanErrorSd: getCfoPlanErrorSd,
    getRiskPolicyValue: getRiskPolicyValue,
    riskPolicyNotSet: riskPolicyNotSet,
    getGtmPriorHistory: getGtmPriorHistory,
    getHistoryYear: getHistoryYear,
    getLoadedAvgAcv: getLoadedAvgAcv,
    getLoadedFunnel: getLoadedFunnel,
    getLoadedPipelineBook: getLoadedPipelineBook,
    measureHistory: measureHistory,
    getLoadedProgramRow: getLoadedProgramRow,
    getLoadedProgramSpend: getLoadedProgramSpend,
    monthLabel: monthLabel,
    resolveOrgId: resolveOrgId,
    applyOutlook: applyOutlook,
    hydrate: hydrate,
    outlookPayloadValid: outlookPayloadValid,
    replaceArrWaterfallTable: replaceArrWaterfallTable,
    replaceTsData: replaceTsData,
    mergeTsData: mergeTsData,
    mergeActuals: mergeActuals,
    pruneDemoActualResidue: pruneDemoActualResidue,
    pruneDemoPlanResidue: pruneDemoPlanResidue,
    pruneSrcActualResidue: pruneSrcActualResidue,
    getArrFromWaterfall: getArrFromWaterfall,
    buildOutlookFetchUrl: buildOutlookFetchUrl,
    isLiveOutlook: isLiveOutlook,
    registerDemoData: registerDemoData,
    getOutlookTsData: getOutlookTsData,
    getOutlookWfTable: getOutlookWfTable,
    getActiveCloseMonth: getActiveCloseMonth,
    tsGetValue: tsGetValue,
    tsGetRow: tsGetRow,
    getCombinedTsRow: getCombinedTsRow,
    getCombinedArr: getCombinedArr,
    getCashBridgeRow: getCashBridgeRow,
    getWarehouseIS: getWarehouseIS,
    getWarehouseGlOpex: getWarehouseGlOpex,
    getWarehouseGlExpenseTypes: getWarehouseGlExpenseTypes,
    getWarehouseGlPrograms: getWarehouseGlPrograms,
    getLoadedStatementRow: getLoadedStatementRow,
    getWarehouseCFS: getWarehouseCFS,
    getWarehouseBS: getWarehouseBS,
    getDecemberSnapshot: getDecemberSnapshot,
    getOutlookYearPeriods: getOutlookYearPeriods,
    logDecemberAlignment: logDecemberAlignment,
    buildAlignmentReport: buildAlignmentReport,
  };
})(window);
