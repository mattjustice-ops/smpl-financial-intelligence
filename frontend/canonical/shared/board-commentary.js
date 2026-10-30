/* Statement commentary. The overview reads each statement paragraph in order.
   Line edits replace that sentence. An overview addition may only cite a number
   already on a statement. Account rows stay blank when the other side is not loaded. */
(function (global) {
  var picked = "mom";
  var viewPicked = "management";
  var gridFilter = "all";
  var opened = {};
  var editingKey = "";
  var aboutOpen = false;
  var gridQuery = "";
  var activeRow = "";
  var gridDensity = "comfortable";
  var expandedText = {};
  var reviewMenu = "";
  var reviewedAt = {};
  var editedAt = {};
  var editBuffer = null;
  var editBaseline = "";
  var leavePrompt = "";
  var sectionRollup = {};
  var revenueHeld = {};
  var revenueHeldFor = "";
  var revenueFetchSerial = {};
  var discussionEvents = { key: "", status: "", events: [] };
  var editingAnalysis = false;
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
    function windowAmount(periods, scenario, table, key) {
      if (!periods.length) return null;
      var stockEnd = table === "bs" || key === "ending_cash";
      var stockOpen = key === "beg_cash" || key === "beginning_cash";
      if (stockEnd) return readAmount(ts, history, scenario, table, periods[periods.length - 1], key);
      if (stockOpen) return readAmount(ts, history, scenario, table, periods[0], key);
      return sumAmounts(periods.map(function (period) { return readAmount(ts, history, scenario, table, period, key); }));
    }
    function linesFor(comparison, statement, table, spec, currentPeriods, basePeriods, baseScenario) {
      return spec
        .map(function (item) {
          var current = windowAmount(currentPeriods, "Actual", table, item[0]);
          var base = windowAmount(basePeriods, baseScenario, table, item[0]);
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
      role: spec.role || "",
      accountNumber: spec.accountNumber || "",
      accountName: spec.accountName || "",
      lineKey: spec.lineKey || "",
      signLine: spec.signLine || "",
      vendor: spec.vendor || "",
      facts: spec.facts || [],
      drivers: spec.drivers || [],
      unassigned: !!spec.unassigned,
      gapAfter: !!spec.gapAfter,
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

  function windowAmount(win, side, table, keys) {
    var list = Array.isArray(keys) ? keys : [keys];
    var periods = win[side] || [];
    if (!periods.length) return null;
    var scenario = side === "base" ? win.scenario : "Actual";
    var stockEnd = table === "bs" || list.indexOf("ending_cash") >= 0 || list.indexOf("end_cash") >= 0;
    var stockOpen = list.indexOf("beg_cash") >= 0 || list.indexOf("beginning_cash") >= 0;
    if (table !== "is" && stockEnd) return periodAmount(win.src, scenario, table, periods[periods.length - 1], list);
    if (table !== "is" && stockOpen) return periodAmount(win.src, scenario, table, periods[0], list);
    return sideSum(win, side, table, keys);
  }

  function metricRow(win, table, id, label, depth, keys) {
    if (!win) return null;
    var current = windowAmount(win, "current", table, keys || id);
    var base = windowAmount(win, "base", table, keys || id);
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
    line.signLine = line.signLine || id;
    kids.forEach(function (row) { row.signLine = id; });
    if (global.SMPL_REPORTING_ENGINE && line.expandable) {
      writeTreeCommentary(line, kids.filter(function (row) { return row.depth === 1; }), win);
    }
    rows.push(line);
    kids.forEach(function (row) { rows.push(row); });
  }

  function rollupForPeriod(win, scenario, period) {
    var block = (win.src.ts && win.src.ts[scenario]) || {};
    var bag = block.gl_rollup;
    var tree = bag && bag[period];
    if (tree && Array.isArray(tree.lines)) return tree;
    if (scenario === "Actual" && win.src.history && win.src.history.gl_rollup) {
      tree = win.src.history.gl_rollup[period];
      if (tree && Array.isArray(tree.lines)) return tree;
    }
    return null;
  }

  function rollupBag(win, side) {
    var scenario = side === "base" ? win.scenario : "Actual";
    var trees = [];
    var missing = false;
    win[side].forEach(function (period) {
      var tree = rollupForPeriod(win, scenario, period);
      if (!tree) {
        missing = true;
        return;
      }
      trees.push(tree);
    });
    if (missing || !trees.length) return null;
    return { lines: mergeNodeLists(trees.map(function (tree) { return tree.lines; })) };
  }

  var FLOW_MEASURES = {
    implementations: 1,
    "customers added": 1,
    "customers ended": 1,
    hires: 1,
    departures: 1,
  };
  var STOCK_MEASURES = {
    customers: 1,
    employees: 1,
    "customers on recurring services": 1,
    "prepaid contracts": 1,
  };
  var AVERAGE_WEIGHT = {
    "average subscription revenue": "customers",
    "average recurring services fee": "customers on recurring services",
    "average implementation fee": "implementations",
    "average amortization": "prepaid contracts",
    "average salary": "employees",
    "average bonus": "employees",
    "average severance": "employees",
    "average payroll tax": "employees",
    "average retirement match": "employees",
    "average benefits": "employees",
    "average payroll cost": "employees",
  };

  function foldPeriodMeasures(snapshots) {
    var lists = snapshots || [];
    if (!lists.length) return [];
    if (lists.length === 1) return (lists[0] || []).slice();
    function asMap(list) {
      var map = {};
      (list || []).forEach(function (measure) {
        if (!measure || !measure.label || measure.value == null || !isFinite(Number(measure.value))) return;
        map[String(measure.label).toLowerCase()] = { label: measure.label, value: Number(measure.value) };
      });
      return map;
    }
    var maps = lists.map(asMap);
    var order = [];
    var labels = {};
    lists.forEach(function (list) {
      (list || []).forEach(function (measure) {
        if (!measure || !measure.label) return;
        var key = String(measure.label).toLowerCase();
        if (labels[key]) return;
        labels[key] = measure.label;
        order.push(key);
      });
    });
    var folded = [];
    order.forEach(function (key) {
      if (FLOW_MEASURES[key]) {
        var sum = 0;
        var complete = maps.every(function (map) { return !!map[key]; });
        if (!complete) return;
        maps.forEach(function (map) { sum += map[key].value; });
        folded.push({ label: labels[key], value: round2(sum) });
        return;
      }
      if (STOCK_MEASURES[key]) {
        var last = maps[maps.length - 1][key];
        if (last) folded.push({ label: last.label, value: last.value });
        return;
      }
      var weightKey = AVERAGE_WEIGHT[key];
      if (!weightKey) return;
      var weighted = 0;
      var weight = 0;
      var ready = maps.every(function (map) { return map[key] && map[weightKey]; });
      if (!ready) return;
      maps.forEach(function (map) {
        weighted += map[key].value * map[weightKey].value;
        weight += map[weightKey].value;
      });
      if (weight) folded.push({ label: labels[key], value: round2(weighted / weight) });
    });
    return folded;
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
            account_number: node.account_number || "",
            vendor: node.vendor || "",
            payouts: (node.payouts || []).slice(),
            bridge: node.bridge || null,
            amount: 0,
            _lists: [],
            _measureSnapshots: [],
          };
          order.push(node.id);
        }
        var slot = byId[node.id];
        slot._measureSnapshots.push((node.measures || []).slice());
        if (slot._seen) {
          slot.payouts = [];
          slot.bridge = null;
        }
        slot._seen = true;
        slot.amount = round2(slot.amount + Number(node.amount || 0));
        if (node.merged_child) slot.merged_child = node.merged_child;
        if (node.account_number) slot.account_number = node.account_number;
        if (node.vendor && !slot.vendor) slot.vendor = node.vendor;
        else if (node.vendor && slot.vendor && slot.vendor !== node.vendor) slot.vendor = "";
        if (node.label) slot.label = node.label;
        slot._lists.push(node.children || []);
      });
    });
    return order.map(function (id) {
      var slot = byId[id];
      slot.measures = foldPeriodMeasures(slot._measureSnapshots);
      slot.children = mergeNodeLists(slot._lists);
      delete slot._lists;
      delete slot._seen;
      delete slot._measureSnapshots;
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

  function monthName(period) {
    var names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var text = String(period || "");
    var month = parseInt(text.slice(5, 7), 10);
    if (!month || month > 12) return text;
    return names[month - 1] + " " + text.slice(0, 4);
  }

  function comparisonName(win) {
    if (!win || !win.base || !win.base.length) return "";
    if (win.id === "budget") return "Budget";
    if (win.id === "forecast") return "Forecast";
    var base = monthName(win.base[win.base.length - 1]);
    if (win.id === "ytd") return "YTD " + base;
    if (win.id === "qoq") return "Q ending " + base;
    return base;
  }

  function periodHeading(win) {
    if (!win || !win.current || !win.current.length) return "";
    var current = monthName(win.current[win.current.length - 1]);
    var base = comparisonName(win);
    if (win.id === "ytd") return "YTD " + current + " vs " + base;
    if (win.id === "qoq") return "Q ending " + current + " vs " + base;
    return current + " vs " + base;
  }

  function shortMonth(period) {
    var names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var text = String(period || "");
    var month = parseInt(text.slice(5, 7), 10);
    if (!month || month > 12 || text.length < 4) return text;
    return names[month - 1] + " " + text.slice(2, 4);
  }

  function quarterStamp(period) {
    var text = String(period || "");
    var month = parseInt(text.slice(5, 7), 10);
    if (!month || month > 12 || text.length < 4) return text;
    return "Q" + (Math.floor((month - 1) / 3) + 1) + " " + text.slice(2, 4);
  }

  function columnHeads(win) {
    if (!win || !win.current || !win.current.length) return { current: "Current", base: "Comparison" };
    var current = win.current[win.current.length - 1];
    var base = win.base && win.base.length ? win.base[win.base.length - 1] : "";
    if (win.id === "qoq") return { current: quarterStamp(current), base: base ? quarterStamp(base) : "Comparison" };
    if (win.id === "ytd") return { current: "YTD " + monthName(current), base: base ? "YTD " + monthName(base) : "Comparison" };
    if (win.id === "budget") return { current: shortMonth(current), base: "Budget" };
    if (win.id === "forecast") return { current: shortMonth(current), base: "Forecast" };
    return { current: shortMonth(current), base: base ? shortMonth(base) : "Comparison" };
  }

  function splitLabel(label) {
    return String(label || "").split(" · ").map(function (part) { return part.trim(); }).filter(Boolean);
  }

  function mergedLabel(label) {
    var parts = splitLabel(label);
    if (parts.length <= 2) return { text: parts.join(" · "), title: parts.join(" › ") };
    return { text: parts[0] + " · " + parts[parts.length - 1], title: parts.join(" › ") };
  }

  function sentenceCaseLabel(text) {
    var value = String(text || "");
    if (value.length < 2) return false;
    return value.slice(1) === value.slice(1).toLowerCase() && /[a-z]/.test(value.slice(1));
  }

  function sentenceLabel(label, atStart) {
    var parts = splitLabel(label);
    var text = parts.length < 2 ? (parts[0] || "") : parts[parts.length - 1] + " in " + parts[0];
    if (!atStart && sentenceCaseLabel(text)) return text.charAt(0).toLowerCase() + text.slice(1);
    return text;
  }

  function wholeAmount(value) {
    if (value == null || value === "") return "—";
    var amount = Number(value);
    if (!isFinite(amount)) return "—";
    var sign = amount < 0 ? "−" : "";
    return sign + Math.abs(Math.round(amount)).toLocaleString("en-US");
  }

  function signedWhole(value) {
    if (value == null || value === "") return "—";
    var amount = Number(value);
    if (!isFinite(amount)) return "—";
    if (Math.round(amount) === 0) return "0";
    var sign = amount < 0 ? "−" : "+";
    return sign + Math.abs(Math.round(amount)).toLocaleString("en-US");
  }

  function percentSigned(row) {
    if (!row || row.variance == null || row.comparison_amount == null) return "";
    if (!Number(row.comparison_amount)) return "n/m";
    var pctValue = (Number(row.variance) / Number(row.comparison_amount)) * 100;
    if (Math.round(Number(row.variance)) === 0) return "0.0%";
    var sign = pctValue < 0 ? "−" : "+";
    return sign + Math.abs(pctValue).toFixed(1) + "%";
  }

  function percentAbs(row) {
    if (!row || row.variance == null || !Number(row.comparison_amount)) return "";
    return Math.abs((Number(row.variance) / Number(row.comparison_amount)) * 100).toFixed(1) + "%";
  }

  function joinAnd(parts) {
    if (parts.length < 2) return parts[0] || "";
    return parts.slice(0, -1).join(", ") + " and " + parts[parts.length - 1];
  }

  function reportParagraph(row, period) {
    var label = sentenceLabel(row && row.label, true);
    if (!row || row.variance == null) return label + " has no comparison amount.";
    var shown = Math.round(Number(row.variance));
    if (!shown) return label + " was unchanged." + factSuffix(row);
    var verb = shown > 0 ? "rose" : "fell";
    var pct = percentAbs(row);
    var lead = label + " " + verb + " " + Math.abs(shown).toLocaleString("en-US") + (pct ? " (" + pct + ")" : "") + (period ? " vs " + period : "");
    var drivers = (row.drivers || []).filter(function (driver) {
      if (!driver || driver.variance == null || Math.round(Number(driver.variance)) === 0) return false;
      if (driver.role === "opportunity" && !driver.linked) return false;
      return true;
    });
    if (!drivers.length) return lead + (row.vendor ? ", on " + row.vendor : "") + "." + factSuffix(row);
    function along(driver) {
      if (driver.contribution != null) return (Number(driver.contribution) > 0) === (shown > 0);
      return (Number(driver.variance) > 0) === (shown > 0);
    }
    var same = drivers.filter(along);
    var opposite = drivers.filter(function (driver) { return !along(driver); });
    function bySize(a, b) { return Math.abs(Number(b.variance)) - Math.abs(Number(a.variance)); }
    same.sort(bySize);
    opposite.sort(bySize);
    function bit(driver) {
      var amount = Math.round(Number(driver.variance));
      var word = amount > 0 ? "higher" : "lower";
      return word + " " + sentenceLabel(driver.label, false) + " (" + signedWhole(amount) + ")";
    }
    var text = lead;
    if (same.length) text += ": " + joinAnd(same.map(bit));
    if (opposite.length) text += (same.length ? ", partly offset by " : ": ") + joinAnd(opposite.map(bit));
    var cited = drivers.reduce(function (total, driver) { return total + Number(driver.variance); }, 0);
    var rest = Math.round(Number(row.variance) - cited);
    if (Math.round(rest) !== 0) text += "; other items (" + signedWhole(rest) + ")";
    text += "." + factSuffix(row);
    return text;
  }

  function formatFact(value) {
    var amount = Math.abs(Number(value));
    if (!isFinite(amount)) return "—";
    if (amount >= 100 || Math.abs(amount - Math.round(amount)) < 1e-6) return Math.round(amount).toLocaleString("en-US");
    return amount.toLocaleString("en-US", { maximumFractionDigits: 4 });
  }

  function pairMeasures(current, base) {
    var byLabel = {};
    function take(list, side) {
      (list || []).forEach(function (measure) {
        if (!measure || !measure.label || measure.value == null || !isFinite(Number(measure.value))) return;
        var slot = byLabel[measure.label] || { label: measure.label };
        slot[side] = Number(measure.value);
        byLabel[measure.label] = slot;
      });
    }
    take(base, "base");
    take(current, "current");
    return Object.keys(byLabel).map(function (label) { return byLabel[label]; }).filter(function (fact) {
      return fact.current != null && fact.base != null;
    });
  }

  function bridgeFacts(current, base) {
    var bridge = current && current.bridge;
    if (!bridge || !base || base.amount == null || current.amount == null) return [];
    if (Math.abs(Number(base.amount) - Number(bridge.beginning)) > 1) return [];
    if (Math.abs(Number(current.amount) - Number(bridge.ending)) > 1) return [];
    return bridge.facts || [];
  }

  function isMoneyFact(label) {
    var text = String(label || "").toLowerCase();
    if (/average|fee|salary|cost|wage|price|\bsize\b/.test(text)) return true;
    if (/customer|implementation|employee|hire|departure|head|people|person|hour|\bgb\b|contract|deal|seat|logo/.test(text)) return false;
    return true;
  }

  function moneyPhrase(value) {
    var amount = Number(value);
    if (!isFinite(amount)) return "—";
    var abs = Math.abs(amount);
    var body;
    if (abs >= 1000000) body = "$" + (abs / 1000000).toFixed(2) + "m";
    else if (abs >= 1000) body = "$" + (abs / 1000).toFixed(2) + "k";
    else body = "$" + abs.toFixed(2);
    return (amount < 0 ? "−" : "") + body;
  }

  function shownFact(label, value) {
    return isMoneyFact(label) ? moneyPhrase(value) : formatFact(value);
  }

  function factClause(fact) {
    if (!fact || !fact.label) return "";
    if (fact.paid != null && fact.quota != null && isFinite(Number(fact.paid)) && isFinite(Number(fact.quota))) {
      return fact.label + " " + moneyPhrase(fact.paid) + " against a commission quota of " + moneyPhrase(fact.quota);
    }
    if (fact.amount != null && fact.current == null) {
      var heads = fact.heads ? " (" + fact.heads + (Number(fact.heads) === 1 ? " person" : " people") + ")" : "";
      var amount = Number(fact.amount);
      var signed = (amount < 0 ? "−" : amount > 0 ? "+" : "") + moneyPhrase(Math.abs(amount));
      return fact.label + " " + signed + heads;
    }
    if (fact.missing || fact.current == null || fact.base == null) return fact.missing ? fact.label + " is not loaded" : "";
    var current = Number(fact.current);
    var base = Number(fact.base);
    if (!isFinite(current) || !isFinite(base)) return "";
    if (Math.abs(current - base) < 1e-9) return fact.label + " was unchanged";
    return fact.label + " " + (current > base ? "rose" : "fell") + " from " + shownFact(fact.label, base) + " to " + shownFact(fact.label, current);
  }

  function factSuffix(row) {
    var parts = (row && row.facts || []).map(factClause).filter(Boolean);
    if (!parts.length) return "";
    var text = joinAnd(parts);
    return " " + text.charAt(0).toUpperCase() + text.slice(1) + ".";
  }

  function uncitedDrivers(text, drivers) {
    var source = String(text || "");
    return (drivers || []).filter(function (driver) {
      if (!driver || driver.variance == null || Math.round(Number(driver.variance)) === 0) return false;
      return source.indexOf("(" + signedWhole(driver.variance) + ")") < 0;
    });
  }

  function favorText(row) {
    if (!row || row.variance == null || Math.round(Number(row.variance)) === 0) return "";
    var up = { revenue: 1, gross_profit: 1, ebitda: 1, op_income: 1, pretax: 1, net_income: 1, cash: 1, total_assets: 1, equity: 1, cfo: 1, net_change: 1, ending_cash: 1 };
    var down = { cogs: 1, sm: 1, rd: 1, ga: 1, total_opex: 1, da: 1, interest: 1, tax: 1, compensation: 1, debt: 1, unmapped: 1, total_liabilities: 1 };
    var key = row.signLine || row.line || row.id;
    var favorable = up[key] ? Number(row.variance) >= 0 : down[key] ? Number(row.variance) <= 0 : Number(row.variance) >= 0;
    return favorable ? "▲ Fav" : "▼ Unfav";
  }

  function driverParts(rows) {
    return (rows || []).filter(function (row) { return row.variance != null; }).map(function (row) {
      return { label: row.label, variance: row.variance, role: row.role || "", linked: !!row.linked };
    });
  }

  function writeTreeCommentary(row, children, win) {
    row.drivers = driverParts(children);
    row.commentary = reportParagraph(row, comparisonName(win));
  }

  var SUM_LINES = {
    gross_profit: [["revenue", 1], ["cogs", -1]],
    total_opex: [["sm", 1], ["rd", 1], ["ga", 1], ["unmapped", 1]],
    ebitda: [["gross_profit", 1], ["total_opex", -1]],
    op_income: [["gross_profit", 1], ["total_opex", -1], ["da", -1]],
    pretax: [["op_income", 1], ["interest", -1]],
    net_income: [["revenue", 1], ["cogs", -1], ["total_opex", -1], ["da", -1], ["interest", -1], ["tax", -1]],
  };

  function fillStatementParagraphs(rows, win) {
    if (!global.SMPL_REPORTING_ENGINE) return;
    applySumCommentary(rows, win);
  }

  function applySumCommentary(rows, win) {
    if (!win) return;
    var byId = {};
    rows.forEach(function (row) {
      if ((row.depth || 0) === 0 && !byId[row.id]) byId[row.id] = row;
    });
    Object.keys(SUM_LINES).forEach(function (id) {
      var row = byId[id];
      if (!row || (row.drivers && row.drivers.length)) return;
      row.signLine = row.signLine || id;
      row.drivers = SUM_LINES[id].map(function (pair) {
        var child = byId[pair[0]];
        if (!child || child.variance == null) return null;
        return { label: child.label, variance: child.variance, contribution: pair[1] * Number(child.variance) };
      }).filter(Boolean);
      if (row.drivers.length) row.commentary = reportParagraph(row, comparisonName(win));
    });
  }

  function applyStoryCommentary(rows, win) {
    if (!win) return;
    var parent = null;
    var children = [];
    function flush() {
      if (parent && children.length) writeTreeCommentary(parent, children, win);
      children = [];
    }
    rows.forEach(function (row) {
      if ((row.depth || 0) === 0) {
        flush();
        parent = row;
      } else if (parent && (row.depth || 0) === 1) {
        children.push(row);
      }
    });
    flush();
    applySumCommentary(rows, win);
  }

  function proseLine(row, win, withBase) {
    if (!row || row.variance == null) return "";
    if (!Math.round(Number(row.variance))) return "";
    var up = Number(row.variance) > 0;
    var text = sentenceLabel(row.label, true) + (up ? " increased " : " decreased ") + moneyPhrase(Math.abs(row.variance));
    if (row.current != null) text += " to " + moneyPhrase(row.current);
    if (withBase && row.comparison_amount != null && win) {
      if (win.id === "budget") text += " from a budget of " + moneyPhrase(row.comparison_amount);
      else if (win.id === "forecast") text += " from a forecast of " + moneyPhrase(row.comparison_amount);
      else text += " from " + moneyPhrase(row.comparison_amount) + " in " + comparisonName(win);
    }
    return text + ".";
  }

  function proseParagraph(lines, win) {
    var sentences = [];
    lines.forEach(function (row) {
      var sentence = proseLine(row, win, sentences.length === 0);
      if (sentence) sentences.push(sentence);
    });
    if (!sentences.length) return "";
    return sentences.join(" ");
  }

  function monthPieces(item, host) {
    var win = windowFor(item);
    var income = statementOf(item, "income_statement");
    var rows = buildIncome(item, income);
    applyStoryCommentary(rows, win);
    if (host && win) {
      Object.keys(ROLLUP_SECTIONS).forEach(function (sectionId) {
        requestSectionRollup(rows, win, host, sectionId);
      });
    }
    var told = { revenue: 1, cogs: 1, sm: 1, rd: 1, ga: 1, unmapped: 1, ebitda: 1, da: 1, interest: 1, pretax: 1, tax: 1, net_income: 1 };
    var pieces = [];
    var prose = [];
    function flushProse() {
      if (!prose.length) return;
      pieces.push(prose.join(" "));
      prose = [];
    }
    rows.forEach(function (row) {
      if ((row.depth || 0) !== 0 || !told[row.id]) return;
      var analysis = shownAnalysis(row);
      if (analysis) {
        flushProse();
        pieces.push(separateGroups(analysis, groupLabels(rows, row.id)));
        return;
      }
      if (row.id === "net_income") {
        flushProse();
        var close = proseLine(row, win, true);
        if (close) pieces.push(close);
        return;
      }
      var sentence = proseLine(row, win, prose.length === 0);
      if (sentence) prose.push(sentence);
    });
    flushProse();
    ["balance_sheet", "cash_flow"].forEach(function (id) {
      var statement = statementOf(item, id);
      var paragraph = proseParagraph((statement && statement.lines) || [], win);
      if (!paragraph) return;
      pieces.push(id === "balance_sheet" ? "On the balance sheet, " + paragraph.charAt(0).toLowerCase() + paragraph.slice(1) : paragraph);
    });
    return pieces;
  }

  var FAVORABLE_UP = { revenue: 1, gross_profit: 1, ebitda: 1, pretax: 1, op_income: 1, net_income: 1, cash: 1, cfo: 1, net_change: 1, ending_cash: 1, total_assets: 1 };

  function childRows(rows, index) {
    var out = [];
    for (var cursor = index + 1; cursor < rows.length; cursor += 1) {
      if ((rows[cursor].depth || 0) === 0) break;
      if ((rows[cursor].depth || 0) === 1) out.push(rows[cursor]);
    }
    return out;
  }

  function themeParts(row, rows, index) {
    var kids = childRows(rows, index);
    if (kids.length) {
      return kids.filter(function (child) { return child.variance != null; }).map(function (child) {
        return { label: child.label, variance: Number(child.variance), contribution: Number(child.variance), current: child.current };
      });
    }
    var byId = {};
    rows.forEach(function (item) {
      if ((item.depth || 0) === 0 && !byId[item.id]) byId[item.id] = item;
    });
    return (SUM_LINES[row.id] || []).map(function (pair) {
      var child = byId[pair[0]];
      if (!child || child.variance == null) return null;
      return { label: child.label, variance: Number(child.variance), contribution: pair[1] * Number(child.variance), current: child.current };
    }).filter(Boolean);
  }

  function largelyOffset(parent, offsetAbs) {
    return offsetAbs >= 10000 && Math.abs(parent) <= offsetAbs * 0.25;
  }

  function joinNames(bits) {
    if (bits.length < 2) return bits.join("");
    if (bits.length === 2) return bits[0] + " and " + bits[1];
    return bits.slice(0, -1).join(", ") + ", and " + bits[bits.length - 1];
  }

  var READ_LABELS = {
    "implementation and onboarding": "implementation",
    "research and development": "R&D",
    "general and administrative": "G&A"
  };

  function readLabel(label) {
    var text = sentenceLabel(label, false);
    return READ_LABELS[text] || text;
  }

  function movePercent(row) {
    if (row.comparison_amount == null || Number(row.comparison_amount) <= 0 || row.variance == null) return "";
    var rate = Math.abs(Number(row.variance) / Number(row.comparison_amount) * 100);
    if (rate < 0.1 || rate >= 100) return "";
    return " (" + rate.toFixed(1) + "%)";
  }

  function changeBit(part) {
    var up = Number(part.variance) > 0;
    return readLabel(part.label) + " (" + (up ? "up " : "down ") + moneyPhrase(Math.abs(part.variance)) + ")";
  }

  function namedParts(parts) {
    var material = parts.filter(function (part) { return Math.abs(part.contribution) >= 10000; });
    var smallNet = parts.reduce(function (total, part) {
      return Math.abs(part.contribution) < 10000 ? total + part.contribution : total;
    }, 0);
    if (Math.abs(smallNet) >= 10000) {
      material.push({ label: "other items", variance: smallNet, contribution: smallNet });
    }
    material.sort(function (left, right) { return Math.abs(right.contribution) - Math.abs(left.contribution); });
    return material;
  }

  function flowHead(row, win) {
    var parent = Number(row.variance);
    var up = parent > 0;
    var amount = moneyPhrase(Math.abs(parent));
    var level = row.current != null ? " to " + moneyPhrase(row.current) : "";
    var pct = movePercent(row);
    if (win.id === "budget" || win.id === "forecast") {
      var baseWord = win.id === "forecast" ? "forecast" : "budget";
      var favorable = !!FAVORABLE_UP[row.id];
      var good = favorable ? up : !up;
      return favorable
        ? sentenceLabel(row.label, true) + (good ? " outperformed " : " missed ") + baseWord + " by " + amount + pct + level
        : sentenceLabel(row.label, true) + " came in " + amount + (good ? " under " : " over ") + baseWord + level;
    }
    return sentenceLabel(row.label, true) + (up ? " rose " : " fell ") + amount + pct + level;
  }

  function componentClause(parent, parts) {
    var material = namedParts(parts);
    var same = material.filter(function (part) { return !part.contribution || (part.contribution > 0) === (parent > 0); });
    var against = material.filter(function (part) { return part.contribution && (part.contribution > 0) !== (parent > 0); });
    var otherNet = 0;
    parts.forEach(function (part) {
      if (!same.length || part === same[0]) return;
      otherNet += part.contribution;
    });
    var single = same.length === 1 && !against.length && Math.abs(otherNet) <= Math.abs(parent) * 0.1;
    if (single) return ", driven by " + changeBit(same[0]);
    var clause = "";
    if (same.length) clause += ", driven by " + joinNames(same.map(changeBit));
    if (against.length) {
      var offsetAbs = against.reduce(function (total, part) { return total + Math.abs(part.contribution); }, 0);
      clause += (largelyOffset(parent, offsetAbs) ? ", largely offset by " : ", partly offset by ") + joinNames(against.map(changeBit));
    }
    return clause;
  }

  function revenueSentence(row, rows, index, win) {
    if (!row || row.current == null) return "";
    var parent = row.variance == null ? 0 : Number(row.variance);
    if (!Math.round(parent) || Math.abs(parent) < 10000) return "Revenue was little changed at " + moneyPhrase(row.current) + ".";
    return flowHead(row, win) + componentClause(parent, themeParts(row, rows, index)) + ".";
  }

  function ebitdaSentence(row, rows, index, win) {
    if (!row || row.current == null) return "";
    var parent = row.variance == null ? 0 : Number(row.variance);
    var parts = themeParts(row, rows, index);
    var gross = parts.filter(function (part) { return sentenceLabel(part.label, false) === "gross profit"; })[0];
    var opex = parts.filter(function (part) { return sentenceLabel(part.label, false) === "operating expenses"; })[0];
    var offsetAbs = 0;
    parts.forEach(function (part) {
      if (part.contribution && (part.contribution > 0) !== (parent > 0)) offsetAbs += Math.abs(part.contribution);
    });
    var flat = Math.abs(parent) < 10000 || largelyOffset(parent, offsetAbs);
    if (flat && !largelyOffset(parent, offsetAbs)) return "EBITDA was little changed at " + moneyPhrase(row.current) + ".";
    var head = flat
      ? "EBITDA was largely flat at " + moneyPhrase(row.current) + ", " + (parent > 0 ? "up " : "down ") + moneyPhrase(Math.abs(parent))
      : flowHead(row, win);
    if (!gross || !opex) return head + componentClause(parent, parts) + ".";
    var grossUp = Number(gross.variance) > 0;
    var opexUp = Number(opex.variance) > 0;
    var text = head + ": gross profit " + (grossUp ? "rose " : "fell ") + moneyPhrase(Math.abs(gross.variance));
    var opexOffsets = (Number(opex.contribution) > 0) !== (parent > 0);
    if (opexOffsets && Math.abs(Number(opex.variance)) >= 10000) {
      text += (largelyOffset(parent, Math.abs(opex.contribution)) ? ", largely offset by " : ", partly offset by ");
      text += "operating expenses, " + (opexUp ? "up " : "down ") + moneyPhrase(Math.abs(opex.variance));
      var found = rowAt(rows, "total_opex");
      var functions = found ? namedParts(themeParts(found.row, rows, found.index)) : [];
      if (functions.length) text += ", led by " + joinNames(functions.map(changeBit));
    } else if (Math.abs(Number(opex.variance)) >= 10000) {
      text += " and operating expenses " + (opexUp ? "up " : "down ") + moneyPhrase(Math.abs(opex.variance));
    }
    return text + ".";
  }

  function lineById(lines, id) {
    for (var index = 0; index < (lines || []).length; index += 1) {
      if (lines[index].id === id) return lines[index];
    }
    return null;
  }

  function cashSentence(item, win) {
    var balance = statementOf(item, "balance_sheet");
    var cashFlow = statementOf(item, "cash_flow");
    var cash = lineById((balance && balance.lines) || [], "cash") || lineById((cashFlow && cashFlow.lines) || [], "ending_cash");
    if (!cash || cash.current == null) return "";
    var variance = cash.variance == null ? 0 : Number(cash.variance);
    var level = moneyPhrase(cash.current);
    if (!Math.round(variance) || Math.abs(variance) < 10000) return "Cash was little changed at " + level + ".";
    if (win.id === "budget" || win.id === "forecast") {
      var baseWord = win.id === "forecast" ? "forecast" : "budget";
      return "Cash was " + moneyPhrase(Math.abs(variance)) + (variance > 0 ? " above " : " below ") + baseWord + ", at " + level + ".";
    }
    var head = "Cash " + (variance > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(variance)) + " to " + level;
    var flows = (cashFlow && cashFlow.lines) || [];
    var cfo = lineById(flows, "cfo");
    var cfi = lineById(flows, "cfi");
    var cff = lineById(flows, "cff");
    if (!cfo || cfo.current == null || !cfi || cfi.current == null || !cff || cff.current == null) return head + ".";
    var total = Number(cfo.current) + Number(cfi.current) + Number(cff.current);
    if (Math.abs(total - variance) >= 10000) return head + ".";
    var parts = [
      { label: "operating cash flow", amount: Number(cfo.current) },
      { label: "investment", amount: Number(cfi.current) },
      { label: "financing", amount: Number(cff.current) }
    ].filter(function (part) { return Math.abs(part.amount) >= 10000; });
    var same = parts.filter(function (part) { return (part.amount > 0) === (variance > 0); });
    var against = parts.filter(function (part) { return part.amount && (part.amount > 0) !== (variance > 0); });
    if (!same.length) return head + ".";
    var text = head + ", driven by " + joinNames(same.map(function (part) { return moneyPhrase(Math.abs(part.amount)) + " of " + part.label; }));
    if (against.length) {
      var offsetAbs = against.reduce(function (sum, part) { return sum + Math.abs(part.amount); }, 0);
      text += (largelyOffset(variance, offsetAbs) ? ", largely offset by " : ", partly offset by ");
      text += joinNames(against.map(function (part) { return moneyPhrase(Math.abs(part.amount)) + " of " + part.label; }));
    }
    return text + ".";
  }

  function rowAt(rows, id) {
    for (var index = 0; index < rows.length; index += 1) {
      if ((rows[index].depth || 0) === 0 && rows[index].id === id) return { row: rows[index], index: index };
    }
    return null;
  }

  function anyRow(rows, id) {
    for (var index = 0; index < rows.length; index += 1) {
      if (rows[index].id === id) return rows[index];
    }
    return null;
  }

  function priorBit(amount, win) {
    if (amount == null || !win || win.id === "budget" || win.id === "forecast") return "";
    var name = comparisonName(win);
    return name ? " (" + moneyPhrase(amount) + " in " + name + ")" : "";
  }

  function movedFact(label, current, variance, base, win) {
    if (current == null) return "";
    var text = label + " " + (/receivables|expenses|services/i.test(label) ? "were" : "was") + " " + moneyPhrase(current);
    if (variance != null && Math.round(Number(variance))) {
      text += ", " + (Number(variance) > 0 ? "up " : "down ") + moneyPhrase(Math.abs(variance));
    }
    return text + priorBit(base, win);
  }

  function arrWindow(periods) {
    if (typeof global.boardWaterfallMonthM !== "function" || typeof global.boardWfTable !== "function") return null;
    var wf = global.boardWfTable();
    var last = null;
    var first = null;
    var nb = 0;
    var exp = 0;
    var react = 0;
    var con = 0;
    var churn = 0;
    var flows = false;
    (periods || []).forEach(function (period) {
      var index = parseInt(String(period).slice(5, 7), 10) - 1;
      if (index < 0) return;
      var month = global.boardWaterfallMonthM(wf, index);
      if (!month || month.eop == null) return;
      if (!first) first = month;
      last = month;
      ["nb", "exp", "react", "con", "churn"].forEach(function (key) {
        if (month[key] == null) return;
        flows = true;
      });
      if (month.nb != null) nb += month.nb;
      if (month.exp != null) exp += month.exp;
      if (month.react != null) react += month.react;
      if (month.con != null) con += month.con;
      if (month.churn != null) churn += month.churn;
    });
    if (!last) return null;
    return {
      bop: first.bop,
      eop: last.eop,
      nb: nb,
      exp: exp,
      react: react,
      con: con,
      churn: churn,
      net: flows ? nb + exp + react + con + churn : null,
    };
  }

  function dollarsM(value) {
    return value == null ? null : value * 1e6;
  }

  function discussionEventKey(win) {
    if (!win || (win.id !== "mom" && win.id !== "forecast") || !win.current || win.current.length !== 1) return "";
    var org = String(global.SMPL_ORG_ID || "");
    if (!org) return "";
    return win.id + "\n" + win.current[0] + "\n" + org;
  }

  function loadDiscussionEvents(win, host) {
    var key = discussionEventKey(win);
    if (!key || typeof fetch !== "function") return;
    if (discussionEvents.key === key && discussionEvents.status) return;
    discussionEvents = { key: key, status: "loading", events: [], lost: [] };
    var parts = key.split("\n");
    var base = (global.SMPL_API_BASE || "/api/v1").replace(/\/$/, "");
    fetch(
      base + "/commentary/customer-events?organization_id=" + encodeURIComponent(parts[2]) + "&period=" + encodeURIComponent(parts[1]) + "&kind=" + encodeURIComponent(parts[0]),
      { credentials: "include" }
    )
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) throw new Error("events_failed");
          return body;
        });
      })
      .then(function (body) {
        if (discussionEvents.key !== key) return;
        discussionEvents = { key: key, status: "ready", events: (body && body.events) || [], lost: (body && body.lost) || [] };
        global.SMPL_LOST_CUSTOMERS = discussionEvents.lost;
        if (host) render(host);
      })
      .catch(function () {
        if (discussionEvents.key !== key) return;
        discussionEvents = { key: key, status: "ready", events: [], lost: [] };
      });
  }

  function storedCustomerEvents(win) {
    if (!win || (win.id !== "mom" && win.id !== "forecast") || !win.current || win.current.length !== 1) return [];
    var key = discussionEventKey(win);
    if (key && discussionEvents.key === key && discussionEvents.status === "ready") return discussionEvents.events || [];
    return Array.isArray(global.SMPL_CUSTOMER_EVENTS) ? global.SMPL_CUSTOMER_EVENTS : [];
  }

  function storedLostCustomers(win) {
    if (!win || win.id !== "mom" || !win.current || win.current.length !== 1) return [];
    var key = discussionEventKey(win);
    if (key && discussionEvents.key === key && discussionEvents.status === "ready") return discussionEvents.lost || [];
    return Array.isArray(global.SMPL_LOST_CUSTOMERS) ? global.SMPL_LOST_CUSTOMERS : [];
  }

  function eventFor(events, bucket) {
    for (var index = 0; index < events.length; index += 1) {
      if (events[index] && events[index].bucket === bucket && events[index].customer) return events[index];
    }
    return null;
  }

  function shareOf(amount, whole) {
    if (whole == null || !Number(whole)) return "";
    return " (" + Math.round(Math.abs(Number(amount)) / Math.abs(Number(whole)) * 100) + "%)";
  }

  function customerSentence(event, part, waterfallAmount) {
    if (!event || !event.customer || event.amount == null) return "";
    var whole = waterfallAmount == null ? null : Math.abs(Number(waterfallAmount));
    var namedAmount = Math.abs(Number(event.amount));
    var othersAmount = event.others > 0 ? Math.abs(Number(event.others_amount || 0)) : 0;
    var named = moneyPhrase(namedAmount);
    if (event.outcome === "did not come in") return event.customer + " did not come in, " + named + " of " + part + shareOf(namedAmount, whole) + ".";
    if (event.outcome === "came in") return event.customer + " came in, " + named + " of " + part + shareOf(namedAmount, whole) + ".";
    if (whole != null && Math.abs(whole - namedAmount) < 1 && !(event.others > 0)) return "All of that " + part + " was " + event.customer + " (" + named + ").";
    var text = event.customer + " accounted for " + named + " of " + part + shareOf(namedAmount, whole);
    if (event.others > 0) text += ", " + event.others + " other customers " + moneyPhrase(othersAmount) + shareOf(othersAmount, whole);
    if (whole != null) {
      var smaller = whole - namedAmount - othersAmount;
      if (smaller >= 1) text += ", and " + (part === "expansion" ? "smaller expansions" : "smaller " + part) + " " + moneyPhrase(smaller) + shareOf(smaller, whole);
    }
    return text + ".";
  }

  function growthParagraph(rows, win) {
    var sentences = [];
    var revenue = anyRow(rows, "revenue");
    if (revenue && revenue.current != null) {
      var lead = "Revenue";
      if (revenue.variance != null && Math.round(Number(revenue.variance))) {
        lead += (Number(revenue.variance) > 0 ? " rose " : " fell ") + moneyPhrase(Math.abs(revenue.variance)) + movePercent(revenue) + " to " + moneyPhrase(revenue.current);
        if (revenue.comparison_amount != null && win.id !== "budget" && win.id !== "forecast") lead += " from " + moneyPhrase(revenue.comparison_amount);
      } else lead += " was " + moneyPhrase(revenue.current);
      sentences.push(lead + ".");
    }
    var classes = [];
    ["sub_rev", "rec_svc_rev", "impl_rev"].forEach(function (id) {
      var row = anyRow(rows, id);
      if (row) classes.push(row);
    });
    if (!classes.length && revenue) {
      var start = rows.indexOf(revenue);
      for (var cursor = start + 1; cursor < rows.length; cursor += 1) {
        if ((rows[cursor].depth || 0) === 0) break;
        if ((rows[cursor].depth || 0) === 1) classes.push(rows[cursor]);
      }
    }
    var classBits = [];
    classes.forEach(function (row) {
      if (!row || row.current == null) return;
      if (row.variance != null && Math.abs(Number(row.variance)) < 1000 && Math.abs(Number(row.current)) < 1000) return;
      var label = readLabel(row.label);
      var bit = label + " " + (label === "recurring services" ? "were " : "was ") + moneyPhrase(row.current);
      if (row.variance != null && Math.round(Number(row.variance))) bit += ", " + (Number(row.variance) > 0 ? "up " : "down ") + moneyPhrase(Math.abs(row.variance));
      classBits.push(bit);
    });
    if (classBits.length) {
      classBits[0] = classBits[0].charAt(0).toUpperCase() + classBits[0].slice(1);
      sentences.push(classBits.join("; ") + ".");
    }
    var book = arrWindow(win.current);
    var events = storedCustomerEvents(win);
    if (book && book.eop != null) {
      var arr = "Ending ARR was " + moneyPhrase(dollarsM(book.eop));
      if (book.net != null) arr += " after " + moneyPhrase(dollarsM(book.net)) + " of net new ARR";
      sentences.push(arr + ".");
      var baseBook = win.id === "forecast" ? null : arrWindow(win.base);
      [["nb", "New business", "New Business", "new business"], ["exp", "Expansion", "Expansion", "expansion"], ["con", "Contraction", "Contraction", "contraction"], ["churn", "Churn", "Churn", "churn"]].forEach(function (pair) {
        var amount = book[pair[0]];
        if (amount == null || Math.abs(dollarsM(amount)) < 1000) return;
        var clause = pair[1] + " was " + moneyPhrase(Math.abs(dollarsM(amount)));
        if (baseBook && baseBook[pair[0]] != null) clause += " from " + moneyPhrase(Math.abs(dollarsM(baseBook[pair[0]])));
        sentences.push(clause + ".");
        var named = customerSentence(eventFor(events, pair[2]), pair[3], dollarsM(amount));
        if (named) sentences.push(named);
      });
    }
    var kpis = typeof global.boardExecKpis === "function" ? global.boardExecKpis() : null;
    if (kpis && kpis.nrr != null && win.current && win.current.length === 1) {
      sentences.push("NRR was " + (Number(kpis.nrr) * 100).toFixed(1) + "%.");
    }
    return sentences.join(" ");
  }

  function ratioBit(part, whole, priorPart, priorWhole, win) {
    if (part == null || !whole) return "";
    var text = ((part / whole) * 100).toFixed(1) + "% of revenue";
    if (priorPart != null && priorWhole) text += ", from " + ((priorPart / priorWhole) * 100).toFixed(1) + "% in " + comparisonName(win);
    return text;
  }

  function profitParagraph(rows, win) {
    var sentences = [];
    var revenue = anyRow(rows, "revenue");
    var ebitda = anyRow(rows, "ebitda");
    var gross = anyRow(rows, "gross_profit");
    var opex = anyRow(rows, "total_opex");
    if (ebitda && ebitda.current != null) {
      var parent = ebitda.variance == null ? 0 : Number(ebitda.variance);
      var offset = opex && opex.variance != null ? Math.abs(Number(opex.variance)) : 0;
      var text = Math.abs(parent) < 10000 || (offset && largelyOffset(parent, offset))
        ? "EBITDA was largely flat at " + moneyPhrase(ebitda.current) + (Math.round(parent) ? ", " + (parent > 0 ? "up " : "down ") + moneyPhrase(Math.abs(parent)) : "")
        : "EBITDA was " + moneyPhrase(ebitda.current) + (Math.round(parent) ? ", " + (parent > 0 ? "up " : "down ") + moneyPhrase(Math.abs(parent)) + movePercent(ebitda) : "");
      sentences.push(text + ".");
    }
    var bridgeBits = [];
    if (gross && gross.current != null) bridgeBits.push("gross profit was " + moneyPhrase(gross.current) + (gross.variance != null && Math.round(Number(gross.variance)) ? ", " + (Number(gross.variance) > 0 ? "up " : "down ") + moneyPhrase(Math.abs(gross.variance)) : ""));
    if (opex && opex.current != null) bridgeBits.push("operating expenses were " + moneyPhrase(opex.current) + (opex.variance != null && Math.round(Number(opex.variance)) ? ", " + (Number(opex.variance) > 0 ? "up " : "down ") + moneyPhrase(Math.abs(opex.variance)) : ""));
    if (bridgeBits.length) sentences.push(bridgeBits[0].charAt(0).toUpperCase() + bridgeBits[0].slice(1) + (bridgeBits[1] ? ", and " + bridgeBits[1] : "") + ".");
    ["rd", "sm", "ga"].forEach(function (id) {
      var row = anyRow(rows, id);
      if (!row || row.current == null) return;
      var label = readLabel(row.label);
      var clause = label + (/marketing|services|expenses/.test(label) ? " were " : " was ") + moneyPhrase(row.current);
      if (row.variance != null && Math.round(Number(row.variance))) clause += ", " + (Number(row.variance) > 0 ? "up " : "down ") + moneyPhrase(Math.abs(row.variance));
      if (revenue && revenue.current) {
        var share = ratioBit(row.current, revenue.current, row.comparison_amount, revenue.comparison_amount, win);
        if (share) clause += ", " + share;
      }
      sentences.push(clause.charAt(0).toUpperCase() + clause.slice(1) + ".");
    });
    if (ebitda && revenue && revenue.current) {
      var margin = (Number(ebitda.current) / Number(revenue.current)) * 100;
      var marginText = "EBITDA margin was " + margin.toFixed(1) + "%";
      if (ebitda.comparison_amount != null && revenue.comparison_amount) {
        marginText += ", from " + ((Number(ebitda.comparison_amount) / Number(revenue.comparison_amount)) * 100).toFixed(1) + "% in " + comparisonName(win);
      }
      sentences.push(marginText + ".");
    }
    var net = anyRow(rows, "net_income");
    if (net && net.current != null) {
      var netMove = net.variance == null ? 0 : Number(net.variance);
      sentences.push((Math.abs(netMove) < 10000 ? "Net income was little changed at " + moneyPhrase(net.current) : movedFact("Net income", net.current, net.variance, net.comparison_amount, win)) + ".");
    }
    return sentences.filter(Boolean).join(" ");
  }

  function cashParagraph(item, win, rows) {
    var sentences = [];
    var balanceLines = ((statementOf(item, "balance_sheet") || {}).lines) || [];
    var bridge = cashSentence(item, win);
    var cashLine = lineById(balanceLines, "cash");
    if (bridge && cashLine && cashLine.current != null) {
      var level = moneyPhrase(cashLine.current);
      var at = bridge.indexOf(level);
      sentences.push(at < 0 ? bridge : bridge.slice(0, at + level.length) + priorBit(cashLine.comparison_amount, win) + bridge.slice(at + level.length));
    } else if (bridge) sentences.push(bridge);
    var flows = ((statementOf(item, "cash_flow") || {}).lines) || [];
    var cfo = lineById(flows, "cfo");
    var ebitda = anyRow(rows, "ebitda");
    if (cfo && cfo.current != null) {
      var already = bridge && bridge.indexOf(moneyPhrase(cfo.current)) >= 0;
      var cfoText = "Operating cash flow";
      if (already && cfo.comparison_amount != null && win.id !== "budget" && win.id !== "forecast") {
        cfoText += (Number(cfo.current) >= Number(cfo.comparison_amount) ? " rose from " : " fell from ") + moneyPhrase(cfo.comparison_amount);
      } else if (!already) cfoText += " was " + moneyPhrase(cfo.current) + priorBit(cfo.comparison_amount, win);
      if (ebitda && ebitda.current) cfoText += (cfoText === "Operating cash flow" ? " was " : " and was ") + (Number(cfo.current) / Number(ebitda.current)).toFixed(1) + " times EBITDA";
      if (cfoText !== "Operating cash flow") sentences.push(cfoText + ".");
    }
    var revenue = anyRow(rows, "revenue");
    var deferred = stockRow(item, win, "deferred_rev", ["deferred_rev", "deferred_revenue", "dr"]);
    if (revenue && revenue.current != null && deferred && deferred.variance != null) {
      var billings = Number(revenue.current) + Number(deferred.variance);
      sentences.push("Calculated billings were " + moneyPhrase(billings) + ", revenue plus the change in deferred revenue.");
    }
    if (deferred && deferred.current != null) sentences.push(movedFact("Deferred revenue", deferred.current, deferred.variance, null, win) + ".");
    var receivables = stockRow(item, win, "ar", ["ar", "accounts_receivable"]);
    if (receivables) {
      var arText = movedFact("Receivables", receivables.current, receivables.variance, null, win);
      if (revenue && revenue.current && receivables.current != null) {
        arText += ", " + Math.round(Number(receivables.current) / Number(revenue.current) * 30) + " days of revenue";
        if (receivables.comparison_amount != null && revenue.comparison_amount) {
          arText += " against " + Math.round(Number(receivables.comparison_amount) / Number(revenue.comparison_amount) * 30) + " in " + comparisonName(win);
        }
      }
      sentences.push(arText + ".");
    }
    return sentences.filter(function (sentence) { return sentence && sentence !== "."; }).join(" ");
  }

  function stockRow(item, win, id, keys) {
    var line = lineById((((statementOf(item, "balance_sheet") || {}).lines) || []), id);
    if (line && line.current != null) return line;
    return win ? metricRow(win, "bs", id, id, 0, keys) : line;
  }

  function proseMonth(period) {
    var names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    var month = parseInt(String(period || "").slice(5, 7), 10);
    if (!month || month > 12) return monthName(period);
    return names[month - 1];
  }

  function displayCustomer(name) {
    return String(name || "").replace(/\s+\d+$/, "");
  }

  function allowedPercent(delta, prior) {
    if (prior == null || prior <= 0 || !delta) return "";
    var rate = Math.abs(delta) / prior * 100;
    if (rate < 0.1 || rate >= 100) return "";
    return " (" + rate.toFixed(1) + "%)";
  }

  function revenueClasses(rows) {
    var classes = [];
    ["sub_rev", "rec_svc_rev", "impl_rev"].forEach(function (id) {
      var row = anyRow(rows, id);
      if (row && row.current != null) classes.push(row);
    });
    return classes;
  }

  function subscriptionDrives(row, classes, parent) {
    if (!row || row.id !== "sub_rev" || !parent || (Number(row.variance) > 0) !== (parent > 0)) return false;
    var net = 0;
    for (var index = 0; index < classes.length; index += 1) {
      if (classes[index] === row) continue;
      var variance = Number(classes[index].variance || 0);
      if (Math.abs(variance) >= 10000) return false;
      net += variance;
    }
    return Math.abs(net) <= Math.abs(parent) * 0.1;
  }

  function componentDirections(book, base) {
    var fell = [];
    var declined = [];
    var rose = [];
    var increased = [];
    function take(key, name, drag) {
      if (book[key] == null || base[key] == null) return;
      var current = Math.abs(dollarsM(book[key]));
      var prior = Math.abs(dollarsM(base[key]));
      if (Math.abs(current - prior) < 1000) return;
      if (drag) (current < prior ? fell : increased).push(name);
      else (current < prior ? declined : rose).push(name);
    }
    take("churn", "churn", true);
    take("con", "contraction", true);
    take("nb", "new business", false);
    take("exp", "expansion", false);
    var bits = [];
    if (fell.length) bits.push(joinNames(fell) + " fell");
    if (declined.length) bits.push(joinNames(declined) + " declined");
    if (rose.length) bits.push(joinNames(rose) + " rose");
    if (increased.length) bits.push(joinNames(increased) + " increased");
    if (!bits.length) return "";
    return bits[0].charAt(0).toUpperCase() + bits[0].slice(1) + (bits.length > 1 ? ", and " + bits.slice(1).join(", and ") : "") + ".";
  }

  function namedCustomerPhrase(event, part, whole, month) {
    if (!event || !event.customer || event.amount == null || !whole) return "";
    var name = displayCustomer(event.customer);
    var namedAmount = Math.abs(Number(event.amount));
    var othersAmount = event.others > 0 ? Math.abs(Number(event.others_amount || 0)) : 0;
    if (Math.abs(whole - namedAmount) < 1 && !(event.others > 0)) return "all of it from " + name;
    var verb = part === "expansion" ? "expanded by" : part === "contraction" ? "contracted by" : part === "churn" ? "churned" : "added";
    var text = name + " " + verb + " " + moneyPhrase(namedAmount) + ", " + Math.round(namedAmount / whole * 100) + "% of " + month + "'s " + part;
    if (event.others > 0) text += "; " + event.others + " other customers " + verb + " $10k or more each, adding " + moneyPhrase(othersAmount) + shareOf(othersAmount, whole);
    var smaller = whole - namedAmount - othersAmount;
    if (smaller >= 1) {
      var gerund = part === "expansion" ? "expanding" : part === "contraction" ? "contracting" : part === "churn" ? "churning" : "adding";
      var byWord = part === "churn" || part === "new business" ? " " : " by ";
      text += ", and customers " + gerund + byWord + "less than $10k each added the remaining " + moneyPhrase(smaller) + shareOf(smaller, whole);
    }
    return text;
  }

  function gtmMovement(win) {
    if (typeof global.boardGtmSummary !== "function") return "";
    var summary = global.boardGtmSummary(win);
    if (!summary || summary.won == null || summary.pipe == null) return "";
    function dollars(value) {
      if (value == null) return null;
      return summary.dollars ? Number(value) : Number(value) * 1e6;
    }
    var won = dollars(summary.won);
    var pipe = dollars(summary.pipe);
    var baseWon = dollars(summary.baseWon);
    var basePipe = dollars(summary.basePipe);
    if (won == null || pipe == null) return "";
    var text = "In go to market, closed won ";
    if (baseWon != null && Math.abs(won - baseWon) >= 1000) text += (won < baseWon ? "fell to " : "rose to ") + moneyPhrase(won) + " from " + moneyPhrase(baseWon);
    else text += "was " + moneyPhrase(won);
    if (basePipe != null && Math.abs(pipe - basePipe) >= 1000) text += " and new pipeline to " + moneyPhrase(pipe) + " from " + moneyPhrase(basePipe);
    else text += " and new pipeline was " + moneyPhrase(pipe);
    return text;
  }

  function headcountMovement(win) {
    if (typeof global.boardWorkforce !== "function" || !win.base || !win.base.length) return "";
    var heads = (global.boardWorkforce() || {}).heads_total || [];
    var closeYear = String(global.CLOSE_MONTH || "").slice(0, 4);
    function at(period) {
      if (!period || String(period).slice(0, 4) !== closeYear) return null;
      var index = parseInt(String(period).slice(5, 7), 10) - 1;
      return heads[index] != null ? heads[index] : null;
    }
    var current = at(win.current[win.current.length - 1]);
    var prior = at(win.base[win.base.length - 1]);
    if (current == null || prior == null || current === prior) return "";
    var delta = current - prior;
    return "Headcount " + (delta > 0 ? "grew by " + delta : "fell by " + Math.abs(delta)) + " to " + current + ".";
  }

  function monthCollections(win) {
    var bridge = (global.SMPL_CASH_BRIDGE && global.SMPL_CASH_BRIDGE.Actual) ||
      (global.SMPL_OUTLOOK_PAYLOAD && global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE && global.SMPL_OUTLOOK_PAYLOAD.CASH_BRIDGE.Actual) ||
      {};
    var row = bridge[win.current[win.current.length - 1]];
    return row && row.collections != null ? Number(row.collections) : null;
  }

  function shipsToday(item, rows, win) {
    var month = proseMonth(win.current[win.current.length - 1]);
    var baseMonth = win.base && win.base.length ? proseMonth(win.base[win.base.length - 1]) : "";
    var paragraphs = [];
    var revenue = anyRow(rows, "revenue");
    var ebitda = anyRow(rows, "ebitda");
    var gross = anyRow(rows, "gross_profit");
    var opex = anyRow(rows, "total_opex");
    var book = arrWindow(win.current);
    var baseBook = arrWindow(win.base);
    var opening = [];
    if (book && book.eop != null && book.net != null && baseBook && baseBook.net != null) {
      var netNew = dollarsM(book.net);
      var priorNet = dollarsM(baseBook.net);
      var netDelta = netNew - priorNet;
      var arrLine = "In " + month + ", net new ARR " + (Math.abs(netDelta) < 1000 ? "was " + moneyPhrase(netNew) : (netDelta > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(netDelta)) + " over " + baseMonth + " to " + moneyPhrase(netNew)) + ", and ending ARR reached " + moneyPhrase(dollarsM(book.eop)) + ".";
      var directions = componentDirections(book, baseBook);
      if (directions) arrLine += " " + directions;
      opening.push(arrLine);
    }
    if (revenue && revenue.current != null && revenue.variance != null && Math.abs(Number(revenue.variance)) >= 1000) {
      var profitBit = "";
      if (ebitda && ebitda.current != null) {
        var parent = ebitda.variance == null ? 0 : Number(ebitda.variance);
        var offset = opex && opex.variance != null ? Math.abs(Number(opex.variance)) : 0;
        var flat = Math.abs(parent) < 10000 || largelyOffset(parent, offset);
        profitBit = flat
          ? " EBITDA was largely flat at " + moneyPhrase(ebitda.current)
          : " EBITDA " + (parent > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(parent)) + " to " + moneyPhrase(ebitda.current);
        if (flat && gross && opex && Number(gross.variance) > 0 && Number(opex.variance) > 0 && offset >= 10000) profitBit += ", with higher operating expenses offsetting higher gross profit";
        profitBit += ".";
      }
      opening.push("Revenue " + (Number(revenue.variance) > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(revenue.variance)) + movePercent(revenue) + " month over month to " + moneyPhrase(revenue.current) + "." + profitBit);
    }
    var cashLine = lineById((((statementOf(item, "balance_sheet") || {}).lines) || []), "cash");
    var cfoLine = lineById((((statementOf(item, "cash_flow") || {}).lines) || []), "cfo");
    if (cashLine && cashLine.current != null && cashLine.variance != null && Math.abs(Number(cashLine.variance)) >= 1000) {
      var cashText = "Cash " + (Number(cashLine.variance) > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(cashLine.variance)) + " in " + month + " to " + moneyPhrase(cashLine.current);
      if (cfoLine && cfoLine.current != null && ebitda && ebitda.current) cashText += ", and operating cash flow was " + (Number(cfoLine.current) / Number(ebitda.current)).toFixed(1) + " times EBITDA";
      opening.push(cashText + ".");
    }
    if (opening.length) paragraphs.push(opening.join("\n\n"));

    var events = storedCustomerEvents(win);
    if (book) {
      var bookings = [];
      if (book.nb != null && baseBook && baseBook.nb != null) {
        var nb = Math.abs(dollarsM(book.nb));
        var nbPrior = Math.abs(dollarsM(baseBook.nb));
        var nbDelta = nb - nbPrior;
        if (Math.abs(nbDelta) >= 1000 || nb >= 1000) {
          bookings.push("New business ARR, which counts new logos, winbacks and first-year expansion, " + (nbDelta < 0 ? "fell " : "rose ") + moneyPhrase(Math.abs(nbDelta)) + allowedPercent(nbDelta, nbPrior) + " to " + moneyPhrase(nb) + " in " + month + " from " + moneyPhrase(nbPrior) + " in " + baseMonth + ".");
        }
      }
      if (book.exp != null && baseBook && baseBook.exp != null) {
        var exp = Math.abs(dollarsM(book.exp));
        var expPrior = Math.abs(dollarsM(baseBook.exp));
        var expDelta = exp - expPrior;
        if (Math.abs(expDelta) >= 1000 || exp >= 1000) {
          var expansion = "Expansion ARR from existing customers " + (expDelta < 0 ? "declined " : "rose ") + moneyPhrase(Math.abs(expDelta)) + allowedPercent(expDelta, expPrior) + " over " + baseMonth + " to " + moneyPhrase(exp) + ".";
          var customers = namedCustomerPhrase(eventFor(events, "Expansion"), "expansion", exp, month);
          if (customers && customers.indexOf("all of it from ") !== 0) expansion += " " + customers + ".";
          bookings.push(expansion);
        }
      }
      var market = gtmMovement(win);
      if (market) bookings.push(market + ".");
      if (bookings.length) paragraphs.push("Bookings and pipeline. " + bookings.join(" "));
      var retention = [];
      if (book.churn != null && baseBook && baseBook.churn != null) {
        var churn = Math.abs(dollarsM(book.churn));
        var churnPrior = Math.abs(dollarsM(baseBook.churn));
        var churnDelta = churn - churnPrior;
        if (Math.abs(churnDelta) >= 1000 || churn >= 1000) {
          var churnText = "Churn " + (churnDelta < 0 ? "fell " : "rose ") + moneyPhrase(Math.abs(churnDelta)) + " over " + baseMonth + " to " + moneyPhrase(churn);
          var churnCustomers = namedCustomerPhrase(eventFor(events, "Churn"), "churn", churn, month);
          if (churnCustomers && churnCustomers.indexOf("all of it from ") === 0) churnText += ", " + churnCustomers;
          else if (churnCustomers) churnText += ". " + churnCustomers;
          retention.push(churnText + ".");
        }
      }
      if (book.con != null && baseBook && baseBook.con != null) {
        var contraction = Math.abs(dollarsM(book.con));
        var contractionPrior = Math.abs(dollarsM(baseBook.con));
        var contractionDelta = contraction - contractionPrior;
        if (Math.abs(contractionDelta) >= 1000) {
          retention.push("Contraction was " + moneyPhrase(contraction) + ", " + (contractionDelta < 0 ? "down " : "up ") + moneyPhrase(Math.abs(contractionDelta)) + ".");
        }
      }
      if (retention.length) paragraphs.push("Retention. " + retention.join(" "));
    }

    var classes = revenueClasses(rows);
    var revenueSentences = [];
    classes.forEach(function (row) {
      if (row.variance == null || Math.abs(Number(row.variance)) < 1000) return;
      var variance = Number(row.variance);
      var label = row.id === "sub_rev" ? "Subscription revenue" : row.id === "rec_svc_rev" ? "Recurring services" : "Implementation and onboarding revenue";
      var verb = row.id === "sub_rev" ? (variance > 0 ? "rose " : "fell ") : (variance > 0 ? "increased " : "decreased ");
      var sentence = label + " " + verb + moneyPhrase(Math.abs(variance));
      if (row.id === "sub_rev") sentence += " in " + month;
      else if (row.id === "rec_svc_rev") sentence += " over " + baseMonth;
      sentence += " to " + moneyPhrase(row.current);
      if (row.id === "sub_rev" && revenue && subscriptionDrives(row, classes, Number(revenue.variance))) sentence += ", driving the revenue increase";
      revenueSentences.push(sentence);
    });
    if (revenueSentences.length > 2) {
      revenueSentences = [revenueSentences[0] + ". " + revenueSentences[1] + ", and " + revenueSentences[2].charAt(0).toLowerCase() + revenueSentences[2].slice(1) + "."];
    } else if (revenueSentences.length === 2) {
      revenueSentences = [revenueSentences[0] + ". " + revenueSentences[1] + "."];
    } else if (revenueSentences.length) revenueSentences[0] += ".";
    if (gross && gross.current != null && gross.variance != null && Math.abs(Number(gross.variance)) >= 1000) {
      var grossText = "Gross profit " + (Number(gross.variance) > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(gross.variance)) + " to " + moneyPhrase(gross.current);
      var cogs = anyRow(rows, "cogs");
      var cogsMove = cogs && cogs.variance != null ? Number(cogs.variance) : (revenue && revenue.variance != null && gross.variance != null ? Number(revenue.variance) - Number(gross.variance) : null);
      if (cogsMove != null && Math.abs(cogsMove) >= 1000) grossText += ", with cost of revenue " + (cogsMove > 0 ? "up " : "down ") + moneyPhrase(Math.abs(cogsMove));
      if (revenue && revenue.current && revenue.comparison_amount && gross.comparison_amount) {
        var marginNow = Number(gross.current) / Number(revenue.current) * 100;
        var marginThen = Number(gross.comparison_amount) / Number(revenue.comparison_amount) * 100;
        var bps = Math.round((marginNow - marginThen) * 100);
        grossText += ", and gross margin was " + marginNow.toFixed(1) + "%";
        if (Math.abs(bps) >= 10) grossText += ", " + (bps > 0 ? "up " : "down ") + Math.abs(bps) + "bps";
      }
      revenueSentences.push(grossText + ".");
    }
    if (revenueSentences.length) paragraphs.push("Revenue. " + revenueSentences.join(" "));

    var spending = [];
    if (opex && opex.current != null && opex.variance != null && Math.abs(Number(opex.variance)) >= 1000) {
      var opexUp = Number(opex.variance) > 0;
      var functionRows = ["rd", "sm", "ga"].map(function (id) { return anyRow(rows, id); }).filter(function (row) {
        return row && row.variance != null && Math.abs(Number(row.variance)) >= 1000 && (Number(row.variance) > 0) === opexUp;
      }).sort(function (left, right) { return Math.abs(Number(right.variance)) - Math.abs(Number(left.variance)); });
      var spendText = "Operating expenses " + (opexUp ? "rose " : "fell ") + moneyPhrase(Math.abs(opex.variance)) + " in " + month + " to " + moneyPhrase(opex.current) + ".";
      if (functionRows.length) {
        var lead = functionRows[0];
        var leadLabel = readLabel(lead.label);
        var share = revenue && revenue.current && revenue.comparison_amount && lead.comparison_amount
          ? ", or " + (Number(lead.current) / Number(revenue.current) * 100).toFixed(1) + "% of revenue from " + (Number(lead.comparison_amount) / Number(revenue.comparison_amount) * 100).toFixed(1) + "% in " + baseMonth
          : "";
        var rest = functionRows.slice(1).map(function (row) {
          var label = readLabel(row.label);
          return label + " " + (Number(row.variance) > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(row.variance));
        });
        spendText += " " + leadLabel.charAt(0).toUpperCase() + leadLabel.slice(1) + " accounted for " + moneyPhrase(Math.abs(lead.variance)) + " of the " + (opexUp ? "increase" : "decrease") + ", reaching " + moneyPhrase(lead.current) + share + (rest.length ? "; " + rest.join(" and ") : "") + ".";
      }
      spending.push(spendText);
    }
    var people = headcountMovement(win);
    if (people) spending.push(people);
    if (ebitda && revenue && revenue.current) {
      var ebitdaMargin = "EBITDA margin was " + (Number(ebitda.current) / Number(revenue.current) * 100).toFixed(1) + "%";
      if (ebitda.comparison_amount != null && revenue.comparison_amount) ebitdaMargin += ", from " + (Number(ebitda.comparison_amount) / Number(revenue.comparison_amount) * 100).toFixed(1) + "%";
      var net = anyRow(rows, "net_income");
      if (net && net.current != null) {
        var netMove = net.variance == null ? 0 : Number(net.variance);
        ebitdaMargin += Math.abs(netMove) < 10000 ? ", and net income was little changed at " + moneyPhrase(net.current) : ", and net income " + (netMove > 0 ? "rose " : "fell ") + moneyPhrase(Math.abs(netMove)) + " to " + moneyPhrase(net.current);
      }
      spending.push(ebitdaMargin + ".");
    }
    if (spending.length) paragraphs.push("Spending and profit. " + spending.join(" "));

    var cashBits = [];
    var flows = ((statementOf(item, "cash_flow") || {}).lines) || [];
    var cfo = lineById(flows, "cfo");
    var cfi = lineById(flows, "cfi");
    var cff = lineById(flows, "cff");
    if (cashLine && cashLine.variance != null && cfo && cfi && cff && cfo.current != null && cfi.current != null && cff.current != null) {
      var cashVariance = Number(cashLine.variance);
      var flowTotal = Number(cfo.current) + Number(cfi.current) + Number(cff.current);
      if (Math.abs(cashVariance) >= 10000 && Math.abs(flowTotal - cashVariance) < 10000) {
        var same = [];
        var against = [];
        [{ label: "operating cash flow", amount: Number(cfo.current), prior: cfo.comparison_amount }, { label: "investment", amount: Number(cfi.current) }, { label: "financing", amount: Number(cff.current) }].forEach(function (part) {
          if (Math.abs(part.amount) < 10000) return;
          ((part.amount > 0) === (cashVariance > 0) ? same : against).push(part);
        });
        if (same.length) {
          var driven = "The cash " + (cashVariance > 0 ? "increase" : "decrease") + " was driven by " + same.map(function (part) {
            var bit = moneyPhrase(Math.abs(part.amount)) + " of " + part.label;
            if (part.prior != null && baseMonth) bit += (Number(part.amount) >= Number(part.prior) ? ", up from " : ", down from ") + moneyPhrase(part.prior) + " in " + baseMonth;
            return bit;
          }).join(" and ");
          if (against.length) {
            var offsetAbs = against.reduce(function (sum, part) { return sum + Math.abs(part.amount); }, 0);
            driven += (largelyOffset(cashVariance, offsetAbs) ? ", largely offset by " : ", partly offset by ") + against.map(function (part) { return moneyPhrase(Math.abs(part.amount)) + " of " + part.label; }).join(" and ");
          }
          cashBits.push(driven + ".");
        }
      }
    }
    var collections = monthCollections(win);
    var deferred = stockRow(item, win, "deferred_rev", ["deferred_rev", "deferred_revenue", "dr"]);
    var billings = revenue && revenue.current != null && deferred && deferred.variance != null ? Number(revenue.current) + Number(deferred.variance) : null;
    if (collections != null || billings != null) {
      var moneyBits = [];
      if (collections != null) moneyBits.push("Collections were " + moneyPhrase(collections));
      if (billings != null) moneyBits.push((collections != null ? "calculated" : "Calculated") + " billings were " + moneyPhrase(billings) + ", revenue plus the change in deferred revenue");
      cashBits.push(moneyBits.join(" and ") + ".");
    }
    var receivables = stockRow(item, win, "ar", ["ar", "accounts_receivable"]);
    var balanceBits = [];
    if (receivables && receivables.current != null) {
      var arText = "Receivables " + (receivables.variance != null && Number(receivables.variance) < 0 ? "fell " : "rose ") + (receivables.variance != null ? moneyPhrase(Math.abs(receivables.variance)) + " to " : "") + moneyPhrase(receivables.current);
      if (revenue && revenue.current) {
        arText += ", or " + Math.round(Number(receivables.current) / Number(revenue.current) * 30) + " days of revenue";
        if (receivables.comparison_amount != null && revenue.comparison_amount) arText += " from " + Math.round(Number(receivables.comparison_amount) / Number(revenue.comparison_amount) * 30);
      }
      balanceBits.push(arText);
    }
    if (deferred && deferred.current != null && deferred.variance != null && Math.abs(Number(deferred.variance)) >= 1000) {
      balanceBits.push("deferred revenue " + (Number(deferred.variance) < 0 ? "declined " : "rose ") + moneyPhrase(Math.abs(deferred.variance)) + " to " + moneyPhrase(deferred.current));
    }
    if (balanceBits.length) cashBits.push(balanceBits.join(", and ") + ".");
    if (cashBits.length) paragraphs.push("Cash. " + cashBits.join(" "));
    return paragraphs;
  }

  function monthRead(item, host) {
    var pieces = monthPieces(item, host);
    var win = windowFor(item);
    loadDiscussionEvents(win, host);
    var rows = buildIncome(item, statementOf(item, "income_statement"));
    if (!win || !rows.length) return pieces;
    if (win.id === "mom" && win.current && win.current.length === 1) {
      var story = shipsToday(item, rows, win);
      if (story.length) return story;
    }
    var opening = periodHeading(win);
    var growth = growthParagraph(rows, win);
    var profit = profitParagraph(rows, win);
    var cash = cashParagraph(item, win, rows);
    var body = [];
    if (growth) body.push((opening ? opening + ". " : "") + growth);
    if (profit) body.push(profit);
    if (cash) body.push(cash);
    return body.length ? body : pieces;
  }

  function zipNodes(current, base, depth, win, signLine) {
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
    if (order.length > 1 && order.every(function (id) { return (byId[id].current || byId[id].base || {}).account_number; })) {
      order.sort(function (a, b) {
        var left = String((byId[a].current || byId[a].base).account_number);
        var right = String((byId[b].current || byId[b].base).account_number);
        return left.localeCompare(right, undefined, { numeric: true });
      });
    }
    var revenueFlow = { "revenue|sub_rev": 0, "revenue|rec_svc_rev": 1, "revenue|impl_rev": 2 };
    if (order.some(function (id) { return revenueFlow[id] != null; })) {
      order.sort(function (a, b) {
        var left = revenueFlow[a] == null ? 50 : revenueFlow[a];
        var right = revenueFlow[b] == null ? 50 : revenueFlow[b];
        return left - right;
      });
    }
    var rows = [];
    order.forEach(function (id) {
      var pair = byId[id];
      var cur = pair.current || {};
      var bas = pair.base || {};
      var label = accountLabel(cur.account_number || bas.account_number, cur.label || bas.label || "Line");
      var kids = zipNodes(cur.children, bas.children, depth + 1, win, signLine);
      var direct = kids.filter(function (row) { return row.depth === depth + 1; });
      var currentAmount = pair.current ? cur.amount : null;
      var baseAmount = pair.base ? bas.amount : null;
      var role = cur.role || bas.role || "";
      if (role !== "plug" && String(label).indexOf("Items not yet mapped") === 0) role = "plug";
      var row = makeRow({
        id: id,
        label: label,
        current: currentAmount,
        base: baseAmount,
        depth: depth,
        expandable: direct.length > 0,
        role: role,
        accountNumber: cur.account_number || bas.account_number || "",
        accountName: cur.label || bas.label || "",
        lineKey: cur.line_key || bas.line_key || "",
        signLine: signLine || "",
        vendor: cur.vendor || bas.vendor || "",
        facts: (cur.payouts || []).concat(bridgeFacts(cur, bas), pairMeasures(cur.measures, bas.measures)),
        unassigned: String(label).indexOf("No ") === 0,
        key: win.id + "|glrollup|" + id,
      });
      writeTreeCommentary(row, direct, win);
      rows.push(row);
      kids.forEach(function (child) { rows.push(child); });
    });
    return rows;
  }

  function attachChildren(line, currentNodes, baseNodes, win) {
    var kids = zipNodes(currentNodes, baseNodes, (line.depth || 0) + 1, win, line.id);
    var direct = kids.filter(function (row) { return row.depth === (line.depth || 0) + 1; });
    line.expandable = direct.length > 0;
    line.signLine = line.signLine || line.id;
    kids.forEach(function (row) { row.signLine = line.signLine; });
    if (line.expandable) writeTreeCommentary(line, direct, win);
    return kids;
  }

  function accountLabel(number, label) {
    var acct = String(number || "").trim();
    var name = String(label || "").trim();
    if (!acct) return name;
    if (name === acct || name.indexOf(acct + " ") === 0 || name.indexOf(acct + " ·") === 0) return name;
    return acct + " " + name;
  }

  function revenueClassKey(label) {
    var text = String(label || "").toLowerCase();
    if (text.indexOf("implementation") >= 0 || text.indexOf("onboarding") >= 0 || text.indexOf("professional") >= 0) return "impl";
    if (text.indexOf("service") >= 0 || text.indexOf("support") >= 0 || text.indexOf("technical account") >= 0) return "recurring";
    return "subscription";
  }

  function collectAccounts(nodes, out) {
    (nodes || []).forEach(function (node) {
      if (!node || node.role === "plug") return;
      if (node.account_number || node.role === "account" || !(node.children || []).length) {
        out.push(node);
        return;
      }
      var before = out.length;
      collectAccounts(node.children, out);
      if (out.length === before) out.push(node);
    });
    return out;
  }

  function regroupRevenue(nodes) {
    var plugs = (nodes || []).filter(function (node) { return node && node.role === "plug"; });
    var accounts = collectAccounts(nodes, []);
    if (!accounts.length) return nodes || [];
    var buckets = { subscription: [], recurring: [], impl: [] };
    accounts.forEach(function (node) { buckets[revenueClassKey(node.label)].push(node); });
    var classes = [
      ["subscription", "Subscription Revenue", "sub_rev"],
      ["recurring", "Recurring Services", "rec_svc_rev"],
      ["impl", "Implementation & Onboarding", "impl_rev"],
    ].map(function (spec) {
      var kids = buckets[spec[0]];
      if (!kids.length) return null;
      var node = {
        id: "revenue|" + spec[2],
        label: spec[1],
        role: "revenue_class",
        statement_line: "revenue",
        line_key: spec[2],
        account_number: "",
        amount: round2(kids.reduce(function (total, child) { return total + Number(child.amount || 0); }, 0)),
        children: kids,
      };
      if (kids.length === 1) {
        var only = kids[0];
        node.account_number = only.account_number || "";
        node.vendor = only.vendor || "";
        node.measures = (only.measures || []).slice();
        node.children = (only.children || []).filter(function (child) { return child.role === "vendor"; });
      }
      return node;
    }).filter(Boolean);
    return classes.concat(plugs);
  }

  function pushRollupLine(rows, lines, win, id, label, currentNode, baseNode) {
    var currentNodes = (currentNode && currentNode.children) || [];
    var baseNodes = (baseNode && baseNode.children) || [];
    if (id === "revenue") {
      currentNodes = regroupRevenue(currentNodes);
      baseNodes = regroupRevenue(baseNodes);
    }
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
    [lineOrMetric(lines, win, "gross_profit", "Gross profit", 0)].forEach(function (row) {
      if (!row) return;
      row.gapAfter = true;
      rows.push(row);
    });
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
    fillStatementParagraphs(rows, win);
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
    [lineOrMetric(lines, win, "gross_profit", "Gross profit", 0)].forEach(function (row) {
      if (!row) return;
      row.gapAfter = true;
      rows.push(row);
    });
    appendFunction(rows, lines, win, entries, "sm", "Sales and marketing");
    appendFunction(rows, lines, win, entries, "rd", "Research and development");
    appendFunction(rows, lines, win, entries, "ga", "General and administrative");
    appendFunction(rows, lines, win, entries, "unmapped", "Unmapped operating expense");
    [lineOrMetric(lines, win, "total_opex", "Operating expenses", 0), metricRow(win, "is", "ebitda", "EBITDA", 0, "ebitda"), lineOrMetric(lines, win, "da", "Depreciation and amortization", 0), lineOrMetric(lines, win, "interest", "Interest", 0), metricRow(win, "is", "op_income", "Operating income", 0, "op_income"), metricRow(win, "is", "pretax", "Pretax income", 0, "pretax"), lineOrMetric(lines, win, "tax", "Tax", 0), lineOrMetric(lines, win, "net_income", "Net income", 0)].forEach(function (row) { if (row) rows.push(row); });
    fillStatementParagraphs(rows, win);
    return rows;
  }

  function claimKeys(used, keys) {
    (keys || []).forEach(function (key) { if (used) used[key] = true; });
  }

  function loadedKeys(win, table) {
    var found = {};
    if (!win || !win.src || !win.src.ts) return found;
    ["current", "base"].forEach(function (side) {
      var scenario = side === "base" ? win.scenario : "Actual";
      var block = (win.src.ts[scenario] && win.src.ts[scenario][table]) || {};
      (win[side] || []).forEach(function (period) {
        var record = block[period];
        if (!record || typeof record !== "object") return;
        Object.keys(record).forEach(function (key) {
          if (record[key] != null && record[key] !== "") found[key] = true;
        });
      });
    });
    return found;
  }

  function keyLabel(key) {
    var text = String(key || "").replace(/_/g, " ");
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Line";
  }

  function narrateRow(row, win) {
    if (!global.SMPL_REPORTING_ENGINE || !win || !row) return row;
    row.commentary = reportParagraph(row, comparisonName(win));
    return row;
  }

  function buildSection(rows, lines, win, table, section, used) {
    var kids = [];
    claimKeys(used, section.keys);
    section.children.forEach(function (child) {
      claimKeys(used, child[2] || [child[0]]);
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
    parent.signLine = parent.signLine || section.id;
    kids.forEach(function (row) { row.signLine = row.signLine || section.id; });
    if (global.SMPL_REPORTING_ENGINE && win && kids.length) {
      kids.forEach(function (row) { narrateRow(row, win); });
      writeTreeCommentary(parent, kids, win);
    }
    rows.push(parent);
    kids.forEach(function (row) { rows.push(row); });
  }

  function appendUnmappedLines(rows, win, table, used, skip) {
    if (!global.SMPL_REPORTING_ENGINE || !win) return;
    var kids = [];
    Object.keys(loadedKeys(win, table)).sort().forEach(function (key) {
      if (used[key] || skip[key]) return;
      var row = metricRow(win, table, key, keyLabel(key), 1, [key]);
      if (!row) return;
      row.signLine = "unmapped";
      narrateRow(row, win);
      kids.push(row);
      used[key] = true;
    });
    if (!kids.length) return;
    var parent = makeRow({
      id: "unmapped_lines",
      label: "Items not yet mapped",
      current: sumSide(kids, "current"),
      base: sumSide(kids, "comparison_amount"),
      depth: 0,
      role: "plug",
      signLine: "unmapped",
      key: win.id + "|" + table + "|unmapped_lines",
    });
    parent.expandable = true;
    writeTreeCommentary(parent, kids, win);
    rows.push(parent);
    kids.forEach(function (row) { rows.push(row); });
  }

  function buildCash(item, statement) {
    var win = windowFor(item);
    var lines = (statement && statement.lines) || [];
    var rows = [];
    var used = {};
    [
      { id: "cfo", label: "Operating cash flow", keys: ["cfo", "net_cash_from_operating_activities"], children: [["ni", "Net income", ["ni", "net_income"]], ["da", "Depreciation and amortization", ["da", "depreciation_and_amortization"]], ["sbc", "Stock-based compensation", ["sbc", "stock_based_compensation"]], ["other_non_cash", "Other non-cash items", ["other_non_cash"]], ["chg_ar", "Change in accounts receivable", ["chg_ar", "change_in_accounts_receivable"]], ["chg_dr", "Change in deferred revenue", ["chg_dr", "change_in_deferred_revenue"]], ["chg_ap", "Change in accounts payable", ["chg_ap", "change_in_accounts_payable"]], ["chg_pre", "Change in prepaids", ["chg_pre", "chg_prepaids", "change_in_prepaids"]], ["chg_dc", "Change in deferred commissions", ["chg_dc", "chg_deferred_commissions", "change_in_deferred_commissions"]], ["chg_other_liab", "Change in other liabilities", ["chg_other_liab", "change_in_other_liabilities"]], ["unclassified", "Unclassified", ["unclassified"]]] },
      { id: "cfi", label: "Investing cash flow", keys: ["cfi", "net_cash_from_investing_activities"], children: [["capex", "Capital expenditures", ["capex", "capital_expenditures"]], ["chg_other_assets", "Change in other assets", ["chg_other_assets", "change_in_other_assets"]]] },
      { id: "cff", label: "Financing cash flow", keys: ["cff", "net_cash_from_financing_activities"], children: [["debt_financing", "Debt issuance and repayment", ["debt_issuance_repayment", "debt_financing", "debt"]], ["equity_issuance", "Equity issuance", ["equity_issuance"]]] },
    ].forEach(function (section) { buildSection(rows, lines, win, "cfs", section, used); });
    [narrateRow(useLine(packaged(lines, "beg_cash"), 0) || metricRow(win, "cfs", "beg_cash", "Beginning cash", 0, ["beg_cash", "beginning_cash"]), win), narrateRow(useLine(packaged(lines, "net_change"), 0) || metricRow(win, "cfs", "net_change", "Net change in cash", 0, ["net_change", "net_change_in_cash"]), win), narrateRow(useLine(packaged(lines, "ending_cash"), 0) || metricRow(win, "cfs", "ending_cash", "Ending cash", 0, ["end_cash", "ending_cash"]), win)].forEach(function (row) {
      if (!row) return;
      claimKeys(used, row.id === "beg_cash" ? ["beg_cash", "beginning_cash"] : row.id === "net_change" ? ["net_change", "net_change_in_cash"] : ["ending_cash", "end_cash"]);
      rows.push(row);
    });
    appendUnmappedLines(rows, win, "cfs", used, { cash_check: 1, balance_sheet_cash: 1, net_change_computed: 1, cash_tie_variance: 1, non_cash_total: 1, working_capital_total: 1 });
    return rows;
  }

  function buildBalance(item, statement) {
    var win = windowFor(item);
    var lines = (statement && statement.lines) || [];
    var rows = [];
    var used = {};
    [
      { id: "total_assets", label: "Total assets", keys: ["total_assets"], children: [["cash", "Cash", ["cash"]], ["ar", "Accounts receivable", ["ar", "accounts_receivable"]], ["prepaids", "Prepaids and other current", ["prepaids", "prepaids_and_other_current", "prepaids_and_other_current_assets", "prepaid_expenses", "prepaid_and_other_current_assets"]], ["other_current", "Other current assets", ["other_current", "other_current_assets"]], ["deferred_commissions_current", "Deferred commissions, current", ["deferred_commissions_current"]], ["deferred_commissions_noncurrent", "Deferred commissions, noncurrent", ["deferred_commissions_noncurrent"]], ["ppe", "Property and equipment, net", ["ppe", "ppe_net", "property_and_equipment_net", "property_plant_equipment_net", "property_plant_and_equipment_net", "property_plant_net", "fixed_assets"]], ["other_assets", "Other assets", ["other_assets"]], ["unmapped", "Unmapped", ["unmapped"]]] },
      { id: "total_liabilities", label: "Total liabilities", keys: ["total_liabilities", "total_liab"], children: [["ap", "Accounts payable", ["ap", "accounts_payable"]], ["deferred_rev", "Deferred revenue", ["deferred_rev", "deferred_revenue", "dr"]], ["debt", "Debt", ["debt", "total_debt", "debt_balance", "notes_payable"]], ["other_liab", "Other liabilities", ["other_liabilities", "other_liab"]]] },
      { id: "equity", label: "Total equity", keys: ["equity"], children: [["paid_in_capital", "Paid-in capital", ["paid_in_capital"]], ["apic_sbc", "APIC, stock compensation", ["apic_sbc", "apic_stock_compensation"]], ["retained_earnings", "Retained earnings", ["retained_earnings"]], ["current_period_net_income", "Net income, current period", ["current_period_net_income"]]] },
    ].forEach(function (section) { buildSection(rows, lines, win, "bs", section, used); });
    var total = narrateRow(useLine(packaged(lines, "total_le"), 0) || metricRow(win, "bs", "total_le", "Total liabilities and equity", 0, ["total_le", "total_liabilities_and_equity"]), win);
    if (total) {
      claimKeys(used, ["total_le", "total_liabilities_and_equity"]);
      rows.push(total);
    }
    appendUnmappedLines(rows, win, "bs", used, { balance_check: 1 });
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
        ? "Management P&L. Same recognized dollars as the income statement. No allocations loaded. Revenue is subscription, recurring services, then implementation and onboarding. A revenue line opens only when more than one account sits in it."
        : "Revenue is subscription, recurring services, then implementation and onboarding. A revenue line opens only when more than one account sits in it. Other lines open into the departments and accounts in the file.";
      var legacyNote = viewPicked === "management"
        ? "Management P&L. Same recognized dollars as the income statement until a management layer is loaded. Open revenue and cost of revenue for their lines. General and administrative opens into G&A and Support. Travel and entertainment and software tools open into the pieces behind the line."
        : "Open revenue for subscription, recurring services, and implementation. Open cost of revenue for the teams and cost lines. General and administrative opens into G&A and Support. Compensation opens into the pay elements. Travel and entertainment and software tools open into the departments or categories in that line, and the commentary is written from those pieces.";
      var note = reportingTrees(windowFor(item)) ? rollupNote : legacyNote;
      if (!built.length && income && income.accounts_note) note = income.accounts_note;
      return { statement: income, rows: built, note: note };
    }
    if (viewPicked === "cash_flow") {
      var cash = statementOf(item, "cash_flow");
      return { statement: cash, rows: buildCash(item, cash), note: "Open operating, investing, and financing for every cash flow line in the file." };
    }
    if (viewPicked === "balance_sheet") {
      var balance = statementOf(item, "balance_sheet");
      return { statement: balance, rows: buildBalance(item, balance), note: "Open each total for every balance sheet line in the file." };
    }
    var statement = statementOf(item, viewPicked);
    return { statement: statement, rows: ((statement && statement.lines) || []).map(function (row) { return copyRow(row, 0); }), note: "" };
  }

  function gtmDiscussion() {
    if (typeof global.boardGtmNarrative !== "function" || typeof global.boardGtmSummary !== "function") return "";
    try {
      var summary = global.boardGtmSummary(windowFor(comparison()));
      if (summary) summary.lostCustomers = storedLostCustomers(windowFor(comparison()));
      return global.boardGtmNarrative(summary) || "";
    } catch (err) {
      return "";
    }
  }

  function businessHtml() {
    var sections = [
      ["ARR and customers", "arr"],
      ["Margin and spending", "revenue"],
      ["Cash", "cash"],
      ["Go to market", "gtm"],
      ["Workforce", "headcount"],
      ["Takeaways", "risks"],
    ];
    if (typeof global.boardDataCommentary !== "function") return "";
    var html = sections
      .map(function (pair) {
        var text = pair[1] === "gtm"
          ? gtmDiscussion()
          : (typeof global.boardDiscussionNarrative === "function"
            ? (global.boardDiscussionNarrative(pair[1], windowFor(comparison())) || "")
            : (global.boardDataCommentary(pair[1]) || ""));
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

  function reportRole(row) {
    if (row.role === "plug") return "plug";
    if ((row.depth || 0) > 0) return "child";
    var id = String(row.id || "");
    if ({ net_income: 1, op_income: 1, total_le: 1, total_assets: 1, total_liabilities: 1, equity: 1, ending_cash: 1 }[id]) return "total";
    if ({ gross_profit: 1, total_opex: 1, ebitda: 1, pretax: 1, net_change: 1, beg_cash: 1, cfo: 1, cfi: 1, cff: 1 }[id]) return "subtotal";
    return "statement";
  }

  function centsTitle(value) {
    if (value == null || value === "") return "";
    var amount = Number(value);
    if (!isFinite(amount)) return "";
    var sign = amount < 0 ? "−" : "";
    return sign + Math.abs(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function varianceTitle(row) {
    var exact = centsTitle(row.variance);
    if (row.current == null || row.comparison_amount == null || row.variance == null) return exact;
    var gap = Math.round(Number(row.current)) - Math.round(Number(row.comparison_amount)) - Math.round(Number(row.variance));
    return gap ? exact + ". Rounded separately from the exact amounts" : exact;
  }

  function expandOnly(rows) {
    var hidden = null;
    return rows.filter(function (row) {
      var depth = row.depth || 0;
      if (hidden != null && depth > hidden) return false;
      hidden = null;
      if (row.expandable && !opened[row.key]) hidden = depth;
      return true;
    });
  }

  function rowText(row) {
    var edited = mergedEdits()[row.key];
    if (edited) return edited;
    return row.commentary || "";
  }

  function reportMatches(row, reviews) {
    var query = gridQuery.trim().toLowerCase();
    if (query && String(row.label || "").toLowerCase().indexOf(query) < 0) return false;
    var text = rowText(row);
    var missing = uncitedDrivers(text, row.drivers || []);
    if (gridFilter === "needs") return !!(row.review_required && !reviews[row.key]);
    if (gridFilter === "edited") return !!mergedEdits()[row.key];
    if (gridFilter === "stale") return !!row.stale;
    if (gridFilter === "explain") return !!(row.review_required && (!String(text).trim() || missing.length));
    return true;
  }

  function sourceButton(row, title) {
    if (!global.SMPL_REPORTING_ENGINE || !global.CLOSE_MONTH) return "";
    var grain = row.accountNumber ? "account" : (row.lineKey || "");
    if (!row.accountNumber && row.role !== "revenue_class") return "";
    if (!grain) return "";
    return '<button type="button" class="quiet source-link" data-source="1" data-period="' + esc(global.CLOSE_MONTH) + '" data-grain="' + esc(grain) + '" data-account="' + esc(row.accountNumber || "") + '" data-name="' + esc(row.accountName || "") + '" data-title="' + esc(title || "") + '">Source</button>';
  }

  function citeHtml(text, row) {
    var html = esc(text);
    var amounts = [];
    if (row.variance != null) amounts.push(Math.abs(Math.round(Number(row.variance))));
    (row.drivers || []).forEach(function (driver) {
      if (driver && driver.variance != null) amounts.push(Math.abs(Math.round(Number(driver.variance))));
    });
    var seen = {};
    amounts.sort(function (a, b) { return String(b).length - String(a).length; });
    amounts.forEach(function (amount) {
      if (!amount || seen[amount]) return;
      seen[amount] = true;
      var token = Number(amount).toLocaleString("en-US");
      html = html.split(token).join('<span class="cite" data-cite="' + amount + '" data-testid="cited-amount">' + token + "</span>");
    });
    return html;
  }

  function reportTextTies(text, row) {
    if (!row || row.variance == null || !String(text || "").trim()) return false;
    if (uncitedDrivers(text, row.drivers || []).length) return false;
    var shown = Math.abs(Math.round(Number(row.variance)));
    if (shown && String(text).indexOf(shown.toLocaleString("en-US")) < 0) return false;
    return true;
  }

  function liveTie(row, text) {
    var missing = uncitedDrivers(text, row.drivers || []);
    if (missing.length) return "Missing " + sentenceLabel(missing[0].label, false);
    if (row.current == null || row.comparison_amount == null || row.variance == null) return "Needs explanation";
    return "Ties: " + signedWhole(row.current) + " − " + signedWhole(row.comparison_amount) + " = " + signedWhole(row.variance) + " ✓";
  }

  function shortWhen(stamp) {
    var date = new Date(stamp);
    var names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return names[date.getMonth()] + " " + date.getDate();
  }

  var ROLLUP_SECTIONS = { revenue: 1, cogs: 1, sm: 1, rd: 1, ga: 1, unmapped: 1, ebitda: 1, da: 1, interest: 1, pretax: 1, tax: 1 };

  function draftSectionId(row) {
    if (!row) return "";
    if (!(row.depth || 0) && ROLLUP_SECTIONS[row.id]) return row.id;
    if ((row.depth || 0) === 1 && row.signLine && ROLLUP_SECTIONS[row.signLine]) return row.signLine;
    return "";
  }

  function groupLabels(allRows, sectionId) {
    var labels = [];
    var index;
    for (index = 0; index < allRows.length; index += 1) {
      var row = allRows[index];
      if ((row.depth || 0) !== 0 || row.id !== sectionId) continue;
      var child;
      for (child = index + 1; child < allRows.length; child += 1) {
        if ((allRows[child].depth || 0) === 0) break;
        if ((allRows[child].depth || 0) === 1 && allRows[child].label) labels.push(allRows[child].label);
      }
      break;
    }
    if (!labels.length && SUM_LINES[sectionId]) {
      var byId = {};
      allRows.forEach(function (row) {
        if ((row.depth || 0) === 0 && !byId[row.id]) byId[row.id] = row;
      });
      SUM_LINES[sectionId].forEach(function (pair) {
        var component = byId[pair[0]];
        if (component && component.label) labels.push(component.label);
      });
    }
    labels.sort(function (left, right) { return String(right).length - String(left).length; });
    return labels;
  }

  function separateGroups(paragraph, labels) {
    var text = String(paragraph || "").replace(/([^.!?\n])[ \t]*\n+[ \t]*/g, "$1 ");
    (labels || []).forEach(function (label) {
      var name = String(label || "");
      if (!name) return;
      var escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      text = text.replace(new RegExp("([.!?])[ \\t]+(" + escaped + ")(?![\\w])", "g"), "$1\n$2");
    });
    return text;
  }

  function sectionPayload(allRows, win, sectionId) {
    if (!win) return null;
    var parent = null;
    var lines = [];
    var index;
    for (index = 0; index < allRows.length; index += 1) {
      var row = allRows[index];
      if ((row.depth || 0) !== 0 || row.id !== sectionId) continue;
      parent = row;
      var childIndex;
      for (childIndex = index + 1; childIndex < allRows.length; childIndex += 1) {
        var child = allRows[childIndex];
        if ((child.depth || 0) === 0) break;
        if ((child.depth || 0) !== 1) continue;
        lines.push({
          label: child.label,
          current: child.current,
          comparison_amount: child.comparison_amount,
          variance: child.variance,
          facts: (child.facts || []).map(function (fact) {
            return {
              label: fact.label || "",
              current: fact.current == null ? null : fact.current,
              base: fact.base == null ? null : fact.base,
              amount: fact.amount == null ? null : fact.amount,
              heads: fact.heads == null ? null : fact.heads,
              paid: fact.paid == null ? null : fact.paid,
              quota: fact.quota == null ? null : fact.quota,
            };
          }),
          drivers: (child.drivers || []).map(function (driver) {
            return { label: driver.label || "", variance: driver.variance };
          }),
        });
      }
      break;
    }
    if (parent && !lines.length && SUM_LINES[sectionId]) {
      var components = {};
      allRows.forEach(function (row) {
        if ((row.depth || 0) === 0 && !components[row.id]) components[row.id] = row;
      });
      SUM_LINES[sectionId].forEach(function (pair) {
        var component = components[pair[0]];
        if (!component || component.variance == null) return;
        lines.push({
          label: component.label,
          current: component.current,
          comparison_amount: component.comparison_amount,
          variance: component.variance,
          contribution: pair[1] * Number(component.variance),
          facts: [],
          drivers: [],
        });
      });
    }
    if (!parent || !lines.length) return null;
    return {
      comparison: periodHeading(win),
      comparison_kind: win.id,
      section_id: sectionId,
      period: (win.src && win.src.close) || "",
      organization_id: String(global.SMPL_ORG_ID || ""),
      materiality: 10000,
      parent: {
        label: parent.label,
        current: parent.current,
        comparison_amount: parent.comparison_amount,
        variance: parent.variance,
      },
      lines: lines,
    };
  }

  function revenueHoldId() {
    return "sfi-revenue-analysis:" + String(global.SMPL_ORG_ID || "") + ":" + String(global.CLOSE_MONTH || "");
  }

  function loadRevenueHeld() {
    var id = revenueHoldId();
    if (revenueHeldFor === id) return;
    revenueHeldFor = id;
    revenueHeld = {};
    revenueFetchSerial = {};
    try {
      if (typeof sessionStorage === "undefined") return;
      var raw = sessionStorage.getItem(id);
      var parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === "object") revenueHeld = parsed;
    } catch (err) {
      revenueHeld = {};
    }
  }

  function saveRevenueHeld() {
    try {
      if (typeof sessionStorage === "undefined") return;
      sessionStorage.setItem(revenueHoldId(), JSON.stringify(revenueHeld));
    } catch (err) {
      return;
    }
  }

  function rememberRevenue(key, stored) {
    revenueHeld[key] = stored;
    saveRevenueHeld();
  }

  function shownAnalysis(row) {
    if (!row || (row.depth || 0) || !ROLLUP_SECTIONS[row.id]) return "";
    var slot = sectionRollup[row.id];
    if (slot && slot.status === "ai" && slot.paragraph) return slot.paragraph;
    return "";
  }

  function requestSectionRollup(allRows, win, host, sectionId, again) {
    loadRevenueHeld();
    var payload = sectionPayload(allRows, win, sectionId);
    if (!payload) {
      sectionRollup[sectionId] = { key: "", status: "", paragraph: "", evidence: null, reason: "" };
      return;
    }
    var key = sectionId + "\n" + JSON.stringify(payload);
    var current = sectionRollup[sectionId];
    if (!again && current && current.key === key && current.status === "loading") return;
    var held = revenueHeld[key];
    if (!again && held && (held.status === "ai" || held.status === "fallback" || held.status === "cleared")) {
      sectionRollup[sectionId] = {
        key: key,
        status: held.status,
        paragraph: held.paragraph || "",
        evidence: null,
        reason: held.reason || "",
      };
      return;
    }
    sectionRollup[sectionId] = {
      key: key,
      status: "loading",
      paragraph: again && current && current.key === key ? (current.paragraph || "") : "",
      evidence: again && current ? current.evidence : null,
      reason: "",
    };
    if (again) render(host);
    var serial = (revenueFetchSerial[key] || 0) + 1;
    revenueFetchSerial[key] = serial;
    var base = (global.SMPL_API_BASE || "/api/v1").replace(/\/$/, "");
    fetch(base + "/commentary/revenue-rollup", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) throw new Error("rollup_failed");
          return body;
        });
      })
      .then(function (body) {
        if (revenueFetchSerial[key] !== serial) return;
        var stored = {
          status: body.status === "ai" ? "ai" : "fallback",
          paragraph: body.paragraph || "",
          reason: body.reason || "",
        };
        rememberRevenue(key, stored);
        var slot = sectionRollup[sectionId];
        if (!slot || slot.key !== key) return;
        sectionRollup[sectionId] = {
          key: key,
          status: stored.status,
          paragraph: stored.paragraph,
          evidence: body.evidence || null,
          reason: stored.reason,
        };
        render(host);
      })
      .catch(function () {
        if (revenueFetchSerial[key] !== serial) return;
        var stored = {
          status: "fallback",
          paragraph: "",
          reason: "The analysis is unavailable. Showing the calculated sentence.",
        };
        rememberRevenue(key, stored);
        var slot = sectionRollup[sectionId];
        if (!slot || slot.key !== key) return;
        sectionRollup[sectionId] = {
          key: key,
          status: stored.status,
          paragraph: "",
          evidence: null,
          reason: stored.reason,
        };
        render(host);
      });
  }

  function revenueRollupHtml(row, text, allRows) {
    if (!row || (row.depth || 0) || !ROLLUP_SECTIONS[row.id]) return "";
    var slot = sectionRollup[row.id] || { status: "" };
    if (slot.status === "cleared" || !slot.status) return "";
    var mark = row.id === "revenue" ? "revenue-analysis" : "section-analysis";
    var grouped = separateGroups(slot.paragraph || "", groupLabels(allRows || [], row.id));
    var calculated = '<div class="read" data-testid="commentary-text">' + (text ? citeHtml(text, row) : "") + "</div>";
    if (slot.status === "ai" && grouped) {
      return '<div class="read" data-testid="' + mark + '">' + esc(grouped) + "</div>";
    }
    if (slot.status === "fallback") {
      var note = slot.reason || "Analysis unavailable.";
      return '<p class="fallback" data-testid="' + mark + '">' + esc(note) + "</p>" + calculated;
    }
    var kept = grouped
      ? '<div class="read" data-testid="' + mark + '">' + esc(grouped) + "</div>"
      : calculated;
    return '<p class="drafting" data-testid="commentary-drafting" aria-live="polite"><span class="spin" aria-hidden="true"></span> Updating commentary</p>' + kept;
  }

  function renderReport(host) {
    var book = package();
    if (!book) {
      host.innerHTML = '<div class="rpt-empty">The commentary grid loads with the books for this close.</div>';
      return;
    }
    var item = comparison();
    if (!item) {
      host.innerHTML = '<div class="rpt-empty">No comparison is loaded for this close yet.</div>';
      return;
    }
    var reviews = mergedReviews();
    var win = windowFor(item);
    var source = item.available === false ? { rows: [], note: item.note || "This comparison is not available.", statement: null } : gridSource(item);
    var allRows = source.rows || [];
    Object.keys(ROLLUP_SECTIONS).forEach(function (sectionId) {
      requestSectionRollup(allRows, win, host, sectionId);
    });
    var narrowed = gridFilter !== "all" || gridQuery.trim();
    var rows = narrowed ? allRows.filter(function (row) { return reportMatches(row, reviews); }) : expandOnly(allRows);
    var required = 0;
    var done = 0;
    allRows.forEach(function (row) {
      if (!row.review_required || (row.depth || 0) > 0) return;
      required += 1;
      if (reviews[row.key] && reportTextTies(rowText(row), row)) done += 1;
    });
    var deepest = 0;
    rows.forEach(function (row) { if ((row.depth || 0) > deepest) deepest = row.depth || 0; });
    var lineWidth = Math.min(360, 220 + deepest * 20);
    function viewCount(id) {
      var previous = viewPicked;
      viewPicked = id;
      var counted = gridSource(item);
      viewPicked = previous;
      var count = 0;
      (counted.rows || []).forEach(function (row) {
        if (row.review_required && !reviews[row.key] && !(row.depth || 0)) count += 1;
      });
      return count;
    }
    function filterCount(id) {
      var previous = gridFilter;
      gridFilter = id;
      var count = allRows.filter(function (row) { return reportMatches(row, reviews); }).length;
      gridFilter = previous;
      return count;
    }
    var compButtons = (book.comparisons || []).map(function (comp) {
      var on = comp.id === item.id;
      var disabled = comp.available === false;
      var why = comp.id === "forecast" ? "No forecast version loaded" : "No data for this comparison";
      return '<button type="button" data-comp="' + esc(comp.id) + '"' + (disabled ? ' disabled title="' + esc(why) + '"' : "") + ' class="' + (on ? "on" : "") + '">' + esc(COMPACT[comp.id] || comp.label) + "</button>";
    }).join("");
    var viewButtons = VIEWS.map(function (pair) {
      var count = item.available === false ? 0 : viewCount(pair[0]);
      return '<button type="button" data-view="' + esc(pair[0]) + '" class="' + (pair[0] === viewPicked ? "on" : "") + '">' + esc(pair[1]) + (count ? '<span class="badge">' + count + "</span>" : "") + "</button>";
    }).join("");
    var filters = [["all", "All lines"], ["needs", "Needs review"], ["edited", "Edited"], ["stale", "Stale"], ["explain", "Needs explanation"]].map(function (pair) {
      return '<button type="button" data-filter="' + pair[0] + '" class="chip' + (gridFilter === pair[0] ? " on" : "") + '">' + pair[1] + '<span class="badge">' + filterCount(pair[0]) + "</span></button>";
    }).join("");
    var body = rows.map(function (row) {
      var role = reportRole(row);
      var text = editingKey === row.key && editBuffer != null ? editBuffer : rowText(row);
      var edited = !!mergedEdits()[row.key];
      var shown = mergedLabel(row.label);
      var missing = uncitedDrivers(rowText(row), row.drivers || []);
      var ties = reportTextTies(rowText(row), row);
      var open = !!opened[row.key];
      var caret = row.expandable
        ? '<button type="button" class="icon caret" data-testid="caret" data-toggle="' + esc(row.key) + '" aria-expanded="' + (open ? "true" : "false") + '" aria-label="' + esc((open ? "Collapse " : "Expand ") + shown.text) + '">' + (open ? "▾" : "▸") + "</button>"
        : '<span class="caret" data-testid="caret"></span>';
      var favor = favorText(row);
      var favorHtml = favor ? '<span aria-label="' + (favor.indexOf("Unfav") >= 0 ? "Unfavorable" : "Favorable") + '">' + favor + "</span>" : "—";
      var pct = percentSigned(row) || "—";
      var status = edited ? "Edited" : (String(rowText(row)).trim() ? "Drafted" : "Needs explanation");
      var tieNote = !String(rowText(row)).trim() || row.variance == null ? "" : (missing.length ? "Doesn't tie: " + missing.length + (missing.length === 1 ? " driver not cited" : " drivers not cited") : (ties ? "Tied" : ""));
      var tiedCell = tieNote === "Tied"
        ? '<span class="tied ok" title="The commentary amount ties to this line">✓</span>'
        : (tieNote ? '<span class="tied bad" title="' + esc(tieNote) + '">!</span>' : "");
      var foot = '<div class="foot" data-testid="commentary-footer"><span>' + status + "</span>";
      var commentary;
      if (editingKey === row.key) {
        commentary = '<textarea data-testid="commentary-editor" data-edit="' + esc(row.key) + '" rows="2">' + esc(text) + "</textarea>" +
          '<div class="live">' + esc(liveTie(row, text)) + "</div>" +
          (leavePrompt === row.key ? '<div class="leave">Save this edit or discard it? <button type="button" class="primary" data-save-edit="' + esc(row.key) + '">Save</button> <button type="button" class="quiet" data-discard-edit="1">Discard</button></div>' : "") +
          '<div class="edit-actions"><button type="button" class="primary" data-save-edit="' + esc(row.key) + '">Save</button><button type="button" class="quiet" data-cancel-edit="1">Cancel</button><button type="button" class="quiet" data-revert-edit="' + esc(row.key) + '">Revert to draft</button></div>';
      } else {
        var rollup = revenueRollupHtml(row, text, allRows);
        var draftId = draftSectionId(row);
        var canDraft = draftId && groupLabels(allRows, draftId).length;
        var clamped = !rollup && !expandedText[row.key] && String(text).length > 280;
        commentary = (rollup || '<div class="read' + (clamped ? " clamp" : "") + '" data-testid="commentary-text">' + (text ? citeHtml(text, row) : "") + "</div>" +
          (clamped ? '<button type="button" class="quiet" data-more="' + esc(row.key) + '">Show more</button>' : "")) +
          foot + '<span class="cell-actions" data-testid="cell-actions"><button type="button" class="quiet" data-start-edit="' + esc(row.key) + '">Edit</button>' +
          (canDraft
            ? (sectionRollup[draftId] && sectionRollup[draftId].status === "loading"
              ? '<button type="button" class="quiet" disabled data-revenue-draft="' + esc(draftId) + '" title="Updating commentary">Updating</button>'
              : '<button type="button" class="quiet" data-revenue-draft="' + esc(draftId) + '" title="Draft this analysis again">AI draft</button>')
            : '<button type="button" class="quiet" disabled title="No AI draft is loaded">AI draft</button>') +
          '<button type="button" class="quiet" disabled title="No history is loaded">History</button></span></div>';
      }
      var reviewed = !!reviews[row.key];
      var changed = reviewed && editedAt[row.key] && reviewedAt[row.key] && editedAt[row.key] > reviewedAt[row.key];
      var blocked = "";
      if (editingKey === row.key) blocked = "Save first";
      else if (!ties && row.variance != null && String(rowText(row)).trim()) blocked = "Fix the tie first";
      else if (row.review_required && !String(rowText(row)).trim()) blocked = "Needs explanation";
      var review = "";
      if (!item.custom) {
        var caption = "";
        if (!row.review_required && !reviewed) {
          review = '<span class="not-required">Not required</span><button type="button" class="quiet anyway" data-review="' + esc(row.key) + '">Review anyway</button>';
        } else if (blocked && !reviewed) {
          review = '<button type="button" class="secondary" disabled title="' + esc(blocked) + '">Review</button><div class="caption">' + esc(blocked) + "</div>";
        } else if (changed) {
          caption = reviewedAt[row.key] ? "FP&A · " + shortWhen(reviewedAt[row.key]) : "FP&A";
          review = '<button type="button" class="secondary" data-review="' + esc(row.key) + '">⚠ Re-review</button><div class="caption struck">' + esc(caption) + "</div>";
        } else if (reviewed) {
          caption = reviewedAt[row.key] ? "FP&A · " + shortWhen(reviewedAt[row.key]) : "FP&A";
          review = '<button type="button" class="primary" data-review-menu="' + esc(row.key) + '">✓ Reviewed</button>' +
            (reviewMenu === row.key ? '<div class="menu"><button type="button" data-unmark="' + esc(row.key) + '">Unmark</button><button type="button" disabled title="No history is loaded">History</button></div>' : "") +
            '<div class="caption">' + esc(caption) + "</div>";
        } else {
          review = '<button type="button" class="secondary" data-review="' + esc(row.key) + '">Review</button>';
        }
      }
      var gap = row.gapAfter ? '<div class="section-gap"></div>' : "";
      return '<div class="rpt-row ' + role + (activeRow === row.key ? " active" : "") + '" data-testid="grid-row" data-row="' + esc(row.key) + '" data-variance="' + Math.round(Number(row.variance) || 0) + '" style="--depth:' + (row.depth || 0) + '" tabindex="-1">' +
        '<div class="line">' + caret + '<span class="name' + (row.unassigned ? " quiet-name" : "") + '" data-testid="line-name" title="' + esc(shown.title || shown.text) + '">' + esc(shown.text) + "</span>" + (role === "plug" ? '<span class="chip reason">Unmapped</span>' : "") + "</div>" +
        '<div class="num" data-testid="amount-current" title="' + esc(centsTitle(row.current)) + '">' + esc(wholeAmount(row.current)) + "</div>" +
        '<div class="num" data-testid="amount-comparison" title="' + esc(centsTitle(row.comparison_amount)) + '">' + esc(wholeAmount(row.comparison_amount)) + "</div>" +
        '<div class="num variance" data-testid="amount-variance" title="' + esc(varianceTitle(row)) + '">' + esc(signedWhole(row.variance)) + "</div>" +
        '<div class="num" data-testid="amount-percent">' + esc(pct) + "</div>" +
        '<div class="mark" data-testid="amount-favor">' + favorHtml + "</div>" +
        '<div class="talk" data-testid="commentary-cell">' + commentary + "</div>" +
        '<div class="mark tied-cell" data-testid="tied">' + tiedCell + "</div>" +
        '<div class="source">' + sourceButton(row, shown.text) + "</div>" +
        '<div class="review" data-testid="review-control">' + review + "</div></div>" + gap;
    }).join("");
    var left = Math.max(0, required - done);
    var approveDisabled = done !== required;
    var pctDone = required ? Math.round((done / required) * 100) : 0;
    var heading = periodHeading(win);
    var heads = columnHeads(win);
    host.innerHTML =
      '<style>' +
      ".rpt{max-width:1760px;color:var(--text);font-family:var(--font);font-size:13px;font-weight:500}" +
      ".rpt-empty{padding:14px 16px;color:var(--text3)}" +
      ".rpt button{font:500 13px/1 var(--font);cursor:pointer;border-radius:var(--radius,6px)}" +
      ".rpt button:focus-visible{outline:2px solid var(--teal);outline-offset:2px}" +
      ".rpt .primary{height:32px;padding:0 12px;background:var(--teal);color:var(--on-accent);border:1px solid var(--teal)}" +
      ".rpt .primary:disabled{opacity:.45;cursor:not-allowed}" +
      ".rpt .secondary{height:32px;padding:0 12px;background:var(--surface);color:var(--text);border:1px solid var(--border)}" +
      ".rpt .secondary:disabled{opacity:.45;cursor:not-allowed}" +
      ".rpt .quiet{height:32px;padding:0 8px;background:transparent;border:0;color:var(--text3)}" +
      ".rpt .quiet:hover{text-decoration:underline}" +
      ".rpt .icon{width:28px;height:28px;padding:0;background:transparent;border:0;color:var(--text)}" +
      ".rpt-title{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:12px}" +
      ".rpt h2{margin:0;font-size:20px;font-weight:650}" +
      ".rpt-title p{margin:4px 0 0;font-size:13px;font-weight:400;color:var(--text3)}" +
      ".rpt-actions{display:flex;gap:8px}" +
      ".rpt-context,.rpt-views,.rpt-tools{position:sticky;background:var(--bg);z-index:6}" +
      ".rpt-context{top:52px;display:flex;align-items:center;gap:16px;min-height:44px}" +
      ".rpt-views{top:96px;display:flex;align-items:center;gap:16px;border-bottom:1px solid var(--border)}" +
      ".rpt-tools{top:140px;display:flex;gap:8px;align-items:center;min-height:44px;flex-wrap:wrap}" +
      ".rpt-seg{display:inline-flex;height:32px}" +
      ".rpt-seg button{height:32px;border:1px solid var(--border);background:var(--surface);padding:0 10px;margin-left:-1px;border-radius:0}" +
      ".rpt-seg button:first-child{margin-left:0;border-radius:var(--radius,6px) 0 0 var(--radius,6px)}" +
      ".rpt-seg button:last-child{border-radius:0 var(--radius,6px) var(--radius,6px) 0}" +
      ".rpt-seg button.on{background:var(--teal);color:var(--on-accent);border-color:var(--teal);position:relative}" +
      ".rpt-seg button:disabled{opacity:.45;cursor:not-allowed}" +
      ".period{display:flex;align-items:center;gap:4px;font-size:14px;font-weight:500}" +
      ".rpt-tabs{display:flex;gap:16px}" +
      ".rpt-tabs button{height:36px;border:0;border-bottom:2px solid transparent;background:transparent;padding:0;color:var(--text3);border-radius:0}" +
      ".rpt-tabs button.on{color:var(--text);border-bottom-color:var(--teal)}" +
      ".badge{display:inline-flex;align-items:center;height:18px;margin-left:6px;padding:0 6px;border-radius:9px;background:var(--tint);color:var(--text2);font-size:11px;font-weight:500}" +
      ".progress{margin-left:auto;text-align:right;font-size:12px;font-weight:400;color:var(--text3)}" +
      ".bar{width:120px;height:4px;margin-top:4px;background:var(--border);border-radius:2px;margin-left:auto}" +
      ".bar span{display:block;height:4px;background:var(--teal)}" +
      ".chip{height:28px;border:1px solid var(--border);background:var(--surface);border-radius:999px;padding:0 10px}" +
      ".chip.on{background:var(--tint);border-color:var(--teal)}" +
      ".search{width:220px;height:28px;border:1px solid var(--border);border-radius:var(--radius,6px);padding:0 8px;font:400 13px/1 var(--font);background:var(--surface);color:var(--text)}" +
      ".about-pop{margin:0 0 8px;font-size:13px;font-weight:400;color:var(--text2);line-height:1.45}" +
      ".rpt-grid{--line:" + lineWidth + "px}" +
      ".rpt-head,.rpt-row{display:grid;grid-template-columns:var(--line) 118px 118px 104px 64px 92px minmax(360px,1.6fr) 56px 72px 120px;align-items:stretch}" +
      ".rpt-head{position:sticky;top:184px;z-index:5;background:var(--bg);font-size:12px;font-weight:500;color:var(--text3);border-bottom:1px solid var(--border)}" +
      ".rpt-head > div{padding:8px 10px;white-space:nowrap}" +
      ".rpt-row{border-bottom:1px solid var(--border)}" +
      ".rpt-row > div{padding:12px 16px;background:var(--bg)}" +
      ".rpt[data-density=compact] .rpt-row > div{padding-top:8px;padding-bottom:8px}" +
      ".num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:14px;font-weight:400;line-height:20px}" +
      ".rpt-head .num{text-align:right}" +
      ".mark{display:flex;align-items:flex-start;justify-content:center;font-size:12px;font-weight:500;white-space:nowrap}" +
      ".tied{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border:1px solid var(--border);border-radius:8px;font-size:16px;line-height:1}" +
      ".tied.ok{color:var(--teal);border-color:#9EC9C6}" +
      ".tied.bad{color:#9A3412}" +
      ".line{position:sticky;left:0;z-index:2;display:flex;align-items:flex-start;gap:4px}" +
      ".rpt-row > .line{padding-left:calc(16px + var(--depth) * 20px)}" +
      ".rpt-head .line{z-index:6}" +
      ".caret{flex:0 0 20px;width:20px;height:20px;line-height:20px}" +
      ".name{flex:1;min-width:0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:20px}" +
      ".rpt-row.statement .name{font-size:14px;font-weight:500}" +
      ".rpt-row.child .name,.rpt-row.child .num,.rpt-row.child .read{font-size:13px}" +
      ".rpt-row.child .line::before{content:'';position:absolute;left:calc(16px + (var(--depth) - 1) * 20px + 9px);top:0;bottom:0;width:1px;background:var(--border)}" +
      ".rpt-row.subtotal{margin-top:8px;border-top:1px solid var(--text)}" +
      ".rpt-row.subtotal > div{font-weight:600}" +
      ".rpt-row.subtotal .name{font-size:14px}" +
      ".rpt-row.total{position:relative;margin-top:16px}" +
      ".rpt-row.total::before{content:'';position:absolute;left:0;right:0;top:0;height:4px;z-index:3;pointer-events:none;background-image:linear-gradient(var(--text),var(--text)),linear-gradient(var(--text),var(--text));background-size:100% 1px,100% 1px;background-position:0 0,0 3px;background-repeat:no-repeat}" +
      ".rpt-row.total > div{font-weight:600;padding-top:12px}" +
      ".rpt-row.total .name,.rpt-row.total .num{font-size:15px}" +
      ".rpt-row.plug{border-top:1px dashed var(--border)}" +
      ".rpt-row.plug .name{font-style:italic}" +
      ".quiet-name{font-style:italic;color:var(--text3)}" +
      ".section-gap{height:16px}" +
      ".rpt-row > .talk{padding-left:24px}" +
      ".read{font-size:14px;font-weight:400;line-height:1.5;white-space:pre-wrap}" +
      ".rollup{margin:0 0 8px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}" +
      ".rollup .kicker{font-size:11px;font-weight:650;letter-spacing:.04em;text-transform:uppercase;color:var(--text3);margin:8px 0 2px}" +
      ".rollup .kicker:first-child{margin-top:0}" +
      ".rollup p,.rollup li{margin:0;font-size:14px;font-weight:400;line-height:1.5}" +
      ".rollup ul{margin:0;padding-left:18px}" +
      ".rollup .fallback{color:var(--text2)}" +
      ".drafting{display:flex;align-items:center;gap:8px;margin:0 0 8px;font-size:13px;font-weight:500;color:var(--text2)}" +
      ".spin{width:12px;height:12px;border:2px solid var(--border);border-top-color:var(--text);border-radius:50%;animation:commentary-spin .7s linear infinite}" +
      "@keyframes commentary-spin{to{transform:rotate(360deg)}}" +
      "@media (prefers-reduced-motion:reduce){.spin{animation:none}}" +
      ".read.clamp{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}" +
      ".source{font-size:12px;font-weight:500}" +
      ".source-link{font-size:12px;line-height:18px}" +
      ".cite{font-weight:500;font-variant-numeric:tabular-nums}" +
      ".foot{display:flex;justify-content:space-between;gap:8px;margin-top:6px;font-size:12px;font-weight:400;color:var(--text3)}" +
      ".cell-actions{opacity:0}" +
      ".rpt-row:hover .cell-actions,.rpt-row:focus-within .cell-actions{opacity:1}" +
      "@media (hover:none){.cell-actions{opacity:1}}" +
      ".review{text-align:center}" +
      ".caption{margin-top:4px;font-size:12px;font-weight:400;color:var(--text3)}" +
      ".struck{text-decoration:line-through}" +
      ".not-required{font-size:12px;font-weight:400;color:var(--text3)}" +
      ".anyway{display:none}" +
      ".rpt-row:hover .anyway,.rpt-row:focus-within .anyway{display:inline-flex}" +
      ".rpt-row:hover .not-required,.rpt-row:focus-within .not-required{display:none}" +
      ".menu{display:flex;flex-direction:column;gap:4px;margin-top:4px}" +
      "textarea{width:100%;border:1px solid var(--border);border-radius:var(--radius,6px);padding:6px;font:400 14px/1.5 var(--font);resize:none;background:var(--surface);color:var(--text)}" +
      ".live,.leave{margin-top:6px;font-size:12px;font-weight:400;color:var(--text3)}" +
      ".edit-actions{display:flex;gap:8px;margin-top:6px}" +
      ".rpt-row.cited > div{background:var(--tint)}" +
      ".chip.reason{height:18px;font-size:11px;margin-left:6px}" +
      "</style>" +
      '<div class="rpt" data-density="' + gridDensity + '" tabindex="0">' +
      '<div class="rpt-title"><div><h2>Variance commentary</h2><p>One paragraph per line · every amount ties to the line</p></div><div class="rpt-actions">' +
      '<button type="button" class="secondary" data-export="1">Export workbook</button>' +
      '<button type="button" class="primary" data-approve="1"' + (approveDisabled ? ' disabled title="Enabled once every required line is reviewed (' + left + ' left)"' : "") + ">Approve comparison</button></div></div>" +
      '<div class="rpt-context"><div class="rpt-seg">' + compButtons + '</div><div class="period">' +
      '<button type="button" class="icon" disabled title="The loaded close is this period" aria-label="Previous period">‹</button>' +
      "<span>" + esc(heading) + "</span>" +
      '<button type="button" class="icon" disabled title="The loaded close is this period" aria-label="Next period">›</button></div></div>' +
      '<div class="rpt-views"><div class="rpt-tabs">' + viewButtons + '</div><div class="progress"><div>' + done + " of " + required + ' required lines reviewed</div><div class="bar"><span style="width:' + pctDone + '%"></span></div></div></div>' +
      '<div class="rpt-tools">' + filters +
      '<input class="search" data-search="1" placeholder="Search lines" value="' + esc(gridQuery) + '" />' +
      '<button type="button" class="quiet" data-expand="1">Expand all</button>' +
      '<button type="button" class="quiet" data-collapse="1">Collapse all</button></div>' +
      '<div class="rpt-grid" data-testid="variance-grid"><div class="rpt-head">' +
      '<div class="line">Line</div><div class="num">' + esc(heads.current) + '</div><div class="num">' + esc(heads.base) + '</div><div class="num">$ Variance</div><div class="num">%</div><div class="mark">Fav/Unfav</div><div>Commentary</div><div class="mark">Tied</div><div class="source">Source</div><div>Review</div>' +
      "</div>" +
      (body || '<div class="rpt-empty">No lines in this view.</div>') +
      "</div></div>";
    function blockedLeave() {
      var field = host.querySelector("[data-edit]");
      if (!field || field.value === editBaseline) {
        leavePrompt = "";
        return false;
      }
      editBuffer = field.value;
      leavePrompt = editingKey;
      render(host);
      return true;
    }
    Array.prototype.forEach.call(host.querySelectorAll("[data-comp]"), function (button) {
      button.onclick = function () {
        if (button.disabled || blockedLeave()) return;
        picked = button.getAttribute("data-comp");
        editingKey = "";
        editBuffer = null;
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-view]"), function (button) {
      button.onclick = function () {
        if (blockedLeave()) return;
        viewPicked = button.getAttribute("data-view");
        editingKey = "";
        editBuffer = null;
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-filter]"), function (button) {
      button.onclick = function () {
        gridFilter = button.getAttribute("data-filter");
        render(host);
      };
    });
    var search = host.querySelector("[data-search]");
    if (search) {
      search.oninput = function () {
        gridQuery = search.value;
        var caret = search.selectionStart;
        render(host);
        var next = host.querySelector("[data-search]");
        if (next) {
          next.focus();
          if (caret != null) next.setSelectionRange(caret, caret);
        }
      };
    }
    var expand = host.querySelector("[data-expand]");
    if (expand) expand.onclick = function () {
      allRows.forEach(function (row) { if (row.expandable) opened[row.key] = true; });
      render(host);
    };
    var collapse = host.querySelector("[data-collapse]");
    if (collapse) collapse.onclick = function () { opened = {}; render(host); };
    Array.prototype.forEach.call(host.querySelectorAll("[data-toggle]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        var key = button.getAttribute("data-toggle");
        opened[key] = !opened[key];
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-more]"), function (button) {
      button.onclick = function () { expandedText[button.getAttribute("data-more")] = true; render(host); };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-row]"), function (rowEl) {
      rowEl.onclick = function (event) {
        if (event.target.closest("button, textarea, input")) return;
        if (blockedLeave()) return;
        activeRow = rowEl.getAttribute("data-row");
        render(host);
        var panel = host.querySelector(".rpt");
        if (panel) panel.focus();
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-cite]"), function (cite) {
      cite.onmouseenter = function () {
        var amount = cite.getAttribute("data-cite");
        Array.prototype.forEach.call(host.querySelectorAll("[data-variance]"), function (rowEl) {
          if (rowEl.getAttribute("data-variance") === amount) rowEl.classList.add("cited");
        });
      };
      cite.onmouseleave = function () {
        Array.prototype.forEach.call(host.querySelectorAll(".cited"), function (rowEl) { rowEl.classList.remove("cited"); });
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-source]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        if (!global.SMPLSourceTrace) return;
        global.SMPLSourceTrace.open({
          period: button.getAttribute("data-period"),
          grain: button.getAttribute("data-grain"),
          accountNumber: button.getAttribute("data-account") || "",
          accountName: button.getAttribute("data-name") || "",
          title: button.getAttribute("data-title") || "",
        });
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-start-edit]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        if (blockedLeave()) return;
        editingKey = button.getAttribute("data-start-edit");
        var row = allRows.filter(function (itemRow) { return itemRow.key === editingKey; })[0];
        var analysis = shownAnalysis(row);
        editingAnalysis = !!analysis;
        editBaseline = analysis || (row ? rowText(row) : "");
        editBuffer = editBaseline;
        leavePrompt = "";
        render(host);
        var field = host.querySelector("[data-edit]");
        if (field) field.focus();
      };
    });
    var cancel = host.querySelector("[data-cancel-edit]");
    if (cancel) cancel.onclick = function () { editingKey = ""; editingAnalysis = false; editBuffer = null; leavePrompt = ""; render(host); };
    var discard = host.querySelector("[data-discard-edit]");
    if (discard) discard.onclick = function () { editingKey = ""; editingAnalysis = false; editBuffer = null; leavePrompt = ""; render(host); };
    Array.prototype.forEach.call(host.querySelectorAll("[data-revenue-draft]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        if (blockedLeave()) return;
        requestSectionRollup(allRows, win, host, button.getAttribute("data-revenue-draft"), true);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-save-edit]"), function (button) {
      button.onclick = function () { saveReportEdit(host, button.getAttribute("data-save-edit")); };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-revert-edit]"), function (button) {
      button.onclick = function () {
        var key = button.getAttribute("data-revert-edit");
        var row = allRows.filter(function (itemRow) { return itemRow.key === key; })[0];
        editBuffer = row ? (row.commentary || "") : "";
        var field = host.querySelector("[data-edit]");
        if (field) field.value = editBuffer;
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-edit]"), function (field) {
      field.oninput = function () {
        editBuffer = field.value;
        var row = allRows.filter(function (itemRow) { return itemRow.key === field.getAttribute("data-edit"); })[0];
        var live = host.querySelector(".live");
        if (editingAnalysis && live) live.textContent = "This wording stays until you draft again.";
        else if (row && live) live.textContent = liveTie(row, field.value);
        var lines = String(field.value).split("\n").length;
        field.rows = Math.max(2, Math.min(12, lines));
      };
      field.onkeydown = function (event) {
        if (event.key === "Escape") {
          editingKey = "";
          editingAnalysis = false;
          editBuffer = null;
          leavePrompt = "";
          render(host);
        }
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) saveReportEdit(host, field.getAttribute("data-edit"));
      };
    });
    function markReviewed(key, on) {
      draft.reviews[key] = on;
      if (on) reviewedAt[key] = Date.now();
      persist();
      render(host);
    }
    Array.prototype.forEach.call(host.querySelectorAll("[data-review]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        markReviewed(button.getAttribute("data-review"), true);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-review-menu]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        var key = button.getAttribute("data-review-menu");
        reviewMenu = reviewMenu === key ? "" : key;
        render(host);
      };
    });
    Array.prototype.forEach.call(host.querySelectorAll("[data-unmark]"), function (button) {
      button.onclick = function (event) {
        event.stopPropagation();
        reviewMenu = "";
        markReviewed(button.getAttribute("data-unmark"), false);
      };
    });
    var exportButton = host.querySelector("[data-export]");
    if (exportButton) exportButton.onclick = download;
    var approve = host.querySelector("[data-approve]");
    if (approve) approve.onclick = function () { if (!approve.disabled) persist(); };
    var panel = host.querySelector(".rpt");
    if (panel) {
      panel.onkeydown = function (event) {
        if (event.target.matches("textarea, input")) return;
        var keys = rows.map(function (row) { return row.key; });
        var index = keys.indexOf(activeRow);
        if (event.key === "ArrowDown" || event.key === "j" || event.key === "J") index = Math.min(keys.length - 1, index + 1);
        else if (event.key === "ArrowUp" || event.key === "k" || event.key === "K") index = Math.max(0, index < 0 ? 0 : index - 1);
        else if ((event.key === "ArrowRight" || event.key === "ArrowLeft") && activeRow) {
          var current = rows.filter(function (row) { return row.key === activeRow; })[0];
          if (current && current.expandable) opened[activeRow] = event.key === "ArrowRight";
          render(host);
          return;
        } else if ((event.key === "e" || event.key === "E") && activeRow && editingKey !== activeRow) {
          editingKey = activeRow;
          var row = allRows.filter(function (itemRow) { return itemRow.key === activeRow; })[0];
          var analysis = shownAnalysis(row);
          editingAnalysis = !!analysis;
          editBaseline = analysis || (row ? rowText(row) : "");
          editBuffer = editBaseline;
          render(host);
          var field = host.querySelector("[data-edit]");
          if (field) field.focus();
          return;
        } else if ((event.key === "r" || event.key === "R") && activeRow) {
          var target = allRows.filter(function (itemRow) { return itemRow.key === activeRow; })[0];
          if (target && reportTextTies(rowText(target), target)) markReviewed(activeRow, !reviews[activeRow]);
          return;
        } else return;
        if (keys[index]) activeRow = keys[index];
        event.preventDefault();
        render(host);
        var nextRow = host.querySelector('[data-row="' + activeRow + '"]');
        if (nextRow) nextRow.focus();
      };
    }
  }

  function saveReportEdit(host, key) {
    var field = host.querySelector('[data-edit="' + key + '"]');
    var item = comparison();
    var source = item && item.available !== false ? gridSource(item) : { rows: [] };
    var row = (source.rows || []).filter(function (itemRow) { return itemRow.key === key; })[0];
    var text = field ? field.value.trim() : "";
    var slot = row && sectionRollup[row.id];
    if (editingAnalysis && slot && slot.key) {
      editingAnalysis = false;
      var kept = text
        ? { status: "ai", paragraph: text, reason: "" }
        : { status: "cleared", paragraph: "", reason: "" };
      rememberRevenue(slot.key, kept);
      sectionRollup[row.id] = {
        key: slot.key,
        status: kept.status,
        paragraph: kept.paragraph,
        evidence: slot.evidence,
        reason: "",
      };
      editingKey = "";
      editBuffer = null;
      leavePrompt = "";
      render(host);
      return;
    }
    if (!text) {
      draft.edits[key] = "";
      editingKey = "";
      editBuffer = null;
      leavePrompt = "";
      persist();
      render(host);
      return;
    }
    if (!reportTextTies(text, row)) {
      if (field) field.classList.add("bad");
      var live = host.querySelector(".live");
      if (row && live) live.textContent = liveTie(row, text);
      return;
    }
    draft.edits[key] = text;
    editedAt[key] = Date.now();
    editingKey = "";
    editBuffer = null;
    leavePrompt = "";
    persist();
    render(host);
  }


  function renderGrid(host) {
    if (global.SMPL_REPORTING_ENGINE) {
      renderReport(host);
      return;
    }
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
      var story = options.mode === "read"
        ? monthRead(item, host).join("\n\n")
        : (item.statements || [])
            .map(paragraph)
            .filter(Boolean)
            .join(" ");
      var addition = mergedAdditions()[item.id] || "";
      var untied = options.mode === "read"
        ? ""
        : (item.statements || [])
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
        '<div style="font-size:13.5px;line-height:1.6;color:var(--text);white-space:pre-wrap">' +
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

  function heldAnalyses() {
    loadRevenueHeld();
    var found = [];
    Object.keys(revenueHeld).forEach(function (key) {
      var stored = revenueHeld[key];
      if (!stored || stored.status !== "ai" || !stored.paragraph) return;
      var split = key.indexOf("\n");
      if (split < 0) return;
      var payload;
      try {
        payload = JSON.parse(key.slice(split + 1));
      } catch (err) {
        return;
      }
      if (!payload || !payload.comparison_kind || !payload.section_id) return;
      found.push({
        comparison: payload.comparison_kind,
        section_id: payload.section_id,
        paragraph: stored.paragraph,
      });
    });
    return found;
  }

  function workbookProgress(stage) {
    var panel = document.getElementById("smplCommentaryProgress");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "smplCommentaryProgress";
      panel.setAttribute("role", "status");
      panel.style.cssText =
        "position:fixed;right:20px;bottom:20px;z-index:99999;width:min(360px,calc(100vw - 32px));" +
        "background:#0f172a;color:#e2e8f0;border:1px solid rgba(255,255,255,0.12);border-radius:12px;" +
        "box-shadow:0 18px 40px rgba(0,0,0,0.35);padding:16px 16px 14px;font:13px/1.45 system-ui,sans-serif;";
      panel.innerHTML =
        '<div style="font-weight:650;color:#fff;font-size:14px;" data-commentary-progress-title>Preparing variance commentary</div>' +
        '<div style="color:#94a3b8;margin-top:4px;font-size:12px;" data-commentary-progress-meta>Starting…</div>' +
        '<ol data-commentary-progress-list style="list-style:none;margin:10px 0 0;padding:0;"></ol>';
      document.body.appendChild(panel);
    }
    panel.style.display = "block";
    var failed = stage === "failed";
    var order = ["preparing", "writing", "ready"];
    var labels = {
      preparing: "Preparing variance commentary",
      writing: "Writing the analysis into the workbook",
      ready: "Ready to download",
    };
    var cursor = order.indexOf(stage);
    if (cursor < 0) cursor = 0;
    var title = panel.querySelector("[data-commentary-progress-title]");
    var meta = panel.querySelector("[data-commentary-progress-meta]");
    var list = panel.querySelector("[data-commentary-progress-list]");
    if (title) {
      title.textContent = failed ? "Variance commentary failed" : "Preparing variance commentary";
      title.style.color = failed ? "#fca5a5" : "#fff";
    }
    if (meta) {
      meta.style.color = failed ? "#fca5a5" : "#94a3b8";
      meta.textContent = failed ? "The workbook could not be downloaded." : labels[stage] || "Working…";
    }
    if (!list) return;
    var rows = order.map(function (id, index) {
      var done = !failed && index < cursor || stage === "ready";
      var current = !failed && index === cursor && stage !== "ready";
      var mark = failed && index === cursor ? "✕" : done ? "✓" : current ? "●" : "○";
      var color = failed && index === cursor ? "#f87171" : done ? "#4ade80" : current ? "#fbbf24" : "#64748b";
      return (
        '<li style="display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-top:1px solid rgba(255,255,255,0.06);">' +
        '<span style="color:' + color + ';min-width:14px;">' + mark + "</span>" +
        '<span style="color:' + (done || current ? "#e2e8f0" : "#94a3b8") + ';">' + labels[id] + "</span></li>"
      );
    });
    if (failed) {
      rows.push(
        '<li style="display:flex;gap:10px;padding:6px 0;border-top:1px solid rgba(255,255,255,0.06);"><span style="color:#f87171;min-width:14px;">✕</span><span style="color:#fecaca;">Export failed — please try again</span></li>'
      );
    }
    list.innerHTML = rows.join("");
    if (stage === "ready") {
      setTimeout(function () {
        if (panel) panel.style.display = "none";
      }, 2500);
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
    workbookProgress("preparing");
    workbookProgress("writing");
    fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analyses: heldAnalyses() }),
    })
      .then(function (response) {
        if (!response.ok) throw new Error("export_failed");
        var disposition = response.headers.get("Content-Disposition") || "";
        var match = /filename="?([^";]+)"?/i.exec(disposition);
        var name = match && match[1] ? match[1] : "SMPL-variance-commentary-" + global.CLOSE_MONTH + ".xlsx";
        return response.blob().then(function (blob) {
          return { blob: blob, name: name };
        });
      })
      .then(function (file) {
        workbookProgress("ready");
        var link = document.createElement("a");
        link.href = URL.createObjectURL(file.blob);
        link.download = file.name;
        link.click();
      })
      .catch(function () {
        workbookProgress("failed");
        global.alert("The commentary file could not be downloaded.");
      });
  }

  global.boardMountStatementStory = mount;
  global.boardDownloadStatementStory = download;
  global.boardStatementReviewOpenCount = openCount;
  global.SMPLReportFormat = {
    mergedLabel: mergedLabel,
    sentenceLabel: sentenceLabel,
    favorText: favorText,
    columnHeads: columnHeads,
    reportParagraph: reportParagraph,
    moneyPhrase: moneyPhrase,
    uncitedDrivers: uncitedDrivers,
    foldPeriodMeasures: foldPeriodMeasures,
  };
})(typeof window !== "undefined" ? window : globalThis);
