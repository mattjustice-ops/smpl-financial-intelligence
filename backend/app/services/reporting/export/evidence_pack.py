"""Customer-facing Evidence Pack for MD&A deck + variance exports.

Same check IDs / $1 bar language as the Board Continuity tab. Soft-warn fidelity
never blocks export, but failures are visible in the pack.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any, Mapping


def build_evidence_pack(
    *,
    as_of_period: str,
    export_kind: str,
    pptx_source: str | None = None,
    freeze_status: str | None = None,
    freeze_as_of: str | None = None,
    validation_status: str | None = None,
    post_render: Mapping[str, Any] | None = None,
    narrative_summary: str | None = None,
    narrative_issues: int | None = None,
    claim_summary: str | None = None,
    attribution_summary: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured Evidence Pack (JSON) + HTML companion string."""
    pr = dict(post_render or {})
    pack: dict[str, Any] = {
        "schema": "smpl.evidence_pack.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_period": as_of_period,
        "export_kind": export_kind,
        "pptx_source": pptx_source,
        "freeze_status": freeze_status,
        "freeze_as_of": freeze_as_of,
        "validation_status": validation_status,
        "tolerance_actuals_usd": 1.0,
        "claim": (
            "Closed-period material KPIs are engine-computed, tagged to _sources, "
            "and checked against named ties at $1. AI narrates from that package — "
            "it does not invent the dollars."
        ),
        "not_claimed": [
            "SOC 2 certified",
            "Every chart datapoint cited at render (Phase 4)",
            "Import/close hard identification complete (Phase 4)",
        ],
        "post_render_ok": pr.get("ok"),
        "post_render_summary": pr.get("summary"),
        "post_render_failures": pr.get("numeric_failures"),
        "anchor_failures": pr.get("anchor_failures"),
        "narrative_issues": narrative_issues if narrative_issues is not None else pr.get("narrative_issues"),
        "narrative_summary": narrative_summary or pr.get("narrative_summary"),
        "claim_summary": claim_summary,
        "attribution_summary": attribution_summary,
        "slide_count": pr.get("slide_count"),
        "text_shape_count": pr.get("text_shape_count"),
    }
    if extra:
        pack.update({str(k): v for k, v in extra.items()})
    pack["summary"] = _one_line_summary(pack)
    pack["html"] = render_evidence_pack_html(pack)
    return pack


def _one_line_summary(pack: Mapping[str, Any]) -> str:
    parts = [
        f"{pack.get('export_kind') or 'export'} · {pack.get('as_of_period') or ''}",
    ]
    if pack.get("post_render_ok") is True:
        parts.append("post-render pass")
    elif pack.get("post_render_ok") is False:
        parts.append("post-render soft-warn")
    ni = pack.get("narrative_issues")
    if ni:
        parts.append(f"{ni} narrative issue(s)")
    af = pack.get("anchor_failures")
    if af:
        parts.append(f"{af} anchor miss(es)")
    return " · ".join(str(p) for p in parts if p)


def render_evidence_pack_html(pack: Mapping[str, Any]) -> str:
    """One-page HTML companion — same stamps Continuity tab shows."""

    def esc(v: Any) -> str:
        return html.escape(str(v if v is not None else "—"))

    rows = [
        ("As-of period", pack.get("as_of_period")),
        ("Export", pack.get("export_kind")),
        ("Generated (UTC)", pack.get("generated_at")),
        ("Freeze status", pack.get("freeze_status")),
        ("Freeze as-of", pack.get("freeze_as_of")),
        ("Validation", pack.get("validation_status")),
        ("PPTX source", pack.get("pptx_source")),
        ("TOL_ACTUALS", f"${pack.get('tolerance_actuals_usd', 1):.2f}"),
        ("Post-render", pack.get("post_render_summary") or pack.get("post_render_ok")),
        ("Anchor misses", pack.get("anchor_failures")),
        ("Narrative issues", pack.get("narrative_issues")),
        ("Narrative", pack.get("narrative_summary")),
        ("Claim verify", pack.get("claim_summary")),
        ("Attribution", pack.get("attribution_summary")),
        ("Slides / text shapes", f"{pack.get('slide_count')} / {pack.get('text_shape_count')}"),
    ]
    body_rows = "".join(
        f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows if v is not None and v != ""
    )
    not_claimed = "".join(f"<li>{esc(x)}</li>" for x in (pack.get("not_claimed") or []))
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SMPL Evidence Pack</title>
<style>
body{{font-family:ui-sans-serif,system-ui,Segoe UI,sans-serif;padding:28px;background:#0f1410;color:#dde8d6;max-width:820px;margin:0 auto}}
h1{{font-size:20px;margin:0 0 8px}} h2{{font-size:14px;margin:24px 0 8px;color:#9aab92}}
p,li{{font-size:13px;line-height:1.5;color:#c5d4bc}}
table{{border-collapse:collapse;width:100%;margin-top:12px}}
th,td{{border:1px solid #2e3f31;padding:8px 10px;font-size:12px;text-align:left;vertical-align:top}}
th{{width:28%;color:#9aab92;font-weight:600}}
.claim{{background:#1a241c;border:1px solid #2e3f31;padding:12px 14px;border-radius:8px;margin:16px 0}}
.foot{{margin-top:28px;font-size:11px;color:#72826a}}
</style></head><body>
<h1>SMPL.ai — Evidence Pack</h1>
<p>{esc(pack.get("summary"))}</p>
<div class="claim"><strong>Defendable claim</strong><br>{esc(pack.get("claim"))}</div>
<table><tbody>{body_rows}</tbody></table>
<h2>Not claimed (Phase 4)</h2>
<ul>{not_claimed}</ul>
<p class="foot">Not SOC 2 certified. Soft-warn fidelity does not block export — failures are disclosed here and on the Board Continuity tab. Check IDs align with client A–F / cash spine C1–C5 where those ran on the Board.</p>
</body></html>
"""


def post_render_to_dict(result: Any) -> dict[str, Any]:
    """Normalize DeckPostRenderResult (or duck-typed) into JSON-safe dict."""
    if result is None:
        return {}
    if isinstance(result, Mapping):
        return dict(result)
    numeric = getattr(result, "numeric", None)
    anchors = getattr(result, "anchors", None)
    narrative = getattr(result, "narrative", None)
    return {
        "ok": bool(getattr(result, "ok", False)),
        "summary": getattr(result, "summary", lambda: "")(),
        "numeric_failures": len(getattr(numeric, "failures", []) or []),
        "anchor_failures": len(getattr(anchors, "failures", []) or []),
        "narrative_issues": len(getattr(narrative, "issues", []) or []),
        "narrative_summary": getattr(narrative, "summary", lambda: "")(),
        "slide_count": getattr(result, "slide_count", None),
        "text_shape_count": getattr(result, "text_shape_count", None),
    }


def dumps_evidence_pack_json(pack: Mapping[str, Any]) -> str:
    slim = {k: v for k, v in pack.items() if k != "html"}
    return json.dumps(slim, indent=2, default=str)
