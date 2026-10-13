/**
 * Workforce plan groups and the budget's beginning headcount, levels and pay.
 *
 * GROUPS rolls loaded departments up the way the income statement does: Sales, Customer Success and Marketing
 * (S&M), Engineering and Product (R&D), G&A, Finance and Support (G&A). The Forecast Engine's FC_HC_DEPTS uses
 * the same departments (checked by scripts/verify-workforce-groups.mjs).
 */
(function (root) {
  'use strict';

  var GROUPS = [
    { key: 'sales', depts: ['Sales'] },
    { key: 'cs', depts: ['Customer Success'] },
    { key: 'marketing', depts: ['Marketing'] },
    { key: 'rd', depts: ['R&D', 'Product', 'Engineering'] },
    { key: 'ga', depts: ['G&A', 'Finance', 'Support'] },
  ];
  var NO_LEVEL = 'No level';

  function groupOf(dept) {
    var d = String(dept || '').trim();
    for (var i = 0; i < GROUPS.length; i++) {
      if (GROUPS[i].depts.indexOf(d) >= 0) return GROUPS[i].key;
    }
    return null;
  }

  function emptyByGroup(make) {
    var out = {};
    GROUPS.forEach(function (g) { out[g.key] = make(); });
    return out;
  }

  /**
   * Per group, the sum of byDept[dept][idx] over the group's departments that have a value there; null when none
   * does. Departments no group covers are listed, not counted.
   */
  function groupValues(byDept, idx) {
    var values = emptyByGroup(function () { return null; });
    var unmapped = [];
    Object.keys(byDept || {}).forEach(function (dept) {
      var key = groupOf(dept);
      if (!key) { unmapped.push(dept); return; }
      var series = byDept[dept];
      var v = series && series[idx];
      if (v == null) return;
      values[key] = (values[key] || 0) + Number(v);
    });
    return { values: values, unmapped: unmapped };
  }

  /** L2 < L3 < ... < L10; levels without a number sort by name, "No level" last. */
  function levelOrder(a, b) {
    if (a === NO_LEVEL || b === NO_LEVEL) return a === b ? 0 : (a === NO_LEVEL ? 1 : -1);
    var ma = /^(\D*)(\d+)/.exec(a);
    var mb = /^(\D*)(\d+)/.exec(b);
    if (ma && mb && ma[1] === mb[1]) return Number(ma[2]) - Number(mb[2]);
    return a < b ? -1 : (a > b ? 1 : 0);
  }

  /**
   * Beginning heads, base salary and bonus % by group x level from the employees on the roster at the prior
   * year's last month. Salary is the level's total base over its heads: an employee with no base salary adds a
   * head and no pay, and is counted in missingBase. Bonus % is the level's bonus (variable pay less commission
   * target) over its base. Hire dates are kept by group for service-based terms; missing ones are counted.
   */
  function startTable(rows) {
    var out = {
      levels: emptyByGroup(function () { return []; }),
      heads: emptyByGroup(function () { return {}; }),
      comp: emptyByGroup(function () { return {}; }),
      hires: emptyByGroup(function () { return []; }),
      total: 0,
      unmapped: [],
      missingLevel: 0,
      missingBase: 0,
      missingHire: 0,
    };
    var sums = emptyByGroup(function () { return {}; });
    (rows || []).forEach(function (r) {
      var key = groupOf(r.dept);
      if (!key) {
        if (out.unmapped.indexOf(r.dept) < 0) out.unmapped.push(r.dept);
        return;
      }
      var lvl = String(r.lvl || '').trim();
      if (!lvl) { lvl = NO_LEVEL; out.missingLevel += 1; }
      if (r.base == null) out.missingBase += 1;
      if (/^\d{4}-\d{2}-\d{2}$/.test(String(r.hire || ''))) out.hires[key].push(String(r.hire));
      else out.missingHire += 1;
      var s = sums[key][lvl] || (sums[key][lvl] = { n: 0, base: 0, bonus: 0 });
      s.n += 1;
      s.base += Number(r.base || 0);
      s.bonus += Number(r.bonus || 0);
      out.total += 1;
    });
    GROUPS.forEach(function (g) {
      var levels = Object.keys(sums[g.key]).sort(levelOrder);
      out.levels[g.key] = levels;
      levels.forEach(function (lvl) {
        var s = sums[g.key][lvl];
        out.heads[g.key][lvl] = s.n;
        out.comp[g.key][lvl] = { salary: s.base / s.n, bonusPct: s.base > 0 ? (100 * s.bonus) / s.base : 0 };
      });
    });
    return out;
  }

  var api = {
    GROUPS: GROUPS,
    NO_LEVEL: NO_LEVEL,
    groupOf: groupOf,
    groupValues: groupValues,
    levelOrder: levelOrder,
    startTable: startTable,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SMPLWorkforceGroups = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
