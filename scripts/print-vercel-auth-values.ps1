# Print copy-paste values for Vercel dashboard (no CLI required).
#
# Usage:
#   .\scripts\print-vercel-auth-values.ps1 -DatabaseUrl "postgresql://..."

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$AuthSecret = "",
    [string]$ResendKey = "",
    [string]$EmailFrom = "SMPL.ai <onboarding@resend.dev>",
    [string]$ProdUrl = "https://smpl-financial-intelligence.vercel.app"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"

if (-not $AuthSecret) {
    $AuthSecret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
}

if (-not $ResendKey -and (Test-Path $envLocal)) {
    $line = Get-Content $envLocal | Where-Object { $_ -match "^AUTH_RESEND_KEY=" } | Select-Object -First 1
    if ($line) {
        $ResendKey = ($line -replace "^AUTH_RESEND_KEY=", "").Trim()
    }
}

$dbUrl = $DatabaseUrl.Trim().Trim('"').Trim("'")

Write-Host ""
Write-Host "=== Paste into Vercel -> Settings -> Environment Variables -> Production ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "AUTH_DATABASE_URL" -ForegroundColor Yellow
Write-Host $dbUrl
Write-Host ""
Write-Host "AUTH_SECRET" -ForegroundColor Yellow
Write-Host $AuthSecret
Write-Host ""
Write-Host "AUTH_URL" -ForegroundColor Yellow
Write-Host $ProdUrl
Write-Host ""
Write-Host "APP_BASE_URL" -ForegroundColor Yellow
Write-Host $ProdUrl
Write-Host ""
Write-Host "AUTH_RESEND_KEY" -ForegroundColor Yellow
Write-Host $ResendKey
Write-Host ""
Write-Host "EMAIL_FROM" -ForegroundColor Yellow
Write-Host $EmailFrom
Write-Host ""
Write-Host "Save AUTH_SECRET somewhere safe, then Redeploy latest on Vercel." -ForegroundColor Green
Write-Host ""
