# gl-5b full stack audit: Vercel Preview env hosts, Railway staging, session-sync, DB workspace.
# Prints hosts only — never secret values.
#
# Usage:
#   .\scripts\audit-gl5b-stack.ps1

param(
    [string]$Email = "mattjustice@smpl-ai.com",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence",
    [string]$StagingApi = "",
    [string]$InternalKey = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"

$expectedStagingApi = "https://sfi-api-staging-production.up.railway.app"
$expectedStagingDbHost = "ep-fragrant-grass-aqa8r22s-pooler.c-8.us-east-1.aws.neon.tech"
$expectedProdApi = "sfi-api-production.up.railway.app"
$demoOrg = "8571e520-0687-4516-bdee-379f37c58c1f"
$customerOrg = "cfa7c116-3a89-4dd1-91df-80d4ece5c59d"

function Get-HostFromUrl {
    param([string]$Line, [string]$Prefix)
    if ($Line -match "^$([regex]::Escape($Prefix))=(.+)$") {
        $raw = $Matches[1].Trim().Trim('"').Trim("'")
        if ($raw -match "@([^/]+)/") { return $Matches[1] }
        if ($raw -match "^https?://([^/]+)") { return $Matches[1] }
        return $raw
    }
    return $null
}

function Get-EnvFileHost {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return $null }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$([regex]::Escape($Key))=") {
            return Get-HostFromUrl -Line $line -Prefix $Key
        }
    }
    return $null
}

function Test-EnvFileHasKey {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return $false }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$([regex]::Escape($Key))=(.+)$") {
            $v = $Matches[1].Trim()
            return ($v -ne "" -and $v -notmatch '^\s*$')
        }
    }
    return $false
}

function Get-NpxBaseArgs {
    $npxBase = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) { $npxBase += @("--token", $env:VERCEL_TOKEN) }
    return $npxBase
}

if (-not $StagingApi) {
    if (Test-Path $stagingFile) {
        foreach ($line in Get-Content $stagingFile) {
            if ($line -match "^STAGING_API_URL=(.+)$") {
                $StagingApi = $Matches[1].Trim()
                break
            }
        }
    }
}
$StagingApi = $StagingApi.Trim().TrimEnd("/")

