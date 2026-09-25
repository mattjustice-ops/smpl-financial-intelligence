# GSC indexing — Glossary hub (Sep 2026)

**Property:** `https://www.smpl-ai.com/` (or `sc-domain:smpl-ai.com`)  
**Why now:** Glossary terms were expanded past the ~800-char index floor and are in the live sitemap. Google may still show old `noindex` / “crawled – currently not indexed” until URL Inspection refreshes them.

Sitemap already lists **29** glossary URLs (thin stubs like FISoD excluded):  
https://www.smpl-ai.com/sitemap.xml

---

## Do this in Search Console (5–10 min)

1. Open [Google Search Console](https://search.google.com/search-console) → select the SMPL property.
2. Left nav → **Sitemaps** → submit (or re-submit):  
   `https://www.smpl-ai.com/sitemap.xml`
3. Top bar → **URL Inspection** → paste each **Priority** URL below → **Request indexing**.  
   Wait for each to finish before the next (Google rate-limits).
4. Optional: **Pages** → filter “Crawled – currently not indexed” / “Excluded by ‘noindex’ tag” and confirm old glossary stubs clear over 1–2 weeks.

### Priority (request these first)

| URL | Why |
| --- | --- |
| https://www.smpl-ai.com/glossary | Hub |
| https://www.smpl-ai.com/glossary/arr | P0 |
| https://www.smpl-ai.com/glossary/waterfall | P0 |
| https://www.smpl-ai.com/glossary/nrr | P0 |
| https://www.smpl-ai.com/glossary/grr | P0 |
| https://www.smpl-ai.com/glossary/billing-arr | New / reconciliation |
| https://www.smpl-ai.com/glossary/crm-arr | New / reconciliation |
| https://www.smpl-ai.com/glossary/board-pack | Board theme |
| https://www.smpl-ai.com/glossary/gaap-revenue | Bridge to waterfall post |
| https://www.smpl-ai.com/blog/grr-vs-nrr | Live pillar (already published) |
| https://www.smpl-ai.com/blog/billing-vs-crm-arr | New pillar (after publish) |

### Next wave (if quota remains)

`net-new-arr`, `cash-forecast`, `scenario-analysis`, `variance-analysis`, `deferred-revenue`, `close`, `mda`

---

## Agent note

URL Inspection **Request indexing** requires an authenticated Search Console session. No API/MCP is wired in this repo for that action — Matt (or whoever owns the GSC property) must click through.
