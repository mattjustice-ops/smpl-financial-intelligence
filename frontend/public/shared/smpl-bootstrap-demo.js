/**
 * Load Board-compatible demo TS_DATA + WF_TABLE for Forecast Engine (and any surface
 * that does not embed them inline). Parses public/board/index.html — same source Board uses.
 */
(function (g) {
  "use strict";

  if (g.SMPL_DEMO_TS_DATA && g.SMPL_DEMO_WF_TABLE) return;

  function parseJsObject(source) {
    return new Function("return (" + source + ");")();
  }

  try {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/board/index.html", false);
    xhr.send();
    if (xhr.status < 200 || xhr.status >= 300) {
      throw new Error("board index HTTP " + xhr.status);
    }
    var html = xhr.responseText;
    var wfMatch =
      html.match(/const WF_TABLE = (\{[\s\S]*?\n\});[\r\n]+window\.SMPL_DEMO_WF_TABLE/) ||
      html.match(/const WF_TABLE = (\{[\s\S]*?\n\});/);
    var tsMatch =
      html.match(/const TS_DATA=(\{[\s\S]*?\});[\r\n]+window\.SMPL_DEMO_TS_DATA/) ||
      html.match(/const TS_DATA=(\{[\s\S]*?\});[\r\n]+function tsGetPeriods/);
    if (!wfMatch || !tsMatch) {
      throw new Error("could not parse WF_TABLE / TS_DATA from board index");
    }
    g.SMPL_DEMO_WF_TABLE = parseJsObject(wfMatch[1]);
    g.SMPL_DEMO_TS_DATA = parseJsObject(tsMatch[1]);
    if (g.SMPLOutlook && g.SMPLOutlook.registerDemoData) {
      g.SMPLOutlook.registerDemoData(g.SMPL_DEMO_TS_DATA, g.SMPL_DEMO_WF_TABLE);
    }
    if (g.console && g.console.info) {
      g.console.info("[smpl-bootstrap-demo] loaded demo constants from /board/index.html");
    }
  } catch (err) {
    console.warn("[smpl-bootstrap-demo] failed to load board demo constants", err);
  }
})(typeof window !== "undefined" ? window : globalThis);
