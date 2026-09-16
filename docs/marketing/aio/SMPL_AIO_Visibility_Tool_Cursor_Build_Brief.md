# SMPL.ai AIO Visibility Tool
## Cursor Build Brief

### Working name
**SMPL Visibility**

## Purpose

Build an internal measurement system that answers:

> **Is SMPL.ai becoming more likely to be discovered, cited, and recommended when buyers use AI to research FP&A software and SaaS Finance problems?**

Measure two different things:

1. **AIO Readiness**: whether SMPL.ai has the technical, content, entity, and topical conditions that should improve discoverability.
2. **Observed AI Visibility**: whether clean, web-enabled AI research sessions actually mention, cite, recommend, and correctly position SMPL.ai.

Preserve historical runs so new content can be evaluated over 7, 30, 60, and 90 days.

---

# Measurement Principle

Do **not** label API benchmark results as "ChatGPT rankings."

Automated testing should use independent OpenAI Responses API calls with web search as a reproducible proxy. Consumer ChatGPT Search and the API are not guaranteed to behave identically.

Label automated results:

**OpenAI Web-Search Benchmark**

Also create a **Manual ChatGPT Audit** workflow where Matt can paste an answer from a clean consumer ChatGPT Search session and store it separately.

Never claim access to OpenAI's ranking algorithm.

---

# Existing Stack

Use the existing SMPL.ai stack unless the repo proves otherwise:

- Python + FastAPI
- Postgres
- Next.js + React
- OpenAI API

Build as an authenticated internal/admin module, for example:

`/internal/visibility`

Do not expose it publicly.

---

# V1 Functional Areas

1. Dashboard
2. Query Library
3. Benchmark Runner
4. Query Results / Competitor Analysis
5. Source Intelligence
6. Content Registry / Content Impact
7. Technical AIO Audit
8. Manual ChatGPT Audit
9. Optional referral CSV import

Do not build paid SEO rank tracking or complex third-party integrations in V1.

---

# Query Library

Seed from `smpl_aio_seed_queries.json`.

Every query must have:

- id
- query
- category
- intent
- priority
- baseline_enabled
- target_topic
- target_page_hint
- notes
- version
- active

Categories:
- category
- saas_icp
- lean_finance
- systems
- use_case
- competitive
- authority

Intents:
- commercial
- problem_solution
- informational

Priority:
- 3 = core buyer/revenue query
- 2 = strategically important
- 1 = broader authority

Allow add/edit/disable/archive. If benchmark wording changes materially, create a new version so historical comparisons remain valid.

---

# Benchmark Execution

## Clean-session behavior

Every benchmark run must be independent.

Do not:
- pass previous response IDs
- inject prior benchmark answers
- use conversation memory
- include private SMPL context
- tell the research model that we want it to find SMPL.ai

Neutral research instruction:

> Answer the user's question as an independent software research assistant. Use current web information where appropriate. Recommend specific products only when relevant and supported by available information. Cite the sources you rely on.

The only user content should be the benchmark buyer query.

Do not inject `smpl_brand_truth.json` into the research call. It is evaluator-only.

## Model configuration

Use the current OpenAI Responses API with web search enabled.

Do not hardcode model IDs throughout the app. Use:

- `AIO_QUERY_MODEL`
- `AIO_VALIDATION_MODEL`
- `AIO_EVALUATOR_MODEL`

Show the model used on every run.

Cursor must verify the current OpenAI SDK and current web-search syntax from official OpenAI documentation before implementing the API wrapper.

## Repetitions

Default Standard Benchmark:

- priority 3: 3 repetitions
- priority 2: 2 repetitions
- priority 1: 1 repetition

Allow configuration.

Each repetition is a separate stateless research request.

---

# Raw Evidence

For every run store:

- query and query version
- benchmark batch
- timestamp
- model
- request settings
- full raw answer
- response ID if provided
- citations / URLs
- source domains
- usage metadata if available
- latency
- evaluator result
- evaluator version

Never retain only a score. Every metric must drill down to the original evidence.

---

