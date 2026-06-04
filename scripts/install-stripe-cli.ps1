# Install Stripe CLI on Windows and verify it works.
# Run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#      .\scripts\install-stripe-cli.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Install Stripe CLI (Windows) ===" -ForegroundColor Cyan
Write-Host ""

if (Get-Command stripe -ErrorAction SilentlyContinue) {
  Write-Host "Stripe CLI is already installed:" -ForegroundColor Green
  stripe --version
  Write-Host ""
  Write-Host "Next: stripe login"
  Write-Host "Then: stripe listen --forward-to localhost:3002/api/stripe/webhook"
  exit 0
}

$installed = $false

if (Get-Command winget -ErrorAction SilentlyContinue) {
  Write-Host "Trying winget install Stripe.StripeCli ..." -ForegroundColor Yellow
  try {
    winget install --id Stripe.StripeCli -e --accept-source-agreements --accept-package-agreements
    $installed = $true
  } catch {
    Write-Host "winget install failed: $_" -ForegroundColor DarkYellow
  }
}

if (-not $installed -and (Get-Command scoop -ErrorAction SilentlyContinue)) {
  Write-Host "Trying scoop install stripe ..." -ForegroundColor Yellow
  scoop install stripe
  $installed = $true
}

if (-not $installed) {
  Write-Host ""
  Write-Host "Automatic install did not complete. Install manually:" -ForegroundColor Yellow
  Write-Host "  1. Open https://github.com/stripe/stripe-cli/releases/latest"
  Write-Host "  2. Download stripe_*_windows_x86_64.zip (or .msi if listed)"
  Write-Host "  3. Extract stripe.exe to a folder, e.g. C:\Tools\stripe\"
  Write-Host "  4. Add that folder to PATH (System Environment Variables -> Path)"
  Write-Host "  5. Close and reopen PowerShell, then: stripe --version"
  Write-Host ""
  Write-Host "Or install winget from Microsoft Store, then re-run this script."
  exit 1
}

Write-Host ""
Write-Host "Refresh PATH in this session ..." -ForegroundColor Cyan
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

if (-not (Get-Command stripe -ErrorAction SilentlyContinue)) {
  $candidates = @(
    "$env:LOCALAPPDATA\Microsoft\WinGet\Links\stripe.exe",
    "$env:ProgramFiles\Stripe\stripe.exe",
    "$env:LOCALAPPDATA\stripe\stripe.exe"
  )
  foreach ($exe in $candidates) {
    if (Test-Path $exe) {
      $dir = Split-Path $exe -Parent
      $env:Path = "$dir;$env:Path"
      break
    }
  }
}

if (Get-Command stripe -ErrorAction SilentlyContinue) {
  Write-Host "Success:" -ForegroundColor Green
  stripe --version
  Write-Host ""
  Write-Host "Next steps:" -ForegroundColor Cyan
  Write-Host "  stripe login"
  Write-Host "  stripe listen --forward-to localhost:3002/api/stripe/webhook"
  Write-Host "  Copy whsec_... into Stripe Token.txt"
} else {
  Write-Host "Install may have finished. Close PowerShell, open a NEW window, run: stripe --version" -ForegroundColor Yellow
}
