# Driver / attribution claim verify (live on primary AI paths)

> **Not SOC 2 certification.** Helper + path wiring. Citation verify + `_sources` warehouse tags: [ai_claim_verify.md](./ai_claim_verify.md).  
> Numeric claim-verify remains required and is **not sufficient** alone.

---

## Why numeric-only is not enough

Correct dollars with the wrong causal story still ship bad board narrative. Attribution allowlist catches that.

---

## Multi-driver AND/comma rule (this increment)

When a causal phrase joins multiple drivers with `and` / commas, **every** named part must be on `allowed_drivers`.

| Phrase | Allowlist | Result |
|--------|-----------|--------|
| driven by expansion | expansion | pass |
| driven by expansion and churn | expansion, churn | pass |
| driven by expansion and three enterprise upsells | expansion only | **fail** (`partial_allowlist`) |
| driven by expansion, contraction, and churn | expansion, churn | **fail** (`partial_allowlist`) |

Previously any single allowlisted token inside the phrase was enough.

Code: `attribution_verify._split_driver_conjuncts`, `_match_claim`.

---

## What shipped

| Piece | Status |
|-------|--------|
| Helper + commentary / Prompt 2 / Prompt 5 / board / Copilot | Live (prior) |
| Deal-count / logo / dominance | Live (prior) |
| Multi-driver AND/comma require-all | **Live this increment** |

**Empty allowlist + causal claims → fail closed.**

---

## Matt review checklist

- [ ] Confirm multi-driver require-all is the right bar
- [ ] Confirm **$1.00** numeric bar unchanged
- [ ] Merge when review OK — not SOC 2 certified

---

_End of attribution claim-verify_
