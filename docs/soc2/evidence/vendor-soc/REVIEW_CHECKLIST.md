# Vendor SOC report — post-download review checklist

> Use **once per PDF** after it lands in the private store.  
> Sanitized outcomes go in [TRACKER.md](./TRACKER.md). Do **not** commit the PDF or paste NDA-secret excerpts.  
> Readiness only — **not** SOC 2 certified.

**Private store (preferred):** `~/Documents/SMPL/soc2/vendor-reports/`  
**Optional gitignored:** `docs/soc2/evidence/vendor-soc/private/`

---

## Per-report review (copy a block per vendor)

### Vendor: _______________ · File: _______________ · Review date: _______________

| # | Check | Result |
|---|--------|--------|
| 1 | File is in **private store** (not staged for git) | [ ] Yes |
| 2 | **Report type** matches target (usually SOC 2 **Type II**) — not marketing PDF alone | Type: _______________ |
| 3 | **Period covered** (start → end) or report date | Period: _______________ |
| 4 | Period current enough? If ended >~3 months ago, **bridge letter** pulled or noted missing | [ ] OK / [ ] Bridge filed / [ ] Gap noted |
| 5 | **Trust Services Criteria** in report (as applicable) | _______________ |
| 6 | **Scope** matches how SMPL uses the service (hosting / DB / payments / LLM / email / CI) | [ ] OK / [ ] Question — note: ____ |
| 7 | **Opinion** — unmodified / qualified / other (one word; no pasted findings) | _______________ |
| 8 | **Material exceptions** relevant to SMPL use? (Y/N + one sanitized line max) | _______________ |
| 9 | Auditor / firm name (optional; from cover page) | _______________ |
| 10 | Tracker status ready to set | [ ] `received` → [ ] `reviewed` |

**Sanitized tracker note (safe for git):**  
`Reviewed YYYY-MM-DD — Type II period ____ — scope OK / note ____ — OK for use under NDA`

**Subprocessors inventory:** Flip “Vendor report collected?” in [02_subprocessors.md](../../02_subprocessors.md) only after this skim is done (`reviewed`).

---

## Bridge letter (when needed)

Pull a bridge / gap letter from the same Trust Center when:

- Type II period ended and the next report is not out yet, **and**
- A customer / CPA questionnaire asks for current coverage.

Store beside the Type II PDF. Note both files in TRACKER. Absence of a bridge letter is a **gap to note**, not a reason to invent one.

---

## Explicit non-goals

- Do not paste exception tables, control descriptions, or customer lists into git.
- Do not mark `reviewed` without completing rows 1–8 above (even lightly).
- Do not treat public SOC 3 as satisfying a Type II tracker row.
