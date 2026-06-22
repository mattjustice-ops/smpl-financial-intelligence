/**
 * Shared ARR forecast engine — opportunity pipeline + renewal cohorts.
 * Used by Forecast Engine (with levers) and Board Platform (default levers).
 */
(function (g) {
  "use strict";

  var DEFAULT_LEVERS = {
    nb: 1,
    exp: 1,
    churn: 1,
    ren_adj: 0,
  };

  function getSrc() {
    if (g.SRC && g.SRC.opp_pipeline) {
      return {
        actuals: g.SRC.actuals || {},
        opp_pipeline: g.SRC.opp_pipeline || {},
        renewals: g.SRC.renewals || {},
      };
    }
    if (g.SMPL_PIPELINE_SRC) return g.SMPL_PIPELINE_SRC;
    return null;
  }

  function arrFromActuals(period, src) {
    var a = src.actuals[period];
    if (!a) return null;
    return {
      arr_bop: a.arr_bop,
      arr_nb: a.arr_nb,
      arr_exp: a.arr_exp,
      arr_react: a.arr_react,
      arr_cont: a.arr_cont,
      arr_nr_churn: a.arr_churn,
      ren_churn: 0,
      arr_eop: a.arr_eop,
      grr: a.grr || 0,
      nrr: a.nrr || 0,
      is_actual: true,
    };
  }

  function computeForecastMonth(period, bopArr, src, levers) {
    levers = levers || DEFAULT_LEVERS;
    var opps = src.opp_pipeline[period] || {};
    var ren_p = src.renewals[period] || { arr: 0, weighted: 0, count: 0 };
    var gross_ren = ren_p.arr || 0;
    var ren_rate = Math.min(
      1,
      Math.max(0, ren_p.weighted / Math.max(1, gross_ren) + (levers.ren_adj || 0))
    );
    var arr_ren = gross_ren * ren_rate;
    var ren_churn = gross_ren - arr_ren;
    var nb = ((opps["New Business"] && opps["New Business"].weighted) || 0) * (levers.nb || 1);
    var exp = ((opps["Expansion"] && opps["Expansion"].weighted) || 0) * (levers.exp || 1);
    var react = (opps["Reactivation"] && opps["Reactivation"].weighted) || 0;
    var cont = (opps["Contraction"] && opps["Contraction"].weighted) || 0;
    var nr_churn = ((opps["Churn"] && opps["Churn"].weighted) || 0) * (levers.churn || 1);
    var arr_nn = arr_ren - gross_ren + nb + exp + react - cont - nr_churn;
    var arr_eop = bopArr + arr_nn;
    return {
      arr_bop: bopArr,
      gross_ren: gross_ren,
      arr_ren: arr_ren,
      ren_churn: ren_churn,
      arr_nb: nb,
      arr_exp: exp,
      arr_react: react,
      arr_cont: cont,
      arr_nr_churn: nr_churn,
      arr_churn: ren_churn + nr_churn,
      arr_nn: arr_nn,
      arr_eop: arr_eop,
      grr: bopArr > 0 ? (bopArr - ren_churn - nr_churn) / bopArr : 0,
      nrr: bopArr > 0 ? (bopArr + arr_nn - nb) / bopArr : 0,
      is_actual: false,
    };
  }

  function computeArrSeries(allPeriods, closeMonth, levers, src) {
    src = src || getSrc();
    if (!src || !allPeriods || !closeMonth) {
      return { byPeriod: {}, decEop: null };
    }
    levers = levers || DEFAULT_LEVERS;
    var byPeriod = {};
    var closeIdx = allPeriods.indexOf(closeMonth);
    if (closeIdx < 0) return { byPeriod: byPeriod, decEop: null };

    for (var i = 0; i <= closeIdx; i++) {
      var act = arrFromActuals(allPeriods[i], src);
      if (act) byPeriod[allPeriods[i]] = act;
    }

    var lastAct = src.actuals[closeMonth];
    if (!lastAct || lastAct.arr_eop == null) {
      return { byPeriod: byPeriod, decEop: null };
    }

    var bop = lastAct.arr_eop;
    for (var j = closeIdx + 1; j < allPeriods.length; j++) {
      var fp = allPeriods[j];
      var fc = computeForecastMonth(fp, bop, src, levers);
      byPeriod[fp] = fc;
      bop = fc.arr_eop;
    }

    var dec = allPeriods[allPeriods.length - 1];
    return {
      byPeriod: byPeriod,
      decEop: byPeriod[dec] ? byPeriod[dec].arr_eop : null,
    };
  }

  function getArr(period, allPeriods, closeMonth, levers, src) {
    var series = computeArrSeries(allPeriods, closeMonth, levers, src);
    return series.byPeriod[period] || null;
  }

  g.SMPLPipeline = {
    DEFAULT_LEVERS: DEFAULT_LEVERS,
    getSrc: getSrc,
    arrFromActuals: arrFromActuals,
    computeForecastMonth: computeForecastMonth,
    computeArrSeries: computeArrSeries,
    getArr: getArr,
  };
})(typeof window !== "undefined" ? window : globalThis);
