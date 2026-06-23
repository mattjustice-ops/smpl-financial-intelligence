/**
 * Board Platform — live warehouse hydration + Claude API (same pattern as Forecast Engine).
 */
(function (global) {
  "use strict";

  var BOARD_SLIDE_API_KEYS = {
    exec: "executive_summary",
    arr: "arr_waterfall",
    revenue: "gaap_revenue",
    gtm: "gtm_performance",
    cash: "cash_forecast",
    headcount: "headcount",
    risks: "risks_opportunities",
  };

  function monthNames() {
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  }

  function boardActiveCloseMonth() {
    return global.CLOSE_MONTH || global.SMPL_CLOSE_MONTH || "2026-06";
  }

  function boardActualPeriods() {
    var cm = boardActiveCloseMonth();
    var y = cm.slice(0, 4);
    var n = parseInt(cm.slice(5), 10);
    var out = [];
    for (var i = 1; i <= n; i++) {
      out.push(y + "-" + String(i).padStart(2, "0"));
    }
    return out;
  }

  function fKpiM(v, d) {
    d = d == null ? 1 : d;
    if (v == null || Number.isNaN(v)) return "—";
    var abs = Math.abs(v);
    if (abs >= 1) return (v < 0 ? "-" : "") + "$" + abs.toFixed(d) + "M";
    if (abs >= 0.001) return (v < 0 ? "-" : "") + "$" + Math.round(abs * 1000) + "k";
    return "$0";
  }

  function fKpiVarM(v) {
    if (v == null || Number.isNaN(v)) return "—";
    return (v >= 0 ? "+" : "") + fKpiM(v);
  }

  function fKpiPct(v) {
    if (v == null || Number.isNaN(v)) return "—";
    return (v * 100).toFixed(1) + "%";
  }

  function boardJunMetrics() {
    var cm = boardActiveCloseMonth();
    var ts = (global.SMPLOutlook && global.SMPLOutlook.getOutlookTsData && global.SMPLOutlook.getOutlookTsData()) || global.TS_DATA || {};
    var isA = (ts.Actual && ts.Actual.is && ts.Actual.is[cm]) || {};
    var isB = (ts.Budget && ts.Budget.is && ts.Budget.is[cm]) || {};
    var bsA = (ts.Actual && ts.Actual.bs && ts.Actual.bs[cm]) || {};
    var bsB = (ts.Budget && ts.Budget.bs && ts.Budget.bs[cm]) || {};
    var src =
      (global.SMPL_OUTLOOK_PAYLOAD &&
        global.SMPL_OUTLOOK_PAYLOAD.SRC &&
        global.SMPL_OUTLOOK_PAYLOAD.SRC.actuals &&
        global.SMPL_OUTLOOK_PAYLOAD.SRC.actuals[cm]) ||
      {};
    var wf = global.SMPL_ARR_WATERFALL || {};
    var idx = boardActualPeriods().length - 1;
    var arrAct =
      wf.Ending && wf.Ending[idx] != null ? wf.Ending[idx] / 1e6 : global.ARR_ACT && global.ARR_ACT[idx];
    var arrBud =
      wf.Budget_Ending && wf.Budget_Ending[idx] != null
        ? wf.Budget_Ending[idx] / 1e6
        : global.ARR_BUD && global.ARR_BUD[idx];
    return {
      arrAct: arrAct,
      arrBud: arrBud,
      revAct: isA.revenue != null ? isA.revenue / 1e6 : null,
      revBud: isB.revenue != null ? isB.revenue / 1e6 : null,
      ebitdaAct: isA.ebitda != null ? isA.ebitda / 1e6 : null,
      ebitdaBud: isB.ebitda != null ? isB.ebitda / 1e6 : null,
      cashAct: bsA.cash != null ? bsA.cash / 1e6 : null,
      cashBud: bsB.cash != null ? bsB.cash / 1e6 : null,
      gmAct: isA.gm_pct,
      gmBud: isB.gm_pct,
      nrr: src.nrr,
    };
  }

  function boardExecDrivers() {
    var cm = boardActiveCloseMonth();
    var wf = global.SMPL_ARR_WATERFALL || {};
    var idx = boardActualPeriods().length - 1;
    function row(key, label) {
      var act = wf[key] && wf[key][idx] != null ? wf[key][idx] / 1e6 : 0;
      var budKey = "Budget_" + key.replace(/ /g, "_");
      var bud =
        wf[budKey] && wf[budKey][idx] != null
          ? wf[budKey][idx] / 1e6
          : wf[key + "_Budget"] && wf[key + "_Budget"][idx] != null
            ? wf[key + "_Budget"][idx] / 1e6
            : 0;
      return { label: label, val: act, bud: bud };
    }
    var drivers = [
      row("New Business", "New Business"),
      row("Expansion", "Expansion"),
      row("Reactivation", "Reactivation"),
      row("Contraction", "Contraction"),
      row("Churn", "Churn"),
    ];
    var nnAct = drivers.reduce(function (s, d) {
      return s + d.val;
    }, 0);
    var nnBud = drivers.reduce(function (s, d) {
      return s + d.bud;
    }, 0);
    var maxAbs = Math.max.apply(
      null,
      drivers.map(function (d) {
        return Math.abs(d.val);
      }).concat([0.01]),
    );
    drivers.forEach(function (d) {
      d.pct = Math.round((Math.abs(d.val) / maxAbs) * 100);
    });
    return { nnAct: nnAct, nnBud: nnBud, drivers: drivers };
  }

  function syncBoardFromOutlook(data) {
    if (!data || !data.meta) return;
    var cm = data.meta.close_month;
    if (cm) {
      global.CLOSE_MONTH = cm;
      global.SMPL_CLOSE_MONTH = cm;
      var names = monthNames();
      var idx = parseInt(cm.slice(5), 10) - 1;
      global.CLOSE_MO = names[idx] || cm.slice(5, 7);
      global.CLOSE_LABEL = global.CLOSE_MO + " " + cm.slice(0, 4);
      global.ACT_MONTHS_COUNT = idx + 1;
      global.CLOSE_MO_IDX = idx;
      var badge = document.getElementById("periodBadge");
      if (badge) badge.textContent = global.CLOSE_LABEL + " \u00b7 YTD Close";
    }

    if (data.ARR_WATERFALL && global.SMPL_DEMO_WF_TABLE && global.SMPLOutlook && global.SMPLOutlook.replaceArrWaterfallTable) {
      global.SMPLOutlook.replaceArrWaterfallTable(global.SMPL_DEMO_WF_TABLE, data.ARR_WATERFALL);
    }

    if (typeof global.boardRefreshAllSeries === "function") {
      global.boardRefreshAllSeries();
    }

    if (data.CASH_BRIDGE && data.CASH_BRIDGE.Actual && global.COLL) {
      var periods = boardActualPeriods();
      periods.forEach(function (period, i) {
        if (i >= global.COLL.length) return;
        var row = data.CASH_BRIDGE.Actual[period];
        if (row && row.collections != null) {
          global.COLL[i] = +(row.collections / 1e6).toFixed(2);
        }
      });
    }

    if (typeof global.tsRender === "function") {
      try {
        global.tsRender();
      } catch (err) {
        console.error("[board-hydrate] tsRender after outlook failed", err);
      }
    }

    if (global.SMPLBoardLive && global.SMPLBoardLive.updateCopilotContext) {
      global.SMPLBoardLive.updateCopilotContext(data);
    }
  }

  function smplBoardRefreshView() {
    var active = document.querySelector(".nav-btn.active");
    var tab = "exec";
    if (active) {
      var m = active.getAttribute("onclick");
      if (m) {
        var hit = m.match(/show\('(\w+)'/);
        if (hit) tab = hit[1];
      }
    }
    if (typeof global.show === "function") {
      global.show(tab, active);
    }
  }
  global.smplBoardRefreshView = smplBoardRefreshView;

  async function boardResolveOrgId() {
    if (global.SMPL_ORG_ID) return global.SMPL_ORG_ID;
    if (global.SMPLOutlook && global.SMPLOutlook.resolveOrgId) {
      return await global.SMPLOutlook.resolveOrgId({ waitForParent: true, parentWaitMs: 4000 });
    }
    return null;
  }

  async function boardApiErrorMessage(res) {
    try {
      var j = await res.json();
      var detail = j.detail;
      if (typeof detail === "string") return detail;
      if (detail && typeof detail === "object") {
        var msg = detail.message || detail.code || "Request failed (" + res.status + ")";
        var checks = detail.validation && detail.validation.checks;
        if (checks && checks.length) {
          var issues = checks
            .filter(function (c) {
              return c.status === "fail" || c.status === "warning";
            })
            .slice(0, 4)
            .map(function (c) {
              return c.validation_name + " (" + c.period + "): " + c.status;
            });
          if (issues.length) msg += " — " + issues.join("; ");
        }
        return msg;
      }
      return "Request failed (" + res.status + ")";
    } catch (_) {
      return "Request failed (" + res.status + ")";
    }
  }

  function formatApiCommentary(c) {
    if (!c || typeof c !== "object") return "";
    return [
      c.what_happened,
      c.why_it_happened,
      c.impact,
      c.favorable,
      c.unfavorable,
      c.leadership_watch,
      c.recommended_actions,
    ]
      .filter(Boolean)
      .join(" ");
  }

  function installLiveAi() {
    if (global._smplBoardAiInstalled) return;
    global._smplBoardAiInstalled = true;

    global.aiComm = async function aiComm(slideKey, targetId) {
      if (global.aiCache && global.aiCache[slideKey]) {
        document.getElementById(targetId).querySelector(".commentary-text").textContent =
          global.aiCache[slideKey];
        return;
      }
      var el = document.getElementById(targetId);
      if (!el) return;
      var txt = el.querySelector(".commentary-text");
      txt.innerHTML = '<span class="spin"></span> Generating AI commentary...';
      var orgId = await boardResolveOrgId();
      if (!orgId) {
        txt.textContent =
          "Open Board Platform from the signed-in operating OS (/app/board) to regenerate live Claude commentary.";
        return;
      }
      var apiSlideKey = BOARD_SLIDE_API_KEYS[slideKey] || slideKey;
      try {
        var res = await fetch(
          "/api/v1/board-platform/commentary/regenerate?organization_id=" + encodeURIComponent(orgId),
          {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slide_key: apiSlideKey }),
          },
        );
        if (!res.ok) {
          txt.textContent = await boardApiErrorMessage(res);
          return;
        }
        var data = await res.json();
        var text = formatApiCommentary(data.commentary) || "Commentary unavailable.";
        txt.textContent = text;
        global.aiCache = global.aiCache || {};
        global.aiCache[slideKey] = text;
      } catch (_) {
        txt.textContent =
          "Unable to reach commentary service. Confirm sign-in and ANTHROPIC_API_KEY on the API server.";
      }
    };

    var origCpSend = global.cpSend;
    global.cpSend = async function cpSendLive() {
      if (global.cpSending) return;
      var input = document.getElementById("cpInput");
      var sendBtn = document.getElementById("cpSendBtn");
      var msgs = document.getElementById("cpMessages");
      if (!input || !msgs) return;
      var q = input.value.trim();
      if (!q) return;

      global.cpSending = true;
      input.value = "";
      if (sendBtn) sendBtn.disabled = true;

      msgs.innerHTML +=
        '<div class="cp-msg user"><div class="cp-avatar">M</div><div class="cp-bubble">' +
        q.replace(/</g, "&lt;") +
        "</div></div>";

      var thinkId = "cpThink_" + Date.now();
      msgs.innerHTML +=
        '<div class="cp-msg assistant" id="' +
        thinkId +
        '"><div class="cp-avatar">S</div><div class="cp-bubble"><div class="cp-thinking"><div class="cp-dot"></div><div class="cp-dot"></div><div class="cp-dot"></div></div></div></div>';
      msgs.scrollTop = msgs.scrollHeight;

      global.cpHistory = global.cpHistory || [];
      global.cpHistory.push({ role: "user", content: q });

      var orgId = await boardResolveOrgId();
      if (!orgId) {
        var el = document.getElementById(thinkId);
        if (el) {
          el.outerHTML =
            '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">Open Board Platform from /app/board (signed in) to use live SMPL Copilot.</div></div>';
        }
        global.cpSending = false;
        if (sendBtn) sendBtn.disabled = false;
        return;
      }

      try {
        var res = await fetch(
          "/api/v1/board-platform/copilot?organization_id=" + encodeURIComponent(orgId),
          {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q }),
          },
        );
        if (!res.ok) {
          var errText = await boardApiErrorMessage(res);
          var errEl = document.getElementById(thinkId);
          if (errEl) {
            errEl.outerHTML =
              '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">' +
              errText.replace(/</g, "&lt;") +
              "</div></div>";
          }
        } else {
          var data = await res.json();
          var reply = data.answer || "Unable to generate response.";
          global.cpHistory.push({ role: "assistant", content: reply });
          var formatted =
            typeof global.formatCopilotReply === "function"
              ? global.formatCopilotReply(reply)
              : reply.replace(/</g, "&lt;");
          var thinkEl = document.getElementById(thinkId);
          if (thinkEl) {
            thinkEl.outerHTML =
              '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble">' +
              formatted +
              "</div></div>";
          }
        }
      } catch (_) {
        var failEl = document.getElementById(thinkId);
        if (failEl) {
          failEl.outerHTML =
            '<div class="cp-msg assistant"><div class="cp-avatar">S</div><div class="cp-bubble" style="color:var(--red)">Connection error. Confirm sign-in and API health.</div></div>';
        }
      }

      global.cpSending = false;
      if (sendBtn) sendBtn.disabled = false;
      msgs.scrollTop = msgs.scrollHeight;
    };
  }

  function updateCopilotWelcome(data) {
    var bubble = document.querySelector("#cpMessages .cp-msg.assistant .cp-bubble");
    if (!bubble || !data || !data.meta) return;
    var org = data.meta.organization_name || "your organization";
    var close = data.meta.close_month || boardActiveCloseMonth();
    var y = close.slice(0, 4);
    var m = parseInt(close.slice(5), 10) - 1;
    var closeLbl = (monthNames()[m] || "") + " " + y;
    bubble.innerHTML =
      '<div class="cp-section">Ready</div>I have live warehouse data for <strong>' +
      org +
      "</strong> through <strong>" +
      closeLbl +
      "</strong> close. Ask about ARR, revenue, cash, headcount, GTM, or variance vs budget." +
      '<div class="cp-source">Source: reconciled Neon warehouse via /api/v1/reporting/outlook</div>';
  }

  function installLiveExec() {
    if (!global.renderExec || global._smplExecLiveInstalled) return;
    global._smplExecLiveInstalled = true;
    var demoRenderExec = global.renderExec;

    global.renderExec = function renderExecLive(area) {
      if (!global.SMPL_LIVE_OUTLOOK) {
        return demoRenderExec(area);
      }
      var m = boardJunMetrics();
      var drivers = boardExecDrivers();
      var closeLbl = global.CLOSE_LABEL || "Close";
      var cm = boardActiveCloseMonth();
      var arrVar = m.arrAct != null && m.arrBud != null ? m.arrAct - m.arrBud : 0;
      var revVar = m.revAct != null && m.revBud != null ? m.revAct - m.revBud : 0;
      var ebitdaVar = m.ebitdaAct != null && m.ebitdaBud != null ? m.ebitdaAct - m.ebitdaBud : 0;
      var cashVar = m.cashAct != null && m.cashBud != null ? m.cashAct - m.cashBud : 0;
      var nnVar = drivers.nnAct - drivers.nnBud;
      var nrrPct = m.nrr != null ? (m.nrr * 100).toFixed(1) + "%" : "—";
      var gmActPct = m.gmAct != null ? fKpiPct(m.gmAct) : "—";
      var gmBudPct = m.gmBud != null ? fKpiPct(m.gmBud) : "—";

      var heroCards = [
        {
          lbl: "Ending ARR",
          val: fKpiM(m.arrAct),
          delta: fKpiVarM(arrVar) + " vs bud",
          dir: arrVar >= 0 ? "pos" : "neg",
          because: "Sourced from live ARR waterfall ending balance",
          link: "show('arr',null)",
        },
        {
          lbl: "Net New ARR",
          val: fKpiM(drivers.nnAct),
          delta: fKpiVarM(nnVar) + " vs bud",
          dir: nnVar >= 0 ? "pos" : "neg",
          because: "Driver decomposition from warehouse waterfall",
          link: "show('arr',null)",
        },
        {
          lbl: "EBITDA",
          val: fKpiM(m.ebitdaAct),
          delta: fKpiVarM(ebitdaVar) + " vs bud",
          dir: ebitdaVar >= 0 ? "pos" : "neg",
          because: "Income statement actual vs budget at " + cm,
          link: "show('pl',null)",
        },
        {
          lbl: "Cash Balance",
          val: fKpiM(m.cashAct),
          delta: fKpiVarM(cashVar) + " vs bud",
          dir: cashVar >= 0 ? "pos" : "neg",
          because: "Balance sheet cash ties to cash flow bridge",
          link: "show('cash',null)",
        },
      ];

      demoRenderExec(area);

      var root = area.querySelector(".slide");
      if (!root) return;

      var mastheadSub = root.querySelector(".slide div[style*='Prepared for Board']");
      if (mastheadSub) {
        mastheadSub.textContent = "Prepared for Board of Directors · " + closeLbl + " Close";
      }

      /* KPI cards + section 02 NN variance come from boardExecKpis() in renderExec — do not replace hero grid (was causing NN var mismatch). */

      var execComm = document.getElementById("execComm");
      if (execComm) {
        var txt = execComm.querySelector(".commentary-text");
        if (txt && !global.aiCache?.exec) {
          txt.textContent =
            closeLbl +
            " close: ARR " +
            fKpiM(m.arrAct) +
            " (" +
            fKpiVarM(arrVar) +
            " vs bud), revenue " +
            fKpiM(m.revAct) +
            " (" +
            fKpiVarM(revVar) +
            " vs bud), EBITDA " +
            fKpiM(m.ebitdaAct) +
            " (" +
            fKpiVarM(ebitdaVar) +
            " vs bud), cash " +
            fKpiM(m.cashAct) +
            " (" +
            fKpiVarM(cashVar) +
            " vs bud), N$R " +
            nrrPct +
            ".";
        }
      }
    };
  }

  async function smplBoardHydrate() {
    if (!global.SMPLOutlook) {
      var el = document.getElementById("warehouseStatus");
      if (el) {
        el.textContent = "Demo data";
        el.style.color = "var(--amber)";
      }
      return;
    }

    installLiveAi();
    installLiveExec();

    global.SMPL_DEMO_TS_DATA = global.TS_DATA;
    if (global.TS_DATA) {
      global.SMPLOutlook.registerDemoData(global.TS_DATA, global.SMPL_DEMO_WF_TABLE || null);
    }

    await global.SMPLOutlook.hydrate({
      endpoint: "reporting/outlook",
      hooks: {
        TS_DATA: global.TS_DATA,
        WF_TABLE: global.SMPL_DEMO_WF_TABLE,
        ARR_ACT: global.ARR_ACT,
        actMonthsCount: global.ACT_MONTHS_COUNT,
      },
      onStatus: function (text, tone) {
        var el = document.getElementById("warehouseStatus");
        if (!el) return;
        el.textContent = text;
        el.style.color =
          tone === "ok" ? "var(--teal)" : tone === "warn" ? "var(--amber)" : "var(--text2)";
      },
      onApplied: function (data) {
        try {
          syncBoardFromOutlook(data);
          updateCopilotWelcome(data);
          smplBoardRefreshView();
        } catch (err) {
          console.error("[board-hydrate] post-hydrate refresh failed", err);
        }
      },
    });
  }

  global.SMPLBoardLive = {
    hydrate: smplBoardHydrate,
    syncBoardFromOutlook: syncBoardFromOutlook,
    updateCopilotContext: updateCopilotWelcome,
    boardJunMetrics: boardJunMetrics,
  };

  global.SMPL_ON_ORG_READY = function () {
    void smplBoardHydrate();
  };

  global.addEventListener("load", function () {
    installLiveAi();

    if (global.SMPLSkin) {
      global.SMPLSkin.init("skinSelect", smplBoardRefreshView);
    } else if (typeof global.applySkin === "function") {
      var sel = document.getElementById("skinSelect");
      var saved = "canvas";
      try {
        saved = localStorage.getItem("smpl-skin") || "canvas";
      } catch (_) {}
      if (sel) sel.value = saved;
      global.applySkin(saved);
    }
    // Defer first hydrate so embedded iframe receives smpl:org from parent (Forecast Engine pattern).
    setTimeout(function () {
      void smplBoardHydrate();
    }, 50);
  });
})(window);
