# Create or update backend/secrets.env with your OpenAI API key (PowerShell-safe).
# Usage:
#   .\scripts\set-openai-key.ps1
#   .\scripts\set-openai-key.ps1 -Key "sk-proj-...."
param(
    [string]$Key = ""
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path $PSScriptRoot -Parent
$secretsPath = Join-Path $backendRoot "secrets.env"

if (-not $Key) {
    $secure = Read-Host "Paste your OpenAI API key (starts with sk-)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $Key = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) | Out-Null
    }
}

$Key = $Key.Trim().Trim('"').Trim("'")
if (-not $Key.StartsWith("sk-")) {
    Write-Host "Key should start with sk-. You entered something else." -ForegroundColor Red
    exit 1
}

$content = @"
# Local secrets (gitignored). Created $(Get-Date -Format 'yyyy-MM-dd HH:mm')
OPENAI_API_KEY=$Key
OPENAI_MODEL=gpt-4o-mini
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($secretsPath, $content + "`n", $utf8NoBom)
Write-Host "Saved backend/secrets.env. Restart API: .\start-api.ps1" -ForegroundColor Green