# Automated Evaluator

After the research response is generated, run a separate low-cost structured evaluator.

Evaluator inputs:

1. original query
2. raw answer
3. citations
4. competitor configuration
5. `smpl_brand_truth.json`

Strict JSON output:

```json
{
  "smpl_mentioned": true,
  "smpl_name_variants_found": ["SMPL.ai"],
  "recommendation_strength": "recommended",
  "explicit_rank": 3,
  "prominence_score": 0.72,
  "smpl_cited": true,
  "smpl_owned_domain_cited": true,
  "smpl_cited_urls": [],
  "competitors": [
    {
      "name": "Abacum",
      "mentioned": true,
      "recommendation_strength": "top_pick",
      "explicit_rank": 1
    }
  ],
  "positioning_accuracy": 0.9,
  "positioning_summary": "",
  "incorrect_or_unverified_claims": [],
  "answer_relevance": 0.95,
  "notes": ""
}
```

Recommendation enum:
- none
- mentioned
- shortlisted
- recommended
- top_pick

Weights:
- none = 0.00
- mentioned = 0.20
- shortlisted = 0.50
- recommended = 0.75
- top_pick = 1.00

Only assign `explicit_rank` when the answer explicitly presents an ordered ranking. Do not infer rank from paragraph order.

`positioning_accuracy` is judged against internal SMPL truth. Unsupported positive claims reduce accuracy.

---

# Core Visibility Metrics

Display each independently.

### Mention Rate
Runs where SMPL appears / total runs.

### Recommendation Rate
Runs where SMPL is at least shortlisted / total runs.

### Strong Recommendation Rate
Runs where SMPL is recommended or top_pick / total runs.

### Top-3 Rate
Only for explicitly ranked answers.

### Citation Rate
Runs where SMPL is supported by a citation / total runs.

### Owned-Domain Citation Rate
Runs citing `smpl-ai.com`.

### Third-Party Citation Rate
Runs citing a non-SMPL source that discusses/supports SMPL.

### Positioning Accuracy
Average 0-1 evaluator score.

### Competitive Share of Voice
`SMPL tracked vendor mentions / total tracked vendor mentions`

### Query Coverage
Active queries where SMPL appeared at least once / active queries.

---

# Internal Composite Score

Create:

## SMPL AI Visibility Index (SAVI)

0-100.

Explicit UI disclosure:

> Internal SMPL.ai benchmark. This is not an OpenAI ranking score.

Initial weights:

- Mention Rate: 20%
- Recommendation Rate: 20%
- Strong Recommendation Strength: 15%
- Citation Rate: 15%
- Owned-Domain Citation Rate: 10%
- Positioning Accuracy: 10%
- Competitive Share of Voice: 10%

Keep weights in configurable settings. Changing weights must not modify raw historical data.

---

# AIO Readiness Score

Separate from observed visibility.

0-100 diagnostic score.

### Technical Eligibility — 20
- HTTPS and public reachability
- OAI-SearchBot not explicitly blocked
- sitemap exists
- target pages reachable
- no accidental noindex
- canonical tags present

### Entity Clarity — 15
- clear SMPL.ai description
- clear category
- clear ICP
- clear problem solved
- consistent naming
- company/about information

### Commercial Intent Coverage — 20
Content covering:
- best FP&A software
- SaaS FP&A
- reporting
- forecasting
- budgeting
- board reporting
- implementation
- systems/integrations
- buyer comparisons/questions

### Topical Cluster Depth — 15
Coverage across:
- FP&A
- SaaS Finance
- SaaS metrics
- reporting
- forecasting
- planning
- cash
- governance
- AI
- implementation
- financial data integration

### Answerability — 15
- direct answers
- useful headings
- definitions
- FAQs where appropriate
- buyer language
- sourced factual claims where appropriate

### Internal Linking — 10
Related pages and articles link to each other and relevant category/product pages.

### Freshness — 5
Publication/update dates where available.

This is an internal strategy diagnostic, not a claimed ranking factor model.

---

# Technical Website Crawler

