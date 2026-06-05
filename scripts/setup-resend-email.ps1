# One-time Resend setup for SMPL magic-link login.
# Run from repo root: .\scripts\setup-resend-email.ps1

param(
  [string]$TokenFile = "C:\Users\mattj\OneDrive\Documents\Resend Token.txt",
  [string]$FromAddress = "onboarding@resend.dev"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ResendApiKey.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"

Write-Host ""
Write-Host "=== SMPL magic-link email (Resend) ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $TokenFile)) {
  @"
# Resend API key for SMPL customer login magic links
# Paste your API key on the line below (must start with re_)

"@ | Set-Content -Path $TokenFile -Encoding UTF8
  Write-Host "Created token file:" $TokenFile -ForegroundColor Green
} else {
  Write-Host "Token file already exists:" $TokenFile -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Opening Resend in your browser..." -ForegroundColor Yellow
Start-Process "https://resend.com/api-keys"

Write-Host ""
Write-Host "Steps:" -ForegroundColor Cyan
Write-Host "  1. In Resend, click Create API Key (Sending access)"
Write-Host "  2. Copy the FULL key immediately - Resend only shows it once"
Write-Host "  3. Paste ONLY that key on its own line in:" $TokenFile
Write-Host "  4. Re-run this script"
Write-Host ""
Write-Host "Important: delete old keys in Resend if unsure which is current." -ForegroundColor Yellow
Write-Host ""

$key = Resolve-ResendApiKey -TokenFile $TokenFile -EnvLocal $envLocal

if (-not $key) {
  Write-Host "No valid re_... API key found yet." -ForegroundColor Yellow
  Write-Host "Paste your key on its own line in the token file, save, and run this script again."
  exit 0
}

Write-Host ("Found key candidate (length {0} chars). Verifying with Resend..." -f $key.Length) -ForegroundColor Cyan

if (-not (Test-ResendApiKey -Key $key)) {
  $detail = Get-ResendApiKeyError -Key $key
  Write-Host ""
  Write-Host "Resend rejected this API key." -ForegroundColor Red
  if ($detail) {
    Write-Host $detail -ForegroundColor Red
  }
  Write-Host ""
  Write-Host "Fix:" -ForegroundColor Yellow
  Write-Host "  1. Go to https://resend.com/api-keys"
  Write-Host "  2. Create a NEW API key (Sending access is correct)"
  Write-Host "  3. Copy the entire key when it appears"
  Write-Host "  4. Replace the line in the token file with ONLY that key"
  Write-Host "  5. Run this script again"
  Write-Host ""
  Write-Host "Do not paste the key into a comment line. It must be on its own line." -ForegroundColor Yellow
  exit 1
}

if (Test-ResendApiKeyIsSendingOnly -Key $key) {
  Write-Host "API key verified with Resend (Sending access - correct for login emails)." -ForegroundColor Green
} else {
  Write-Host "API key verified with Resend." -ForegroundColor Green
}

$normalized = @"
# Resend API key for SMPL customer login magic links
# Keep ONLY the re_... key on the line below.

$key

# Until smpl-ai.com is verified, From is onboarding@resend.dev
# and Resend only delivers to the email on your Resend account.
"@
Set-Content -Path $TokenFile -Value $normalized.TrimEnd() -Encoding UTF8
Write-Host "Normalized token file." -ForegroundColor Green

function Set-EnvLine {
  param([string[]]$Lines, [string]$Name, [string]$Value)
  $filtered = @($Lines | Where-Object { $_ -notmatch "^$([regex]::Escape($Name))=" })
  return ,@($filtered + "$Name=$Value")
}

function Remove-EnvLine {
  param([string[]]$Lines, [string]$Name)
  return ,@($Lines | Where-Object { $_ -notmatch "^$([regex]::Escape($Name))=" })
}

$lines = if (Test-Path $envLocal) { Get-Content $envLocal } else { @() }
$lines = Set-EnvLine $lines "RESEND_TOKEN_FILE" $TokenFile
$lines = Set-EnvLine $lines "AUTH_RESEND_KEY" $key
$lines = Set-EnvLine $lines "EMAIL_FROM" $FromAddress
$lines | Set-Content -Path $envLocal -Encoding UTF8

Write-Host ""
Write-Host "Updated frontend/.env.local with a verified AUTH_RESEND_KEY." -ForegroundColor Green
Write-Host "Restart npm run dev, then test with:" -ForegroundColor Green
Write-Host '  .\scripts\test-resend-email.ps1 -To your-email@example.com' -ForegroundColor Green
Write-Host ""
