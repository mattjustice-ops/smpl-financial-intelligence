/**
 * Working-day accrual. One rate for the year: annual amount ÷ weekdays in that year,
 * minus any dates in `holidays`. A person on payroll every working day lands on the annual amount.
 * A start or a leave is the same count, shortened. The merit date is included in the raised days.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SMPLWorkingDays = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  function pad(n) {
    return (n < 10 ? '0' : '') + n;
  }

  function iso(year, month, day) {
    return year + '-' + pad(month) + '-' + pad(day);
  }

  function monthLength(year, month) {
    return new Date(year, month, 0).getDate();
  }

  function holidaySet(list) {
    var set = {};
    (list || []).forEach(function (d) {
      var text = String(d || '').slice(0, 10);
      if (/^\d{4}-\d{2}-\d{2}$/.test(text)) set[text] = true;
    });
    return set;
  }

  function isOff(year, month, day, set) {
    var dow = new Date(year, month - 1, day).getDay();
    if (dow === 0 || dow === 6) return true;
    return !!(set && set[iso(year, month, day)]);
  }

  function countDays(year, month, dayFrom, dayTo, set) {
    var last = monthLength(year, month);
    var a = Math.max(1, dayFrom);
    var b = Math.min(last, dayTo);
    var n = 0;
    for (var day = a; day <= b; day++) {
      if (!isOff(year, month, day, set)) n += 1;
    }
    return n;
  }

  function yearWorkingDays(year, holidays) {
    var set = holidaySet(holidays);
    var n = 0;
    for (var month = 1; month <= 12; month++) n += countDays(year, month, 1, 31, set);
    return n;
  }

  function monthWorkingDays(year, month, holidays) {
    return countDays(year, month, 1, 31, holidaySet(holidays));
  }

  /** Working days on payroll. startIso null means the person was already employed. */
  function daysOnPayroll(year, month, startIso, holidays) {
    var set = holidaySet(holidays);
    var last = monthLength(year, month);
    var monthStart = iso(year, month, 1);
    var monthEnd = iso(year, month, last);
    if (startIso && String(startIso) > monthEnd) return 0;
    var from = 1;
    if (startIso && String(startIso) > monthStart) {
      if (String(startIso).slice(0, 7) !== monthStart.slice(0, 7)) return 0;
      from = Number(String(startIso).slice(8, 10)) || 1;
    }
    return countDays(year, month, from, last, set);
  }

  /**
   * Days on payroll split at meritIso. The merit date and every working day after it are `after`.
   */
  function splitMerit(year, month, startIso, meritIso, holidays) {
    var set = holidaySet(holidays);
    var last = monthLength(year, month);
    var monthStart = iso(year, month, 1);
    var monthEnd = iso(year, month, last);
    if (startIso && String(startIso) > monthEnd) return { before: 0, after: 0 };
    var from = 1;
    if (startIso && String(startIso) > monthStart && String(startIso).slice(0, 7) === monthStart.slice(0, 7)) {
      from = Number(String(startIso).slice(8, 10)) || 1;
    }
    var employed = countDays(year, month, from, last, set);
    if (!meritIso || String(meritIso) > monthEnd) return { before: employed, after: 0 };
    var merit = String(meritIso);
    if (merit <= iso(year, month, from)) return { before: 0, after: employed };
    var meritDay = Number(merit.slice(8, 10));
    return {
      before: countDays(year, month, from, meritDay - 1, set),
      after: countDays(year, month, meritDay, last, set),
    };
  }

  function accrue(annual, yearDays, daysBefore, daysAfter, uplift) {
    if (!yearDays || !annual) return 0;
    var up = uplift || 0;
    return (annual * daysBefore / yearDays) + (annual * (1 + up) * daysAfter / yearDays);
  }

  return {
    yearWorkingDays: yearWorkingDays,
    monthWorkingDays: monthWorkingDays,
    daysOnPayroll: daysOnPayroll,
    splitMerit: splitMerit,
    accrue: accrue,
  };
});
