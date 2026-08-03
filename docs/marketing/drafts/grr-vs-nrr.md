---
seoTitle: GRR vs NRR: What the Board Actually Hears | SMPL.ai
seoDescription: GRR vs NRR explained for SaaS boards — what each retention metric measures, the questions directors ask, and how to report both without confusing the room.
slug: grr-vs-nrr
title: GRR vs NRR: What the Board Actually Hears
category: ARR & revenue
status: draft — ready to publish when Matt approves
---

# GRR vs NRR: What the Board Actually Hears

Two retention percentages sit on almost every SaaS board deck. One looks healthier than the other. Both are usually correct. And the gap between them is where directors decide whether finance understands the business — or is dressing up churn with upsell.

**Gross revenue retention (GRR)** and **net revenue retention (NRR)** answer different questions. Boards that hear only one of them hear an incomplete story. This piece is metric literacy for finance leaders who have to put both numbers in front of a room that will ask what they mean.

If you need the short definitions first: see [NRR](/glossary/nrr) and [GRR](/glossary/grr) in the glossary. The rest of this article is about what those numbers *sound like* in a board meeting — and how to keep the conversation honest.

## The one-sentence difference

**GRR** asks: of the ARR we started with, how much did we keep after contraction and churn — *before* giving ourselves credit for expansion?

**NRR** asks: of the ARR we started with, where did we end after contraction, churn, *and* expansion?

Same starting cohort. Same period. Different credit for growth inside the base.

That is why NRR can sit at 115% while GRR sits at 88%. Expansion covered the holes. The board needs both percentages, or it will invent a story that flatters one and ignores the other.

## How the math actually works

Both metrics start from a cohort: the customers (and their ARR) you had at the beginning of the period. New logos acquired during the period do **not** belong in classic NRR/GRR. They belong in new ARR on the [ARR waterfall](/blog/arr-waterfall-vs-gaap-revenue).

From that starting ARR:

- Subtract **contraction** (downgrades, seat loss, tier moves down).
- Subtract **churn** (full logo or ARR exits).
- For **NRR only**, add **expansion** (upsells, cross-sells, seat growth, price increases on renewals).

A clean way to say it:

- **GRR** = (starting ARR − contraction − churn) ÷ starting ARR  
- **NRR** = (starting ARR − contraction − churn + expansion) ÷ starting ARR  

If your waterfall cannot reproduce both from the same movements, the retention slide is not finished. GRR and NRR are not separate models. They are two readings of one bridge — see also [waterfall](/glossary/waterfall) and [ARR](/glossary/arr).

### A simple example

Start the quarter with $10.0M ARR in the existing base.

| Movement | Amount |
| --- | ---: |
| Expansion | +$1.8M |
| Contraction | −$0.7M |
| Churn | −$0.9M |

Ending ARR from that cohort = $10.0M + $1.8M − $0.7M − $0.9M = **$10.2M**.

- **NRR** = $10.2M ÷ $10.0M = **102%**  
- **GRR** = ($10.0M − $0.7M − $0.9M) ÷ $10.0M = **84%**

NRR says the installed base grew slightly. GRR says you kept 84 cents of every starting dollar before upsell. Both are true. Presenting only 102% invites the wrong celebration.

## What the board actually hears

Directors do not hear formulas. They hear narratives.

### When you show NRR alone

They hear: *the customer base is getting healthier.* Expansion is doing work. Land-and-expand is working. Maybe sales efficiency looks better than it is, because growth inside the base is doing some of what new logo was supposed to do.

That story can be right. It can also hide a retention problem under a strong upsell engine. A company can post 120% NRR and still be losing logos or shrinking accounts underneath — GRR tells you whether that is happening.

### When you show GRR alone

They hear: *how sticky is the product without commercial heroics?* GRR is the colder number. It ignores the flattering expansion line. Boards that care about durability — especially later-stage or capital-constrained boards — often lean on GRR when they smell a growth story that depends too much on selling more to the customers who stayed.

Show GRR alone and you underplay expansion quality. A 90% GRR with weak expansion is a different business from a 90% GRR with a path to 115% NRR.

### When you show both — and own the gap

They hear: *finance can separate retention from expansion.* The gap between NRR and GRR is not a reconciliation bug. It **is** expansion's contribution to the base. A wide gap means growth is concentrated in customers who stayed. A narrow gap with high GRR means you keep what you have and expand modestly. A narrow gap with low GRR means you are not keeping the base — and expansion is not saving you.

That is the conversation worth having. Not “is NRR good?” in isolation.

## Board questions you should be ready for

These come up whether or not they appear on the slide.

1. **“Is NRR above 100% because we retained customers — or because a few whales expanded?”**  
   Be ready to show concentration: top-10 expansion vs the rest of the base. Cohort NRR without a concentration note is easy to misread.

2. **“What would GRR be if we excluded involuntary churn / bankruptcies / one large logo?”**  
   Have a policy before the meeting. Adjustments are fine when disclosed. Silent exclusions destroy trust.

3. **“Why did GRR fall while NRR held?”**  
   Classic pattern: churn or contraction worsened, and expansion plugged the hole. That is an early warning, not a win.

