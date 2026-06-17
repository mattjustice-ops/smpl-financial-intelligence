# poc-0 smoke test: verify org + warehouse after direct-access load.
#
# Usage:
#   .\scripts\smoke-test-direct-access-poc.ps1 `
#     -OrganizationId "uuid" `
#     -Email admin@customer.com

param(
    [Parameter(Mandatory = $true)]
    [string]$OrganizationId,
    [string]$Email = "",
    [string]$DatabaseUrl = "",
    [int]$MinRows = 1,
    [switch]$TryVercelPull
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if (-not $DatabaseUrl) {
    $resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot -TryVercelPull:$TryVercelPull
    if ($resolved) { $DatabaseUrl = $resolved.Url }
}
if (-not $DatabaseUrl) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

$dbUrl = $DatabaseUrl
if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}

$argsList = @(
    (Join-Path $backendDir "scripts\verify_warehouse_org.py"),
    "--organization-id", $OrganizationId,
    "--min-rows", $MinRows
)
if ($Email) {
    $argsList += @("--email", $Email)
}

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
