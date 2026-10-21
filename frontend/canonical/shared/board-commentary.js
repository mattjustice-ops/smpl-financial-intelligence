/* Statement commentary. The overview reads each statement paragraph in order.
   Line edits replace that sentence. An overview addition may only cite a number
   already on a statement. Account rows stay blank when the other side is not loaded. */
(function (global) {
  var picked = "mom";
  var draft = { reviews: {}, edits: {}, additions: {} };

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

  function render(host) {
    var options = host._storyOptions || {};
    var book = package();
    if (!book) {
      host.innerHTML =
        '<div style="margin:0 0 16px;padding:12px 14px;border:0.5px solid var(--border);border-radius:8px;color:var(--text3);font-size:12px">The month story appears when the books for this close are loaded.</div>';
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
        options.mode === "read" || options.mode === "work"
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