Crawl `https://www.smpl-ai.com`.

Start with:
- `/robots.txt`
- sitemap(s)
- homepage

Respect robots and rate limits.

Store for each page:

- URL
- HTTP status
- canonical
- robots meta
- title
- meta description
- H1
- H2s
- word count
- JSON-LD types
- publication date if discoverable
- modified date if discoverable
- internal links
- external links
- inbound internal-link count
- outbound internal-link count
- sitemap presence
- content hash
- crawl timestamp

## OAI-SearchBot

Parse robots.txt and show:
- allowed
- blocked
- ambiguous

Do not conflate GPTBot and OAI-SearchBot.

Display a high-priority warning if OAI-SearchBot is disallowed.

---

# Content Registry

Fields:

- title
- URL
- slug
- topic cluster
- target primary query
- mapped benchmark queries
- publication date
- last update date
- content type
- status
- notes

Content types:
- pillar
- buyer-intent
- thought-leadership
- comparison
- integration
- educational
- product

Support manual entry plus site-crawl discovery.

---

# Content Impact

For each content item and mapped query cluster:

- show nearest available pre-publication benchmark
- 7-day post
- 30-day post
- 60-day post
- 90-day post

Metrics:
- mention-rate change
- recommendation-rate change
- citation-rate change
- owned-domain citation change
- positioning-accuracy change
- share-of-voice change

Label:

**Observed change after publication**

Never label it causal.

If multiple relevant articles publish during the period, show:

**Attribution confounded by multiple content changes.**

---

# Competitors

Seed configuration:

- Abacum
- Aleph
- Anaplan
- Cube
- Datarails
- Drivetrain
- Mosaic
- Pigment
- Planful
- Prophix
- Runway
- Vena
- Workday Adaptive Planning

Allow aliases, add, disable, group.

Do not hardcode capability claims. This module tracks visibility only.

---

# Source Intelligence

For each citation domain store/display:

- domain
- total citations
- queries where cited
- brands associated
- first seen
- last seen
- example URLs

Domain type:
- vendor-owned
- analyst/research
- review/directory
- publication
- community
- partner
- other

Key report:

## Citation Opportunities

Show domains frequently cited for competitors but never for SMPL.ai.

This should inform future PR, partnerships, comparison coverage, and third-party authority work.

---

# Manual ChatGPT Audit

Form fields:

- buyer query
- observed date
- model/product note
- pasted response
- pasted citation URLs
- clean-session confirmation
- notes

Run the same evaluator.

Source type = `manual_chatgpt`.

Display separately from API benchmarks unless the user explicitly chooses a combined view.

---

# Referral Tracking

V1: optional CSV import only.

Fields:
- date
- landing_page
- sessions
- conversions
- source
- notes

Recognize `chatgpt.com` if present.

Show:
- ChatGPT referral sessions
- top landing pages
- conversions if provided
- trend

Phase 2 can connect analytics directly.

---

# SEO Extension

Do not buy/build a paid rank tracker.

Create future Google Search Console import/API support.

CSV fields:
- date
- query
- page
- clicks
- impressions
- ctr
- position

Keep SEO metrics separate from AIO metrics while allowing both to map to the same URL/query cluster.

---

# Dashboard

Top cards:

- SAVI
- Mention Rate
- Recommendation Rate
- Citation Rate
- Query Coverage
- AIO Readiness Score

Each:
- current
- previous benchmark
- delta

Other panels:

### SAVI Trend
Historical line chart.

### Visibility by Category
- Category
- SaaS ICP
- Lean Finance
- Systems
- Use Case
- Competitive
- Authority

### Competitor Share of Voice

### Biggest Gains
Queries improving most.

### Biggest Gaps
Priority-3 queries where SMPL is absent.

### Citation Opportunities
Domains supporting competitors but not SMPL.

---

# Query Explorer

Columns:

- query
- category
- priority
- latest mention rate
- recommendation rate
- citation rate
- latest competitors
- target content
- last run
- delta

Query detail page:

