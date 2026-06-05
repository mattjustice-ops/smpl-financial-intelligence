# Sends a test email through Resend using the same config as customer login.
# Run: .\scripts\test-resend-email.ps1 -To mattjustice@smpl-ai.com

param(
  [Parameter(Mandatory = $true)]
  [string]$To,
  [string]$TokenFile = "C:\Users\mattj\OneDrive\Documents\Resend Token.txt",
  [string]$From = "onboarding@resend.dev"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ResendApiKey.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"

if ($To -match "YOUR_RESEND_ACCOUNT_EMAIL") {
  Write-Host "Replace YOUR_RESEND_ACCOUNT_EMAIL with the email shown in Resend Settings." -ForegroundColor Red
  exit 1
}

$key = Resolve-ResendApiKey -TokenFile $TokenFile -EnvLocal $envLocal

if (-not $key) {
  Write-Host "No valid Resend API key found." -ForegroundColor Red
  Write-Host "1. Open Resend dashboard and copy your API key (starts with re_)"
  Write-Host "2. Paste it on its own line in:" $TokenFile
  Write-Host "3. Run: .\scripts\setup-resend-email.ps1"
  exit 1
}

if (Test-Path $envLocal) {
  $fromLine = Get-Content $envLocal | Where-Object { $_ -match "^EMAIL_FROM=" } | Select-Object -First 1
  if ($fromLine -match "^EMAIL_FROM=(.+)$") {
    $From = $Matches[1]
  }
}

$body = @{
  from = $From
  to = @($To)
  subject = "SMPL Resend test"
  html = "<p>If you received this, Resend is configured correctly for SMPL login.</p>"
} | ConvertTo-Json

Write-Host "Sending test email from $From to $To ..." -ForegroundColor Cyan

try {
  $response = Invoke-RestMethod `
    -Uri "https://api.resend.com/emails" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $key" } `
    -ContentType "application/json" `
    -Body $body

  Write-Host "OK - Resend accepted the send. Message id:" $response.id -ForegroundColor Green
  Write-Host "Check the inbox for $To (and spam)." -ForegroundColor Yellow
} catch {
  $detail = $_.ErrorDetails.Message
  if (-not $detail) { $detail = $_.Exception.Message }
  Write-Host "Resend rejected the send:" -ForegroundColor Red
  Write-Host $detail
  exit 1
}
