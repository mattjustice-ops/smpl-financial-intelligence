# List organizations in production Neon.
#
# Usage:
#   .\scripts\list-prod-organizations.ps1

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot
if (-not $resolved) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

$dbUrl = $resolved.Url
if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl
    & $python (Join-Path $backendDir "scripts\list_organizations.py")
}
finally {
    Pop-Location
}