- all raw responses
- citations
- evaluator JSON
- historical trend
- competitor trend
- mapped content
- manual ChatGPT observations

---

# Database Tables

Use migrations.

### `aio_queries`
- id
- external_id
- query_text
- category
- intent
- priority
- baseline_enabled
- target_topic
- target_page_hint
- version
- active
- created_at
- updated_at

### `aio_benchmark_batches`
- id
- name
- started_at
- completed_at
- query_model
- evaluator_model
- status
- settings_json

### `aio_runs`
- id
- batch_id
- query_id
- repetition
- model
- raw_response
- response_external_id
- citations_json
- usage_json
- latency_ms
- created_at

### `aio_evaluations`
- id
- run_id
- evaluator_version
- smpl_mentioned
- recommendation_strength
- explicit_rank
- prominence_score
- smpl_cited
- smpl_owned_domain_cited
- cited_urls_json
- competitors_json
- positioning_accuracy
- positioning_summary
- incorrect_claims_json
- answer_relevance
- raw_json
- created_at

### `aio_competitors`
- id
- name
- aliases_json
- active

### `aio_content`
- id
- title
- url
- slug
- topic_cluster
- content_type
- publication_date
- updated_date
- status
- notes

### `aio_content_query_map`
- content_id
- query_id
- relationship
- primary_target

### `aio_crawls`
- id
- started_at
- completed_at
- status

### `aio_pages`
- id
- crawl_id
- url
- status_code
- canonical
- robots_meta
- title
- meta_description
- h1
- h2_json
- word_count
- jsonld_types_json
- published_at
- modified_at
- internal_links_json
- external_links_json
- content_hash

### `aio_manual_audits`
- id
- query_text
- observed_at
- product_note
- raw_response
- citations_json
- evaluation_json
- clean_session_confirmed
- notes

### `aio_referrals`
- id
- date
- landing_page
- sessions
- conversions
- source
- notes

### `aio_settings`
- key
- value_json
- updated_at

---

# Suggested FastAPI Endpoints

### Queries
- `GET /api/internal/aio/queries`
- `POST /api/internal/aio/queries`
- `PATCH /api/internal/aio/queries/{id}`

### Benchmarks
- `POST /api/internal/aio/benchmarks`
- `GET /api/internal/aio/benchmarks`
- `GET /api/internal/aio/benchmarks/{id}`
- `POST /api/internal/aio/benchmarks/{id}/run`

### Results
- `GET /api/internal/aio/results/overview`
- `GET /api/internal/aio/results/query/{id}`
- `GET /api/internal/aio/results/competitors`
- `GET /api/internal/aio/results/sources`

### Crawl
- `POST /api/internal/aio/crawl`
- `GET /api/internal/aio/crawl/latest`

### Content
- `GET /api/internal/aio/content`
- `POST /api/internal/aio/content`
- `PATCH /api/internal/aio/content/{id}`

### Manual audit
- `POST /api/internal/aio/manual-audits`
- `GET /api/internal/aio/manual-audits`

### Referral import
- `POST /api/internal/aio/referrals/import`

Authenticate every endpoint.

---

# Background Jobs

Use the repo's existing job system if present.

States:
- queued
- running
- completed
- partial_failure
- failed

Per-query failure must not fail the whole batch.

Use bounded retries with exponential backoff for transient API errors.

---

# Cost Controls

Before running, show:

- query count
- planned research calls
- planned evaluator calls
- model(s)

Presets:

### Quick Scan
Priority-3 only, 1 repetition.

### Standard Benchmark
Priority-3 × 3
Priority-2 × 2
Priority-1 × 1

### Full Benchmark
Custom.

Require confirmation for Full Benchmark.

---

# Baseline Workflow

After V1 is complete:

1. Crawl smpl-ai.com.
2. Run AIO Readiness audit.
3. Import seed queries.
4. Confirm competitor list.
5. Run Standard Benchmark.
6. Save batch as `Baseline - YYYY-MM-DD`.
7. Register existing strategic articles.
8. Map articles to relevant queries.
9. Never overwrite the original baseline.

