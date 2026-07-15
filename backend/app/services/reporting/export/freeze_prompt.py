"""Shared freeze-pack prompt formatting for board AI surfaces.

Quality rule: never truncate the freeze pack here unless the caller opts in.
Freeze blobs are already capped at build time (~48k); secondary cuts hurt commentary.
"""

from __future__ import annotations


def format_freeze_prompt_block(
    *,
    context_text: str | None,
    context_as_of: str | None = None,
    status: str | None = None,
    stale: bool = False,
    max_chars: int | None = None,
    number_guidance: str | None = None,
) -> str:
    """Render the CLOSE FREEZE CONTEXT preamble used by Prompt 2 / 5 / regenerate."""
    body = (context_text or "").strip()
    if not body:
        return ""

    status_u = (status or ("STALE" if stale else "COMPLETE")).upper()
    label = (
        "STALE — last complete freeze (treat narrative/as-of as frozen; prefer payload numbers)"
        if stale or status_u == "STALE"
        else "COMPLETE close freeze pack"
    )
    as_of = context_as_of or "unknown"
    if max_chars is not None and max_chars > 0 and len(body) > max_chars:
        body = body[:max_chars] + "\n…[freeze context truncated]"

    guidance = number_guidance or (
        "Use this freeze for narrative tone, drivers, and period framing. "
        "Copy slide / sheet numbers from the structured DATA PAYLOAD verbatim — do not invent figures."
    )
    return (
        "CLOSE FREEZE CONTEXT (authoritative labeled snapshot for commentary/as-of):\n"
        f"Context source: freeze ({label})\n"
        f"Freeze status: {status_u}\n"
        f"Context as of: {as_of}\n"
        f"{guidance}\n\n"
        f"{body}\n\n"
    )
