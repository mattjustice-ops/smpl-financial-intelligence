/**
 * Load pipeline SRC (actuals, opp_pipeline, renewals) from Forecast Engine demo seed.
 * Board Platform uses this; Forecast Engine registers SRC inline.
 */
(function (g) {
  "use strict";

  if (g.SMPL_PIPELINE_SRC && g.SMPL_PIPELINE_SRC.opp_pipeline) return;

  function parseJsObject(source) {
    return new Function("return (" + source + ");")();
  }

  function extractSrcLiteral(html) {
    var marker = "const SRC=";
    var start = html.indexOf(marker);
    if (start < 0) return null;
    var brace = html.indexOf("{", start);
    if (brace < 0) return null;
    var depth = 0;
    var inStr = false;
    var strCh = "";
    var esc = false;
    for (var i = brace; i < html.length; i++) {
      var c = html[i];
      if (inStr) {
        if (esc) {
          esc = false;
          continue;
        }
        if (c === "\\") {
          esc = true;
          continue;
        }
        if (c === strCh) inStr = false;
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
        if (depth === 0) {
          if (html[i + 1] === ";") return html.slice(brace, i + 1);
          return null;
        }
      }
    }
    return null;
  }

  try {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/forecast-engine/index.html", false);
    xhr.send();
    if (xhr.status < 200 || xhr.status >= 300) {
      throw new Error("forecast-engine index HTTP " + xhr.status);
    }
    var html = xhr.responseText;
    var srcLiteral = extractSrcLiteral(html);
    if (!srcLiteral) {
      throw new Error("could not parse SRC from forecast-engine index");
    }
    var full = parseJsObject(srcLiteral);
    g.SMPL_PIPELINE_SRC = {
      actuals: full.actuals || {},
      opp_pipeline: full.opp_pipeline || {},
      renewals: full.renewals || {},
    };
    if (g.console && g.console.info) {
      g.console.info("[smpl-bootstrap-pipeline] loaded pipeline SRC from /forecast-engine/index.html");
    }
  } catch (err) {
    console.warn("[smpl-bootstrap-pipeline] failed to load pipeline SRC", err);
  }
})(typeof window !== "undefined" ? window : globalThis);
