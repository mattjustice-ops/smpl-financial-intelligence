# Step 1 — Add smpl-ai.com to Vercel and point auth URLs at the custom domain.
#
# Usage (repo root):
#   .\scripts\setup-smpl-ai-domain.ps1
#   .\scripts\setup-smpl-ai-domain.ps1 -SkipVercelAdd   # DNS only instructions + env update
#
# After DNS propagates:
#   .\scripts\set-vercel-prod-auth-env.ps1 -DatabaseUrl "..." -ProdUrl "https://smpl-ai.com" -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"
#   .\scripts\set-vercel-resend-from.ps1
#   Redeploy latest on Vercel

param(
    [string]$Domain = "smpl-ai.com",
    [string]$ProdUrl = "https://smpl-ai.com",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence",
    [string]$VercelToken = "",
    [switch]$SkipVercelAdd
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

if ($VercelToken) {
    $env:VERCEL_TOKEN = $VercelToken.Trim()
}

function Get-NpxBaseArgs {
    $args = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) {
        $args += @("--token", $env:VERCEL_TOKEN)
    }
    return $args
}

Write-Host ""
Write-Host "=== Step 1: smpl-ai.com on Vercel ===" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipVercelAdd) {
    Push-Location $frontendDir
    try {
        Write-Host "Adding domain to Vercel project..." -ForegroundColor Yellow
        $npxArgs = Get-NpxBaseArgs + @("domains", "add", $Domain, "--scope", $Scope, "--project", $Project)
        & npx @npxArgs 2>&1 | Write-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "If domain add failed, add manually:" -ForegroundColor Yellow
            Write-Host "  Vercel -> $Project -> Settings -> Domains -> Add $Domain and www.$Domain" -ForegroundColor White
        } else {
            Write-Host "Domain add request sent." -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "Checking domain status..." -ForegroundColor Yellow
        $lsArgs = Get-NpxBaseArgs + @("domains", "ls", "--scope", $Scope)
        & npx @lsArgs 2>&1 | Write-Host
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "=== Squarespace DNS (smpl-ai.com) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "In Squarespace -> Domains -> smpl-ai.com -> DNS Settings, add:" -ForegroundColor White
Write-Host ""
Write-Host "  Apex (@):" -ForegroundColor Yellow
Write-Host "    Type: A" -ForegroundColor White
Write-Host "    Host: @  ->  76.76.21.21  (Vercel apex)" -ForegroundColor White
Write-Host ""
Write-Host "  www:" -ForegroundColor Yellow
Write-Host "    Type: CNAME" -ForegroundColor White
Write-Host "    Host: www  ->  cname.vercel-dns.com" -ForegroundColor White
Write-Host ""
Write-Host "Vercel may show different records after you add the domain — use their dashboard if these differ." -ForegroundColor DarkGray
Write-Host ""
Write-Host "Also set www.$Domain -> redirect to $Domain in Vercel (recommended)." -ForegroundColor DarkGray
Write-Host ""

Write-Host "=== Step 2 prep: auth URLs ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "After DNS is Valid in Vercel, run:" -ForegroundColor Yellow
Write-Host '  .\scripts\set-vercel-prod-auth-env.ps1 -DatabaseUrl "postgresql://..." -ProdUrl "' + $ProdUrl + '"' -ForegroundColor White
Write-Host '  .\scripts\set-vercel-resend-from.ps1 -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"' -ForegroundColor White
Write-Host "  Vercel -> Deployments -> Redeploy latest" -ForegroundColor White
Write-Host ""
Write-Host "Smoke test:" -ForegroundColor Yellow
Write-Host "  $ProdUrl" -ForegroundColor White
Write-Host "  $ProdUrl/login" -ForegroundColor White
Write-Host ""
