# Verify Preview deployment can reach staging Railway (gl-5b).
#
# Usage:
#   .\scripts\verify-preview-deploy.ps1
#   .\scripts\verify-preview-deploy.ps1 -PreviewUrl "https://smpl-financial-intelligence-git-gl-5b-sandbox-smplai.vercel.app"

param(
    [string]$PreviewUrl = "https://smpl-financial-intelligence-git-gl-5b-sandbox-smplai.vercel.app",
    [string]$StagingApi = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent

if (-not $StagingApi) {
    $stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"
    if (Test-Path $stagingFile) {
        foreach ($line in Get-Content $stagingFile) {
            if ($line -match "^STAGING_API_URL=(.+)$") {
                $StagingApi = $Matches[1].Trim()
                break
            }
        }
    }
}

$PreviewUrl = $PreviewUrl.Trim().TrimEnd("/")
$StagingApi = $StagingApi.Trim().TrimEnd("/")

Write-Host ""
Write-Host "=== Preview deploy verify (gl-5b) ===" -ForegroundColor Cyan
Write-Host "Preview: $PreviewUrl" -ForegroundColor DarkGray
Write-Host "Staging API (expected): $StagingApi" -ForegroundColor DarkGray
Write-Host ""

function Test-JsonGet {
    param([string]$Label, [string]$Url)
    Write-Host "$Label" -ForegroundColor Yellow
    Write-Host "  GET $Url" -ForegroundColor DarkGray
    try {
        $res = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 45 -UseBasicParsing
        $body = $res.Content
        if ($body.Length -gt 200) { $body = $body.Substring(0, 200) + "..." }
        Write-Host "  OK $($res.StatusCode): $body" -ForegroundColor Green
        return "ok"
    }
    catch {
        $msg = "$_"
        if ($msg -match "Authentication Required|Vercel Authentication|vercel\.com/sso-api") {
            Write-Host "  SKIP: Vercel Deployment Protection (normal for curl/PowerShell)." -ForegroundColor DarkYellow
            Write-Host "  While logged into Preview in your browser, open: $Url" -ForegroundColor DarkGray
            Write-Host "  Expect JSON with status ok — not 502." -ForegroundColor DarkGray
            return "protected"
        }
        Write-Host "  FAIL: $msg" -ForegroundColor Red
        return "fail"
    }
}

$ok = $true
$previewHealth = "skip"
if ($StagingApi) {
    if ((Test-JsonGet "1) Staging Railway (direct)" "$StagingApi/health") -eq "fail") { $ok = $false }
    Write-Host ""
}

# Preview /health uses runtime SFI_BACKEND_URL on Vercel (browser test when Deployment Protection is on)
$previewHealth = Test-JsonGet "2) Preview /health proxy (CLI may hit Deployment Protection)" "$PreviewUrl/health"
if ($previewHealth -eq "fail") {
    $ok = $false
    Write-Host "  -> Set SFI_BACKEND_URL on Vercel Preview to staging Railway URL, then redeploy." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "3) Preview env checklist (Vercel dashboard -> Preview):" -ForegroundColor Yellow
Write-Host "   SFI_BACKEND_URL = $StagingApi" -ForegroundColor White
Write-Host "   NEXT_PUBLIC_API_URL = same as SFI_BACKEND_URL" -ForegroundColor White
Write-Host "   BILLING_INTERNAL_API_KEY = same as Railway sfi-api-staging" -ForegroundColor White
Write-Host "   AUTH_URL = leave UNSET on Preview (do not use prod URL)" -ForegroundColor White
Write-Host ""

if (-not $ok) {
    Write-Host "FAILED: staging API unreachable from CLI." -ForegroundColor Red
    exit 1
}

if ($previewHealth -eq "protected") {
    Write-Host "Staging API OK from CLI. Preview URL is behind Vercel login — verify /health in the browser." -ForegroundColor Yellow
}
else {
    Write-Host "OK: Preview /health proxy works from CLI." -ForegroundColor Green
}

Write-Host ""
Write-Host "To deploy code + trigger Vercel rebuild, run:" -ForegroundColor Yellow
Write-Host "  .\scripts\deploy-gl5b-preview-auth-fix.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Then: sign out on Preview -> new magic link -> expect SMPL Demo Co." -ForegroundColor Yellow
Write-Host ""
