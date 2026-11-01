/**
 * Seeded lever sampler for the Budget Engine full-plan Monte Carlo.
 *
 * Contract (must match SAMPLER in backend mc_inputs.py):
 *   mulberry32 uniforms -> Box-Muller normals (cos branch, two uniforms per
 *   normal) -> Cholesky-correlated shocks, one normal per lever in draw order.
 * Same seed + priors + correlations => the same shock sequence, so a run
 * reproduces from the recorded inputs on the same plan.
 */
(function (root) {
  'use strict';

  var LEVERS = ['yoyPp', 'cplLog', 'attrPp', 'pipe'];
  var BUDGET_LEVERS = ['nbLog', 'expLog', 'contLog', 'churnLog', 'billPp', 'cogsPp', 'cplLog', 'pipe', 'attrPp', 'attainPp'];
  var LEVER_LABELS = {
    yoyPp: 'ARR growth',
    nbLog: 'new business',
    expLog: 'expansion',
    contLog: 'contraction',
    churnLog: 'churn',
    billPp: 'annual billing',
    cogsPp: 'cost of revenue',
    cplLog: 'cost per lead',
    attrPp: 'sales attrition',
    pipe: 'pipeline coverage',
    attainPp: 'quota attainment',
  };
  var SAMPLER = 'mulberry32_box_muller_cholesky_v1';

  function leverOrder(levers) {
    return levers && levers.length ? levers : LEVERS;
  }

  /** The levers with a usable prior (a finite, non-negative sd); every other lever is not drawn. */
  function drawnPriors(priors, levers) {
    var out = {};
    leverOrder(levers).forEach(function (k) {
      var raw = priors ? priors[k] : null;
      var v = raw == null || raw === '' ? NaN : Number(raw);
      if (isFinite(v) && v >= 0) out[k] = v;
    });
    return out;
  }

  /** Correlations whose levers are both drawn. */
  function drawnCorrelations(correlations, sig) {
    var out = {};
    Object.keys(correlations || {}).forEach(function (key) {
      var parts = String(key).replace('|', ':').split(':');
      if (Object.prototype.hasOwnProperty.call(sig, parts[0]) && Object.prototype.hasOwnProperty.call(sig, parts[1])) {
        out[key] = correlations[key];
      }
    });
    return out;
  }

  function undrawnLabels(sig, levers) {
    return leverOrder(levers).filter(function (k) { return !Object.prototype.hasOwnProperty.call(sig, k); })
      .map(function (k) { return LEVER_LABELS[k]; });
  }

  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function normalFrom(uniform) {
    return function () {
      var u = 0, v = 0;
      while (u === 0) u = uniform();
      while (v === 0) v = uniform();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    };
  }

  function correlationMatrix(correlations, levers) {
    var names = leverOrder(levers);
    var n = names.length;
    var m = [];
    for (var i = 0; i < n; i++) {
      m.push([]);
      for (var j = 0; j < n; j++) m[i].push(i === j ? 1 : 0);
    }
    Object.keys(correlations || {}).forEach(function (key) {
      var parts = String(key).replace('|', ':').split(':');
      var a = names.indexOf(parts[0]);
      var b = names.indexOf(parts[1]);
      var rho = Number(correlations[key]);
      if (a < 0 || b < 0 || a === b || !isFinite(rho)) {
        throw new Error('Invalid lever correlation ' + key);
      }
      m[a][b] = rho;
      m[b][a] = rho;
    });
    return m;
  }

  function cholesky(matrix) {
    var n = matrix.length;
    var lower = [];
    for (var i = 0; i < n; i++) {
      lower.push([]);
      for (var k = 0; k < n; k++) lower[i].push(0);
    }
    for (var r = 0; r < n; r++) {
      for (var c = 0; c <= r; c++) {
        var s = 0;
        for (var q = 0; q < c; q++) s += lower[r][q] * lower[c][q];
        if (r === c) {
          var d = matrix[r][r] - s;
          if (d <= 1e-12) throw new Error('Lever correlations are not positive definite');
          lower[r][c] = Math.sqrt(d);
        } else {
          lower[r][c] = (matrix[r][c] - s) / lower[c][c];
        }
      }
    }
    return lower;
  }

  /**
   * Returns { next() } yielding one trial's correlated standard-normal shocks
   * keyed by lever. Scale by the lever priors at the call site.
   */
  function createLeverSampler(opts) {
    opts = opts || {};
    var seed = opts.seed != null ? opts.seed : 42;
    var names = leverOrder(opts.levers);
    var normal = normalFrom(mulberry32(seed));
    var lower = cholesky(correlationMatrix(opts.correlations, names));
    var n = names.length;
    return {
      lower: lower,
      next: function () {
        var e = [];
        for (var i = 0; i < n; i++) e.push(normal());
        var z = {};
        for (var r = 0; r < n; r++) {
          var acc = 0;
          for (var c = 0; c <= r; c++) acc += lower[r][c] * e[c];
          z[names[r]] = acc;
        }
        return z;
      },
    };
  }

  /**
   * Partial effect of each drawn lever on year-end cash, holding the others at
   * the plan, plus the pairs that still move cash after those main effects.
   * rows: [{ z: {lever: standard normal}, cash: number }]
   */
  function solveLinear(matrix, vector) {
    var n = vector.length;
    var m = matrix.map(function (row, i) { return row.concat([vector[i]]); });
    for (var col = 0; col < n; col++) {
      var pivot = col;
      for (var r = col + 1; r < n; r++) if (Math.abs(m[r][col]) > Math.abs(m[pivot][col])) pivot = r;
      if (Math.abs(m[pivot][col]) < 1e-10) return null;
      var swap = m[col]; m[col] = m[pivot]; m[pivot] = swap;
      var div = m[col][col];
      for (var c = col; c <= n; c++) m[col][c] /= div;
      for (var r2 = 0; r2 < n; r2++) {
        if (r2 === col) continue;
        var factor = m[r2][col];
        for (var c2 = col; c2 <= n; c2++) m[r2][c2] -= factor * m[col][c2];
      }
    }
    return m.map(function (row) { return row[n]; });
  }

  function rankDriverEffects(rows, keys) {
    keys = keys || [];
    var n = rows ? rows.length : 0;
    var p = keys.length;
    if (n < p + 2 || !p) return { main: [], pairs: [] };
    var y = rows.map(function (row) { return Number(row.cash) || 0; });
    var k = p + 1;
    var xtx = [];
    var xty = [];
    for (var i = 0; i < k; i++) {
      xtx.push([]);
      xty.push(0);
      for (var j = 0; j < k; j++) xtx[i].push(0);
    }
    rows.forEach(function (row, t) {
      var x = [1];
      keys.forEach(function (key) { x.push(row.z && row.z[key] != null ? Number(row.z[key]) : 0); });
      for (var a = 0; a < k; a++) {
        xty[a] += x[a] * y[t];
        for (var b = 0; b < k; b++) xtx[a][b] += x[a] * x[b];
      }
    });
    var beta = solveLinear(xtx, xty);
    if (!beta) return { main: [], pairs: [] };
    var main = keys.map(function (key, i) {
      return { key: key, label: LEVER_LABELS[key] || key, dollarsPerSd: beta[i + 1] };
    });
    main.sort(function (a, b) { return Math.abs(b.dollarsPerSd) - Math.abs(a.dollarsPerSd); });
    var fitted = rows.map(function (row) {
      var value = beta[0];
      keys.forEach(function (key, i) {
        value += beta[i + 1] * (row.z && row.z[key] != null ? Number(row.z[key]) : 0);
      });
      return value;
    });
    var pairs = [];
    for (var i = 0; i < p; i++) {
      for (var j = i + 1; j < p; j++) {
        var meanP = 0;
        var meanR = 0;
        var prod = rows.map(function (row) {
          var zi = row.z && row.z[keys[i]] != null ? Number(row.z[keys[i]]) : 0;
          var zj = row.z && row.z[keys[j]] != null ? Number(row.z[keys[j]]) : 0;
          return zi * zj;
        });
        prod.forEach(function (v, t) { meanP += v; meanR += y[t] - fitted[t]; });
        meanP /= n;
        meanR /= n;
        var ss = 0;
        var cov = 0;
        prod.forEach(function (v, t) {
          var dp = v - meanP;
          ss += dp * dp;
          cov += dp * ((y[t] - fitted[t]) - meanR);
        });
        if (ss > 1e-8) {
          pairs.push({
            a: keys[i],
            b: keys[j],
            labelA: LEVER_LABELS[keys[i]] || keys[i],
            labelB: LEVER_LABELS[keys[j]] || keys[j],
            dollarsPerSd: cov / ss,
          });
        }
      }
    }
    pairs.sort(function (a, b) { return Math.abs(b.dollarsPerSd) - Math.abs(a.dollarsPerSd); });
    return { main: main, pairs: pairs.slice(0, 3) };
  }

  var api = {
    LEVERS: LEVERS,
    BUDGET_LEVERS: BUDGET_LEVERS,
    LEVER_LABELS: LEVER_LABELS,
    SAMPLER: SAMPLER,
    drawnPriors: drawnPriors,
    drawnCorrelations: drawnCorrelations,
    undrawnLabels: undrawnLabels,
    mulberry32: mulberry32,
    cholesky: cholesky,
    correlationMatrix: correlationMatrix,
    createLeverSampler: createLeverSampler,
    rankDriverEffects: rankDriverEffects,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SMPLPlanMc = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