---

# Initial Content to Register

Auto-discover if live, otherwise create draft placeholders:

- Best FP&A Software for SaaS Companies
- Why FP&A Software Implementations Shouldn't Take Months
- AI Is Changing the Cost Structure FP&A Has to Understand
- Financial Data Governance
- Data Bullwhip Effect
- SaaS Financial Reporting
- Board Reporting
- Budgeting and Forecasting
- AI for FP&A
- Predictive Planning Intelligence

Require confirmation before auto-mapping URLs to benchmark queries.

---

# Security

Use only public website information and generic benchmark queries.

Do not include:
- customer financial data
- private customer names
- confidential Maxio materials
- internal partnership docs
- proprietary implementation details

OpenAI API keys remain server-side.

---

# Acceptance Tests

## Integrity
- every repetition is independent
- no previous benchmark response is passed into a research call
- brand truth is never injected into discovery calls
- all raw answers/citations are retained

## Evaluator
- detects SMPL mention correctly
- detects owned-domain citation separately
- does not treat competitor mentions as SMPL
- leaves explicit rank null for unordered answers
- lowers accuracy for unsupported claims

## Historical
- new runs never overwrite old runs
- score weights can change without destroying raw evidence

## Crawler
- retrieves robots.txt
- reports OAI-SearchBot state
- crawls sitemap pages
- flags noindex/canonical/HTTP issues

## Content
- one article can map to many target queries
- pre/post visibility can be compared

## UX
- every score drills into raw evidence
- composite scores explain methodology
- API and manual consumer observations are visually distinct

---

# Non-Goals

Do not build:

- paid SEO rank tracking
- automated backlink buying/outreach
- content generation/publishing
- consumer ChatGPT browser automation
- authenticated scraping
- claims about knowing OpenAI ranking logic
- a giant general-purpose marketing suite

The job is:

> **Measure whether SMPL.ai is becoming more visible and credible inside AI-assisted FP&A research.**

---

# Phase 2

After V1 works:

1. Google Search Console direct API
2. GA4 direct integration
3. Additional AI/search engines through supported APIs
4. Automated citation-gap recommendations
5. Query expansion subject to manual approval
6. Content-opportunity recommendations
7. Weekly scheduled benchmark

Never collapse multiple engines into one opaque score. Preserve engine-specific metrics.

---

# Implementation Sequence for Cursor

## Step 1
Inspect the repo:
- FastAPI conventions
- migrations
- auth
- job/background system
- frontend component library
- OpenAI client wrapper

Return a short implementation plan before introducing new architecture.

## Step 2
Add migrations and seed configuration.

## Step 3
Build benchmark runner using current official OpenAI Responses API web-search capabilities.

## Step 4
Build structured evaluator.

## Step 5
Build metrics/scoring with unit tests.

## Step 6
Build site crawler / OAI technical audit.

## Step 7
Build internal API endpoints.

## Step 8
Build Overview dashboard and Query Explorer.

## Step 9
Build competitor/source intelligence.

## Step 10
Build Content Registry and Impact view.

## Step 11
Build Manual ChatGPT Audit.

## Step 12
Run in local/staging and return:
- screenshots
- migration summary
- test results
- estimated number of API calls for Standard Benchmark

Do not launch the first large production benchmark until Matt confirms.

---

# V1 Must Answer

When Matt opens the dashboard:

1. How often is SMPL.ai showing up?
2. For which buyer questions?
3. Is it recommended or merely mentioned?
4. Is smpl-ai.com being cited?
5. Which competitors appear instead?
6. Is visibility improving?
7. What changed after we published specific content?
8. What are our biggest priority-query gaps?
9. Is the site technically available to OpenAI search?
10. Which external sources influence AI recommendations?

If these are not easy to answer, V1 is not finished.

---

# Final Principle

This is an evidence system, not a vanity-score generator.

Negative results are valuable.

Every score must be traceable to:
- the exact query
- the exact answer
- the exact sources
- the exact evaluation

SMPL.ai must earn its visibility.