$issues = @()
$ok = @()

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  gl-5b stack audit (hosts only)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1) Vercel Preview env pull ---
Write-Host "1) Vercel Preview environment" -ForegroundColor Yellow
$previewEnvFile = Join-Path $env:TEMP "sfi-audit-preview-$([guid]::NewGuid().ToString('N')).env"
Push-Location $frontendDir
try {
    $pullArgs = Get-NpxBaseArgs + @(
        "env", "pull", $previewEnvFile,
        "--environment", "preview",
        "--yes",
        "--scope", $Scope,
        "--project", $Project
    )
    $pullOut = & npx @pullArgs 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $previewEnvFile)) {
        $issues += "Vercel env pull (preview) failed — run: npx vercel login"
        Write-Host "   FAIL: could not pull Preview env" -ForegroundColor Red
        if ($pullOut) { Write-Host ($pullOut -join "`n") -ForegroundColor DarkGray }
    }
    else {
        $checks = @(
            @{ Key = "SFI_BACKEND_URL"; Want = "api-host-staging"; Expected = $expectedStagingApi },
            @{ Key = "NEXT_PUBLIC_API_URL"; Want = "api-host-staging"; Expected = $expectedStagingApi },
            @{ Key = "AUTH_DATABASE_URL"; Want = "db-host-staging"; Expected = $expectedStagingDbHost },
            @{ Key = "AUTH_SECRET"; Want = "nonempty" },
            @{ Key = "AUTH_RESEND_KEY"; Want = "nonempty" },
            @{ Key = "EMAIL_FROM"; Want = "nonempty" }
        )
        foreach ($c in $checks) {
            $present = Test-EnvFileHasKey -FilePath $previewEnvFile -Key $c.Key
            if (-not $present) {
                $issues += "Preview missing or empty: $($c.Key)"
                Write-Host "   MISSING: $($c.Key)" -ForegroundColor Red
                continue
            }
            if ($c.Want -eq "nonempty") {
                Write-Host "   OK: $($c.Key) is set" -ForegroundColor Green
                $ok += $c.Key
                continue
            }
            $resolvedHost = Get-EnvFileHost -FilePath $previewEnvFile -Key $c.Key
            if ($c.Want -eq "api-host-staging") {
                if ($resolvedHost -match "sfi-api-staging" -and $resolvedHost -notmatch "sfi-api-production\.up\.railway\.app") {
                    Write-Host "   OK: $($c.Key) -> $resolvedHost" -ForegroundColor Green
                    $ok += "$($c.Key) staging API"
                }
                elseif ($resolvedHost -match $expectedProdApi) {
                    $issues += "Preview $($c.Key) points at PRODUCTION API ($resolvedHost)"
                    Write-Host "   WRONG: $($c.Key) -> $resolvedHost (PRODUCTION API)" -ForegroundColor Red
                }
                else {
                    $issues += "Preview $($c.Key) unexpected host: $resolvedHost"
                    Write-Host "   WARN: $($c.Key) -> $resolvedHost" -ForegroundColor Yellow
                }
            }
            if ($c.Want -eq "db-host-staging") {
                if ($resolvedHost -match "fragrant-grass") {
                    Write-Host "   OK: $($c.Key) -> $resolvedHost" -ForegroundColor Green
                    $ok += "AUTH_DATABASE_URL staging Neon"
                }
                elseif ($resolvedHost -match "cool-moon|ep-cool") {
                    $issues += "Preview AUTH_DATABASE_URL points at PRODUCTION Neon ($resolvedHost)"
                    Write-Host "   WRONG: $($c.Key) -> $resolvedHost (likely PROD Neon)" -ForegroundColor Red
                }
                else {
                    Write-Host "   WARN: $($c.Key) -> $resolvedHost" -ForegroundColor Yellow
                }
            }
        }

        $authUrlHost = Get-EnvFileHost -FilePath $previewEnvFile -Key "AUTH_URL"
        if ($authUrlHost) {
            if ($authUrlHost -match "smpl-financial-intelligence\.vercel\.app" -and $authUrlHost -notmatch "git-") {
                $issues += "Preview AUTH_URL set to production site ($authUrlHost) — unset for Preview"
                Write-Host "   WRONG: AUTH_URL -> $authUrlHost (use unset on Preview)" -ForegroundColor Red
            }
            else {
                Write-Host "   INFO: AUTH_URL -> $authUrlHost" -ForegroundColor DarkGray
            }
        }
        else {
            Write-Host "   OK: AUTH_URL unset on Preview" -ForegroundColor Green
        }

        $hasBilling = Test-EnvFileHasKey -FilePath $previewEnvFile -Key "BILLING_INTERNAL_API_KEY"
        if ($hasBilling) {
            Write-Host "   INFO: BILLING_INTERNAL_API_KEY is set (must match Railway staging)" -ForegroundColor DarkGray
        }
        else {
            Write-Host "   OK: BILLING_INTERNAL_API_KEY unset (OK if Railway staging also unset)" -ForegroundColor Green
        }
    }
}
finally {
    Pop-Location
    if (Test-Path $previewEnvFile) { Remove-Item $previewEnvFile -Force -ErrorAction SilentlyContinue }
}
Write-Host ""

# --- 2) Staging API + session-sync ---
Write-Host "2) Railway staging API + session-sync" -ForegroundColor Yellow
if ($StagingApi) {
    try {
        $h = Invoke-RestMethod -Uri "$StagingApi/health" -TimeoutSec 45
        Write-Host "   OK: $StagingApi/health -> $($h.status)" -ForegroundColor Green
    }
    catch {
        $issues += "Staging API /health failed"
        Write-Host "   FAIL: staging /health — $_" -ForegroundColor Red
    }

    $headers = @{ "Content-Type" = "application/json" }
    if ($InternalKey) { $headers["X-Billing-Internal-Key"] = $InternalKey.Trim() }
    else {
        $localBilling = Get-EnvFileHost -FilePath (Join-Path $frontendDir ".env.local") -Key "BILLING_INTERNAL_API_KEY"
        # cannot read value from host helper for non-url — check file
        if (Test-Path (Join-Path $frontendDir ".env.local")) {
            $line = Get-Content (Join-Path $frontendDir ".env.local") | Where-Object { $_ -match "^BILLING_INTERNAL_API_KEY=" } | Select-Object -First 1
            if ($line -match "^BILLING_INTERNAL_API_KEY=(.+)$" -and $Matches[1].Trim()) {
                $headers["X-Billing-Internal-Key"] = $Matches[1].Trim()
            }
        }
    }
    try {
        $body = @{ email = $Email.Trim().ToLower() } | ConvertTo-Json
        $sync = Invoke-RestMethod -Uri "$StagingApi/api/v1/auth/session-sync" -Method Post -Headers $headers -Body $body -TimeoutSec 45
        Write-Host "   session-sync activeOrganizationId: $($sync.activeOrganizationId)" -ForegroundColor $(if ($sync.activeOrganizationId -eq $demoOrg) { "Green" } else { "Red" })
        foreach ($org in $sync.organizations) {
            $mark = if ($org.organizationId -eq $sync.activeOrganizationId) { " <-- active" } else { "" }
            Write-Host "     $($org.organizationName) ($($org.organizationId))$mark" -ForegroundColor DarkGray
        }
        if ($sync.activeOrganizationId -eq $demoOrg) {
            $ok += "session-sync returns SMPL Demo Co"
        }
        else {
            $issues += "session-sync returns $($sync.activeOrganizationId) not Demo Co — run set-staging-demo-workspace.ps1"
        }
    }
    catch {
        $issues += "session-sync failed: $_"
        Write-Host "   FAIL: session-sync — $_" -ForegroundColor Red
        if ($_.Exception.Response.StatusCode.value__ -eq 401) {
            Write-Host "   -> 401: BILLING_INTERNAL_API_KEY mismatch (Vercel Preview vs Railway)" -ForegroundColor Yellow
        }
    }
}
Write-Host ""

