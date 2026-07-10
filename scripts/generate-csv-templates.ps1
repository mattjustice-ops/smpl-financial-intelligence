# Generate CSV templates + calculation lineage from repo root.
# Usage (from anywhere):
#   powershell -File scripts\generate-csv-templates.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
& (Join-Path $repoRoot "backend\templates\csv\run_all.ps1")
