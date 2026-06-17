# Set SFI_BACKEND_URL + NEXT_PUBLIC_API_URL on Vercel Preview (gl-5 staging).
#
# Usage:
#   .\scripts\set-vercel-staging-env.ps1 -BackendUrl "https://sfi-api-staging-xxxx.up.railway.app"
#
# Dashboard fallback (recommended if CLI fails):
#   .\scripts\print-vercel-preview-api-values.ps1

param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [string]$VercelToken = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence",
    [switch]$DashboardOnly
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$url = $BackendUrl.Trim().Trim('"').Trim("'").TrimEnd("/")

if ($url -match "YOUR-|YOUR-SERVICE|example\.com") {
    Write-Host "ERROR: Replace the placeholder with your real Railway staging URL." -ForegroundColor Red
    exit 1
}

if ($url -match "sfi-api-production\.up\.railway\.app") {
    Write-Host "ERROR: That is the production API. Use sfi-api-staging (staging service URL)." -ForegroundColor Red
    exit 1
}

if ($DashboardOnly) {
    & (Join-Path $repoRoot "scripts\print-vercel-preview-api-values.ps1") -StagingApi $url
    exit 0
}

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
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)

    Push-Location $frontendDir
    try {
        $npxArgs = Get-NpxBaseArgs + Get-VercelProjectArgs
        # Avoid piping to ForEach-Object — it breaks $LASTEXITCODE on Windows PowerShell.
        $raw = & npx @npxArgs @CliArgs 2>&1
        $lines = @()
        foreach ($item in $raw) {
            $lines += "$item"
        }
        return @{
            ExitCode = $LASTEXITCODE
            Output   = ($lines -join "`n").Trim()
        }
    }
    finally {
        Pop-Location
    }
}

function Set-VercelPreviewEnvValue {
    param([string]$Name, [string]$Value)

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        $npxArgs = Get-NpxBaseArgs + Get-VercelProjectArgs
        Push-Location $frontendDir
        try {
            $raw = Get-Content -LiteralPath $tempFile -Raw | & npx @npxArgs env add $Name preview --yes --force 2>&1
            $lines = @()
            foreach ($item in $raw) { $lines += "$item" }
            $text = ($lines -join "`n").Trim()
            $exitCode = $LASTEXITCODE

            if ($text -match "Deploying outputs|Build Completed in /vercel/output|Uploading \[") {
                return @{ Ok = $false; Message = "Vercel CLI ran deploy instead of env add."; Output = $text }
            }
            if ($exitCode -ne 0) {
                return @{
                    Ok      = $false
                    Message = "vercel env add $Name preview failed (exit $exitCode)"
                    Output  = $text
                }
            }
            return @{ Ok = $true; Message = ""; Output = $text }
        }
        finally {
            Pop-Location
        }
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "=== Vercel Preview (staging) API env ===" -ForegroundColor Cyan
Write-Host "Backend URL: $url" -ForegroundColor DarkGray
Write-Host ""

$who = Invoke-VercelCli -whoami
if ($who.ExitCode -eq 0 -and $who.Output) {
    $account = ($who.Output -split "`n" | Where-Object { $_ -and $_ -notmatch "Vercel CLI" } | Select-Object -First 1)
    if ($account) {
        Write-Host "Vercel account: $account" -ForegroundColor DarkGray
    }
}
else {
    Write-Host "WARN: vercel whoami failed. Run: npx vercel login" -ForegroundColor Yellow
    if ($who.Output) { Write-Host $who.Output -ForegroundColor DarkGray }
}
Write-Host ""

$failed = $false
foreach ($pair in @(@{ Name = "SFI_BACKEND_URL"; Value = $url }, @{ Name = "NEXT_PUBLIC_API_URL"; Value = $url })) {
    $res = Set-VercelPreviewEnvValue -Name $pair.Name -Value $pair.Value
    if ($res.Ok) {
        Write-Host "  OK: $($pair.Name) (preview)" -ForegroundColor Green
    }
    else {
        $failed = $true
        Write-Host "  FAIL: $($pair.Name)" -ForegroundColor Red
        if ($res.Output) {
            Write-Host $res.Output -ForegroundColor DarkGray
        }
        if ($res.Message) {
            Write-Host "  $($res.Message)" -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
if ($failed) {
    Write-Host "CLI could not update Preview env. Use the dashboard (fastest):" -ForegroundColor Yellow
    Write-Host ""
    & (Join-Path $repoRoot "scripts\print-vercel-preview-api-values.ps1") -StagingApi $url
    exit 1
}

Write-Host "Verifying..." -ForegroundColor DarkGray
& (Join-Path $repoRoot "scripts\verify-vercel-preview-api-url.ps1") -Scope $Scope -Project $Project
exit $LASTEXITCODE
