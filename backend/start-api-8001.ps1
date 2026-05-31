# Start API on port 8001 when port 8000 is stuck on a stale process.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Import-BackendSecrets {
    $secretsPath = Join-Path $PSScriptRoot "secrets.env"
    if (-not (Test-Path -LiteralPath $secretsPath)) { return }
    foreach ($line in Get-Content -LiteralPath $secretsPath) {
        if ($line -match '^\s*#\s*' -or $line -notmatch '\S') { continue }
        if ($line -match '^\s*OPENAI_API_KEY\s*=\s*(.+)\s*$') {
            $env:OPENAI_API_KEY = $Matches[1].Trim().Trim('"').Trim("'")
        }
        if ($line -match '^\s*OPENAI_MODEL\s*=\s*(.+)\s*$') {
            $env:OPENAI_MODEL = $Matches[1].Trim().Trim("'")
        }
    }
}
Import-BackendSecrets

$venvPython = $null
foreach ($venvName in @(".venv312", ".venv")) {
    $candidate = Join-Path $PSScriptRoot "$venvName\Scripts\python.exe"
    if (Test-Path -LiteralPath $candidate) { $venvPython = $candidate; break }
}
if (-not $venvPython) { throw "No .venv312 or .venv found under backend" }

Write-Host "Python: $venvPython"
& $venvPython -c "from app.core.config import get_settings; s=get_settings(); print('OpenAI:', 'configured' if s.openai_api_key else 'NOT SET')"

Write-Host "Starting API at http://127.0.0.1:8001 (use this URL in the dashboard)"
Write-Host "Set frontend: NEXT_PUBLIC_API_URL=http://127.0.0.1:8001"
& $venvPython -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
