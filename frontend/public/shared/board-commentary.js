/* Statement commentary. The overview reads each statement paragraph in order.
   Line edits replace that sentence. An overview addition may only cite a number
   already on a statement. Account rows stay blank when the other side is not loaded. */
(function (global) {
  var picked = "mom";
  var viewPicked = "income_statement";
  var gridFilter = "all";
  var draft = { reviews: {}, edits: {}, additions: {} };
  var COMPACT = { mom: "MoM", qoq: "QoQ", yoy: "YoY", ytd: "YTD", budget: "vs Budget", forecast: "vs Forecast" };
  var VIEWS = [
    ["income_statement", "Income statement"],
    ["management", "Management P&L"],
    ["gl", "GL detail"],
    ["balance_sheet", "Balance sheet"],
    ["cash_flow", "Cash flow"],
  ];

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function package() {
    var payload = global.SMPL_OUTLOOK_PAYLOAD;
    return payload && payload.COMMENTARY ? payload.COMMENTARY : null;
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

  function paragraph(statement) {
    var byId = {};
    (statement.lines || []).forEach(function (row) {
      byId[row.id] = row;
    });
    var parts = [];
    (statement.paragraph_line_ids || []).concat(statement.extra_line_ids || []).forEach(function (id) {
      if (byId[id]) parts.push(lineText(byId[id]));
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

  function gridSource(item) {
    var income = statementOf(item, "income_statement");
    if (viewPicked === "management") return { statement: income, rows: (income && income.lines) || [], note: "Same recognized dollars as the income statement until a management layer is loaded." };
    if (viewPicked === "gl") {
      var rows = [].concat((income && income.departments) || []).concat((income && income.accounts) || []);
      return { statement: income, rows: rows, note: rows.length ? "" : (income && income.accounts_note) || "Account and department detail is not loaded." };
    }
    var statement = statementOf(item, viewPicked);
    return { statement: statement, rows: (statement && statement.lines) || [], note: "" };
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
    if (!item) return;
    var reviews = mergedReviews();
    var source = item.available === false ? { rows: [], note: item.note || "This comparison is not available.", statement: null } : gridSource(item);
    var rows = (source.rows || []).filter(function (row) {
      if (gridFilter === "needs") return !!row.review_required;
      if (gridFilter === "open") return !!row.review_required && !reviews[row.key];
      return true;
    });
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
    var body = rows
      .map(function (row) {
        var text = lineText(row);
        return (
          "<tr>" +
          '<td style="padding:8px;vertical-align:top;font-weight:600">' +
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
      '<div style="overflow-x:auto;background:#fff;border:1px solid #D9D6CE;border-radius:8px"><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:#0E5A5F;color:#fff;text-align:left">' +
      "<th style=\"padding:8px\">Line</th><th style=\"padding:8px;text-align:right\">Current</th><th style=\"padding:8px;text-align:right\">Comparison</th><th style=\"padding:8px;text-align:right\">Variance</th><th style=\"padding:8px;text-align:right\">%</th><th style=\"padding:8px\">F/U</th><th style=\"padding:8px\">Commentary</th><th style=\"padding:8px\">Future impacts</th><th style=\"padding:8px\">Ties</th><th style=\"padding:8px\">Review</th>" +
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
    render(host);
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
