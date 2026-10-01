/**
 * Seeded lever sampler for the Budget Engine full-plan Monte Carlo.
 *
 * Contract (must match SAMPLER in backend mc_inputs.py):
 *   mulberry32 uniforms -> Box-Muller normals (cos branch, two uniforms per
 *   normal) -> Cholesky-correlated shocks, four normals per trial in LEVERS order.
 * Same seed + priors + correlations => the same shock sequence, so a run
 * reproduces from the recorded inputs on the same plan.
 */
(function (root) {
  'use strict';

  var LEVERS = ['yoyPp', 'cplLog', 'attrPp', 'pipe'];
  var SAMPLER = 'mulberry32_box_muller_cholesky_v1';

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

  function correlationMatrix(correlations) {
    var n = LEVERS.length;
    var m = [];
    for (var i = 0; i < n; i++) {
      m.push([]);
      for (var j = 0; j < n; j++) m[i].push(i === j ? 1 : 0);
    }
    Object.keys(correlations || {}).forEach(function (key) {
      var parts = String(key).replace('|', ':').split(':');
      var a = LEVERS.indexOf(parts[0]);
      var b = LEVERS.indexOf(parts[1]);
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
    var normal = normalFrom(mulberry32(seed));
    var lower = cholesky(correlationMatrix(opts.correlations));
    var n = LEVERS.length;
    return {
      lower: lower,
      next: function () {
        var e = [];
        for (var i = 0; i < n; i++) e.push(normal());
        var z = {};
        for (var r = 0; r < n; r++) {
          var acc = 0;
          for (var c = 0; c <= r; c++) acc += lower[r][c] * e[c];
          z[LEVERS[r]] = acc;
        }
        return z;
      },
    };
  }

  var api = {
    LEVERS: LEVERS,
    SAMPLER: SAMPLER,
    mulberry32: mulberry32,
    cholesky: cholesky,
    correlationMatrix: correlationMatrix,
    createLeverSampler: createLeverSampler,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SMPLPlanMc = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
