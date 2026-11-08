import fs from "node:fs";
import vm from "node:vm";

const code = fs.readFileSync(new URL("../public/shared/board-continuity.js", import.meta.url), "utf8");
const context = { console };
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(code, context);
const built = context.SMPLContinuity.datasetBuilt;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(built("2026-11-08T00:38:48.396852+00:00") === "Nov 7, 2026, 4:38 PM", built("2026-11-08T00:38:48.396852+00:00"));
assert(built("2026-09-07T19:36:31.428955+00:00") === "Sep 7, 2026, 11:36 AM", built("2026-09-07T19:36:31.428955+00:00"));
assert(built("") === "—", built(""));
assert(code.indexOf('id="veRefreezeBtn"') > code.indexOf("<strong>Freeze</strong>"), "the dataset button sits with Freeze");
assert(code.split('id="veRefreezeBtn"').length === 2, "the dataset button is only on the Freeze row");

const openMap = context.SMPLContinuity.renderMappingHtml({
  mapping_material_open_count: 2,
  monthly_align: { mapping_clear: false },
  mapping_queue: [],
  management_lines: [],
});
assert(openMap.indexOf("Accounts Mapped") > 0, "mapping shows the accounts check");
assert(openMap.indexOf("2 accounts still need a map.") > 0, openMap);
assert(openMap.indexOf('class="ve-check ve-bad">!</span>') > 0, "an open queue is not checked off");
assert(openMap.indexOf("<th>Acct</th>") > 0, "column heads stay");

const oneMap = context.SMPLContinuity.renderMappingHtml({
  mapping_material_open_count: 1,
  monthly_align: { mapping_clear: false },
  mapping_queue: [],
  management_lines: [],
});
assert(oneMap.indexOf("1 account still needs a map.") > 0, oneMap);

const clearMap = context.SMPLContinuity.renderMappingHtml({
  mapping_material_open_count: 0,
  monthly_align: { mapping_clear: true },
  mapping_queue: [],
  management_lines: ["ga"],
});
assert(clearMap.indexOf("Every account is mapped.") > 0, clearMap);
assert(clearMap.indexOf('class="ve-check ve-ok">✓</span>') > 0, "a clear queue is checked off");
assert(context.SMPLContinuity.renderMappingHtml(null).indexOf("Accounts Mapped") < 0, "the check waits until status loads");

console.log("ok");
