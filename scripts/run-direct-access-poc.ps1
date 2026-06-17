# poc-0 Path A: white-glove direct-access POC (provision org + load warehouse + verify).
#
# Prerequisite: customer exports staged locally in -CsvFolder (SMPL-shaped CSVs).
#
# Usage — new customer POC:
#   $env:DATABASE_URL = "postgresql://..."
#   .\scripts\run-direct-access-poc.ps1 `
#     -Email admin@acme.com `
#     -OrganizationName "Acme Corp" `
#     -CsvFolder "D:\smpl-staging\acme-poc" `
#     -AccessMethod snowflake
#
# Usage — org already provisioned, load data only:
#   .\scripts\run-direct-access-poc.ps1 `
#     -Email admin@acme.com `
#     -OrganizationId "uuid-here" `
#     -CsvFolder "D:\smpl-staging\acme-poc" `
#     -SkipProvision
#
# Preview CSVs without loading:
#   .\scripts\run-direct-access-poc.ps1 ... -ListOnly

param(
    [Parameter(Mandatory = $true)]
    [string]$Email,
    [string]$OrganizationName = "",
    [string]$OrganizationId = "",
    [string]$DatabaseUrl = "",
    [string]$CsvFolder = "",
    [ValidateSet("starter", "professional", "enterprise")]
    [string]$Plan = "enterprise",
    [ValidateSet("snowflake", "s3", "erp", "sftp", "other")]
    [string]$AccessMethod = "other",
    [string]$AccessNotes = "",
    [switch]$SkipProvision,
    [switch]$SkipWarehouseLoad,
    [switch]$UseBundledDemoData,
    [switch]$ListOnly,
    [switch]$SkipSecurityAck,
    [switch]$TryVercelPull
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$prodLogin = "https://smpl-financial-intelligence.vercel.app/login"

function Write-SecurityChecklist {
    Write-Host ""
    Write-Host "=== Security checklist (direct access) ===" -ForegroundColor Cyan
    Write-Host '  [ ] Written scope: systems, date range, entities' -ForegroundColor DarkGray
    Write-Host '  [ ] Read-only access to customer systems' -ForegroundColor DarkGray
    Write-Host '  [ ] Credentials in password manager - not in git/chat' -ForegroundColor DarkGray
    Write-Host '  [ ] Staging copy retention policy agreed' -ForegroundColor DarkGray
    Write-Host '  [ ] Customer can revoke access after POC' -ForegroundColor DarkGray
    Write-Host '  [ ] Correct organization_id before warehouse load' -ForegroundColor DarkGray
    Write-Host ""
}

Write-Host ""
Write-Host "=== poc-0: Direct data access POC (Path A) ===" -ForegroundColor Cyan
Write-Host "Access method: $AccessMethod" -ForegroundColor White
if ($AccessNotes) {
    Write-Host "Notes:         $AccessNotes" -ForegroundColor DarkGray
}
Write-Host ""

Write-SecurityChecklist

if (-not $SkipSecurityAck) {
    $ack = Read-Host "Type YES to confirm security checklist reviewed"
    if ($ack -ne "YES") {
        Write-Host "Aborted. Re-run with -SkipSecurityAck only for non-prod dry runs." -ForegroundColor Yellow
        exit 1
    }
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
    Write-Host "ERROR: Use production Neon DATABASE_URL." -ForegroundColor Red
    exit 1
}

# Fail fast before creating an org if customer CSV folder is missing.
if (-not $SkipWarehouseLoad -and -not $ListOnly -and -not $UseBundledDemoData) {
    if (-not $CsvFolder) {
        Write-Host "ERROR: Pass -CsvFolder with staged customer exports." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path -LiteralPath $CsvFolder)) {
        Write-Host "ERROR: CSV folder not found: $CsvFolder" -ForegroundColor Red
        Write-Host ""
        Write-Host "Create the folder and copy customer exports, then re-run." -ForegroundColor Yellow
        Write-Host "If org was already provisioned, use -SkipProvision -OrganizationId <uuid>." -ForegroundColor Yellow
        exit 1
    }
}

$orgId = $OrganizationId.Trim()

