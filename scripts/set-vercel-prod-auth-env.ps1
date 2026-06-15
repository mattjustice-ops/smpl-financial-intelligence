# Push Auth milestone env vars to Vercel Production via CLI.
#
# Usage (from repo root):
#   .\scripts\set-vercel-prod-auth-env.ps1 -DatabaseUrl "postgresql://..."
#
# Manual fallback (no CLI):
#   .\scripts\print-vercel-auth-values.ps1 -DatabaseUrl "..."

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$AuthSecret = "",
    [string]$ResendKey = "",
    [string]$EmailFrom = "SMPL.ai <onboarding@resend.dev>",
    [string]$ProdUrl = "https://smpl-financial-intelligence.vercel.app",
    [string]$VercelToken = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$envLocal = Join-Path $frontendDir ".env.local"
$prodSecretsFile = Join-Path $frontendDir ".env.vercel-production.local"

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

function Get-VercelProjectArgs {
    return @("--scope", $Scope, "--project", $Project)
}

function Invoke-VercelCli {
    param(
        [switch]$WithProject,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs
    )

    $npxArgs = Get-NpxBaseArgs
    if ($WithProject) {
        $npxArgs += Get-VercelProjectArgs
    }
    $output = & npx @npxArgs @CliArgs 2>&1 | ForEach-Object { "$_" }
    return @{
        ExitCode = $LASTEXITCODE
        Output   = ($output -join "`n").Trim()
    }
}

function Get-WhoAmILine {
    param([string]$Output)
    foreach ($line in ($Output -split "`n")) {
        $trim = $line.Trim()
        if (-not $trim) { continue }
        if ($trim -match "Vercel CLI|node\.exe|CategoryInfo|FullyQualifiedErrorId|At line:|^Error:") { continue }
        if ($trim -match "^\+") { continue }
        return $trim
    }
    return ""
}

function Set-VercelProdEnvValue {
    param([string]$Name, [string]$Value)

    # CLI 54 rejects --value in some flag orders; pipe the value on stdin instead.
    $npxArgs = Get-NpxBaseArgs + Get-VercelProjectArgs
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        $output = Get-Content -LiteralPath $tempFile -Raw | & npx @npxArgs env add $Name production --yes --force 2>&1 | ForEach-Object { "$_" }
        $text = ($output -join "`n").Trim()
        if ($LASTEXITCODE -ne 0) {
            Write-Host $text -ForegroundColor Red
            throw "vercel env add $Name failed (exit $LASTEXITCODE)"
        }
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npx not found. Install Node.js from https://nodejs.org" -ForegroundColor Red
    exit 1
}

if (-not $AuthSecret -and (Test-Path $prodSecretsFile)) {
    $secretLine = Get-Content $prodSecretsFile | Where-Object { $_ -match "^AUTH_SECRET=" } | Select-Object -First 1
    if ($secretLine) {
        $AuthSecret = ($secretLine -replace "^AUTH_SECRET=", "").Trim()
    }
}

if (-not $ResendKey -and (Test-Path $envLocal)) {
    $line = Get-Content $envLocal | Where-Object { $_ -match "^AUTH_RESEND_KEY=" } | Select-Object -First 1
    if ($line) {
        $ResendKey = ($line -replace "^AUTH_RESEND_KEY=", "").Trim()
    }
}
if (-not $ResendKey) {
    Write-Host "ERROR: AUTH_RESEND_KEY not found. Pass -ResendKey or set it in frontend/.env.local" -ForegroundColor Red
    exit 1
}

if (-not $AuthSecret) {
    $AuthSecret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
}

$vars = [ordered]@{
    AUTH_DATABASE_URL = $DatabaseUrl.Trim().Trim('"').Trim("'")
    AUTH_SECRET       = $AuthSecret
    AUTH_URL          = $ProdUrl
    APP_BASE_URL      = $ProdUrl
    AUTH_RESEND_KEY   = $ResendKey
    EMAIL_FROM        = $EmailFrom
}

Write-Host ""
Write-Host "=== Vercel Production auth env ===" -ForegroundColor Cyan
Write-Host "Target: $Scope/$Project" -ForegroundColor DarkGray
Write-Host ""
Write-Host "AUTH_SECRET for Vercel:" -ForegroundColor Yellow
Write-Host "  $AuthSecret" -ForegroundColor White
Write-Host ""

Push-Location $frontendDir
try {
    # Do NOT pass --project to whoami (CLI treats the next token as a folder path).
    $whoResult = Invoke-VercelCli whoami
    $who = Get-WhoAmILine $whoResult.Output
    if ($whoResult.ExitCode -ne 0 -or -not $who) {
        Write-Host "ERROR: Vercel CLI auth failed." -ForegroundColor Red
        Write-Host $whoResult.Output -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "Run: npx vercel@latest login" -ForegroundColor Yellow
        Write-Host "Or:  -VercelToken from https://vercel.com/account/tokens" -ForegroundColor Yellow
        Write-Host "Or paste manually: .\scripts\print-vercel-auth-values.ps1 -DatabaseUrl `"...`"" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Vercel account: $who" -ForegroundColor DarkGray
    Write-Host ""

    foreach ($entry in $vars.GetEnumerator()) {
        Set-VercelProdEnvValue -Name $entry.Key -Value $entry.Value
        Write-Host "  OK: $($entry.Key)" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "All 6 Production auth env vars set on Vercel." -ForegroundColor Green
    Write-Host "Verify in dashboard: Vercel -> Settings -> Environment Variables -> Production" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Next: Vercel -> Deployments -> Redeploy latest" -ForegroundColor Yellow
    Write-Host "Then: https://smpl-financial-intelligence.vercel.app/login" -ForegroundColor Yellow
    Write-Host ""
}
finally {
    Pop-Location
}
