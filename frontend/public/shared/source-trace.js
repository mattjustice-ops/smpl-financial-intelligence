/* The records behind one number. Actual months open to the ledger.
   Forecast months open to the pipeline. */
(function (global) {
  var PAGE = 100;

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function money(value) {
    if (value == null || value === "") return "—";
    var amount = Number(value);
    if (!isFinite(amount)) return "—";
    var text = Math.abs(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return amount < 0 ? "−$" + text : "$" + text;
  }

  function ensure() {
    if (global.document.getElementById("sourceTrace")) return;
    var style = global.document.createElement("style");
    style.textContent =
      "#sourceTrace{position:fixed;inset:0;z-index:80;background:rgba(20,20,18,.28);display:flex;justify-content:flex-end}" +
      "#sourceTrace[hidden]{display:none}" +
      "#sourceTrace .panel{width:min(460px,100%);height:100%;overflow:auto;background:#fff;color:#1c1c1a;border-left:1px solid #d9d6ce;padding:20px 22px 32px;box-shadow:-8px 0 24px rgba(20,20,18,.08)}" +
      "#sourceTrace h2{font-size:16px;font-weight:560;margin:0 0 4px}" +
      "#sourceTrace .meta{color:#5f6469;font-size:12px;margin:0 0 14px}" +
      "#sourceTrace .note{font-size:13px;line-height:1.45;margin:0 0 14px}" +
      "#sourceTrace h3{font-size:12px;font-weight:560;letter-spacing:.04em;text-transform:uppercase;color:#5f6469;margin:18px 0 6px}" +
      "#sourceTrace table{width:100%;border-collapse:collapse;font-size:12.5px}" +
      "#sourceTrace th{text-align:left;font-weight:500;color:#5f6469;font-size:11px;padding:4px 6px 4px 0;border-bottom:1px solid #d9d6ce}" +
      "#sourceTrace td{padding:5px 6px 5px 0;border-bottom:1px solid #eee;vertical-align:top}" +
      "#sourceTrace td.num, #sourceTrace th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}" +
      "#sourceTrace .rowbtn, #sourceTrace .close{font:inherit;background:transparent;border:1px solid #d9d6ce;border-radius:4px;padding:2px 8px;cursor:pointer;color:#1c1c1a}" +
      "#sourceTrace .close{float:right;margin-top:2px}" +
      "#sourceTrace .total td{font-weight:560;border-bottom:0}";
    global.document.head.appendChild(style);
    var root = global.document.createElement("div");
    root.id = "sourceTrace";
    root.hidden = true;
    root.innerHTML = '<div class="panel" role="dialog" aria-label="Source"><button type="button" class="close" data-close>Close</button><div data-body></div></div>';
    global.document.body.appendChild(root);
    root.addEventListener("click", function (event) {
      var target = event.target;
      if (target === root || (target.closest && target.closest("[data-close]"))) {
        root.hidden = true;
        return;
      }
      var account = target.closest && target.closest("[data-open-account]");
      if (account) {
        open(Object.assign({}, root._opts, {
          grain: "account",
          accountNumber: account.getAttribute("data-open-account"),
          accountName: account.getAttribute("data-open-name") || "",
          title: account.getAttribute("data-open-title") || root._opts.title,
          includeEntries: false,
          offset: 0,
          dealType: "",
          dealOffset: 0,
        }));
        return;
      }
      if (target.closest && target.closest("[data-show-entries]")) {
        open(Object.assign({}, root._opts, { includeEntries: true, offset: 0 }));
        return;
      }
      var page = target.closest && target.closest("[data-entry-offset]");
      if (page) {
        open(Object.assign({}, root._opts, { includeEntries: true, offset: Number(page.getAttribute("data-entry-offset")) || 0 }));
        return;
      }
      var deals = target.closest && target.closest("[data-deal-offset]");
      if (deals) {
        open(Object.assign({}, root._opts, { dealOffset: Number(deals.getAttribute("data-deal-offset")) || 0 }));
      }
    });
  }

  function rows(items, columns) {
    if (!items || !items.length) return "";
    var head = "<tr>" + columns.map(function (column) {
      return '<th class="' + (column.num ? "num" : "") + '">' + esc(column.label) + "</th>";
    }).join("") + "</tr>";
    var body = items.map(function (item) {
      return "<tr>" + columns.map(function (column) {
        var value = column.cell ? column.cell(item) : item[column.key];
        return '<td class="' + (column.num ? "num" : "") + '">' + value + "</td>";
      }).join("") + "</tr>";
    }).join("");
    return "<table><thead>" + head + "</thead><tbody>" + body + "</tbody></table>";
  }

  function accountCell(account) {
    var label = (account.number ? account.number + " " : "") + (account.name || "Account");
    return '<button type="button" class="rowbtn" data-open-account="' + esc(account.number || "") + '" data-open-name="' + esc(account.name || "") + '" data-open-title="' + esc(label) + '">' + esc(label) + "</button>";
  }

  function render(trace, opts) {
    var html = "<h2>" + esc(opts.title || "Source") + "</h2>";
    html += '<p class="meta">' + esc(trace.period || opts.period || "") + (trace.forecast ? " · Forecast" : " · Actual") + "</p>";
    if (trace.note) html += '<p class="note">' + esc(trace.note) + "</p>";
    if (trace.accounts && trace.accounts.length) {
      html += "<h3>Accounts</h3>";
      var accountRows = trace.accounts.map(function (account) {
        return {
          account: accountCell(account),
          count: String(account.count || 0),
          amount: money(account.amount),
        };
      });
      accountRows.push({ account: "Total", count: "", amount: money(trace.account_total) });
      html += rows(accountRows, [
        { label: "Account", cell: function (row) { return row.account; } },
        { label: "Lines", key: "count", num: true },
        { label: "Amount", key: "amount", num: true },
      ]);
    }
    if (trace.vendors && trace.vendors.length) {
      html += "<h3>Vendors</h3>";
      if (trace.vendor_note) html += '<p class="note">' + esc(trace.vendor_note) + "</p>";
      var vendorRows = trace.vendors.map(function (vendor) {
        return { vendor: esc(vendor.vendor || "No vendor on the line"), count: String(vendor.count || 0), amount: money(vendor.amount) };
      });
      html += rows(vendorRows, [
        { label: "Vendor", key: "vendor" },
        { label: "Lines", key: "count", num: true },
        { label: "Amount", key: "amount", num: true },
      ]);
    }
    if (trace.entries_available && !opts.includeEntries) {
      html += '<p><button type="button" class="rowbtn" data-show-entries>Show the journal entries</button></p>';
    }
    if (trace.entries && trace.entries.length) {
      html += "<h3>Journal entries</h3>";
      html += rows(trace.entries.map(function (entry) {
        return {
          id: esc(entry.id || ""),
          vendor: esc(entry.vendor || ""),
          memo: esc(entry.memo || entry.department || ""),
          amount: money(entry.amount),
        };
      }), [
        { label: "Entry", key: "id" },
        { label: "Vendor", key: "vendor" },
        { label: "Memo", key: "memo" },
        { label: "Amount", key: "amount", num: true },
      ]);
      var start = Number(trace.entry_offset) || 0;
      var shown = start + trace.entries.length;
      if (trace.entry_count > shown) {
        html += '<p class="meta">Showing ' + (start + 1) + "–" + shown + " of " + trace.entry_count +
          ' <button type="button" class="rowbtn" data-entry-offset="' + (start + PAGE) + '">Next</button></p>';
      }
    }
    var bookings = trace.bookings;
    if (bookings) {
      html += "<h3>" + esc(bookings.heading || (bookings.forecast ? "Pipeline" : "Closed bookings")) + "</h3>";
      if (bookings.note && bookings.note !== trace.note) html += '<p class="note">' + esc(bookings.note) + "</p>";
      if (bookings.loaded && bookings.deals && bookings.deals.length) {
        html += rows(bookings.deals.map(function (deal) {
          return {
            customer: esc(deal.customer || deal.id || ""),
            type: esc(deal.type || ""),
            stage: esc(deal.stage || ""),
            amount: money(deal.amount),
          };
        }).concat([{ customer: esc(bookings.total_label || "Total"), type: "", stage: "", amount: money(bookings.total) }]), [
          { label: "Customer", key: "customer" },
          { label: "Type", key: "type" },
          { label: "Stage", key: "stage" },
          { label: "Amount", key: "amount", num: true },
        ]);
        var dealStart = Number(bookings.deal_offset) || 0;
        var dealShown = dealStart + bookings.deals.length;
        if (Number(bookings.deal_count) > dealShown) {
          html += '<p class="meta">Showing ' + (dealStart + 1) + "–" + dealShown + " of " + bookings.deal_count +
            ' <button type="button" class="rowbtn" data-deal-offset="' + dealShown + '">Next</button></p>';
        }
      }
      if (bookings.lost && bookings.lost.length) {
        html += "<h3>Lost</h3>";
        html += rows(bookings.lost.map(function (deal) {
          return { customer: esc(deal.customer || deal.id || ""), amount: money(deal.amount) };
        }).concat([{ customer: "Lost", amount: money(bookings.lost_total) }]), [
          { label: "Customer", key: "customer" },
          { label: "Amount", key: "amount", num: true },
        ]);
      }
    }
    return html;
  }

  async function open(opts) {
    opts = opts || {};
    ensure();
    var root = global.document.getElementById("sourceTrace");
    root._opts = opts;
    root.hidden = false;
    var body = root.querySelector("[data-body]");
    body.innerHTML = '<p class="note">Loading the records for this number.</p>';
    var org = global.SMPL_ORG_ID;
    if (!org && global.SMPLOutlook && global.SMPLOutlook.resolveOrgId) {
      try {
        org = await global.SMPLOutlook.resolveOrgId({ waitForParent: true, parentWaitMs: 4000 });
      } catch (err) {
        org = null;
      }
    }
    if (!org) {
      body.innerHTML = '<h2>' + esc(opts.title || "Source") + '</h2><p class="note">Sign in to open the records behind this number.</p>';
      return;
    }
    var params = new URLSearchParams();
    params.set("organization_id", org);
    params.set("period", opts.period || "");
    params.set("grain", opts.grain || "account");
    if (opts.accountNumber) params.set("account_number", opts.accountNumber);
    if (opts.accountName) params.set("account_name", opts.accountName);
    if (opts.dealType) params.set("deal_type", opts.dealType);
    if (opts.dealOffset) params.set("deal_offset", String(opts.dealOffset));
    if (opts.includeEntries) {
      params.set("include_entries", "true");
      params.set("offset", String(opts.offset || 0));
    }
    try {
      var res = await fetch("/api/v1/reporting/trace?" + params.toString(), { credentials: "include" });
      if (!res.ok) {
        body.innerHTML = '<h2>' + esc(opts.title || "Source") + '</h2><p class="note">The records for this number did not load.</p>';
        return;
      }
      body.innerHTML = render(await res.json(), opts);
    } catch (err) {
      body.innerHTML = '<h2>' + esc(opts.title || "Source") + '</h2><p class="note">The records for this number did not load.</p>';
    }
  }

  global.SMPLSourceTrace = { open: open };
})(window);
