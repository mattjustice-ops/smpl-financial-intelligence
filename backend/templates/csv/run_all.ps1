# Generate SMPL CSV templates + calculation lineage exports.
# Run from anywhere:
#   powershell -File backend\templates\csv\run_all.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $repoRoot

Write-Host ""
Write-Host "SMPL CSV template generator" -ForegroundColor Cyan
Write-Host "Repo: $repoRoot"
Write-Host ""

$py = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $py = $candidate
        break
    }
}
if (-not $py) {
    Write-Host "ERROR: Python not found on PATH." -ForegroundColor Red
    exit 1
}

& $py "backend\templates\csv\generate_templates.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py "backend\templates\csv\calculation_lineage.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$out = Join-Path $repoRoot "backend\templates\csv"

Write-Host ""
Write-Host "Done. Open these files:" -ForegroundColor Green
Write-Host "  Lineage trace-back: $out\Calculation_Lineage_Registry.csv"
Write-Host "  Gaps only:          $out\Calculation_Lineage_Gaps.csv"
Write-Host "  Dependencies:       $out\Calculation_Dataset_Dependencies.csv"
Write-Host ""
Write-Host "CSV templates (headers only):" -ForegroundColor Yellow
Write-Host "  $out\01-source-inputs\"
Write-Host "  $out\03-calculated-outputs\actual\"
Write-Host ""
Write-Host "Templates are header rows only. Lineage CSV has formulas and source trace-back."
Write-Host ""
