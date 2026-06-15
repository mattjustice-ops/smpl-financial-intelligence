# Optional: create frontend/.vercel/project.json for local CLI tools.
# Not required if you use --scope/--project on vercel commands.
#
# Usage:
#   cd frontend
#   ..\scripts\ensure-vercel-link.ps1

$ErrorActionPreference = "Stop"
$frontendDir = Join-Path (Split-Path $PSScriptRoot -Parent) "frontend"
$projectJson = Join-Path $frontendDir ".vercel\project.json"

Push-Location $frontendDir
try {
    if (Test-Path $projectJson) {
        Write-Host "Already linked:" -ForegroundColor Green
        Get-Content $projectJson
        exit 0
    }

    Write-Host "Linking smplai/smpl-financial-intelligence ..." -ForegroundColor Cyan
    & npx --yes vercel@latest link --scope smplai --project smpl-financial-intelligence --yes
    if ($LASTEXITCODE -ne 0) {
        throw "vercel link failed"
    }

    if (Test-Path $projectJson) {
        Write-Host "Created:" -ForegroundColor Green
        Get-Content $projectJson
    } else {
        Write-Host "Link reported success but project.json is still missing." -ForegroundColor Yellow
        Write-Host "That is OK for newer Vercel CLI. Use:" -ForegroundColor Yellow
        Write-Host "  ..\scripts\set-vercel-prod-auth-env.ps1 -DatabaseUrl `"...`"" -ForegroundColor White
    }
}
finally {
    Pop-Location
}
