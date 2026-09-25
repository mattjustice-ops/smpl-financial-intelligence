/**
 * Smoke: Mgmt P&L KPIs expose Sub/Svc/COGS from the same TS_DATA IS as Financial Statements.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const code = fs.readFileSync(
  path.join(__dirname, "../public/shared/board-data.js"),
  "utf8",
);

const sandbox = {
  console,
  CLOSE_MONTH: "2026-06",
  ACT_MONTHS_COUNT: 6,
  TS_DATA: {
    Actual: {
      periods: ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
      is: {
        "2026-06": {
          revenue: 7300000,
          sub_rev: 7100000,
          svc_rev: 200000,
          cogs: 2200000,
          gross_profit: 5100000,
          gm_pct: 0.7,
          sm: 2500000,
          rd: 1200000,
          ga: 800000,
          total_opex: 4500000,
          ebitda: 600000,
        },
      },
    },
    Budget: {
      periods: ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
      is: {
        "2026-06": {
          revenue: 7700000,
          sub_rev: 7460000,
          svc_rev: 240000,
          cogs: 2310000,
          gross_profit: 5390000,
          gm_pct: 0.7,
          sm: 2650000,
          rd: 1250000,
          ga: 860000,
          total_opex: 4760000,
          ebitda: 630000,
        },
      },
    },
  },
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

const pk = sandbox.boardPlKpis();
const checks = [
  ["sub", Math.abs(pk.sub - 7.1) < 1e-9],
  ["svc", Math.abs(pk.svc - 0.2) < 1e-9],
  ["rev", Math.abs(pk.rev - 7.3) < 1e-9],
  ["cogs", Math.abs(pk.cogs - 2.2) < 1e-9],
  ["gp", Math.abs(pk.gp - 5.1) < 1e-9],
  ["sub+svc=rev", Math.abs(pk.sub + pk.svc - pk.rev) < 1e-9],
  ["rev-cogs=gp", Math.abs(pk.rev - pk.cogs - pk.gp) < 1e-9],
];
const failed = checks.filter((c) => !c[1]);
if (failed.length) {
  console.error("FAIL", failed.map((f) => f[0]), pk);
  process.exit(1);
}
console.log("ok boardPlKpis Sub/Svc/COGS tie to IS", {
  sub: pk.sub,
  svc: pk.svc,
  rev: pk.rev,
  cogs: pk.cogs,
  gp: pk.gp,
});
