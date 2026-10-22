const assert = require("assert");
const fin = require("./financing-rounds.js");

const periods = [];
for (let m = 1; m <= 12; m++) periods.push("2026-" + String(m).padStart(2, "0"));
const close = "2026-06";

function debt(extra) {
  return Object.assign({
    month: "2026-08",
    instrument: "debt",
    gross: 20000000,
    fees: 500000,
    ratePct: 12,
    interestStart: "2026-08",
    warrantPct: 0,
  }, extra || {});
}

const equity = fin.effects([{ month: "2026-08", instrument: "equity", gross: 20000000, fees: 500000 }], periods, close);
assert.strictEqual(equity["2026-08"].financing, 19500000);
assert.strictEqual(equity["2026-08"].equityDelta, 19500000);
assert.strictEqual(equity["2026-08"].debtDelta, 0);
assert.strictEqual(equity["2026-08"].interest, 0);
assert.strictEqual(equity["2026-06"].financing, 0);

const drawn = fin.effects([debt()], periods, close);
assert.strictEqual(drawn["2026-08"].financing, 19500000);
assert.strictEqual(drawn["2026-08"].debtDelta, 19500000);
assert.strictEqual(drawn["2026-08"].interest, 195000);
assert.strictEqual(drawn["2026-09"].interest, 195000);
assert.strictEqual(drawn["2026-09"].debtBalance, 19500000);

const warrant = fin.effects([debt({ warrantPct: 10 })], periods, close)["2026-08"];
assert.strictEqual(warrant.debtDelta, 17550000);
assert.strictEqual(warrant.equityDelta, 1950000);
assert.strictEqual(warrant.interest, 175500);

const repaid = fin.effects([debt({ principalDue: 1000000, principalMonth: "2026-11" })], periods, close);
assert.strictEqual(repaid["2026-11"].financing, -1000000);
assert.strictEqual(repaid["2026-11"].debtBalance, 18500000);
assert.strictEqual(repaid["2026-12"].interest, 185000);

const closed = fin.normalizeRound(debt({ month: "2026-06" }), close);
assert.strictEqual(closed.ok, false);

const walk = fin.directWalk({
  periods: periods,
  closeMonth: close,
  floor: 10000000,
  actual: { "2026-06": { beginning_cash: 32000000, ending_cash: 30000000, collections: 100, payroll: 50, cash_floor: 10000000 } },
  forecast: {
    "2026-07": { collections: 1000000, payroll: 4000000, commission: 0, vendor: 0, tax: 0, interest: 0, other_operating: 0, capex: 0, financing: 9000000 },
    "2026-08": { collections: 1000000, payroll: 4000000, commission: 0, vendor: 0, tax: 0, interest: 0, other_operating: 0, capex: 0, financing: 0 },
    "2026-09": { collections: 1000000, payroll: 4000000, commission: 0, vendor: 0, tax: 0, interest: 0, other_operating: 0, capex: 0, financing: 0 },
  },
  rounds: [],
});
assert.strictEqual(walk.juneCash, 30000000);
assert.strictEqual(walk.unfunded[6].ending, 27000000);
assert.strictEqual(walk.unfunded[6].financing, 0);
assert.strictEqual(walk.funded[6].financing, 0);

console.log("financing-rounds selftest ok");