4. **“Are these logo-weighted or ARR-weighted?”**  
   Almost all board NRR/GRR should be **ARR-weighted** (dollar retention). Logo retention is a different chart. Mixing the two mid-answer is how meetings derail.

5. **“Does this match the waterfall on the prior slide?”**  
   If ending ARR, expansion, contraction, and churn on the waterfall cannot regenerate the retention percentages, stop. Fix the pack before you defend a narrative. Related failure mode: when [ARR, cash, and the P&L tell different stories](/blog/saas-board-reporting-arr-cash-pl) because each came from a different export.

6. **“Is starting ARR the same population RevOps uses for renewal forecasts?”**  
   Definition drift between finance and RevOps is one of the fastest ways to lose a room. Align the cohort rules in writing.

## Common ways teams talk past each other

**CRM ARR vs billing ARR.** If Sales’ expansion sits in the CRM and Finance’s retention sits in billing, NRR and GRR will disagree with bookings commentary. The metrics are only as trustworthy as the [source definitions behind ARR](/blog/arr-waterfall-vs-gaap-revenue) — and as a [documented ARR methodology](/blog/arr-governance) the whole company can reuse. Billing vs CRM ARR deserves its own deep dive; until then, pick one governed definition for board retention and stick to it.

**Including new logos in NRR.** That inflates the rate and breaks comparability. New business is a growth line, not a retention credit.

**Price increases counted as expansion without disclosure.** Legitimate in many ARR policies — but boards should know when NRR is partly a pricing story.

**Multi-year ramps and delayed starts.** Ramp deals can look like expansion when they are really contracted schedule. Your ARR policy has to say which is which, consistently, every close.

**GRR capped at 100%.** By construction GRR cannot exceed 100% if expansion is excluded. If someone shows GRR above 100%, the definition is wrong or expansion leaked into the numerator.

## How to present GRR and NRR in the pack

A practical pattern that keeps the board oriented:

1. **Waterfall first** — beginning ARR → new / expansion / contraction / churn → ending ARR.  
2. **Retention second** — GRR and NRR for the same period, same cohort, same movements.  
3. **One sentence on the gap** — “NRR is 108%; GRR is 91%; the 17-point spread is expansion in the existing base, concentrated in enterprise.”  
4. **Optional: segment** — enterprise vs mid-market GRR/NRR often matters more than the blended number.

Keep commentary tied to the same figures as the table. If the narrative says expansion saved the quarter, the expansion dollar amount on the waterfall should be the one in the sentence. That is the same trust standard as the rest of [SaaS board reporting](/blog/saas-board-reporting-arr-cash-pl): traceable numbers beat a polished story that cannot be checked.

When CFOs start hearing “which number is correct?” about retention, the root cause is usually conflicting definitions — not a missing chart. The fix is one cohort, one set of movements, two clearly labeled rates. See also [why CFOs stop trusting their own numbers](/blog/why-cfos-stop-trusting-their-numbers).

## What “good” looks like (without fake benchmarks)

There is no universal “good NRR.” Segment, contract length, and growth stage change the bar. What *does* travel across companies:

- **Both metrics every period**, not NRR only in good quarters.  
- **Stable definitions** quarter to quarter — if the policy changes, call it out.  
- **Reproducibility** — two people using the same close package get the same GRR and NRR.  
- **Segment honesty** — a blended 115% NRR that is 140% enterprise and 85% SMB is a different business than a uniform 115%.

Treat retention as governed reporting, not a slide decoration. The board is not asking for a prettier retention chart. They are asking whether the base is durable — and whether expansion is real growth or cover for leakage.

## How SMPL.ai approaches this

SMPL.ai is SaaS FP&A software built so ARR movements, NRR, and GRR come from one reconciled model — billing, CRM, and the general ledger read into a consistent operating picture — rather than three spreadsheets refreshed on three different days.

SMPL reads and reconciles your systems of record; it does not post transactions back to your ERP. Retention rates are computed from the same waterfall movements you show the board, so the percentages and the bridge stay aligned. AI narrative, when you use it, should explain those computed movements — not invent a retention story the data does not support.

We do not claim a certification status here. Trust in board metrics comes from definitions, reconciliation, and the ability to drill from the percentage to the customers underneath.

## See both numbers on one bridge

If your board pack still treats NRR as the headline and GRR as a footnote — or the other way around — the next meeting is a good time to put them side by side on the same cohort.

[Book a demo](https://www.smpl-ai.com/book-demo) and we will walk GRR and NRR from the same ARR waterfall on data that looks like yours.

---

### Alternate titles

1. NRR vs GRR: The Retention Slide Boards Misread  
2. What Gross and Net Revenue Retention Actually Mean in a Board Meeting  
3. Stop Reporting NRR Without GRR  

### FAQ seeds (for later SEO / FAQ block)

1. What is the difference between GRR and NRR?  
2. Can GRR be higher than NRR?  
3. Should new customers be included in NRR?  
4. Why is my NRR above 100% but GRR below 90%?  
5. How do GRR and NRR tie to the ARR waterfall?
