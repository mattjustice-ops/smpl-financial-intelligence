"""Copy V0 board HTML into frontend/public/board/index.html and apply SMPL patches."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = Path(r"c:\Users\mattj\Downloads\SMPL_Board_Platform_June2026 (10).html")
DST = REPO / "frontend" / "public" / "board" / "index.html"

HYDRATION = """
<script>
/* Live warehouse hydration — same-origin proxy (Forecast Engine pattern). */
(function () {
  let SMPL_BOARD_TAB = "exec";

  const origShow = window.show;
  if (typeof origShow === "function") {
    window.show = function (name, btn) {
      SMPL_BOARD_TAB = name;
      return origShow(name, btn);
    };
  }

  function setWarehouseStatus(text, tone) {
    const el = document.getElementById("warehouseStatus");
    if (!el) return;
    el.textContent = text;
    el.style.color =
      tone === "ok" ? "var(--teal)" : tone === "warn" ? "var(--amber)" : "var(--text2)";
  }

  async function smplOrgId() {
    const q = new URLSearchParams(window.location.search);
    if (q.get("organization_id")) return q.get("organization_id");
    try {
      const s = await fetch("/api/auth/session", { credentials: "include" });
      const j = await s.json();
      return j?.user?.activeOrganizationId || null;
    } catch (_) {
      return null;
    }
  }

  async function smplBoardHydrate() {
    const orgId = await smplOrgId();
    if (!orgId) {
      setWarehouseStatus("Demo data", "warn");
      return;
    }
    setWarehouseStatus("Syncing live warehouse…", "warn");
    try {
      const params = new URLSearchParams({
        organization_id: orgId,
        include_validation: "false",
        include_three_statement: "false",
      });
      const res = await fetch("/api/v1/board-platform/payload?" + params.toString(), {
        credentials: "include",
      });
      if (!res.ok) {
        setWarehouseStatus("Demo data (API " + res.status + ")", "warn");
        return;
      }
      const data = await res.json();
      window.SMPL_BOARD_PAYLOAD = data;
      const orgName = data.meta?.organization_name;
      setWarehouseStatus(orgName ? "Live · " + orgName : "Live warehouse", "ok");
      const close = data.meta?.close_month;
      if (close && typeof CLOSE_MONTH !== "undefined") {
        /* keep demo period labels unless we add full hydration later */
      }
    } catch (err) {
      console.warn("Board hydrate error", err);
      setWarehouseStatus("Demo data (offline)", "warn");
    }
  }

  window.addEventListener("load", function () {
    smplBoardHydrate();
  });
})();
</script>
"""


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Source not found: {SRC}")

    html = SRC.read_text(encoding="utf-8")

    if 'id="warehouseStatus"' not in html:
        html = html.replace(
            '<span class="period-badge" id="periodBadge"></span>',
            '<span class="period-badge" id="warehouseStatus">Demo data</span>\n'
            '    <span class="period-badge" id="periodBadge"></span>',
        )

    export_block = """const BOARD_EXPORTS = {
  boardReview: '/board/exports/SMPL_Board_Review_Q2_2026.pptx',
  mdaPackage: '/board/exports/SMPL_MDA_Package_June2026.xlsx',
};
function openBoardExport(url) {
  const opened = window.open(url, '_blank', 'noopener,noreferrer');
  if (!opened) window.location.assign(url);
}
function globalMDA(){ openBoardExport(BOARD_EXPORTS.boardReview); }
function varComm(){ openBoardExport(BOARD_EXPORTS.mdaPackage); }"""

    html = html.replace(
        "function globalMDA(){window.open('SMPL_MDA_Package_May2026.xlsx');}\n"
        "function varComm(){window.open('SMPL_MDA_Package_May2026.xlsx');}",
        export_block,
    )

    if "smplBoardHydrate" not in html:
        html = html.replace("</body>", HYDRATION + "\n</body>")

    if "Where We Stand" not in html:
        raise SystemExit("Source HTML missing V0 executive summary — wrong file?")

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(html, encoding="utf-8")
    print(f"Wrote {DST} ({len(html)} chars)")


if __name__ == "__main__":
    main()
