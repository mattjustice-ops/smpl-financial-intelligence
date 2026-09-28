/**
 * Load Board-compatible demo TS_DATA + WF_TABLE for Forecast Engine.
 * Parses public/board/index.html (supports var/const/let declarations).
 */
(function (g) {
  "use strict";

  if (g.SMPL_DEMO_TS_DATA && g.SMPL_DEMO_WF_TABLE) {
    if (g.console && g.console.info) {
      g.console.info("[smpl-bootstrap-demo] demo seed ready (static seed file)");
    }
    return;
  }

  function parseJsObject(source) {
    return new Function("return (" + source + ");")();
  }

  function extractJsObject(html, varName) {
    var prefixes = ["var " + varName, "const " + varName, "let " + varName];
    var start = -1;
    for (var i = 0; i < prefixes.length; i++) {
      start = html.indexOf(prefixes[i]);
      if (start >= 0) break;
    }
    if (start < 0) return null;
    var eq = html.indexOf("=", start);
    if (eq < 0) return null;
    var brace = html.indexOf("{", eq);
    if (brace < 0) return null;
    var depth = 0;
    var inStr = false;
    var strCh = "";
    for (var j = brace; j < html.length; j++) {
      var c = html[j];
      var prev = html[j - 1];
      if (inStr) {
        if (c === strCh && prev !== "\\") inStr = false;
        continue;
      }
      if (c === '"' || c === "'") {
        inStr = true;
        strCh = c;
        continue;
      }
      if (c === "{") depth++;
      else if (c === "}") {
        depth--;
        if (depth === 0) return html.slice(brace, j + 1);
      }
    }
    return null;
  }

  function registerDemo(tsData, wfTable) {
    if (!tsData || !wfTable) return false;
    g.SMPL_DEMO_TS_DATA = tsData;
    g.SMPL_DEMO_WF_TABLE = wfTable;
    if (g.SMPLOutlook && g.SMPLOutlook.registerDemoData) {
      g.SMPLOutlook.registerDemoData(tsData, wfTable);
    }
    if (g.console && g.console.info) {
      g.console.info("[smpl-bootstrap-demo] demo seed ready (TS_DATA + WF_TABLE)");
    }
    return true;
  }

  function loadFromBoardHtml(html) {
    var tsSource =
      extractJsObject(html, "TS_DATA") || extractJsObject(html, "SMPL_DEMO_TS_DATA");
    var wfSource = extractJsObject(html, "SMPL_DEMO_WF_TABLE");
    if (!tsSource || !wfSource) {
      throw new Error("could not extract TS_DATA or SMPL_DEMO_WF_TABLE from board index");
    }
    return registerDemo(parseJsObject(tsSource), parseJsObject(wfSource));
  }

  try {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/board/index.html", false);
    xhr.send();
    if (xhr.status < 200 || xhr.status >= 300) {
      throw new Error("board index HTTP " + xhr.status);
    }
    loadFromBoardHtml(xhr.responseText);
  } catch (err) {
    console.warn("[smpl-bootstrap-demo] failed to load board demo constants", err);
  }
})(typeof window !== "undefined" ? window : globalThis);
