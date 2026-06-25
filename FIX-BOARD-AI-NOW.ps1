# One-click: commit + push board AI fixes (run from repo root in PowerShell).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

git add `
  backend/app/core/config.py `
  backend/app/core/openai_status.py `
  backend/app/services/commentary/anthropic_client.py `
  backend/app/services/reporting/export/data_collector.py `
  backend/app/api/board_platform_routes.py `
  frontend/app/api/smpl/board-config/route.ts `
  frontend/components/app/EmbeddedModuleChrome.tsx `
  frontend/public/shared/board-hydrate.js `
  frontend/public/shared/smpl-outlook.js `
  frontend/public/board/index.html `
  frontend/scripts/verify-board-platform.mjs `
  frontend/vercel.json `
  FIX-BOARD-AI-NOW.ps1

$staged = git diff --cached --name-only
if ($staged) {
  git commit -m "fix: MD&A exports via Railway direct; faster copilot; CORS for smpl-ai.com"
}
git push origin main
git log -1 --oneline
Write-Host "Done. Wait 2-3 min for Railway + Vercel, then hard-refresh /app/board (Ctrl+Shift+R)."