# --- 3) Staging DB workspace ---
Write-Host "3) Staging Neon workspace (local script)" -ForegroundColor Yellow
$wsScript = Join-Path $repoRoot "scripts\set-staging-demo-workspace.ps1"
if (Test-Path $wsScript) {
    & $wsScript -Email $Email 2>&1 | ForEach-Object {
        $line = "$_"
        Write-Host "   $line" -ForegroundColor DarkGray
    }
    if ($LASTEXITCODE -ne 0) {
        $issues += "set-staging-demo-workspace.ps1 failed"
    }
}
Write-Host ""

# --- 4) Git / deploy ---
Write-Host "4) Latest gl-5b code on branch" -ForegroundColor Yellow
Push-Location $repoRoot
try {
    $branch = (& git branch --show-current 2>&1 | Select-Object -Last 1).Trim()
    $log = (& git log -1 --oneline 2>&1 | Select-Object -Last 1).Trim()
    Write-Host "   branch: $branch" -ForegroundColor DarkGray
    Write-Host "   HEAD:   $log" -ForegroundColor DarkGray
    $authContent = Get-Content (Join-Path $repoRoot "frontend\auth.ts") -Raw
    if ($authContent -match "session callback sync failed") {
        Write-Host "   OK: auth.ts has session re-sync on load" -ForegroundColor Green
    }
    else {
        $issues += "auth.ts missing session re-sync — push latest auth.ts"
        Write-Host "   WARN: auth.ts may be outdated (no session re-sync)" -ForegroundColor Yellow
    }
    $debugRoute = Join-Path $repoRoot "frontend\app\api\debug\preview-workspace\route.ts"
    if (Test-Path $debugRoute) {
        $uncommitted = & git status --porcelain $debugRoute "frontend/auth.ts" 2>&1
        if ($uncommitted) {
            $issues += "Unpushed auth/debug changes — commit and redeploy Preview"
            Write-Host "   WARN: auth.ts or debug route not pushed" -ForegroundColor Yellow
        }
    }
}
finally {
    Pop-Location
}
Write-Host ""

# --- Summary ---
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
if ($issues.Count -eq 0) {
    Write-Host "No blocking issues found in this audit." -ForegroundColor Green
    Write-Host ""
    Write-Host "If banner still shows Customer Corp:" -ForegroundColor Yellow
    Write-Host "  1. Redeploy Preview (gl-5b-sandbox) AFTER env fixes" -ForegroundColor White
    Write-Host "  2. Incognito -> login -> open /api/debug/preview-workspace" -ForegroundColor White
    Write-Host "  3. Compare session_workspace vs sync_workspace" -ForegroundColor White
}
else {
    Write-Host "Issues to fix ($($issues.Count)):" -ForegroundColor Red
    foreach ($i in $issues) {
        Write-Host "  - $i" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Fix order:" -ForegroundColor Yellow
    Write-Host "  1. Vercel dashboard -> Preview env (staging API + staging AUTH_DATABASE_URL)" -ForegroundColor White
    Write-Host "  2. Match BILLING_INTERNAL_API_KEY on Preview + Railway staging (or unset both)" -ForegroundColor White
    Write-Host "  3. .\scripts\set-staging-demo-workspace.ps1" -ForegroundColor White
    Write-Host "  4. git push gl-5b-sandbox && redeploy PREVIEW deployment" -ForegroundColor White
    Write-Host "  5. Incognito login on Preview URL from Vercel 'Visit'" -ForegroundColor White
}
Write-Host ""

if ($issues.Count -gt 0) { exit 1 }
exit 0
