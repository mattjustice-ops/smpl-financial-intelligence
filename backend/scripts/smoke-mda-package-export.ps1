# MDA package export smoke (read-only Neon, writes XLSX only)
#
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-package-export.ps1" -LocalExport

param(
    [string]$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$ClosePeriod = "2026-06",
    [switch]$LocalExport
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Split-Path -Parent $scriptDir

function Import-DatabaseUrlFromEnvFiles {
    if ($env:DATABASE_URL) { return }
    foreach ($file in @(
            (Join-Path $backendRoot ".env"),
            (Join-Path $backendRoot "secrets.env"),
            (Join-Path $backendRoot ".env.local")
        )) {
        if (-not (Test-Path $file)) { continue }
        Get-Content $file | ForEach-Object {
            if ($_ -match '^\s*DATABASE_URL\s*=\s*(.+)\s*$') {
                $env:DATABASE_URL = $matches[1].Trim().Trim('"').Trim("'")
            }
        }
        if ($env:DATABASE_URL) {
            Write-Host ("  Loaded DATABASE_URL from {0}" -f $file) -ForegroundColor DarkGray
            return
        }
    }
}

function Invoke-LocalPython {
    param([string[]]$PythonArgs)
    $python = Join-Path $backendRoot ".venv312\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = Join-Path $backendRoot ".venv\Scripts\python.exe"
    }
    Import-DatabaseUrlFromEnvFiles
    if (-not $env:DATABASE_URL) {
        Write-Host "   DATABASE_URL not found in backend\.env" -ForegroundColor Red
        exit 1
    }
    $env:MDA_CLOSE_PERIOD = $ClosePeriod
    Push-Location $backendRoot
    try {
        & $python @PythonArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

Write-Host "SMPL MDA package export" -ForegroundColor White
Write-Host ("  Org:    {0}" -f $OrgId)
Write-Host ("  Period: {0}" -f $ClosePeriod)

if ($LocalExport) {
    Write-Host ""
    Write-Host "=== Local SMPL_MDA_Package export (Claude Prompt 2) ===" -ForegroundColor Cyan
    Invoke-LocalPython @((Join-Path $backendRoot "scripts\export_mda_package_local.py"))
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

Write-Host "Pass -LocalExport to build the workbook locally." -ForegroundColor Yellow
