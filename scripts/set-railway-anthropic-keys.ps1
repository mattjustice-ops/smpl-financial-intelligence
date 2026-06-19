# Set ANTHROPIC_API_KEY on Railway sandbox + production backend services.
#
# Prerequisites:
#   npx @railway/cli login
#
# Usage (repo root):
#   .\scripts\set-railway-anthropic-keys.ps1
#   .\scripts\set-railway-anthropic-keys.ps1 -KeysFile "C:\Windows\System32\Claude Keys.txt"
#   .\scripts\set-railway-anthropic-keys.ps1 -SkipSandbox          # prod only (sandbox already set)
#   .\scripts\set-railway-anthropic-keys.ps1 -ProdService sfi-api  # override prod service name

param(
    [string]$KeysFile = "C:\Windows\System32\Claude Keys.txt",
    [string]$SandboxService = "sfi-api-staging",
    [string]$ProdService = "sfi-api",
    [string]$AnthropicModel = "claude-sonnet-4-20250514",
    [string]$RailwayToken = "",
    [switch]$PrintOnly,
    [switch]$SkipSandbox,
    [switch]$SkipProd
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$importScript = Join-Path $backendDir "scripts\import-anthropic-keys.ps1"

# npx writes notices to stderr; PowerShell can treat those as errors with Stop preference.
$env:NPM_CONFIG_UPDATE_NOTIFIER = "false"
$env:NPM_CONFIG_FUND = "false"
$env:NPM_CONFIG_LOGLEVEL = "error"

if ($RailwayToken) {
    $env:RAILWAY_TOKEN = $RailwayToken.Trim()
}

function Get-RailwayInvoker {
    if (Get-Command railway -ErrorAction SilentlyContinue) {
        return @{
            Label  = "railway"
            Invoke = { param([string[]]$CliArgs) & railway @CliArgs }
        }
    }
    return @{
        Label  = "npx @railway/cli"
        Invoke = { param([string[]]$CliArgs) & npx --yes --silent @railway/cli @CliArgs }
    }
}

function Normalize-RailwayOutput {
    param([string]$Text)

    if (-not $Text) { return "" }
    $filtered = @()
    foreach ($line in ($Text -split "`r?`n")) {
        $t = $line.Trim()
        if (-not $t) { continue }
        if ($t -match '^(npm (notice|warn|ERR!)|npm$)') { continue }
        $filtered += $t
    }
    return ($filtered -join "`n").Trim()
}

function Invoke-RailwayCli {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)

    Push-Location $backendDir
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $raw = & $railwayInvoker.Invoke $CliArgs 2>&1
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
        $lines = @()
        foreach ($item in $raw) { $lines += "$item" }
        return @{
            ExitCode = $exitCode
            Output   = (Normalize-RailwayOutput (($lines -join "`n").Trim()))
        }
    }
    finally {
        Pop-Location
    }
}

function Parse-ClaudeKeys([string]$raw) {
    $map = @{}
    $pending = $null
    foreach ($line in ($raw -split "`r?`n")) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        if ($t -match '^(?i)smpl-(local|sandbox|prod)\s*$') {
            $pending = "smpl-$($Matches[1].ToLower())"
            continue
        }
        if ($t -match '^(sk-ant-[A-Za-z0-9_\-\.]+)$' -and $pending) {
            $map[$pending] = $Matches[1]
            $pending = $null
        }
    }
    return $map
}

function Get-RailwayServiceNames {
    $result = Invoke-RailwayCli service list
    if ($result.ExitCode -ne 0 -or -not $result.Output) {
        return @()
    }

    $names = @()
    foreach ($line in ($result.Output -split "`r?`n")) {
        $t = $line.Trim()
        if (-not $t) { continue }
        if ($t -match '^(Services|Project|--|Available|Linked|Use )') { continue }
        if ($t -match '^[\*\>]?\s*([A-Za-z0-9][A-Za-z0-9\-_]*)\s*$') {
            $names += $Matches[1]
        }
    }
    return ($names | Select-Object -Unique)
}

function Resolve-ProdServiceName {
    param(
        [string]$Preferred,
        [string]$SandboxServiceName
    )

    $candidates = @(
        $Preferred
        "sfi-api"
        "sfi-api-production"
        "sfi-api-prod"
    ) | Where-Object { $_ } | Select-Object -Unique

    $listed = Get-RailwayServiceNames
    if ($listed.Count -gt 0) {
        Write-Host "Railway services: $($listed -join ', ')" -ForegroundColor DarkGray
        foreach ($candidate in $candidates) {
            if ($listed -contains $candidate) {
                return $candidate
            }
        }

        $nonSandbox = $listed | Where-Object {
            $_ -ne $SandboxServiceName -and $_ -notmatch '(?i)staging|sandbox'
        }
        if ($nonSandbox) {
            return ($nonSandbox | Select-Object -First 1)
        }
    }

    return ($Preferred | Select-Object -First 1)
}

