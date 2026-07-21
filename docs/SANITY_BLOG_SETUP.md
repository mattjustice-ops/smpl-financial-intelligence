# Sanity blog + glossary setup

SMPL.ai Resources (Blog + Glossary) are powered by Sanity CMS and rendered with the marketing site’s slate/teal UI. Studio is embedded at `/studio` in the Next.js app (one Vercel deploy).

**Editors only:** `/studio` is intentionally not linked from public blog/glossary pages. Bookmark the URL (local or production) — public empty states say “coming soon” and link to `/book-demo` only.

**Project (current):** `sda23ulo` · **Dataset:** `production`

## 1. Account & project

1. Sign in at [sanity.io/manage](https://www.sanity.io/manage).
2. Open project **sda23ulo** (or create a new project and update env vars).
3. Confirm dataset `production` exists (default).
4. Invite editors: Project → Members → Invite (role: Editor or Administrator).

If you create a *new* project later, replace `NEXT_PUBLIC_SANITY_PROJECT_ID` everywhere.

## 2. Environment variables

### Local — `frontend/.env.local` (gitignored)

```bash
NEXT_PUBLIC_SANITY_PROJECT_ID=sda23ulo
NEXT_PUBLIC_SANITY_DATASET=production

# Optional — draft/private reads
# SANITY_API_READ_TOKEN=

# Seed script only (Editor+ token). Never commit. Never NEXT_PUBLIC_*.
# SANITY_API_WRITE_TOKEN=

# On-demand ISR webhook
# SANITY_REVALIDATE_SECRET=generate-a-long-random-string
```

Copy comments also live in `frontend/.env.example`.

### Vercel

In the Vercel project → Settings → Environment Variables, set for Production (and Preview if desired):

| Name | Value | Notes |
|------|-------|--------|
| `NEXT_PUBLIC_SANITY_PROJECT_ID` | `sda23ulo` | Public |
| `NEXT_PUBLIC_SANITY_DATASET` | `production` | Public |
| `SANITY_REVALIDATE_SECRET` | (random secret) | Server-only; match Sanity webhook header |
| `SANITY_API_READ_TOKEN` | (optional) | Only if you enable draft mode later |
| `SANITY_API_WRITE_TOKEN` | — | **Do not** put write tokens on Vercel unless you run seed in CI |

Redeploy after adding env vars.

## 3. Deploy schema & open Studio

From `frontend/`:

```bash
npm run dev
```

Open [http://localhost:3002/studio](http://localhost:3002/studio) and sign in with your Sanity account.

The first Studio load registers schemas (`post`, `author`, `category`, `glossaryTerm`, `blockContent`) with the project.

Optional CLI (same project/dataset via `sanity.cli.ts`):

```bash
npx sanity schema deploy
```

CORS: Sanity Manage → API → CORS origins should include:

- `http://localhost:3002`
- `https://www.smpl-ai.com`
- your Vercel preview URLs if Studio is used from Preview

## 4. Seed cornerstone content

Starter bodies live in `frontend/sanity/seed/content.mjs`:

- 3 posts (board evidence, close Load→Validate→Lock→Freeze, AI commentary)
- ~20 glossary terms (ARR, NRR/GRR, deferred revenue, waterfall, freeze pack, etc.)

1. Create a token: Sanity Manage → API → Tokens → Add API token → **Editor**.
2. Add to `frontend/.env.local`:

   ```bash
   SANITY_API_WRITE_TOKEN=sk...
   ```

3. Run:

   ```bash
   cd frontend
   npm run seed:sanity
   ```

4. Visit `/blog` and `/glossary`. Edit further in `/studio`.

Without a write token, create the same documents manually in Studio using the seed file as copy.

## 5. How editors publish

1. Open `/studio` (local or production).
2. Create or edit **Post** / **Glossary term**.
3. Fill fields, write body, set author/categories, set `publishedAt` for posts.
4. Click **Publish**.
5. Site refreshes within ~60s (ISR) or immediately if the revalidate webhook is configured.

Internal CTA: each cornerstone post already links to `/book-demo` / `/request-quote` in body copy. Keep that pattern for new posts.

## 6. Revalidate webhook (recommended)

1. Generate `SANITY_REVALIDATE_SECRET` and set it on Vercel + `.env.local`.
2. Sanity Manage → API → Webhooks → Create:
   - URL: `https://www.smpl-ai.com/api/revalidate`
   - Trigger on create/update/delete for `post`, `glossaryTerm`, `author`, `category`
   - HTTP header: `x-sanity-webhook-secret: <same secret>`
3. Publish a post and confirm `/blog` updates promptly.

## 7. Routes & SEO

| Route | Purpose |
|-------|---------|
| `/blog` | Post index |
| `/blog/[slug]` | Post detail |
| `/glossary` | A–Z glossary |
| `/glossary/[slug]` | Term detail |
| `/studio` | Embedded Sanity Studio (editors; not advertised on public pages) |

Titles use the house `|` separator via `frontend/lib/site.ts` (`SITE_NAME` = SMPL.ai). Prefer `seoTitle` / `seoDescription` on posts when set.

If `NEXT_PUBLIC_SANITY_PROJECT_ID` is missing or content is empty, `/blog` and `/glossary` render customer-friendly empty states with a Book a demo CTA (no Studio link; no build failure).

## 8. Verify build

```bash
cd frontend
npm run build
```

Build succeeds with project ID set. Studio and public pages compile without requiring a write token. Content lists stay empty until schema + seed/publish land in the dataset.

## Troubleshooting

- **Empty blog after seed:** confirm dataset is `production`, documents are published, and env on the running process matches.
- **Studio blank / CORS error:** add the origin under Sanity CORS origins; allow credentials if prompted.
- **Webhook 401:** secret header must exactly match `SANITY_REVALIDATE_SECRET`.
- **Image 404:** `next.config.js` already allows `cdn.sanity.io`.
