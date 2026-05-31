# Import OPENAI_API_KEY from a local text file (Notepad, upload export, etc.)
param(
    [string]$Path = ""
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path $PSScriptRoot -Parent
$secretsPath = Join-Path $backendRoot "secrets.env"

function Resolve-SourceFile([string]$p) {
    if ($p -and (Test-Path -LiteralPath $p)) { return (Resolve-Path -LiteralPath $p).Path }
    $candidates = @()
    if ($p) {
        $candidates += $p, "$p.txt", "$p.md", "$p.json"
        if ($p -match '\.env$') { $candidates += "$p.txt" }
    }
    $candidates += @(
        "$env:USERPROFILE\Downloads\ChatGPT API Commentary Key.txt",
        "$env:USERPROFILE\Downloads\upload_result",
        "$env:USERPROFILE\Downloads\upload_result.json",
        "$env:USERPROFILE\Downloads\upload_result.txt",
        "$env:USERPROFILE\Downloads\OPENAI_API_KEY.txt"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return (Resolve-Path -LiteralPath $c).Path }
    }
    $dl = Join-Path $env:USERPROFILE "Downloads"
    if (Test-Path $dl) {
        $hit = Get-ChildItem -LiteralPath $dl -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match 'upload|openai|api.?key|chatgpt.*commentary.*key' } |
            Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

$source = Resolve-SourceFile $Path
if (-not $source) {
    Write-Host "No file found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Either:"
    Write-Host "  1. Save your Notepad note to a file, e.g. C:\Users\mattj\Downloads\openai-key.txt"
    Write-Host "     Then: .\scripts\import-openai-key.ps1 -Path `"C:\Users\mattj\Downloads\openai-key.txt`""
    Write-Host ""
    Write-Host "  2. Or run (paste key at prompt, hidden): .\scripts\set-openai-key.ps1"
    exit 1
}

$raw = Get-Content -LiteralPath $source -Raw
$key = $null

if ($raw -match '(?m)^\s*OPENAI_API_KEY\s*=\s*(\S+)\s*$') {
    $key = $Matches[1].Trim().Trim('"').Trim("'")
} elseif ($raw -match '(sk-[A-Za-z0-9_\-\.]+)') {
    $key = $Matches[1]
}

if (-not $key -or $key -eq 'sk-your-actual-key-here' -or $key -eq 'sk-your-key-here') {
    Write-Host "Found file: $source" -ForegroundColor Yellow
    if ($raw -match 'uvicorn|load_versioned_csvs|sync_warehouse') {
        Write-Host "That file is a command log, not an API key file." -ForegroundColor Red
    } elseif ($raw -match 'DATABASE_URL' -and $raw -notmatch 'OPENAI_API_KEY') {
        Write-Host "That .env file has database/CORS settings but no OPENAI_API_KEY line." -ForegroundColor Red
        Write-Host "Add this line to the file (with your real key from platform.openai.com):"
        Write-Host "  OPENAI_API_KEY=sk-proj-..." -ForegroundColor Cyan
        Write-Host "Then re-run this script, OR use .\scripts\set-openai-key.ps1"
    } else {
        Write-Host "No sk-... API key found in that file." -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Fastest fix: .\scripts\set-openai-key.ps1"
    Write-Host "Create key: https://platform.openai.com/api-keys"
    exit 1
}

$content = @"
# Imported from $source on $(Get-Date -Format 'yyyy-MM-dd HH:mm')
OPENAI_API_KEY=$key
OPENAI_MODEL=gpt-4o-mini
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($secretsPath, $content, $utf8NoBom)
Write-Host "Wrote backend/secrets.env from:" $source -ForegroundColor Green
Write-Host "Restart API: .\start-api.ps1"
