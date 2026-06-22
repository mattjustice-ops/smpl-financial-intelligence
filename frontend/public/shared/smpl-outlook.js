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
    if (fromQuery) return fromQuery;
    if (global.SMPL_ORG_ID) return global.SMPL_ORG_ID;

    if (options.waitForParent !== false) {
      var waited = await waitForParentOrg(options.parentWaitMs || 4000);
      if (waited) return waited;
    }

    try {
      var res = await fetch("/api/auth/session", { credentials: "include" });
      if (!res.ok) return null;
      var j = await res.json();
      return j && j.user && j.user.activeOrganizationId ? j.user.activeOrganizationId : null;
    } catch (_) {
      return null;
    }
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
    if (!data || data.type !== "smpl:org" || !data.organizationId) return;
    global.SMPL_ORG_ID = data.organizationId;
    if (typeof global.SMPL_ON_ORG_READY === "function") {
      global.SMPL_ON_ORG_READY(data.organizationId);
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
    var churnMag = Math.abs(churn || 0);
    var contMag = Math.abs(cont || 0);
    return {
      arr_bop: bop,
      arr_nb: nb,
      arr_exp: exp,
      arr_react: react,
      arr_cont: contMag,
      arr_nr_churn: churnMag,
      ren_churn: 0,
      arr_eop: eop,
      nrr: bop ? (bop + (exp || 0) + (react || 0) + (cont || 0) + (churn || 0)) / bop : null,
      grr: bop ? (bop + (cont || 0) + (churn || 0)) / bop : null,
    };
  }

  function replaceArrWaterfallTable(WF_TABLE, incoming) {
    if (!incoming) return;
    Object.keys(incoming).forEach(function (key) {
      if (Array.isArray(incoming[key])) {
        WF_TABLE[key] = incoming[key].slice();
      }
    });
  }

  function replaceTsData(target, incoming) {
    if (!incoming || !target) return;
    ["Actual", "Forecast", "Budget"].forEach(function (sc) {
      if (incoming[sc]) target[sc] = JSON.parse(JSON.stringify(incoming[sc]));
    });
  }

  function getActiveCloseMonth(fallback) {
    return global.SMPL_CLOSE_MONTH || global.CLOSE_MONTH || fallback || null;
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
    if (isLiveOutlook()) return global.SMPL_TS_DATA;
    return global.SMPL_DEMO_TS_DATA || null;
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
    var sc = scenario || scenarioForPeriod(period, closeMonth || getActiveCloseMonth("2026-06"));
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
    if (out.total_opex == null) {
      out.total_opex = (out.sm || 0) + (out.rd || 0) + (out.ga || 0);
    }
    return out;
  }

  function getWarehouseIS(period, allPeriods, closeMonth) {
    void allPeriods;
    return enrichIsRow(getCombinedTsRow(period, "is", closeMonth));
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

  function sumBsLiabilities(row, deferredRev, otherLiab) {
    return (row.ap || 0) + (deferredRev || 0) + (row.debt || 0) + (otherLiab || 0);
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
    if (totalLe == null && row.total_assets != null) {
      totalLe = row.total_assets;
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
    ["is", "bs", "cfs"].forEach(function (stmt) {
      if (!incoming[stmt]) return;
      target[stmt] = target[stmt] || {};
      Object.keys(incoming[stmt]).forEach(function (period) {
        var row = incoming[stmt][period];
        if (!row) return;
        var hasValue = Object.keys(row).some(function (k) {
          return row[k] != null;
        });
        if (!hasValue) return;
        target[stmt][period] = Object.assign({}, target[stmt][period] || {}, row);
      });
    });
  }

  function replaceActuals(target, incoming) {
    if (!incoming) return;
    Object.keys(incoming).forEach(function (period) {
      var row = incoming[period];
      if (!row) return;
      target[period] = Object.assign({}, row);
    });
  }

  function mergeActuals(target, incoming) {
    if (!incoming) return;
    Object.keys(incoming).forEach(function (period) {
      var row = incoming[period];
      if (!row) return;
      var hasValue = Object.keys(row).some(function (k) {
        return row[k] != null;
      });
      if (!hasValue) return;
      target[period] = Object.assign({}, target[period] || {}, row);
    });
  }

  function getOutlookYearPeriods(data) {
    var close = (data.meta && data.meta.close_month) || getActiveCloseMonth("2026-06");
    var year = String(close).slice(0, 4);
    return Array.from({ length: 12 }, function (_, i) {
      return year + "-" + String(i + 1).padStart(2, "0");
    });
  }

  function getDecemberSnapshot(allPeriods) {
    if (!allPeriods || !allPeriods.length || !getOutlookTsData()) return null;
    var dec = allPeriods[allPeriods.length - 1];
    var closeMonth = getActiveCloseMonth("2026-06");
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
    closeMonth = closeMonth || getActiveCloseMonth("2026-06");
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
    global.SMPL_BASELINE_ENGINE = data.baseline_engine || null;
    global.SMPL_TS_DATA = data.TS_DATA || null;
    global.SMPL_CASH_BRIDGE = data.CASH_BRIDGE || null;
    global.SMPL_LIVE_OUTLOOK = true;

    if (hooks.TS_DATA && data.TS_DATA) {
      replaceTsData(hooks.TS_DATA, data.TS_DATA);
    }

    if (hooks.WF_TABLE && data.ARR_WATERFALL) {
      replaceArrWaterfallTable(hooks.WF_TABLE, data.ARR_WATERFALL);
    }

    if (hooks.SRC && data.SRC && data.SRC.actuals) {
      hooks.SRC.actuals = hooks.SRC.actuals || {};
      replaceActuals(hooks.SRC.actuals, data.SRC.actuals);
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

  async function hydrate(config) {
    config = config || {};
    var orgId = await resolveOrgId(config);
    if (!orgId) {
      if (config.onStatus) config.onStatus("Demo data (sign in for live)", "warn");
      return false;
    }

    if (config.onStatus) config.onStatus("Syncing live warehouse…", "warn");

    try {
      var result = await fetchOutlook(orgId, config.endpoint, config.query);
      if (result.stale) return false;
      if (!result.ok) {
        console.warn("[smpl-outlook] hydrate failed", result.status, result.body);
        if (config.onStatus) {
          config.onStatus("Demo data (API " + (result.status || "?") + ")", "warn");
        }
        return false;
      }

      var applied = applyOutlook(result.data, config.hooks || {});
      if (!applied) {
        if (config.onStatus) config.onStatus("Demo data (incomplete warehouse)", "warn");
        return false;
      }

      if (config.onApplied) config.onApplied(result.data);
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
      return true;
    } catch (err) {
      if (err && err.name === "AbortError") return false;
      console.warn("[smpl-outlook] hydrate error", err);
      if (config.onStatus) config.onStatus("Demo data (offline)", "warn");
      return false;
    }
  }

  global.SMPLOutlook = {
    monthLabel: monthLabel,
    resolveOrgId: resolveOrgId,
    applyOutlook: applyOutlook,
    hydrate: hydrate,
    outlookPayloadValid: outlookPayloadValid,
    replaceArrWaterfallTable: replaceArrWaterfallTable,
    replaceTsData: replaceTsData,
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
    getWarehouseCFS: getWarehouseCFS,
    getWarehouseBS: getWarehouseBS,
    getDecemberSnapshot: getDecemberSnapshot,
    getOutlookYearPeriods: getOutlookYearPeriods,
    logDecemberAlignment: logDecemberAlignment,
    buildAlignmentReport: buildAlignmentReport,
  };
})(window);