if (-not $SkipProvision) {
    if (-not $OrganizationName -and -not $orgId) {
        Write-Host "ERROR: Pass -OrganizationName for a new customer org, or -OrganizationId with -SkipProvision." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "[1/3] Provision org + invite ..." -ForegroundColor Yellow

    $backendDir = Join-Path $repoRoot "backend"
    $python = Join-Path $backendDir ".venv312\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    $provisionPy = Join-Path $backendDir "scripts\provision_customer.py"

    $pyArgs = @($provisionPy, "--email", $Email, "--plan", $Plan)
    if ($OrganizationName) { $pyArgs += @("--organization-name", $OrganizationName) }
    if ($orgId) { $pyArgs += @("--organization-id", $orgId) }

    $dbUrl = $DatabaseUrl
    if ($dbUrl -match "^postgresql://") {
        $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
    }

    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $dbUrl
        $provisionLines = & $python @pyArgs 2>&1
        $provisionLines | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }

    $idLine = $provisionLines | Where-Object { "$_" -match "^ORGANIZATION_ID=" } | Select-Object -Last 1
    if ($idLine -match "^ORGANIZATION_ID=(.+)$") {
        $orgId = $Matches[1].Trim()
    }
    if (-not $orgId) {
        Write-Host "ERROR: Could not parse ORGANIZATION_ID from provision output." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Organization ID: $orgId" -ForegroundColor Green
} else {
    if (-not $orgId) {
        Write-Host "ERROR: -SkipProvision requires -OrganizationId." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "[1/3] Skipping provision (-SkipProvision)" -ForegroundColor DarkGray
    Write-Host "  Organization ID: $orgId" -ForegroundColor DarkGray
}

if ($ListOnly) {
    if (-not $CsvFolder) {
        Write-Host "ERROR: -ListOnly requires -CsvFolder." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "[2/3] List CSV files only ..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "setup-prod-warehouse.ps1") `
        -DatabaseUrl $DatabaseUrl `
        -OrganizationId $orgId `
        -CsvFolder $CsvFolder `
        -ListOnly
    exit $LASTEXITCODE
}

if (-not $SkipWarehouseLoad) {
    if (-not $CsvFolder -and -not $UseBundledDemoData) {
        Write-Host ""
        Write-Host "ERROR: Pass -CsvFolder with staged customer exports, or -UseBundledDemoData for a dry run." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "[2/3] Load warehouse ..." -ForegroundColor Yellow

    $warehouseArgs = @{
        DatabaseUrl    = $DatabaseUrl
        OrganizationId = $orgId
    }

    if ($UseBundledDemoData) {
        if (-not $CsvFolder) {
            $CsvFolder = Join-Path $repoRoot "backend\demo_data"
        }
        $warehouseArgs.CsvFolder = $CsvFolder
        Write-Host "  Dry run: bundled demo_data + CSV folder $CsvFolder" -ForegroundColor DarkGray
    } else {
        $warehouseArgs.CsvFolder = $CsvFolder
        $warehouseArgs.SkipBundledDemo = $true
        Write-Host "  Customer CSV folder: $CsvFolder (no bundled demo_data)" -ForegroundColor DarkGray
    }

    & (Join-Path $PSScriptRoot "setup-prod-warehouse.ps1") @warehouseArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host ""
    Write-Host "[2/3] Skipping warehouse load (-SkipWarehouseLoad)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[3/3] Verify warehouse + access ..." -ForegroundColor Yellow
$verifyArgs = @{
    OrganizationId = $orgId
    Email          = $Email
    DatabaseUrl    = $DatabaseUrl
}
& (Join-Path $PSScriptRoot "smoke-test-direct-access-poc.ps1") @verifyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== poc-0 run complete ===" -ForegroundColor Green
Write-Host "Org ID:    $orgId" -ForegroundColor White
Write-Host "Plan:      $Plan" -ForegroundColor White
Write-Host "Login:     $prodLogin" -ForegroundColor White
Write-Host "Customer:  $Email (sign out and sign in after first invite)" -ForegroundColor White
Write-Host ""
Write-Host 'Mark poc-0 done on /progress after validation call with customer.' -ForegroundColor Yellow
Write-Host 'Doc: docs/GO_LIVE_POC_DIRECT_DATA_ACCESS.md' -ForegroundColor DarkGray
Write-Host ""
