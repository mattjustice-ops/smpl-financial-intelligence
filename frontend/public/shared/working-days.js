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

  /** Names on the company holiday file. Each one is filled with that year's date. A blank row stays a working day. */
  var HOLIDAY_NAMES = [
    "New Year's Day",
    'Martin Luther King Jr. Day',
    "Presidents' Day",
    'Memorial Day',
    'Juneteenth',
    'Independence Day',
    'Labor Day',
    'Thanksgiving',
    'Day after Thanksgiving',
    'Christmas Eve',
    'Christmas Day',
  ];

  function nthWeekday(year, month, weekday, n) {
    var first = new Date(year, month - 1, 1).getDay();
    var day = 1 + ((weekday - first + 7) % 7) + (n - 1) * 7;
    return iso(year, month, day);
  }

  function lastWeekday(year, month, weekday) {
    var last = monthLength(year, month);
    var dow = new Date(year, month - 1, last).getDay();
    return iso(year, month, last - ((dow - weekday + 7) % 7));
  }

  /** Saturday closes the Friday before. Sunday closes the Monday after. */
  function observe(year, month, day) {
    var dt = new Date(year, month - 1, day);
    var dow = dt.getDay();
    if (dow === 6) dt = new Date(year, month - 1, day - 1);
    else if (dow === 0) dt = new Date(year, month - 1, day + 1);
    return iso(dt.getFullYear(), dt.getMonth() + 1, dt.getDate());
  }

  function previousWeekday(dateIso) {
    var parts = String(dateIso).split('-');
    var dt = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    do {
      dt.setDate(dt.getDate() - 1);
    } while (dt.getDay() === 0 || dt.getDay() === 6);
    return iso(dt.getFullYear(), dt.getMonth() + 1, dt.getDate());
  }

  /** The closed day for this name in this year. A Saturday New Year's is the Friday in the prior December. */
  function namedHolidayDate(year, name) {
    if (name === "New Year's Day") return observe(year, 1, 1);
    if (name === 'Martin Luther King Jr. Day') return nthWeekday(year, 1, 1, 3);
    if (name === "Presidents' Day") return nthWeekday(year, 2, 1, 3);
    if (name === 'Memorial Day') return lastWeekday(year, 5, 1);
    if (name === 'Juneteenth') return observe(year, 6, 19);
    if (name === 'Independence Day') return observe(year, 7, 4);
    if (name === 'Labor Day') return nthWeekday(year, 9, 1, 1);
    if (name === 'Thanksgiving') return nthWeekday(year, 11, 4, 4);
    if (name === 'Day after Thanksgiving') {
      var tg = nthWeekday(year, 11, 4, 4).split('-');
      var next = new Date(Number(tg[0]), Number(tg[1]) - 1, Number(tg[2]) + 1);
      return iso(next.getFullYear(), next.getMonth() + 1, next.getDate());
    }
    if (name === 'Christmas Day') return observe(year, 12, 25);
    if (name === 'Christmas Eve') {
      var christmas = observe(year, 12, 25);
      var eveDow = new Date(year, 11, 24).getDay();
      var eve = iso(year, 12, 24);
      if (eveDow === 0 || eveDow === 6 || eve === christmas) return previousWeekday(christmas);
      return eve;
    }
    return '';
  }

  function csvEscape(value) {
    var text = value == null ? '' : String(value);
    if (/[",\n]/.test(text)) return '"' + text.replace(/"/g, '""') + '"';
    return text;
  }

  function csvTable(text) {
    var rows = [];
    var row = [];
    var field = '';
    var quoted = false;
    var s = String(text || '').replace(/^\uFEFF/, '');
    for (var i = 0; i < s.length; i++) {
      var c = s.charAt(i);
      if (quoted) {
        if (c === '"') {
          if (s.charAt(i + 1) === '"') { field += '"'; i += 1; }
          else quoted = false;
        } else field += c;
      } else if (c === '"') quoted = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else if (c !== '\r') field += c;
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    return rows.filter(function (r) { return r.some(function (cell) { return String(cell || '').trim() !== ''; }); });
  }

  /**
   * Read a holiday file. Blank dates are skipped. A date that is not YYYY-MM-DD is reported
   * and the file is not applied. The date has to fall in the Year column, or in the prior
   * December when New Year's Day is observed then.
   */
  function parseHolidayCsv(text) {
    var table = csvTable(text);
    var errors = [];
    if (!table.length) return { rows: [], years: [], errors: ['The file is empty.'] };
    var header = table[0].map(function (cell) { return String(cell || '').trim().toLowerCase(); });
    var yearCol = header.indexOf('year');
    var nameCol = header.indexOf('holiday');
    var dateCol = header.indexOf('date');
    if (yearCol < 0 || nameCol < 0 || dateCol < 0) {
      return { rows: [], years: [], errors: ['The first row has to be Year, Holiday, Date.'] };
    }
    var rows = [];
    var years = {};
    var seen = {};
    for (var i = 1; i < table.length; i++) {
      var cells = table[i];
      var yearText = String(cells[yearCol] || '').trim();
      var name = String(cells[nameCol] || '').trim();
      var date = String(cells[dateCol] || '').trim();
      if (!yearText && !name && !date) continue;
      var year = Number(yearText);
      if (!/^\d{4}$/.test(yearText)) {
        errors.push('Row ' + (i + 1) + ' needs a four-digit year.');
        continue;
      }
      years[year] = true;
      if (!date) continue;
      var sameYear = date.slice(0, 4) === yearText;
      var priorDecember = date.slice(0, 4) === String(year - 1) && date.slice(5, 7) === '12';
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || (!sameYear && !priorDecember)) {
        errors.push('Row ' + (i + 1) + ' needs a date like ' + yearText + '-01-01.');
        continue;
      }
      if (seen[date]) continue;
      seen[date] = true;
      rows.push({ year: year, name: name, date: date });
    }
    return {
      rows: rows,
      years: Object.keys(years).map(Number),
      errors: errors,
    };
  }

  /** Keep years the file does not mention. Years in the file replace what was saved. */
  function mergeHolidayRows(existing, parsed) {
    var drop = {};
    (parsed.years || []).forEach(function (year) { drop[year] = true; });
    var kept = (existing || []).filter(function (row) { return !drop[Number(row.year)]; });
    return kept.concat(parsed.rows || []);
  }

  function holidayDatesForYear(rows, year) {
    var want = String(year);
    var out = [];
    var seen = {};
    (rows || []).forEach(function (row) {
      var date = String(row.date || '').slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date.slice(0, 4) !== want || seen[date]) return;
      seen[date] = true;
      out.push(date);
    });
    return out;
  }

  function holidayTemplateCsv(years, saved) {
    var lines = ['Year,Holiday,Date'];
    var list = (saved || []).slice();
    years.forEach(function (year) {
      var used = {};
      HOLIDAY_NAMES.forEach(function (name) {
        var hit = null;
        list.forEach(function (row) {
          if (Number(row.year) === Number(year) && String(row.name || '').toLowerCase() === name.toLowerCase()) hit = row;
        });
        var date = hit ? String(hit.date || '') : namedHolidayDate(Number(year), name);
        if (date) used[date] = true;
        lines.push([year, csvEscape(name), date].join(','));
      });
      list.forEach(function (row) {
        if (Number(row.year) !== Number(year)) return;
        var named = HOLIDAY_NAMES.some(function (name) {
          return String(row.name || '').toLowerCase() === name.toLowerCase();
        });
        if (named || used[row.date]) return;
        lines.push([year, csvEscape(row.name || ''), row.date].join(','));
      });
      lines.push([year, 'Company holiday', ''].join(','));
      lines.push([year, 'Company holiday', ''].join(','));
    });
    return lines.join('\r\n') + '\r\n';
  }

  function holidaySummary(rows, year) {
    var want = String(year);
    var list = (rows || []).filter(function (row) { return row.date && String(row.date).slice(0, 4) === want; });
    if (!list.length) return 'No holidays loaded. Every weekday counts.';
    return list.map(function (row) {
      return (row.name ? row.name + ' ' : '') + row.date;
    }).join(' · ');
  }

  return {
    yearWorkingDays: yearWorkingDays,
    monthWorkingDays: monthWorkingDays,
    daysOnPayroll: daysOnPayroll,
    splitMerit: splitMerit,
    accrue: accrue,
    parseHolidayCsv: parseHolidayCsv,
    mergeHolidayRows: mergeHolidayRows,
    holidayDatesForYear: holidayDatesForYear,
    holidayTemplateCsv: holidayTemplateCsv,
    holidaySummary: holidaySummary,
  };
});
