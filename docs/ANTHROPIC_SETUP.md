# Anthropic API key setup (Claude commentary)

SMPL uses **Claude** for board commentary, variance narrative, and SMPL Copilot. OpenAI remains a fallback if `ANTHROPIC_API_KEY` is unset.

## 1. Create an Anthropic account and API key

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/) and sign up or log in.
2. Open **Settings → API keys** (or **API Keys** in the left nav).
3. Click **Create Key**, name it (e.g. `smpl-prod-commentary`), and copy the key once shown.
   - Keys start with `sk-ant-…`
   - You cannot view the full key again after closing the dialog.

## 2. Set billing

Anthropic requires a payment method on the account before production traffic. For demos, use a **usage limit** in the console to cap spend.

Recommended model (configured in code): `claude-sonnet-4-20250514`

**Routing posture:** prefer thick freeze / evidence packages + the purpose-based model in `llm_factory` (`SMPL_FAST_AI` Haiku for latency; Sonnet when fast is off). Do not chase larger models for board-ready output from thin prompts — see [AI_SKILL_PRACTICES.md](./AI_SKILL_PRACTICES.md) §6.

## 3. Add the key to each environment

### Local backend

```powershell
cd backend
.\scripts\import-anthropic-keys.ps1 -Path "C:\Windows\System32\Claude Keys.txt"
pip install anthropic
```

This writes `secrets.env` (local `smpl-local` key) and updates `frontend/.env.local` with sandbox/prod reference keys.

Restart the API after saving.

### Railway (sandbox + production API)

```powershell
.\scripts\set-railway-anthropic-keys.ps1
```

Or manually in Railway -> **sfi-api-staging** / **sfi-api** -> **Variables**:

- `ANTHROPIC_API_KEY` = environment-specific key (`smpl-sandbox` / `smpl-prod`)
- `ANTHROPIC_MODEL` = `claude-sonnet-4-20250514`

Redeploy the service after saving.

### Vercel

Commentary runs on the **backend (Railway)**, not Vercel serverless — you only need the key on Railway unless you add a Next.js route that calls Anthropic directly (we do not today).

Optional: add `ANTHROPIC_API_KEY` to Vercel if you later proxy from the frontend.

## 4. Verify

```powershell
curl http://127.0.0.1:8000/api/v1/export/ping
# Expect: "anthropic_configured": true, "ai_configured": true, "llm_provider": "anthropic"
```

With a logged-in session, open `/app/board` and click **Regenerate commentary**. If the key is missing, the API returns `503` with a clear message.

## 5. Security

- Never commit keys to git (`secrets.env` is gitignored).
- Rotate keys if exposed.
- Use separate keys per environment (local / sandbox / prod) when possible.

## Env vars

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Required for Claude |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model id |
| `ANTHROPIC_TEMPERATURE` | `0.2` | Sampling |
| `ANTHROPIC_TIMEOUT_SECONDS` | `60` | Request timeout |

OpenAI vars remain supported as fallback (`OPENAI_API_KEY`).
