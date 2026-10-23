/* Statement commentary. The overview reads each statement paragraph in order.
   Line edits replace that sentence. An overview addition may only cite a number
   already on a statement. Account rows stay blank when the other side is not loaded. */
(function (global) {
  var picked = "mom";
  var viewPicked = "management";
  var gridFilter = "all";
  var opened = {};
  var draft = { reviews: {}, edits: {}, additions: {} };
  var COMPACT = { mom: "MoM", qoq: "QoQ", yoy: "YoY", ytd: "YTD", budget: "vs Budget", forecast: "vs Forecast" };
  var VIEWS = [
    ["management", "Management P&L"],
    ["income_statement", "Income statement"],
    ["balance_sheet", "Balance sheet"],
    ["cash_flow", "Cash flow"],
    ["gl", "GL"],
  ];

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function monthAdd(period, delta) {
    var year = parseInt(String(period).slice(0, 4), 10);
    var month = parseInt(String(period).slice(5, 7), 10) + delta;
    while (month < 1) {
      month += 12;
      year -= 1;
    }
    while (month > 12) {
      month -= 12;
      year += 1;
    }
    return year + "-" + (month < 10 ? "0" : "") + month;
  }

  function readAmount(ts, history, scenario, statement, period, key) {
    var block = (ts && ts[scenario]) || {};
    var row = block[statement] && block[statement][period];
    if (row && row[key] != null && row[key] !== "") return Number(row[key]);
    if (scenario === "Actual" && history && history[statement] && history[statement][period] && history[statement][period][key] != null) {
      return Number(history[statement][period][key]);
    }
    return null;
  }

  function sumAmounts(values) {
    if (values.some(function (value) { return value == null || !isFinite(value); })) return null;
    return Math.round(values.reduce(function (total, value) { return total + value; }, 0) * 100) / 100;
  }

  function booksPackage() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD || {};
    var ts = payload.TS_DATA || global.SMPL_TS_DATA || global.TS_DATA;
    var close = global.CLOSE_MONTH || global.SMPL_CLOSE_MONTH || (payload.meta && payload.meta.close_month);
    if (!ts || !close || String(close).length < 7) return null;
    var history = payload.HISTORY || {};
    var specs = [
      ["revenue", "Revenue", true],
      ["cogs", "Cost of revenue", false],
      ["gross_profit", "Gross profit", true],
      ["sm", "Sales and marketing", false],
      ["rd", "Research and development", false],
      ["ga", "General and administrative", false],
      ["total_opex", "Operating expenses", true],
      ["da", "Depreciation and amortization", false],
      ["interest", "Interest", false],
      ["tax", "Tax", false],
      ["net_income", "Net income", true],
    ];
    var balance = [
      ["cash", "Cash", true],
      ["total_assets", "Total assets", true],
      ["total_liabilities", "Total liabilities", true],
    ];
    var cash = [
      ["cfo", "Operating cash flow", true],
      ["cfi", "Investing cash flow", false],
      ["cff", "Financing cash flow", false],
      ["net_change", "Net change in cash", true],
      ["ending_cash", "Ending cash", true],
    ];
    function yearToDate(period) {
      var year = parseInt(String(period).slice(0, 4), 10);
      var month = parseInt(String(period).slice(5, 7), 10);
      var out = [];
      for (var index = 1; index <= month; index += 1) out.push(year + "-" + (index < 10 ? "0" : "") + index);
      return out;
    }
    function quarterOf(period) {
      var month = parseInt(String(period).slice(5, 7), 10);
      var start = month - ((month - 1) % 3);
      return [0, 1, 2].map(function (offset) { return monthAdd(period, start + offset - month); });
    }
    function linesFor(comparison, statement, table, spec, currentPeriods, basePeriods, baseScenario) {
      return spec
        .map(function (item) {
          var current = sumAmounts(currentPeriods.map(function (period) { return readAmount(ts, history, "Actual", table, period, item[0]); }));
          var base = sumAmounts(basePeriods.map(function (period) { return readAmount(ts, history, baseScenario, table, period, item[0]); }));
          if (current == null && base == null) return null;
          var variance = current == null || base == null ? null : Math.round((current - base) * 100) / 100;
          return {
            id: item[0],
            label: item[1],
            current: current,
            comparison_amount: base,
            variance: variance,
            commentary: "",
            review_required: item[2] || (variance != null && Math.abs(variance) >= 10000),
            key: comparison + "|" + statement + "|" + item[0],
            amounts: [],
          };
        })
        .filter(Boolean);
    }
    function statement(comparison, id, title, table, spec, currentPeriods, basePeriods, baseScenario) {
      var lines = linesFor(comparison, id, table, spec, currentPeriods, basePeriods, baseScenario);
      return { id: id, title: title, lines: lines, departments: [], accounts: [], accounts_note: "", paragraph_line_ids: lines.map(function (row) { return row.id; }), extra_line_ids: [], ties: true, tie_note: "" };
    }
    function glSide(scenario, period) {
      var block = (ts && ts[scenario]) || {};
      var gl = block.gl_opex && block.gl_opex[period];
      return gl && typeof gl === "object" ? gl : null;
    }
    function attachDetail(income, comparison, currentPeriods, basePeriods, baseScenario) {
      if (currentPeriods.length !== 1 || basePeriods.length !== 1) {
        income.accounts_note = "Account and department commentary is for a single month. This comparison is more than one month.";
        return;
      }
      var current = glSide("Actual", currentPeriods[0]);
      var base = glSide(baseScenario, basePeriods[0]);
      if (!current || !base) {
        income.accounts_note = "Account and department detail is not loaded for this comparison.";
        return;
      }
      var keys = {};
      Object.keys(current).forEach(function (key) { keys[key] = true; });
      Object.keys(base).forEach(function (key) { keys[key] = true; });
      var accounts = [];
      var byDept = {};
      Object.keys(keys).sort().forEach(function (key) {
        var parts = String(key).split("|");
        if (parts.length < 3 || !parts[0]) return;
        var line = parts[0];
        var dept = parts[1] || "Unassigned";
        var account = parts.slice(2).join("|") || "Unassigned";
        var cur = current[key] == null || current[key] === "" ? null : Number(current[key]);
        var cmp = base[key] == null || base[key] === "" ? null : Number(base[key]);
        var variance = cur == null || cmp == null || !isFinite(cur) || !isFinite(cmp) ? null : Math.round((cur - cmp) * 100) / 100;
        var row = {
          id: key,
          label: account,
          department: dept,
          line: line,
          current: cur,
          comparison_amount: cmp,
          variance: variance,
          commentary: variance == null ? "No comparison amount." : reasonText(account, variance, []),
          review_required: variance != null && Math.abs(variance) >= 10000,
          key: comparison + "|income_statement|" + dept + "|" + account,
          amounts: [],
        };
        accounts.push(row);
        (byDept[dept] = byDept[dept] || []).push(row);
      });
      income.accounts = accounts;
      income.departments = Object.keys(byDept).sort().map(function (dept) {
        var rows = byDept[dept];
        var incomplete = rows.some(function (row) { return row.variance == null; });
        var cur = incomplete ? null : Math.round(rows.reduce(function (sum, row) { return sum + Number(row.current || 0); }, 0) * 100) / 100;
        var cmp = incomplete ? null : Math.round(rows.reduce(function (sum, row) { return sum + Number(row.comparison_amount || 0); }, 0) * 100) / 100;
        var variance = cur == null || cmp == null ? null : Math.round((cur - cmp) * 100) / 100;
        return {
          id: dept,
          label: dept,
          department: dept,
          current: cur,
          comparison_amount: cmp,
          variance: variance,
          commentary: incomplete ? "Department comparison is incomplete." : reasonText(dept, variance, rows.map(function (row) { return [row.label, row.variance]; })),
          review_required: variance != null && Math.abs(variance) >= 10000,
          key: comparison + "|income_statement|dept|" + dept,
          amounts: [],
        };
      });
      if (!accounts.length) income.accounts_note = "No operating-expense accounts for this month.";
    }
    var prior = monthAdd(close, -1);
    var yearAgo = monthAdd(close, -12);
    var thisQuarter = quarterOf(close);
    var lastQuarter = quarterOf(monthAdd(thisQuarter[0], -1));
    var plans = [
      ["mom", "Month over month", [close], [prior], "Actual"],
      ["qoq", "Quarter over quarter", thisQuarter, lastQuarter, "Actual"],
      ["yoy", "Year over year", [close], [yearAgo], "Actual"],
      ["ytd", "Year to date", yearToDate(close), yearToDate(yearAgo), "Actual"],
      ["budget", "Versus budget", [close], [close], "Budget"],
      ["forecast", "Versus forecast", [close], [close], "Forecast"],
    ];
    return {
      close: close,
      comparisons: plans.map(function (plan) {
        var income = statement(plan[0], "income_statement", "Income statement", "is", specs, plan[2], plan[3], plan[4]);
        attachDetail(income, plan[0], plan[2], plan[3], plan[4]);
        var statements = [
          income,
          statement(plan[0], "balance_sheet", "Balance sheet", "bs", balance, plan[2], plan[3], plan[4]),
          statement(plan[0], "cash_flow", "Cash flow", "cfs", cash, plan[2], plan[3], plan[4]),
        ];
        var hasAmount = statements.some(function (item) {
          return (item.lines || []).some(function (row) { return row.current != null || row.comparison_amount != null; });
        });
        return {
          id: plan[0],
          label: plan[1],
          available: hasAmount,
          note: hasAmount ? "" : "This comparison is not loaded for " + close + ".",
          statements: hasAmount ? statements : [],
        };
      }),
    };
  }

  function package() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    var commentary = payload && payload.COMMENTARY;
    if (commentary && commentary.comparisons && commentary.comparisons.length) return commentary;
    return booksPackage();
  }

  function saved() {
    var status = global.SMPL_VALIDATION_STATUS;
    var commentary = status && status.commentary;
    return commentary || { reviews: {}, edits: {}, additions: {} };
  }

  function mergedReviews() {
    var out = {};
    var reviews = saved().reviews || {};
    Object.keys(reviews).forEach(function (key) {
      var record = reviews[key];
      if (record && record.reviewed) out[key] = true;
    });
    Object.keys(draft.reviews).forEach(function (key) {
      if (draft.reviews[key]) out[key] = true;
      else delete out[key];
    });
    return out;
  }

  function mergedEdits() {
    var out = Object.assign({}, saved().edits || {});
    Object.keys(draft.edits).forEach(function (key) {
      if (draft.edits[key]) out[key] = draft.edits[key];
      else delete out[key];
    });
    return out;
  }

  function mergedAdditions() {
    var out = Object.assign({}, saved().additions || {});
    Object.keys(draft.additions).forEach(function (key) {
      if (draft.additions[key]) out[key] = draft.additions[key];
      else delete out[key];
    });
    return out;
  }

  function dollars(text) {
    var source = String(text || "");
    var matches = source.match(/\$[0-9][0-9,]*(?:\.\d+)?/g) || [];
    var signs = source.match(/\$/g) || [];
    if (signs.length !== matches.length) return null;
    var values = [];
    for (var i = 0; i < matches.length; i++) {
      var raw = matches[i].slice(1).replace(/,/g, "");
      if (raw.indexOf(".") >= 0 && raw.split(".")[1].length !== 2) return null;
      values.push(Math.round(parseFloat(raw) * 100) / 100);
    }
    return values;
  }

  function textTies(text, amounts) {
    var cited = dollars(text);
    if (!cited) return false;
    return cited.every(function (amount) {
      return (amounts || []).some(function (allowed) {
        return Math.abs(amount - Number(allowed)) < 0.01;
      });
    });
  }

  function lineText(row) {
    var edited = mergedEdits()[row.key];
    return edited || row.commentary || "";
  }

  function reasonText(label, variance, parts) {
    if (variance == null) return label + " has no comparison amount.";
    var amount = Number(variance);
    if (Math.abs(amount) < 0.005) return label + " was unchanged.";
    var lead = label + (amount > 0 ? " rose " : " fell ") + money(Math.abs(amount));
    var useful = (parts || []).filter(function (part) {
      return part[1] != null && Math.abs(Number(part[1])) >= 0.5;
    });
    if (!useful.length) return lead + ".";
    var sum = useful.reduce(function (total, part) {
      return total + Number(part[1]);
    }, 0);
    if (Math.abs(Math.round(sum * 100) / 100 - amount) > 1) return lead + ".";
    var same = useful.filter(function (part) {
      return (Number(part[1]) > 0) === (amount > 0);
    });
    var opposite = useful.filter(function (part) {
      return (Number(part[1]) > 0) !== (amount > 0);
    });
    same.sort(function (a, b) {
      return Math.abs(b[1]) - Math.abs(a[1]);
    });
    opposite.sort(function (a, b) {
      return Math.abs(b[1]) - Math.abs(a[1]);
    });
    var chosen = same.slice(0, 3);
    if (opposite.length) chosen.push(opposite[0]);
    function clause(part) {
      return (Number(part[1]) > 0 ? "higher " : "lower ") + part[0] + " (" + money(part[1]) + ")";
    }
    var chunks = chosen.map(clause);
    var joined = chunks.length < 2 ? chunks[0] : chunks.slice(0, -1).join(", ") + " and " + chunks[chunks.length - 1];
    var cited = chosen.reduce(function (total, part) {
      return total + Number(part[1]);
    }, 0);
    var rest = Math.round((amount - cited) * 100) / 100;
    var text = lead + " because " + joined;
    if (Math.abs(rest) >= 0.5) text += "; other items (" + money(rest) + ")";
    return text + ".";
  }

  function reasonsFor(statement) {
    var lines = (statement && statement.lines) || [];
    var byId = {};
    lines.forEach(function (row) {
      byId[row.id] = row;
    });
    function effect(id, sign) {
      var row = byId[id];
      if (!row || row.variance == null) return null;
      return Math.round(sign * Number(row.variance) * 100) / 100;
    }
    function named(spec) {
      return spec
        .map(function (item) {
          return [item[1], effect(item[0], item[2])];
        })
        .filter(function (item) {
          return item[1] != null;
        });
    }
    var plans = {};
    if (statement.id === "income_statement") {
      plans.gross_profit = named([
        ["revenue", "revenue", 1],
        ["cogs", "cost of revenue", -1],
      ]);
      plans.total_opex = named([
        ["sm", "sales and marketing", 1],
        ["rd", "research and development", 1],
        ["ga", "general and administrative", 1],
      ]);
      plans.net_income = named([
        ["revenue", "revenue", 1],
        ["cogs", "cost of revenue", -1],
        ["total_opex", "operating expenses", -1],
        ["da", "depreciation and amortization", -1],
        ["interest", "interest", -1],
        ["tax", "tax", -1],
      ]);
      ["sm", "rd", "ga"].forEach(function (lineId) {
        plans[lineId] = (statement.accounts || [])
          .filter(function (row) {
            return row.line === lineId && row.variance != null;
          })
          .map(function (row) {
            return [row.label + " in " + row.department, Number(row.variance)];
          });
      });
    }
    if (statement.id === "cash_flow") {
      plans.net_change = named([
        ["cfo", "operating cash flow", 1],
        ["cfi", "investing cash flow", 1],
        ["cff", "financing cash flow", 1],
      ]);
    }
    var out = {};
    lines.forEach(function (row) {
      var edited = mergedEdits()[row.key];
      if (edited) {
        out[row.id] = edited;
        return;
      }
      if (row.commentary && String(row.commentary).indexOf(" because ") >= 0) {
        out[row.id] = row.commentary;
        return;
      }
      out[row.id] = plans[row.id] ? reasonText(row.label, row.variance, plans[row.id]) : lineText(row);
    });
    return out;
  }

  function paragraph(statement) {
    var byId = {};
    (statement.lines || []).forEach(function (row) {
      byId[row.id] = row;
    });
    var parts = [];
    var reasons = reasonsFor(statement);
    (statement.paragraph_line_ids || []).concat(statement.extra_line_ids || []).forEach(function (id) {
      if (byId[id]) parts.push(reasons[id] || lineText(byId[id]));
    });
    return parts.join(" ");
  }

  function comparison() {
    var book = package();
    if (!book) return null;
    var found = (book.comparisons || []).filter(function (item) {
      return item.id === picked;
    })[0];
    return found || (book.comparisons || [])[0] || null;
  }

  function money(value) {
    if (value == null || value === "") return "";
    var amount = Number(value);
    if (!isFinite(amount)) return "";
    var sign = amount < 0 ? "-" : "";
    return sign + "$" + Math.abs(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function rowsOf(statement) {
    return []
      .concat(statement.lines || [])
      .concat(statement.departments || [])
      .concat(statement.accounts || []);
  }

  function openCount() {
    var book = package();
    if (!book) return 0;
    var reviews = mergedReviews();
    var count = 0;
    (book.comparisons || []).forEach(function (item) {
      if (item.available === false) return;
      (item.statements || []).forEach(function (statement) {
        rowsOf(statement).forEach(function (row) {
          if (row.review_required && !reviews[row.key]) count += 1;
        });
      });
    });
    return count;
  }

  function persist() {
    var org = global.SMPL_ORG_ID;
    if (!org || !global.CLOSE_MONTH) return;
    var base = (global.SMPL_API_BASE || "/api/v1").replace(/\/$/, "");
    var url =
      base +
      "/validation-engine/commentary?organization_id=" +
      encodeURIComponent(org) +
      "&as_of_period=" +
      encodeURIComponent(global.CLOSE_MONTH);
    fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reviews: mergedReviews(),
        edits: mergedEdits(),
        additions: mergedAdditions(),
        reviewed_by: "FP&A Owner",
      }),
    })
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) throw new Error(body.detail || "commentary_save_failed");
          global.SMPL_VALIDATION_STATUS = body;
          draft = { reviews: {}, edits: {}, additions: {} };
        });
      })
      .catch(function (error) {
        global.alert(String(error.message || error));
      });
  }

  function pct(row) {
    if (row.variance == null || row.comparison_amount == null || !Number(row.comparison_amount)) return "";
    return ((Number(row.variance) / Number(row.comparison_amount)) * 100).toFixed(1) + "%";
  }

  function mark(row) {
    if (row.variance == null) return "";
    var up = { revenue: 1, gross_profit: 1, net_income: 1, cash: 1, total_assets: 1, cfo: 1, net_change: 1, ending_cash: 1 };
    var down = { cogs: 1, sm: 1, rd: 1, ga: 1, total_opex: 1, da: 1, interest: 1, tax: 1, compensation: 1, debt: 1 };
    var favorable = up[row.id] ? Number(row.variance) >= 0 : down[row.id] || row.department ? Number(row.variance) <= 0 : Number(row.variance) >= 0;
    return favorable ? "F" : "U";
  }

  function statementOf(item, id) {
    return (item.statements || []).filter(function (statement) {
      return statement.id === id;
    })[0];
  }

  function copyRow(row, depth) {
    var copy = {};
    Object.keys(row || {}).forEach(function (key) { copy[key] = row[key]; });
    copy.depth = depth;
    return copy;
  }

  var COMP_BUCKETS = [
    ["base", "Base salaries", /base salar|salaries and wages|^wages|regular wages|\bsalar/i],
    ["labor", "Labor", /^labor$|\blabor\b/i],
    ["bonus", "Bonuses", /bonus/i],
    ["commission", "Commissions", /commission/i],
    ["benefits", "Employee benefits", /benefit|health|medical/i],
    ["tax", "Payroll taxes", /payroll tax|employer tax/i],
    ["match", "401(k) employer match", /401|retirement match|employer match/i],
    ["sbc", "Stock-based compensation", /stock|share-based|\bsbc\b/i],
    ["severance", "Severance", /severance/i],
  ];
  var GROUP_ORDER = [
    { key: "sales", label: "Sales", line: "sm", depts: ["Sales"] },
    { key: "cs", label: "Customer Success", line: "sm", depts: ["Customer Success"] },
    { key: "marketing", label: "Marketing", line: "sm", depts: ["Marketing"] },
    { key: "rd", label: "R&D / Product", line: "rd", depts: ["R&D", "Product", "Engineering"] },
    { key: "ga", label: "G&A", line: "ga", depts: ["G&A", "Finance"] },
    { key: "support", label: "Support", line: "ga", depts: ["Support"] },
  ];

  function round2(value) {
    return Math.round(value * 100) / 100;
  }

  function sumLoaded(values) {
    if (values.some(function (value) { return value == null || !isFinite(value); })) return null;
    return round2(values.reduce(function (total, value) { return total + value; }, 0));
  }

  function booksTs() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD || {};
    var commentary = payload.COMMENTARY;
    var close = (commentary && commentary.close) || global.CLOSE_MONTH || global.SMPL_CLOSE_MONTH || (payload.meta && payload.meta.close_month) || "";
    return {
      ts: payload.TS_DATA || global.SMPL_TS_DATA || global.TS_DATA || null,
      history: payload.HISTORY || {},
      close: String(close),
    };
  }

  function periodAmount(src, scenario, table, period, keys) {
    var list = Array.isArray(keys) ? keys : [keys];
    var block = (src.ts && src.ts[scenario]) || {};
    var row = block[table] && block[table][period];
    var index;
    if (row) {
      for (index = 0; index < list.length; index += 1) {
        if (row[list[index]] != null && row[list[index]] !== "") return Number(row[list[index]]);
      }
    }
    if (scenario === "Actual" && src.history && src.history[table] && src.history[table][period]) {
      row = src.history[table][period];
      for (index = 0; index < list.length; index += 1) {
        if (row[list[index]] != null && row[list[index]] !== "") return Number(row[list[index]]);
      }
    }
    return null;
  }

  function quarterPeriods(period) {
    var month = parseInt(String(period).slice(5, 7), 10);
    var start = month - ((month - 1) % 3);
    return [0, 1, 2].map(function (offset) { return monthAdd(period, start + offset - month); });
  }

  function yearPeriods(period) {
    var year = parseInt(String(period).slice(0, 4), 10);
    var month = parseInt(String(period).slice(5, 7), 10);
    var out = [];
    for (var index = 1; index <= month; index += 1) out.push(year + "-" + (index < 10 ? "0" : "") + index);
    return out;
  }

  function windowFor(item) {
    var src = booksTs();
    if (!item || src.close.length < 7) return null;
    var close = src.close;
    var prior = monthAdd(close, -1);
    var yearAgo = monthAdd(close, -12);
    var plans = {
      mom: [[close], [prior], "Actual"],
      yoy: [[close], [yearAgo], "Actual"],
      ytd: [yearPeriods(close), yearPeriods(yearAgo), "Actual"],
      budget: [[close], [close], "Budget"],
      forecast: [[close], [close], "Forecast"],
    };
    var quarter = quarterPeriods(close);
    plans.qoq = [quarter, quarterPeriods(monthAdd(quarter[0], -1)), "Actual"];
    var plan = plans[item.id];
    if (!plan) return null;
    return { id: item.id, current: plan[0], base: plan[1], scenario: plan[2], src: src };
  }

  function sideSum(win, side, table, keys) {
    var scenario = side === "base" ? win.scenario : "Actual";
    return sumLoaded(win[side].map(function (period) { return periodAmount(win.src, scenario, table, period, keys); }));
  }

  function detailMaps(win, side, field, line) {
    var scenario = side === "base" ? win.scenario : "Actual";
    var block = (win.src.ts && win.src.ts[scenario]) || {};
    var bag = block[field];
    if (!bag) return null;
    var maps = [];
    var missing = false;
    win[side].forEach(function (period) {
      var gl = bag[period];
      if (!gl || typeof gl !== "object") {
        missing = true;
        return;
      }
      if (!line) {
        maps.push(gl);
        return;
      }
      var filtered = {};
      Object.keys(gl).forEach(function (key) {
        if (String(key).split("|")[0] === line) filtered[key] = gl[key];
      });
      maps.push(filtered);
    });
    return missing ? null : maps;
  }

  function glMaps(win, side) {
    return detailMaps(win, side, "gl_opex");
  }

  function glSum(maps, key) {
    if (!maps) return null;
    var total = 0;
    maps.forEach(function (map) { total += Number(map[key] || 0); });
    return round2(total);
  }

  function makeRow(spec) {
    var current = spec.current;
    var base = spec.base;
    var variance = current == null || base == null ? null : round2(current - base);
    return {
      id: spec.id,
      label: spec.label,
      current: current,
      comparison_amount: base,
      variance: variance,
      commentary: spec.commentary || "",
      review_required: spec.review != null ? spec.review : variance != null && Math.abs(variance) >= 10000,
      key: spec.key,
      amounts: [],
      depth: spec.depth || 0,
      expandable: !!spec.expandable,
      department: spec.department || "",
    };
  }

  function packaged(lines, id) {
    var found = null;
    (lines || []).some(function (row) {
      if (row.id === id) {
        found = row;
        return true;
      }
      return false;
    });
    return found;
  }

  function useLine(line, depth) {
    if (!line) return null;
    var row = copyRow(line, depth);
    row.expandable = false;
    return row;
  }

  function metricRow(win, table, id, label, depth, keys) {
    if (!win) return null;
    var current = sideSum(win, "current", table, keys || id);
    var base = sideSum(win, "base", table, keys || id);
    if (current == null && base == null) return null;
    return makeRow({
      id: id,
      label: label,
      current: current,
      base: base,
      depth: depth,
      key: win.id + "|" + table + "|" + id,
    });
  }

  function lineOrMetric(lines, win, id, label, depth, keys) {
    var line = packaged(lines, id);
    if (line) return useLine(line, depth);
    return metricRow(win, "is", id, label, depth, keys || id);
  }

  function shownAmount(current, base) {
    return !((current == null || current === 0) && (base == null || base === 0));
  }

  function laborBucket(name) {
    var text = String(name || "");
    var index;
    for (index = 0; index < COMP_BUCKETS.length; index += 1) {
      if (COMP_BUCKETS[index][2].test(text)) return COMP_BUCKETS[index];
    }
    if (/salar|wage|payroll|benefit|bonus|commission|severance|401|compensation|stock/i.test(text)) return ["other", "Other compensation"];
    return null;
  }

  function groupFor(line, dept) {
    var index;
    for (index = 0; index < GROUP_ORDER.length; index += 1) {
      if (GROUP_ORDER[index].line === line && GROUP_ORDER[index].depts.indexOf(dept) >= 0) return GROUP_ORDER[index];
    }
    return { key: "dept:" + dept, label: dept, line: line, depts: [dept] };
  }

  function accountEntries(curMaps, baseMaps) {
    var keys = {};
    [curMaps, baseMaps].forEach(function (maps) {
      (maps || []).forEach(function (map) {
        Object.keys(map).forEach(function (key) { keys[key] = true; });
      });
    });
    return Object.keys(keys).map(function (key) {
      var parts = String(key).split("|");
      return {
        key: key,
        line: parts[0] || "",
        dept: parts[1] || "Unassigned",
        account: parts.slice(2).join("|") || "Unassigned",
        current: glSum(curMaps, key),
        base: glSum(baseMaps, key),
      };
    }).filter(function (row) { return row.line && shownAmount(row.current, row.base); });
  }

  function sumSide(rows, field) {
    if (!rows.length || rows.some(function (row) { return row[field] == null; })) return null;
    return round2(rows.reduce(function (total, row) { return total + Number(row[field] || 0); }, 0));
  }

  function spendCategory(name) {
    var text = String(name || "");
    if (/sales travel/i.test(text)) return null;
    if (/travel|entertainment|airfare|flight|lodging|hotel|\bmeal|\bmeals\b|\bfood\b/i.test(text)) return ["travel", "Travel and Entertainment"];
    if (/software tools?/i.test(text)) return ["software-tools", "Software tools"];
    return null;
  }

  function varianceOf(current, base) {
    if (current == null || base == null) return null;
    return round2(current - base);
  }

  function pieceLabel(account, rows) {
    var names = {};
    rows.forEach(function (row) { names[row.account] = true; });
    if (Object.keys(names).length === 1) return account.dept || account.account;
    return account.account + (account.dept ? " — " + account.dept : "");
  }

  function rollupLabel(rows, fallback) {
    var names = [];
    rows.forEach(function (row) {
      if (names.indexOf(row.account) < 0) names.push(row.account);
    });
    return names.length === 1 ? names[0] : fallback;
  }

  function pushGroup(target, win, lineId, group, accounts, depth) {
    var labor = [];
    var other = [];
    accounts.forEach(function (account) {
      if (laborBucket(account.account)) labor.push(account);
      else other.push(account);
    });
    var slots = {};
    labor.forEach(function (account) {
      var bucket = laborBucket(account.account);
      var slot = slots[bucket[0]] || (slots[bucket[0]] = { label: bucket[1], rows: [] });
      slot.rows.push(account);
    });
    var bucketRows = COMP_BUCKETS.concat([["other", "Other compensation"]]).map(function (bucket) {
      var slot = slots[bucket[0]];
      if (!slot) return null;
      var current = sumSide(slot.rows, "current");
      var base = sumSide(slot.rows, "base");
      if (!shownAmount(current, base)) return null;
      return makeRow({
        id: lineId + ":" + group.key + ":" + bucket[0],
        label: bucket[1],
        current: current,
        base: base,
        depth: depth + 2,
        department: group.label,
        commentary: reasonText(bucket[1], varianceOf(current, base), []),
        key: win.id + "|income_statement|" + lineId + "|" + group.key + "|" + bucket[0],
      });
    }).filter(Boolean);
    var spend = {};
    other.forEach(function (account) {
      var category = spendCategory(account.account);
      var key = category ? "cat:" + category[0] : "name:" + String(account.account).toLowerCase();
      var slot = spend[key] || (spend[key] = { label: category ? category[1] : account.account, rows: [] });
      slot.rows.push(account);
    });
    var discRows = Object.keys(spend).map(function (key) {
      var slot = spend[key];
      var label = rollupLabel(slot.rows, slot.label);
      var current = sumSide(slot.rows, "current");
      var base = sumSide(slot.rows, "base");
      if (!shownAmount(current, base)) return null;
      var kids = slot.rows.length > 1 ? slot.rows.slice().sort(function (a, b) {
        return pieceLabel(a, slot.rows).localeCompare(pieceLabel(b, slot.rows));
      }).map(function (account) {
        var piece = pieceLabel(account, slot.rows);
        return makeRow({
          id: account.key,
          label: piece,
          current: account.current,
          base: account.base,
          depth: depth + 2,
          department: account.dept,
          commentary: reasonText(piece, varianceOf(account.current, account.base), []),
          key: win.id + "|income_statement|" + lineId + "|" + group.key + "|" + key + "|" + account.dept + "|" + account.account,
        });
      }) : [];
      return {
        row: makeRow({
          id: lineId + ":" + group.key + ":" + key,
          label: label,
          current: current,
          base: base,
          depth: depth + 1,
          expandable: kids.length > 0,
          department: group.label,
          commentary: reasonText(label, varianceOf(current, base), kids.map(function (row) { return [row.label, row.variance]; })),
          key: win.id + "|income_statement|" + lineId + "|" + group.key + "|" + key,
        }),
        kids: kids,
      };
    }).filter(Boolean).sort(function (a, b) { return a.row.label.localeCompare(b.row.label); });
    var nested = [];
    if (bucketRows.length) {
      var compCurrent = sumSide(bucketRows, "current");
      var compBase = sumSide(bucketRows, "comparison_amount");
      nested.push(makeRow({
        id: lineId + ":" + group.key + ":compensation",
        label: "Compensation",
        current: compCurrent,
        base: compBase,
        depth: depth + 1,
        expandable: true,
        department: group.label,
        commentary: reasonText("Compensation", varianceOf(compCurrent, compBase), bucketRows.map(function (row) { return [row.label, row.variance]; })),
        key: win.id + "|income_statement|" + lineId + "|" + group.key + "|compensation",
      }));
      bucketRows.forEach(function (row) { nested.push(row); });
    }
    discRows.forEach(function (item) {
      nested.push(item.row);
      item.kids.forEach(function (row) { nested.push(row); });
    });
    var groupCurrent = sumSide(accounts, "current");
    var groupBase = sumSide(accounts, "base");
    var direct = nested.filter(function (row) { return row.depth === depth + 1; });
    target.push(makeRow({
      id: lineId + ":" + group.key,
      label: group.label,
      current: groupCurrent,
      base: groupBase,
      depth: depth,
      expandable: nested.length > 0,
      department: group.label,
      commentary: reasonText(group.label, varianceOf(groupCurrent, groupBase), direct.map(function (row) { return [row.label, row.variance]; })),
      key: win.id + "|income_statement|" + lineId + "|" + group.key,
    }));
    nested.forEach(function (row) { target.push(row); });
  }

  function groupsFor(line, accounts) {
    var byKey = {};
    accounts.filter(function (account) { return account.line === line; }).forEach(function (account) {
      var group = groupFor(line, account.dept);
      (byKey[group.key] = byKey[group.key] || { group: group, accounts: [] }).accounts.push(account);
    });
    var ordered = [];
    GROUP_ORDER.forEach(function (group) {
      if (group.line === line && byKey[group.key]) ordered.push(byKey[group.key]);
    });
    Object.keys(byKey).sort().forEach(function (key) {
      if (!ordered.some(function (item) { return item.group.key === key; })) ordered.push(byKey[key]);
    });
    return ordered;
  }

  function opexEntries(win) {
    if (!win) return [];
    return accountEntries(glMaps(win, "current"), glMaps(win, "base"));
  }

  function cogsEntries(win) {
    if (!win) return [];
    return accountEntries(detailMaps(win, "current", "gl_expense_types", "cogs"), detailMaps(win, "base", "gl_expense_types", "cogs"));
  }

  function appendFunction(rows, lines, win, entries, id, label) {
    var kids = [];
    if (win) groupsFor(id, entries).forEach(function (item) { pushGroup(kids, win, id, item.group, item.accounts, 1); });
    var line = lineOrMetric(lines, win, id, label, 0);
    if (!line && !kids.length) return;
    if (!line) {
      line = makeRow({ id: id, label: label, current: sumSide(kids.filter(function (row) { return row.depth === 1; }), "current"), base: sumSide(kids.filter(function (row) { return row.depth === 1; }), "comparison_amount"), depth: 0, key: (win ? win.id : "x") + "|is|" + id });
    }
    line.expandable = kids.length > 0;
    rows.push(line);
    kids.forEach(function (row) { rows.push(row); });
  }

  function rollupBag(win, side) {
    var scenario = side === "base" ? win.scenario : "Actual";
    var block = (win.src.ts && win.src.ts[scenario]) || {};
    var bag = block.gl_rollup;
    if (!bag || typeof bag !== "object") return null;
    var trees = [];
    var missing = false;
    win[side].forEach(function (period) {
      var tree = bag[period];
      if (!tree || !Array.isArray(tree.lines)) {
        missing = true;
        return;
      }
      trees.push(tree);
    });
    if (missing || !trees.length) return null;
    return { lines: mergeNodeLists(trees.map(function (tree) { return tree.lines; })) };
  }

  function mergeNodeLists(lists) {
    var byId = {};
    var order = [];
    lists.forEach(function (list) {
      (list || []).forEach(function (node) {
        if (!byId[node.id]) {
          byId[node.id] = {
            id: node.id,
            label: node.label,
            role: node.role,
            statement_line: node.statement_line,
            line_key: node.line_key || "",
            merged_child: node.merged_child || "",
            amount: 0,
            _lists: [],
          };
          order.push(node.id);
        }
        var slot = byId[node.id];
        slot.amount = round2(slot.amount + Number(node.amount || 0));
        if (node.merged_child) slot.merged_child = node.merged_child;
        if (node.label) slot.label = node.label;
        slot._lists.push(node.children || []);
      });
    });
    return order.map(function (id) {
      var slot = byId[id];
      slot.children = mergeNodeLists(slot._lists);
      delete slot._lists;
      return slot;
    });
  }

  function reportingTrees(win) {
    if (!global.SMPL_REPORTING_ENGINE || !win) return null;
    var current = rollupBag(win, "current");
    var base = rollupBag(win, "base");
    if (!current || !base) return null;
    return { current: current, base: base };
  }

  function findRollupLine(tree, statementLine) {
    var lines = (tree && tree.lines) || [];
    for (var index = 0; index < lines.length; index += 1) {
      if (lines[index].statement_line === statementLine || lines[index].line_key === statementLine) return lines[index];
    }
    return null;
  }

  function findFunction(tree, key) {
    var opex = findRollupLine(tree, "opex");
    var kids = (opex && opex.children) || [];
    for (var index = 0; index < kids.length; index += 1) {
      if (kids[index].line_key === key) return kids[index];
    }
    return null;
  }

  function hasFunctions(tree) {
    return !!(findFunction(tree, "sm") || findFunction(tree, "rd") || findFunction(tree, "ga") || findFunction(tree, "undivided"));
  }

  function zipNodes(current, base, depth, win) {
    var byId = {};
    var order = [];
    function take(list, side) {
      (list || []).forEach(function (node) {
        if (!byId[node.id]) {
          byId[node.id] = {};
          order.push(node.id);
        }
        byId[node.id][side] = node;
      });
    }
    take(current, "current");
    take(base, "base");
    var rows = [];
    order.forEach(function (id) {
      var pair = byId[id];
      var cur = pair.current || {};
      var bas = pair.base || {};
      var label = cur.label || bas.label || "Line";
      var kids = zipNodes(cur.children, bas.children, depth + 1, win);
      var direct = kids.filter(function (row) { return row.depth === depth + 1; });
      var currentAmount = pair.current ? cur.amount : null;
      var baseAmount = pair.base ? bas.amount : null;
      rows.push(makeRow({
        id: id,
        label: label,
        current: currentAmount,
        base: baseAmount,
        depth: depth,
        expandable: direct.length > 0,
        commentary: reasonText(label, varianceOf(currentAmount, baseAmount), direct.map(function (child) { return [child.label, child.variance]; })),
        key: win.id + "|glrollup|" + id,
      }));
      kids.forEach(function (child) { rows.push(child); });
    });
    return rows;
  }

  function attachChildren(line, currentNodes, baseNodes, win) {
    var kids = zipNodes(currentNodes, baseNodes, (line.depth || 0) + 1, win);
    var direct = kids.filter(function (row) { return row.depth === (line.depth || 0) + 1; });
    line.expandable = direct.length > 0;
    if (line.expandable && !line.commentary) {
      line.commentary = reasonText(line.label, line.variance, direct.map(function (row) { return [row.label, row.variance]; }));
    }
    return kids;
  }

  function pushRollupLine(rows, lines, win, id, label, currentNode, baseNode) {
    var currentNodes = (currentNode && currentNode.children) || [];
    var baseNodes = (baseNode && baseNode.children) || [];
    var line = lineOrMetric(lines, win, id, label, 0);
    if (!line && !currentNodes.length && !baseNodes.length) return;
    if (!line) {
      line = makeRow({
        id: id,
        label: label,
        current: currentNodes.length ? round2(currentNodes.reduce(function (total, node) { return total + Number(node.amount || 0); }, 0)) : null,
        base: baseNodes.length ? round2(baseNodes.reduce(function (total, node) { return total + Number(node.amount || 0); }, 0)) : null,
        depth: 0,
        key: win.id + "|is|" + id,
      });
    }
    var rename = (currentNode && currentNode.merged_child && currentNode.label) || (baseNode && baseNode.merged_child && baseNode.label) || "";
    if (rename) line.label = rename;
    var kids = attachChildren(line, currentNodes, baseNodes, win);
    rows.push(line);
    kids.forEach(function (row) { rows.push(row); });
  }

  function buildIncomeFromRollup(item, income, win, trees) {
    var lines = (income && income.lines) || [];
    var rows = [];
    pushRollupLine(rows, lines, win, "revenue", "Revenue", findRollupLine(trees.current, "revenue"), findRollupLine(trees.base, "revenue"));
    pushRollupLine(rows, lines, win, "cogs", "Cost of revenue", findRollupLine(trees.current, "cogs"), findRollupLine(trees.base, "cogs"));
    [lineOrMetric(lines, win, "gross_profit", "Gross profit", 0)].forEach(function (row) { if (row) rows.push(row); });
    var functions = hasFunctions(trees.current) || hasFunctions(trees.base);
    if (functions) {
      [["sm", "Sales and marketing"], ["rd", "Research and development"], ["ga", "General and administrative"]].forEach(function (pair) {
        pushRollupLine(rows, lines, win, pair[0], pair[1], findFunction(trees.current, pair[0]), findFunction(trees.base, pair[0]));
      });
      if (findFunction(trees.current, "undivided") || findFunction(trees.base, "undivided")) {
        pushRollupLine(rows, lines, win, "unmapped", "Unmapped operating expense", findFunction(trees.current, "undivided"), findFunction(trees.base, "undivided"));
      }
      var totalOpex = lineOrMetric(lines, win, "total_opex", "Operating expenses", 0);
      if (totalOpex) rows.push(totalOpex);
    } else {
      var opexLine = lineOrMetric(lines, win, "total_opex", "Operating expenses", 0);
      if (opexLine) {
        var opexKids = attachChildren(opexLine, ((findRollupLine(trees.current, "opex") || {}).children) || [], ((findRollupLine(trees.base, "opex") || {}).children) || [], win);
        rows.push(opexLine);
        opexKids.forEach(function (row) { rows.push(row); });
      }
    }
    [metricRow(win, "is", "ebitda", "EBITDA", 0, "ebitda")].forEach(function (row) { if (row) rows.push(row); });
    pushRollupLine(rows, lines, win, "da", "Depreciation and amortization", findRollupLine(trees.current, "da"), findRollupLine(trees.base, "da"));
    [metricRow(win, "is", "op_income", "Operating income", 0, "op_income")].forEach(function (row) { if (row) rows.push(row); });
    pushRollupLine(rows, lines, win, "interest", "Interest", findRollupLine(trees.current, "interest"), findRollupLine(trees.base, "interest"));
    [metricRow(win, "is", "pretax", "Pretax income", 0, "pretax")].forEach(function (row) { if (row) rows.push(row); });
    pushRollupLine(rows, lines, win, "tax", "Tax", findRollupLine(trees.current, "tax"), findRollupLine(trees.base, "tax"));
    [lineOrMetric(lines, win, "net_income", "Net income", 0)].forEach(function (row) { if (row) rows.push(row); });
    return rows;
  }

  function buildIncome(item, income) {
    var win = windowFor(item);
    var trees = reportingTrees(win);
    if (trees) return buildIncomeFromRollup(item, income, win, trees);
    var lines = (income && income.lines) || [];
    var entries = opexEntries(win);
    var rows = [];
    var revenue = lineOrMetric(lines, win, "revenue", "Revenue", 0);
    var revenueKids = [];
    if (win) {
      [["sub_rev", "Subscription revenue"], ["rec_svc_rev", "Recurring services"], ["impl_rev", "Implementation and onboarding"]].forEach(function (pair) {
        var row = metricRow(win, "is", pair[0], pair[1], 1, pair[0]);
        if (row) revenueKids.push(row);
      });
    }
    if (revenue) {
      revenue.expandable = revenueKids.length > 0;
      rows.push(revenue);
      revenueKids.forEach(function (row) { rows.push(row); });
    }
    appendFunction(rows, lines, win, cogsEntries(win), "cogs", "Cost of revenue");
    [lineOrMetric(lines, win, "gross_profit", "Gross profit", 0)].forEach(function (row) { if (row) rows.push(row); });
    appendFunction(rows, lines, win, entries, "sm", "Sales and marketing");
    appendFunction(rows, lines, win, entries, "rd", "Research and development");
    appendFunction(rows, lines, win, entries, "ga", "General and administrative");
    appendFunction(rows, lines, win, entries, "unmapped", "Unmapped operating expense");
    [lineOrMetric(lines, win, "total_opex", "Operating expenses", 0), metricRow(win, "is", "ebitda", "EBITDA", 0, "ebitda"), lineOrMetric(lines, win, "da", "Depreciation and amortization", 0), lineOrMetric(lines, win, "interest", "Interest", 0), metricRow(win, "is", "op_income", "Operating income", 0, "op_income"), metricRow(win, "is", "pretax", "Pretax income", 0, "pretax"), lineOrMetric(lines, win, "tax", "Tax", 0), lineOrMetric(lines, win, "net_income", "Net income", 0)].forEach(function (row) { if (row) rows.push(row); });
    return rows;
  }

  function buildSection(rows, lines, win, table, section) {
    var kids = [];
    section.children.forEach(function (child) {
      var row = packaged(lines, child[0]);
      if (row) {
        row = useLine(row, 1);
        kids.push(row);
        return;
      }
      row = metricRow(win, table, child[0], child[1], 1, child[2]);
      if (row) kids.push(row);
    });
    var parent = useLine(packaged(lines, section.id), 0) || metricRow(win, table, section.id, section.label, 0, section.keys);
    if (!parent && !kids.length) return;
    if (!parent) parent = makeRow({ id: section.id, label: section.label, current: null, base: null, depth: 0, key: (win ? win.id : "x") + "|" + table + "|" + section.id });
    parent.expandable = kids.length > 0;
    rows.push(parent);
    kids.forEach(function (row) { rows.push(row); });
  }

  function buildCash(item, statement) {
    var win = windowFor(item);
    var lines = (statement && statement.lines) || [];
    var rows = [];
    [
      { id: "cfo", label: "Operating cash flow", keys: ["cfo"], children: [["ni", "Net income", ["ni", "net_income"]], ["da", "Depreciation and amortization", ["da"]], ["sbc", "Stock-based compensation", ["sbc"]], ["chg_ar", "Change in accounts receivable", ["chg_ar"]], ["chg_dr", "Change in deferred revenue", ["chg_dr"]], ["chg_ap", "Change in accounts payable", ["chg_ap"]], ["chg_pre", "Change in prepaids", ["chg_pre", "chg_prepaids"]], ["chg_dc", "Change in deferred commissions", ["chg_dc", "chg_deferred_commissions"]], ["other_non_cash", "Other non-cash items", ["other_non_cash"]]] },
      { id: "cfi", label: "Investing cash flow", keys: ["cfi"], children: [["capex", "Capital expenditures", ["capex"]], ["chg_other_assets", "Change in other assets", ["chg_other_assets"]]] },
      { id: "cff", label: "Financing cash flow", keys: ["cff"], children: [["debt_financing", "Debt issuance and repayment", ["debt"]], ["equity_issuance", "Equity issuance", ["equity_issuance"]]] },
    ].forEach(function (section) { buildSection(rows, lines, win, "cfs", section); });
    [useLine(packaged(lines, "beg_cash"), 0) || metricRow(win, "cfs", "beg_cash", "Beginning cash", 0, ["beg_cash", "beginning_cash"]), useLine(packaged(lines, "net_change"), 0) || metricRow(win, "cfs", "net_change", "Net change in cash", 0, ["net_change"]), useLine(packaged(lines, "ending_cash"), 0) || metricRow(win, "cfs", "ending_cash", "Ending cash", 0, ["end_cash", "ending_cash"])].forEach(function (row) { if (row) rows.push(row); });
    return rows;
  }

  function buildBalance(item, statement) {
    var win = windowFor(item);
    var lines = (statement && statement.lines) || [];
    var rows = [];
    [
      { id: "total_assets", label: "Total assets", keys: ["total_assets"], children: [["cash", "Cash", ["cash"]], ["ar", "Accounts receivable", ["ar"]], ["prepaids", "Prepaids and other current", ["prepaids"]], ["deferred_commissions_current", "Deferred commissions, current", ["deferred_commissions_current"]], ["deferred_commissions_noncurrent", "Deferred commissions, noncurrent", ["deferred_commissions_noncurrent"]], ["ppe", "Property and equipment, net", ["ppe"]], ["other_assets", "Other assets", ["other_assets"]]] },
      { id: "total_liabilities", label: "Total liabilities", keys: ["total_liabilities", "total_liab"], children: [["ap", "Accounts payable", ["ap"]], ["deferred_rev", "Deferred revenue", ["deferred_rev", "dr"]], ["debt", "Debt", ["debt"]], ["other_liab", "Other liabilities", ["other_liabilities", "other_liab"]]] },
      { id: "equity", label: "Total equity", keys: ["equity"], children: [["paid_in_capital", "Paid-in capital", ["paid_in_capital"]], ["apic_sbc", "APIC, stock compensation", ["apic_sbc"]], ["retained_earnings", "Retained earnings", ["retained_earnings"]], ["current_period_net_income", "Net income, current period", ["current_period_net_income"]]] },
    ].forEach(function (section) { buildSection(rows, lines, win, "bs", section); });
    var total = useLine(packaged(lines, "total_le"), 0) || metricRow(win, "bs", "total_le", "Total liabilities and equity", 0, ["total_le"]);
    if (total) rows.push(total);
    return rows.length ? rows : (lines || []).map(function (row) { return copyRow(row, 0); });
  }

  function applyOpen(rows, reviews) {
    if (gridFilter !== "all") {
      var keep = {};
      rows.forEach(function (row, index) {
        var match = gridFilter === "needs" ? !!row.review_required : !!row.review_required && !reviews[row.key];
        if (!match) return;
        keep[index] = true;
        var depth = row.depth || 0;
        for (var cursor = index - 1; cursor >= 0 && depth > 0; cursor -= 1) {
          if ((rows[cursor].depth || 0) < depth) {
            keep[cursor] = true;
            depth = rows[cursor].depth || 0;
          }
        }
      });
      return rows.filter(function (_row, index) { return keep[index]; });
    }
    var hidden = null;
    return rows.filter(function (row) {
      var depth = row.depth || 0;
      if (hidden != null && depth > hidden) return false;
      hidden = null;
      if (row.expandable && !opened[row.key]) hidden = depth;
      return true;
    });
  }

  function gridSource(item) {
    var income = statementOf(item, "income_statement");
    if (viewPicked === "gl") {
      var win = windowFor(item);
      var trees = reportingTrees(win);
      if (trees) {
        var built = buildIncome(item, income);
        var forest = [];
        var open = false;
        var showTotal = !built.some(function (row) { return (row.depth || 0) === 0 && (row.id === "sm" || row.id === "rd" || row.id === "ga"); });
        built.forEach(function (row) {
          if ((row.depth || 0) === 0) {
            open = row.id === "cogs" || row.id === "sm" || row.id === "rd" || row.id === "ga" || row.id === "unmapped" || (showTotal && row.id === "total_opex");
          }
          if (open) forest.push(row);
        });
        return { statement: income, rows: forest, note: "Cost of revenue and operating expense, opened to the departments and accounts in the file." };
      }
      var entries = opexEntries(win);
      var cogs = cogsEntries(win);
      var forest = [];
      var lines = (income && income.lines) || [];
      if (cogs.length) appendFunction(forest, lines, win, cogs, "cogs", "Cost of revenue");
      if (entries.length) {
        appendFunction(forest, lines, win, entries, "sm", "Sales and marketing");
        appendFunction(forest, lines, win, entries, "rd", "Research and development");
        appendFunction(forest, lines, win, entries, "ga", "General and administrative");
        appendFunction(forest, lines, win, entries, "unmapped", "Unmapped operating expense");
      }
      if (forest.length) {
        return { statement: income, rows: forest, note: "Open cost of revenue or a function, then a team. General and administrative opens into G&A and Support. Compensation opens into the pay elements. Travel and entertainment and software tools open into the departments or categories in that line, and the commentary is written from those pieces." };
      }
      var accounts = (income && income.accounts) || [];
      var grouped = [];
      var deptNames = [];
      accounts.forEach(function (row) {
        if (deptNames.indexOf(row.department) < 0) deptNames.push(row.department);
      });
      deptNames.sort().forEach(function (dept) {
        var deptRow = ((income && income.departments) || []).filter(function (row) { return row.department === dept; })[0];
        if (deptRow) {
          var parent = copyRow(deptRow, 0);
          parent.expandable = accounts.some(function (row) { return row.department === dept; });
          grouped.push(parent);
        }
        accounts.filter(function (row) { return row.department === dept; }).forEach(function (row) {
          grouped.push(copyRow(row, 1));
        });
      });
      return {
        statement: income,
        rows: grouped,
        note: grouped.length ? "Departments, then the GL accounts in each department." : ((income && income.accounts_note) || "Account and department detail is not loaded for this comparison."),
      };
    }
    if (viewPicked === "management" || viewPicked === "income_statement") {
      var built = buildIncome(item, income);
      var rollupNote = viewPicked === "management"
        ? "Management P&L. Same recognized dollars as the income statement. No allocations loaded. Open a line for the departments and accounts in the file."
        : "Open a line for the departments, expense types, and accounts in the file.";
      var legacyNote = viewPicked === "management"
        ? "Management P&L. Same recognized dollars as the income statement until a management layer is loaded. Open revenue and cost of revenue for their lines. General and administrative opens into G&A and Support. Travel and entertainment and software tools open into the pieces behind the line."
        : "Open revenue for subscription, recurring services, and implementation. Open cost of revenue for the teams and cost lines. General and administrative opens into G&A and Support. Compensation opens into the pay elements. Travel and entertainment and software tools open into the departments or categories in that line, and the commentary is written from those pieces.";
      var note = reportingTrees(windowFor(item)) ? rollupNote : legacyNote;
      if (!built.length && income && income.accounts_note) note = income.accounts_note;
      return { statement: income, rows: built, note: note };
    }
    if (viewPicked === "cash_flow") {
      var cash = statementOf(item, "cash_flow");
      return { statement: cash, rows: buildCash(item, cash), note: "Open operating, investing, and financing for the lines on the cash flow statement." };
    }
    if (viewPicked === "balance_sheet") {
      var balance = statementOf(item, "balance_sheet");
      return { statement: balance, rows: buildBalance(item, balance), note: "Open each total for the lines on the balance sheet." };
    }
    var statement = statementOf(item, viewPicked);
    return { statement: statement, rows: ((statement && statement.lines) || []).map(function (row) { return copyRow(row, 0); }), note: "" };
  }

  function businessHtml() {
    var sections = [
      ["ARR, customers, and sales", "arr"],
      ["Gross margin", "revenue"],
      ["Cash and runway", "cash"],
      ["Workforce", "headcount"],
      ["Takeaways", "risks"],
    ];
    if (typeof global.boardDataCommentary !== "function") return "";
    var html = sections
      .map(function (pair) {
        var text = global.boardDataCommentary(pair[1]) || "";
        if (!text || text.indexOf("Commentary unavailable") === 0) return "";
        if (pair[1] === "cash" && typeof global.boardCashYearWalk === "function") {
          var walk = global.boardCashYearWalk();
          if (walk && walk.runwayMonths != null) text += " " + Number(walk.runwayMonths).toFixed(1) + " months of runway from the close.";
        }
        return (
          '<div style="margin-top:16px"><div style="font-size:12px;font-weight:650;letter-spacing:.04em;text-transform:uppercase;color:var(--text3)">' +
          esc(pair[0]) +
          '</div><div style="margin-top:4px;font-size:13.5px;line-height:1.6;color:var(--text)">' +
          esc(text) +
          "</div></div>"
        );
      })
      .join("");
    return html;
  }

  function renderGrid(host) {
    var book = package();
    if (!book) {
      host.innerHTML =
        '<div style="padding:14px 16px;border:1px solid #D9D6CE;border-radius:8px;color:#5F6469;background:#fff">The commentary grid loads with the books for this close. Each line gets one paragraph, and the amounts in it tie to that line.</div>';
      return;
    }
    var item = comparison();
    if (!item) {
      host.innerHTML =
        '<div style="padding:14px 16px;border:1px solid #D9D6CE;border-radius:8px;color:#5F6469;background:#fff">No comparison is loaded for this close yet.</div>';
      return;
    }
    var reviews = mergedReviews();
    var source = item.available === false ? { rows: [], note: item.note || "This comparison is not available.", statement: null } : gridSource(item);
    var rows = applyOpen(source.rows || [], reviews);
    var required = 0;
    var done = 0;
    (book.comparisons || []).forEach(function (comp) {
      if (comp.available === false || comp.id !== item.id) return;
      (comp.statements || []).forEach(function (statement) {
        rowsOf(statement).forEach(function (row) {
          if (!row.review_required) return;
          required += 1;
          if (reviews[row.key]) done += 1;
        });
      });
    });
    var compButtons = (book.comparisons || [])
      .map(function (comp) {
        var on = comp.id === item.id;
        return (
          '<button type="button" data-comp="' +
          esc(comp.id) +
          '" style="border:1px solid ' +
          (on ? "#0E5A5F" : "#D9D6CE") +
          ";background:" +
          (on ? "#0E5A5F" : "#fff") +
          ";color:" +
          (on ? "#fff" : "#16181A") +
          ';border-radius:999px;padding:5px 10px;font-size:12px;cursor:pointer">' +
          esc(COMPACT[comp.id] || comp.label) +
          "</button>"
        );
      })
      .join("");
    var viewButtons = VIEWS.map(function (pair) {
      var on = pair[0] === viewPicked;
      return (
        '<button type="button" data-view="' +
        esc(pair[0]) +
        '" style="border:0;border-bottom:2px solid ' +
        (on ? "#0E5A5F" : "transparent") +
        ";background:transparent;color:" +
        (on ? "#0E5A5F" : "#5F6469") +
        ';padding:8px 10px;font-size:13px;font-weight:600;cursor:pointer">' +
        esc(pair[1]) +
        "</button>"
      );
    }).join("");
    var filters = [
      ["all", "All lines"],
      ["needs", "Needs commentary"],
      ["open", "Not reviewed"],
    ]
      .map(function (pair) {
        var on = gridFilter === pair[0];
        return (
          '<button type="button" data-filter="' +
          pair[0] +
          '" style="border:1px solid #D9D6CE;background:' +
          (on ? "#E6EFEF" : "#fff") +
          ';border-radius:6px;padding:4px 8px;font-size:12px;cursor:pointer">' +
          pair[1] +
          "</button>"
        );
      })
      .join("");
    var reasons = source.statement ? reasonsFor(source.statement) : {};
    var body = rows
      .map(function (row) {
        var text = reasons[row.id] || lineText(row);
        var toggle = row.expandable
          ? '<button type="button" data-toggle="' + esc(row.key) + '" aria-expanded="' + (opened[row.key] ? "true" : "false") + '" style="border:0;background:transparent;color:#0E5A5F;width:18px;padding:0;cursor:pointer;font:inherit;font-weight:700">' + (opened[row.key] ? "▾" : "▸") + "</button>"
          : '<span style="display:inline-block;width:18px"></span>';
        return (
          "<tr>" +
          '<td style="padding:8px 8px 8px ' + (8 + (row.depth || 0) * 16) + 'px;vertical-align:top;font-weight:' + (row.depth ? "500" : "600") + '">' +
          toggle +
          esc(row.label) +
          (row.department && row.department !== row.label ? '<div style="font-weight:400;color:#5F6469;font-size:11px">' + esc(row.department) + "</div>" : "") +
          "</td>" +
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">' +
          esc(money(row.current)) +
          "</td>" +
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">' +
          esc(money(row.comparison_amount)) +
          "</td>" +
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">' +
          esc(money(row.variance)) +
          "</td>" +
          '<td style="padding:8px;text-align:right">' +
          esc(pct(row)) +
          '</td><td style="padding:8px;text-align:center">' +
          esc(mark(row)) +
          "</td>" +
          '<td style="padding:8px;min-width:280px"><textarea data-edit="' +
          esc(row.key) +
          '" style="width:100%;min-height:52px;border:1px solid #D9D6CE;border-radius:6px;padding:6px;font:inherit;background:#fff">' +
          esc(text) +
          "</textarea></td>" +
          '<td style="padding:8px;color:#5F6469;font-size:12px">—</td>' +
          '<td style="padding:8px;text-align:center;color:' +
          (row.variance == null ? "#5F6469" : "#0E5A5F") +
          '">' +
          (row.variance == null ? "" : "✓") +
          "</td>" +
          '<td style="padding:8px;text-align:center">' +
          (row.review_required
            ? '<input type="checkbox" data-review="' + esc(row.key) + '"' + (reviews[row.key] ? " checked" : "") + " />"
            : '<span style="color:#5F6469;font-size:11px">Not required</span>') +
          "</td></tr>"
        );
      })
      .join("");
    host.innerHTML =
      '<div style="background:#F4F3EF;color:#16181A;font-family:IBM Plex Sans,system-ui,sans-serif">' +
      '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-end;flex-wrap:wrap;margin-bottom:12px">' +
      "<div><div style=\"font-size:20px;font-weight:650;color:#0E5A5F\">Variance commentary</div>" +
      '<div style="font-size:13px;color:#5F6469;margin-top:2px">One paragraph per line · every amount ties to the line</div></div>' +
      '<button type="button" data-export="1" style="border:1px solid #0E5A5F;background:#fff;color:#0E5A5F;border-radius:6px;padding:6px 10px;cursor:pointer">Export workbook</button></div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">' +
      compButtons +
      "</div>" +
      '<div style="font-size:12px;color:#5F6469;margin-bottom:10px">' +
      esc(item.label || "") +
      (item.available === false ? " · " + esc(item.note || "") : "") +
      "</div>" +
      '<div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #D9D6CE;margin-bottom:8px">' +
      '<div style="display:flex;gap:2px;flex-wrap:wrap">' +
      viewButtons +
      "</div>" +
      '<div style="font-size:12px;color:#5F6469">' +
      done +
      " of " +
      required +
      " lines reviewed on this comparison</div></div>" +
      '<div style="display:flex;gap:6px;margin:8px 0">' +
      filters +
      "</div>" +
      (source.note ? '<div style="font-size:12px;color:#5F6469;margin-bottom:8px">' + esc(source.note) + "</div>" : "") +
      '<div style="background:#fff;border:1px solid #D9D6CE;border-radius:8px"><table style="width:100%;border-collapse:separate;border-spacing:0;font-size:13px"><thead><tr style="text-align:left">' +
      '<th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px">Line</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px;text-align:right">Current</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px;text-align:right">Comparison</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px;text-align:right">Variance</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px;text-align:right">%</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px">F/U</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px">Commentary</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px">Future impacts</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px">Ties</th><th style="position:sticky;top:0;z-index:4;background:#0E5A5F;color:#fff;padding:8px">Review</th>' +
      "</tr></thead><tbody>" +
      (body || '<tr><td colspan="10" style="padding:16px;color:#5F6469">No lines in this view.</td></tr>') +
      "</tbody></table></div>" +
      '<div style="margin-top:8px;font-size:12px;color:#5F6469">F is favorable and U is unfavorable. Future impacts stay blank until they are noted on a GL line. A blank amount means that side is not loaded.</div></div>';
    Array.prototype.forEach.call(host.querySelectorAll("[data-comp]"), function (button) {
      button.onclick = function () {
        picked = button.getAttribute("data-comp");
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-view]"), function (button) {
      button.onclick = function () {
        viewPicked = button.getAttribute("data-view");
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-filter]"), function (button) {
      button.onclick = function () {
        gridFilter = button.getAttribute("data-filter");
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-toggle]"), function (button) {
      button.onclick = function () {
        var key = button.getAttribute("data-toggle");
        opened[key] = !opened[key];
        render(host);
      };
    });
    var exportButton = host.querySelector("[data-export]");
    if (exportButton) exportButton.onclick = download;
    Array.prototype.forEach.call(host.querySelectorAll("[data-review]"), function (box) {
      box.onchange = function () {
        draft.reviews[box.getAttribute("data-review")] = box.checked;
        persist();
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-edit]"), function (field) {
      field.onchange = function () {
        var key = field.getAttribute("data-edit");
        var row = findRow(key);
        var text = field.value.trim();
        if (!text) {
          draft.edits[key] = "";
          persist();
          return;
        }
        if (!row || !textTies(text, row.amounts || [])) {
          field.style.borderColor = "#b42318";
          return;
        }
        draft.edits[key] = text;
        persist();
      };
    });
  }

  function render(host) {
    var options = host._storyOptions || {};
    if (options.mode === "grid") {
      renderGrid(host);
      return;
    }
    var book = package();
    if (!book) {
      host.innerHTML =
        '<div style="margin:0 0 16px;padding:12px 14px;border:0.5px solid var(--border);border-radius:8px;color:var(--text3);font-size:12px">The month story loads with the books for this close: income statement, balance sheet, then cash flow. A blank line means that amount is not loaded.</div>';
      return;
    }
    var item = comparison();
    if (!item) return;
    var buttons = (book.comparisons || [])
      .map(function (comp) {
        var on = comp.id === item.id;
        return (
          '<button type="button" data-comp="' +
          esc(comp.id) +
          '" style="border:0.5px solid var(--border);background:' +
          (on ? "var(--accent)" : "transparent") +
          ";color:" +
          (on ? "#fff" : "var(--text2)") +
          ';border-radius:6px;padding:4px 8px;font-size:11px;cursor:pointer">' +
          esc(comp.label) +
          "</button>"
        );
      })
      .join("");
    var body = "";
    if (!item.available) {
      body =
        '<div style="font-size:13px;color:var(--text2);line-height:1.5">' +
        esc(item.note || "This comparison is blank.") +
        "</div>";
    } else if (options.mode === "lead") {
      var incomeLead = (item.statements || []).filter(function (statement) {
        return statement.id === "income_statement";
      })[0];
      body =
        '<div style="font-size:13.5px;line-height:1.6;color:var(--text)">' +
        esc(incomeLead ? paragraph(incomeLead) : "") +
        "</div>" +
        '<button type="button" data-open-discussion="1" style="margin-top:10px;border:0;background:none;color:var(--accent);font:inherit;font-size:12px;cursor:pointer;padding:0">Executive Discussion →</button>';
    } else if (options.mode === "read" || options.mode === "work" || options.mode === "overview") {
      var story = (item.statements || [])
        .map(paragraph)
        .filter(Boolean)
        .join(" ");
      var addition = mergedAdditions()[item.id] || "";
      var untied = (item.statements || [])
        .filter(function (statement) {
          return !statement.ties;
        })
        .map(function (statement) {
          return esc(statement.title) + ": " + esc(statement.tie_note || "Does not tie.");
        })
        .join("<br>");
      var additionBox =
        options.mode === "read"
          ? addition
            ? '<div style="margin-top:10px;font-size:13.5px;line-height:1.6;color:var(--text)">' + esc(addition) + "</div>"
            : ""
          : '<label style="display:block;margin-top:12px;font-size:11px;color:var(--text3)">Add to the overview. A number here has to already be on a statement.</label>' +
            '<textarea data-addition="' +
            esc(item.id) +
            '" style="width:100%;min-height:64px;margin-top:6px;background:var(--bg);color:var(--text);border:0.5px solid var(--border);border-radius:6px;padding:8px;font:inherit">' +
            esc(addition) +
            "</textarea>";
      var publishedLines =
        options.mode === "work"
          ? (item.statements || [])
              .map(function (statement) {
                return statementBlock(statement, { working: options.mode !== "read" });
              })
              .join("")
          : "";
      body =
        '<div style="font-size:13.5px;line-height:1.6;color:var(--text)">' +
        esc(story) +
        "</div>" +
        additionBox +
        (untied
          ? '<div style="margin-top:8px;font-size:12px;color:var(--red)">' + untied + "</div>"
          : "") +
        (options.mode === "read" ? businessHtml() : "") +
        publishedLines;
    } else {
      var wanted = options.statements || ["income_statement", "balance_sheet", "cash_flow"];
      body = (item.statements || [])
        .filter(function (statement) {
          return wanted.indexOf(statement.id) >= 0;
        })
        .map(function (statement) {
          return statementBlock(statement, options);
        })
        .join("");
    }
    host.innerHTML =
      '<div style="margin:0 0 18px;padding:14px 16px;background:var(--bg2);border:0.5px solid var(--border);border-radius:10px">' +
      '<div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px">' +
      '<div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)">The month</div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
      buttons +
      "</div></div>" +
      body +
      "</div>";
    Array.prototype.forEach.call(host.querySelectorAll("[data-comp]"), function (button) {
      button.onclick = function () {
        picked = button.getAttribute("data-comp");
        document.querySelectorAll("[data-story-host]").forEach(function (node) {
          render(node);
        });
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-review]"), function (box) {
      box.onchange = function () {
        draft.reviews[box.getAttribute("data-review")] = box.checked;
        persist();
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-edit]"), function (field) {
      field.onchange = function () {
        var key = field.getAttribute("data-edit");
        var row = findRow(key);
        var text = field.value.trim();
        if (!text) {
          draft.edits[key] = "";
          persist();
          return;
        }
        if (!row || !textTies(text, row.amounts || [])) {
          field.style.borderColor = "var(--red)";
          return;
        }
        draft.edits[key] = text;
        persist();
        render(host);
      };
    });
    var discussionBtn = host.querySelector("[data-open-discussion]");
    if (discussionBtn) {
      discussionBtn.onclick = function () {
        var tab = Array.prototype.filter.call(document.querySelectorAll(".nav-btn"), function (button) {
          return (button.getAttribute("onclick") || "").indexOf("show('discussion'") >= 0;
        })[0];
        if (typeof global.show === "function") global.show("discussion", tab || null);
      };
    }
    var additionField = host.querySelector("[data-addition]");
    if (additionField) {
      additionField.onchange = function () {
        var text = additionField.value.trim();
        if (text && !textTies(text, comparisonAmounts(item))) {
          additionField.style.borderColor = "var(--red)";
          return;
        }
        draft.additions[item.id] = text;
        persist();
      };
    }
  }

  function findRow(key) {
    var book = package();
    var found = null;
    ((book && book.comparisons) || []).forEach(function (item) {
      (item.statements || []).forEach(function (statement) {
        rowsOf(statement).forEach(function (row) {
          if (row.key === key) found = row;
        });
      });
    });
    return found;
  }

  function comparisonAmounts(item) {
    var amounts = [];
    (item.statements || []).forEach(function (statement) {
      rowsOf(statement).forEach(function (row) {
        (row.amounts || []).forEach(function (amount) {
          amounts.push(amount);
        });
      });
    });
    return amounts;
  }

  function statementBlock(statement, options) {
    var note = "";
    if (options.management) {
      note =
        '<div style="font-size:11px;color:var(--text3);margin-bottom:8px">Same income-statement lines. A check here is the check on the income statement.</div>';
    }
    var reviews = mergedReviews();
    var working = options.working !== false;
    var table = (statement.lines || [])
      .map(function (row) {
        return lineRow(row, reviews, "Statement", working);
      })
      .concat(
        (statement.departments || []).map(function (row) {
          return lineRow(row, reviews, "Department", working);
        })
      )
      .concat(
        (statement.accounts || []).map(function (row) {
          return lineRow(row, reviews, row.department || "Account", working);
        })
      )
      .join("");
    var blank = !statement.accounts || !statement.accounts.length
      ? '<div style="margin-top:8px;font-size:12px;color:var(--text3)">' + esc(statement.accounts_note || "") + "</div>"
      : "";
    return (
      '<div style="margin-top:8px">' +
      note +
      '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">' +
      esc(statement.title) +
      "</div>" +
      '<div style="font-size:13.5px;line-height:1.6;color:var(--text);margin-bottom:6px">' +
      esc(paragraph(statement)) +
      "</div>" +
      '<div style="font-size:11px;color:' +
      (statement.ties ? "var(--teal)" : "var(--red)") +
      '">' +
      (statement.ties ? "Ties" : "Does not tie") +
      " · " +
      esc(statement.tie_note || "") +
      "</div>" +
      '<div style="overflow-x:auto;margin-top:8px"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr>' +
      "<th></th><th>Line</th><th>Current</th><th>Comparison</th><th>Variance</th><th>Commentary</th></tr></thead><tbody>" +
      table +
      "</tbody></table></div>" +
      blank +
      "</div>"
    );
  }

  function lineRow(row, reviews, grain, working) {
    var checked = reviews[row.key] ? " checked" : "";
    var box = !working
      ? reviews[row.key]
        ? "Reviewed"
        : ""
      : row.review_required
        ? '<input type="checkbox" data-review="' + esc(row.key) + '"' + checked + " />"
        : "";
    var edited = mergedEdits()[row.key] || "";
    var commentaryCell = working
      ? '<textarea data-edit="' +
        esc(row.key) +
        '" style="width:100%;min-height:44px;background:var(--bg);color:var(--text);border:0.5px solid var(--border);border-radius:6px;padding:6px;font:inherit">' +
        esc(edited || row.commentary || "") +
        "</textarea>"
      : esc(edited || row.commentary || "");
    return (
      "<tr>" +
      '<td style="padding:4px 6px;vertical-align:top;font-size:11px;color:var(--text3)">' +
      box +
      "</td>" +
      '<td style="padding:4px 6px;vertical-align:top">' +
      esc(grain) +
      " · " +
      esc(row.label) +
      (!row.review_required && row.variance != null && Math.abs(Number(row.variance)) < 10000
        ? ' <span style="color:var(--text3)">under $10,000</span>'
        : "") +
      "</td>" +
      '<td style="padding:4px 6px;font-family:var(--mono);vertical-align:top">' +
      esc(money(row.current)) +
      "</td>" +
      '<td style="padding:4px 6px;font-family:var(--mono);vertical-align:top">' +
      esc(money(row.comparison_amount)) +
      "</td>" +
      '<td style="padding:4px 6px;font-family:var(--mono);vertical-align:top">' +
      esc(money(row.variance)) +
      "</td>" +
      "<td style=\"padding:4px 6px\">" +
      commentaryCell +
      "</td></tr>"
    );
  }

  function mount(host, options) {
    if (!host) return;
    host.setAttribute("data-story-host", "1");
    host._storyOptions = options || {};
    try {
      render(host);
    } catch (err) {
      host.innerHTML =
        '<div style="padding:14px 16px;border:1px solid #D9D6CE;border-radius:8px;color:#16181A;background:#fff">The commentary screen hit an error while drawing. ' +
        esc(err && err.message ? err.message : err) +
        "</div>";
    }
  }

  function download() {
    var org = global.SMPL_ORG_ID;
    if (!org || !global.CLOSE_MONTH) {
      global.alert("No organization data is loaded, so there is no variance commentary to export.");
      return;
    }
    var base = (global.SMPL_API_BASE || "/api/v1").replace(/\/$/, "");
    var url =
      base +
      "/validation-engine/commentary.xlsx?organization_id=" +
      encodeURIComponent(org) +
      "&as_of_period=" +
      encodeURIComponent(global.CLOSE_MONTH);
    fetch(url, { credentials: "include" })
      .then(function (response) {
        if (!response.ok) throw new Error("export_failed");
        return response.blob();
      })
      .then(function (blob) {
        var link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "SMPL-variance-commentary-" + global.CLOSE_MONTH + ".xlsx";
        link.click();
      })
      .catch(function () {
        global.alert("The commentary file could not be downloaded.");
      });
  }

  global.boardMountStatementStory = mount;
  global.boardDownloadStatementStory = download;
  global.boardStatementReviewOpenCount = openCount;
})(typeof window !== "undefined" ? window : globalThis);
