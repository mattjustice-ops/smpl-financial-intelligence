# One-click: commit + push board AI fixes (run from repo root in PowerShell).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

git add `
  backend/app/api/board_platform_routes.py `
  backend/app/services/reporting/export/board_commentary_service.py `
  frontend/app/api/smpl/board-config/route.ts `
  frontend/components/app/EmbeddedModuleChrome.tsx `
  frontend/public/shared/board-hydrate.js `
  frontend/public/shared/smpl-outlook.js `
  frontend/public/board/index.html `
  frontend/scripts/verify-board-platform.mjs `
  frontend/vercel.json `
  scripts/deploy-board-ai-fix.ps1 `
  FIX-BOARD-AI-NOW.ps1

$staged = git diff --cached --name-only
if ($staged) {
  git commit -m "fix: board Claude uses same-origin proxy (fix Failed to fetch CORS)"
}
git push origin main
git log -1 --oneline
Write-Host "Done. Wait 2-3 min for Railway + Vercel, then hard-refresh /app/board (Ctrl+Shift+R)."