function Set-RailwayServiceVars {
    param(
        [string]$ServiceName,
        [string]$AnthropicKey
    )

    Write-Host ""
    Write-Host "Service: $ServiceName" -ForegroundColor Yellow

    foreach ($pair in @(
            "ANTHROPIC_API_KEY=$AnthropicKey"
            "ANTHROPIC_MODEL=$AnthropicModel"
        )) {
        $name = ($pair -split "=", 2)[0]
        if ($PrintOnly) {
            Write-Host "  $pair" -ForegroundColor DarkGray
            continue
        }

        $setArgs = @("variables", "--set", $pair, "--service", $ServiceName)
        $result = Invoke-RailwayCli @setArgs
        if ($result.ExitCode -ne 0) {
            Write-Host $result.Output -ForegroundColor Red
            Write-Host "Failed to set $name on $ServiceName (exit $($result.ExitCode))." -ForegroundColor Red
            if ($result.Output -match 'not found') {
                Write-Host "Tip: list services with: cd backend; npx @railway/cli service list" -ForegroundColor Yellow
                Write-Host "Then re-run with -ProdService <name> or -SandboxService <name>." -ForegroundColor Yellow
            }
            exit 1
        }
        Write-Host "  OK: $name" -ForegroundColor Green
    }
}

if (-not (Test-Path -LiteralPath $KeysFile)) {
    Write-Host "Keys file not found: $KeysFile" -ForegroundColor Red
    exit 1
}

$keys = Parse-ClaudeKeys (Get-Content -LiteralPath $KeysFile -Raw)
if (-not $keys["smpl-sandbox"] -or -not $keys["smpl-prod"]) {
    Write-Host "Expected smpl-sandbox and smpl-prod keys in: $KeysFile" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Railway Anthropic keys ===" -ForegroundColor Cyan

$railwayInvoker = Get-RailwayInvoker
if (-not $PrintOnly) {
    Write-Host "Using: $($railwayInvoker.Label)" -ForegroundColor DarkGray
    Write-Host ""
}

$resolvedProdService = if ($PrintOnly) {
    $ProdService
} else {
    Resolve-ProdServiceName -Preferred $ProdService -SandboxServiceName $SandboxService
}
if ($resolvedProdService -ne $ProdService) {
    Write-Host "Production service resolved to: $resolvedProdService" -ForegroundColor DarkGray
}

if ($PrintOnly) {
    Write-Host "Print-only mode - paste into Railway dashboard if CLI is unavailable." -ForegroundColor Yellow
    if (-not $SkipSandbox) {
        Set-RailwayServiceVars -ServiceName $SandboxService -AnthropicKey $keys["smpl-sandbox"]
    }
    if (-not $SkipProd) {
        Set-RailwayServiceVars -ServiceName $resolvedProdService -AnthropicKey $keys["smpl-prod"]
    }
    exit 0
}

$who = Invoke-RailwayCli whoami
if ($who.ExitCode -ne 0 -or -not $who.Output) {
    Write-Host "ERROR: Railway CLI not logged in." -ForegroundColor Red
    Write-Host $who.Output -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Run: cd backend; npx @railway/cli login" -ForegroundColor Yellow
    Write-Host "Or re-run with -PrintOnly and paste into Railway Variables." -ForegroundColor Yellow
    exit 1
}

Write-Host "Railway account: $($who.Output -split "`n" | Select-Object -First 1)" -ForegroundColor DarkGray

if (-not $SkipSandbox) {
    Set-RailwayServiceVars -ServiceName $SandboxService -AnthropicKey $keys["smpl-sandbox"]
}
else {
    Write-Host ""
    Write-Host "Skipping sandbox ($SandboxService) - already configured." -ForegroundColor DarkGray
}

if (-not $SkipProd) {
    Set-RailwayServiceVars -ServiceName $resolvedProdService -AnthropicKey $keys["smpl-prod"]
}

& $importScript -Path $KeysFile | Out-Null

Write-Host ""
Write-Host "OK: Anthropic keys set on Railway sandbox + production." -ForegroundColor Green
Write-Host "Railway will redeploy both services automatically." -ForegroundColor DarkGray
Write-Host ""
Write-Host "Verify after deploy:" -ForegroundColor Cyan
Write-Host '  curl https://sfi-api-staging-production.up.railway.app/api/v1/export/ping' -ForegroundColor White
Write-Host '  curl https://sfi-api-production.up.railway.app/api/v1/export/ping' -ForegroundColor White
