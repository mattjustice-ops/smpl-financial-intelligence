/**
 * Shared design skins for Board Platform + Forecast Engine (localStorage: smpl-skin).
 */
(function (global) {
  "use strict";

  var SKINS = {
    canvas: {
      bg: "#18241b",
      bg2: "#23332699",
      bg3: "#2b3c2e",
      text: "#dde8d6",
      text2: "#aab8a2",
      text3: "#72826a",
      border: "#2e3f31",
      border2: "rgba(56,75,60,0.25)",
      accent: "#c4855a",
      teal: "#5fa878",
      red: "#b8705f",
      amber: "#b89060",
      shadow: "0 1px 2px rgba(0,0,0,0.3),0 12px 32px -8px rgba(0,0,0,0.4)",
    },
    smpl: {
      bg: "#0c1418",
      bg2: "#14222899",
      bg3: "#1a2e35",
      text: "#d8eae8",
      text2: "#8eb0ad",
      text3: "#5e8280",
      border: "#1e3540",
      border2: "rgba(36,64,76,0.25)",
      accent: "#3db8a6",
      teal: "#4aaa94",
      red: "#b87068",
      amber: "#c4924a",
      shadow: "0 1px 2px rgba(0,0,0,0.45),0 16px 40px -10px rgba(0,0,0,0.6)",
    },
    midnight: {
      bg: "#141a2e",
      bg2: "#1e273f99",
      bg3: "#252e4a",
      text: "#d8daf0",
      text2: "#9098c0",
      text3: "#606880",
      border: "#2c3558",
      border2: "rgba(52,62,100,0.25)",
      accent: "#c4a058",
      teal: "#5ea87a",
      red: "#b87070",
      amber: "#c4a058",
      shadow: "0 1px 2px rgba(0,0,0,0.35),0 12px 32px -8px rgba(0,0,0,0.45)",
    },
    harbor: {
      bg: "#0e2428",
      bg2: "#16363999",
      bg3: "#1d4045",
      text: "#d2e8e4",
      text2: "#88b0ac",
      text3: "#567874",
      border: "#244850",
      border2: "rgba(44,88,92,0.25)",
      accent: "#c49058",
      teal: "#52a882",
      red: "#b87068",
      amber: "#c49058",
      shadow: "0 1px 2px rgba(0,0,0,0.35),0 12px 32px -8px rgba(0,0,0,0.45)",
    },
    eclipse: {
      bg: "#0d1018",
      bg2: "#181e2e",
      bg3: "#202638",
      text: "#d4d8e8",
      text2: "#8890b0",
      text3: "#586080",
      border: "#282f48",
      border2: "rgba(50,58,86,0.25)",
      accent: "#6090c8",
      teal: "#52a882",
      red: "#b07070",
      amber: "#b8904a",
      shadow: "0 1px 2px rgba(0,0,0,0.45),0 16px 40px -10px rgba(0,0,0,0.62)",
    },
    graphite: {
      bg: "#141311",
      bg2: "#221f1c",
      bg3: "#2c2924",
      text: "#dedad4",
      text2: "#a09890",
      text3: "#706860",
      border: "#363028",
      border2: "rgba(66,58,50,0.25)",
      accent: "#c0825a",
      teal: "#5aa87a",
      red: "#b07060",
      amber: "#c0825a",
      shadow: "0 1px 2px rgba(0,0,0,0.4),0 16px 40px -10px rgba(0,0,0,0.55)",
    },
    aurora: {
      bg: "#0c1020",
      bg2: "#161e30",
      bg3: "#1e283e",
      text: "#ccd8ec",
      text2: "#7890b0",
      text3: "#506080",
      border: "#263450",
      border2: "rgba(46,62,96,0.25)",
      accent: "#5090c0",
      teal: "#4898a0",
      red: "#a87070",
      amber: "#a89050",
      shadow: "0 1px 2px rgba(0,0,0,0.45),0 16px 40px -10px rgba(0,0,0,0.62)",
    },
    ember: {
      bg: "#160f12",
      bg2: "#261a20",
      bg3: "#302028",
      text: "#e8dcd8",
      text2: "#a88880",
      text3: "#785850",
      border: "#3c2830",
      border2: "rgba(70,48,58,0.25)",
      accent: "#c09050",
      teal: "#5aa87a",
      red: "#b07070",
      amber: "#c09050",
      shadow: "0 1px 2px rgba(0,0,0,0.45),0 16px 40px -10px rgba(0,0,0,0.6)",
    },
    slate: {
      bg: "#181b22",
      bg2: "#20252e99",
      bg3: "#282e38",
      text: "#d4d8e4",
      text2: "#8890a8",
      text3: "#606878",
      border: "#303848",
      border2: "rgba(58,68,88,0.25)",
      accent: "#6090c0",
      teal: "#5aa87a",
      red: "#a87060",
      amber: "#a89050",
      shadow: "0 1px 2px rgba(0,0,0,0.3),0 12px 32px -8px rgba(0,0,0,0.4)",
    },
    mist: {
      bg: "#1c2028",
      bg2: "#242a34",
      bg3: "#2c3240",
      text: "#d0d4de",
      text2: "#848c9c",
      text3: "#5c6270",
      border: "#323848",
      border2: "rgba(62,70,88,0.25)",
      accent: "#7890a8",
      teal: "#5a9878",
      red: "#a07068",
      amber: "#a08858",
      shadow: "0 1px 2px rgba(0,0,0,0.3),0 14px 36px -12px rgba(0,0,0,0.42)",
    },
  };

  function apply(id, onRefresh) {
    var s = SKINS[id] || SKINS.canvas;
    var r = document.documentElement.style;
    r.setProperty("--bg", s.bg);
    r.setProperty("--bg2", s.bg2);
    r.setProperty("--bg3", s.bg3);
    r.setProperty("--panel", s.bg2);
    r.setProperty("--text", s.text);
    r.setProperty("--text2", s.text2);
    r.setProperty("--text3", s.text3);
    r.setProperty("--border", s.border);
    r.setProperty("--border2", s.border2);
    r.setProperty("--accent", s.accent);
    r.setProperty("--teal", s.teal);
    r.setProperty("--red", s.red);
    r.setProperty("--amber", s.amber);
    r.setProperty("--navy", s.bg2);
    r.setProperty("--blue", s.teal);
    r.setProperty("--green", s.teal);
    r.setProperty("--gray", s.text3);
    r.setProperty("--lgray", s.border);
    r.setProperty("--shadow", s.shadow);
    r.setProperty("--teal-light", s.teal + "22");
    r.setProperty("--red-light", s.red + "18");
    r.setProperty("--amber-light", s.amber + "18");
    r.setProperty("--green-light", s.teal + "18");

    if (global.Chart) {
      global.Chart.defaults.color = s.text2;
      global.Chart.defaults.borderColor = "rgba(255,255,255,0.14)";
      global.Chart.defaults.font.family = "'Inter',-apple-system,sans-serif";
      global.Chart.defaults.font.size = 10;
    }

    try {
      localStorage.setItem("smpl-skin", id);
    } catch (_) {}

    if (typeof onRefresh === "function") {
      onRefresh(id);
    }
  }

  function init(selectId, onRefresh) {
    var saved = "canvas";
    try {
      saved = localStorage.getItem("smpl-skin") || "canvas";
    } catch (_) {}
    var sel = document.getElementById(selectId);
    if (sel) {
      sel.value = saved;
    }
    /* Apply tokens only on init — avoid full tab rebuild racing first chart paint */
    apply(saved);
    return saved;
  }

  /** Read live skin CSS tokens at chart-build time (never cache at module load). */
  function chartSkinTokens() {
    var cs = getComputedStyle(document.documentElement);
    var C = function (k) {
      return cs.getPropertyValue(k).trim();
    };
    var cPos = C("--teal");
    var cNeg = C("--red");
    var cAmber = C("--amber");
    var cAccent = C("--accent");
    var cText = C("--text");
    var cText2 = C("--text2");
    var cText3 = C("--text3");
    var cBorder = C("--border");
    var cBlue = "#7a9fc2";
    var fade = function (hex, a) {
      hex = (hex || "").replace("#", "");
      if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
      var r = parseInt(hex.slice(0, 2), 16) || 122;
      var g = parseInt(hex.slice(2, 4), 16) || 159;
      var b = parseInt(hex.slice(4, 6), 16) || 194;
      return "rgba(" + r + "," + g + "," + b + "," + a + ")";
    };
    var gridColor = "rgba(255,255,255,0.14)";
    var tickFont = { size: 10, family: "'Inter',-apple-system,sans-serif", weight: "500" };
    var tickColor = cText2;
    var baseScaleX = { ticks: { font: tickFont, color: tickColor }, grid: { display: false } };
    var baseScaleY = function (cb) {
      return {
        ticks: { callback: cb, font: tickFont, color: tickColor },
        grid: { color: gridColor, drawTicks: false },
      };
    };
    var bubblePalette = [
      "#7a9fc2",
      "#74b88a",
      "#c2a07a",
      "#a07ab8",
      "#7ab8b0",
      "#b87a7a",
      "#b8a87a",
      "#7a8ab8",
      "#8ab87a",
      "#b87aa0",
      "#7ab8c2",
    ];
    return {
      cPos: cPos,
      cNeg: cNeg,
      cAmber: cAmber,
      cAccent: cAccent,
      cText: cText,
      cText2: cText2,
      cText3: cText3,
      cBorder: cBorder,
      cBlue: cBlue,
      fade: fade,
      gridColor: gridColor,
      tickFont: tickFont,
      tickColor: tickColor,
      baseScaleX: baseScaleX,
      baseScaleY: baseScaleY,
      bubblePalette: bubblePalette,
    };
  }

  function patchChartCfg(cfg) {
    var tokens = chartSkinTokens();
    var opts = cfg.options || (cfg.options = {});
    if (opts.scales) {
      Object.keys(opts.scales).forEach(function (key) {
        var scale = opts.scales[key];
        if (!scale) return;
        if (scale.grid && scale.grid.display !== false) {
          scale.grid.color = tokens.gridColor;
          scale.grid.drawTicks = false;
        }
        if (scale.ticks) {
          scale.ticks.font = Object.assign({}, tokens.tickFont, scale.ticks.font || {});
          if (!scale.ticks.color) scale.ticks.color = tokens.tickColor;
        }
      });
    }
    if (opts.plugins && opts.plugins.legend && opts.plugins.legend.labels && !opts.plugins.legend.labels.color) {
      opts.plugins.legend.labels.color = tokens.cText2;
    }
    return cfg;
  }

  global.SMPLSkin = {
    SKINS: SKINS,
    apply: apply,
    init: init,
    chartSkinTokens: chartSkinTokens,
    patchChartCfg: patchChartCfg,
  };
})(window);
