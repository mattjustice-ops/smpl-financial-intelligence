# gl-1: Provision a production customer (Neon org + pending invite).
#
# Add user to existing demo org:
#   .\scripts\provision-prod-customer.ps1 `
#     -DatabaseUrl "postgresql://..." `
#     -Email colleague@theircompany.com
#
# New customer org:
#   .\scripts\provision-prod-customer.ps1 `
#     -DatabaseUrl "postgresql://..." `
#     -Email admin@acme.com `
#     -OrganizationName "Acme Corp" `
#     -Plan professional

param(
    [Parameter(Mandatory = $true)]
    [string]$Email,
    [string]$DatabaseUrl = "",
    [string]$OrganizationId = "",
    [string]$OrganizationName = "",
    [ValidateSet("starter", "professional", "enterprise")]
    [string]$Plan = "professional",
    [string]$Role = "admin",
    [switch]$UseDemoOrg,
    [switch]$TryVercelPull
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$pythonScript = Join-Path $backendDir "scripts\provision_customer.py"
$venvPython = Join-Path $backendDir ".venv312\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

function Convert-ToAlembicUrl {
    param([string]$Url)
    $normalized = $Url.Trim().Trim('"').Trim("'")
    if ($normalized -match "^postgresql://") {
        return $normalized -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($normalized -match "^postgres://") {
        return $normalized -replace "^postgres://", "postgresql+psycopg://"
    }
    return $normalized
}

if (-not $DatabaseUrl) {
    $resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot -TryVercelPull:$TryVercelPull
    if ($resolved) {
        $DatabaseUrl = $resolved.Url
        Write-Host ("Using {0} from {1}" -f $resolved.Name, $resolved.Source) -ForegroundColor DarkGray
    }
}

if (-not $DatabaseUrl) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

if (Test-IsLocalDatabaseUrl $DatabaseUrl) {
    Write-Host "ERROR: Production scripts cannot use localhost DATABASE_URL." -ForegroundColor Red
    Write-ProdDatabaseUrlHelp
    exit 1
}

$alembicUrl = Convert-ToAlembicUrl $DatabaseUrl

Write-Host ""
Write-Host "=== gl-1: Provision production customer ===" -ForegroundColor Cyan
Write-Host "Email: $Email" -ForegroundColor White
Write-Host ""

$argsList = @(
    $pythonScript,
    "--email", $Email,
    "--plan", $Plan,
    "--role", $Role
)

if ($UseDemoOrg) {
    $argsList += @("--organization-id", "8571e520-0687-4516-bdee-379f37c58c1f")
} elseif ($OrganizationId) {
    $argsList += @("--organization-id", $OrganizationId)
    if ($OrganizationName) {
        $argsList += @("--organization-name", $OrganizationName)
    }
} elseif ($OrganizationName) {
    $argsList += @("--organization-name", $OrganizationName)
} else {
    $argsList += @("--organization-id", "8571e520-0687-4516-bdee-379f37c58c1f")
    Write-Host "No org specified - adding invite to SMPL Demo Co (8571e520-...)." -ForegroundColor DarkGray
    Write-Host "For a new customer org, pass -OrganizationName `"Acme Corp`"." -ForegroundColor DarkGray
    Write-Host ""
}

Push-Location $backendDir
try {
    $env:DATABASE_URL = $alembicUrl
    & $python @argsList
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

Write-Host "Verify access:" -ForegroundColor Yellow
Write-Host "  .\scripts\check-login-access.ps1 -Email $Email" -ForegroundColor White
Write-Host ""
Write-Host "New org with empty dashboards? Load warehouse data:" -ForegroundColor DarkGray
Write-Host "  .\scripts\setup-prod-warehouse.ps1 -DatabaseUrl `"...`" -OrganizationId <id-from-output>" -ForegroundColor White
Write-Host ""
