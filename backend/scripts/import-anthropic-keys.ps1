# Import Anthropic API keys from Claude Keys.txt (smpl-local / smpl-sandbox / smpl-prod).
# Writes backend/secrets.env (local key) and frontend/.env.local (all three for reference).
param(
    [string]$Path = "C:\Windows\System32\Claude Keys.txt"
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $backendRoot -Parent
$secretsPath = Join-Path $backendRoot "secrets.env"
$envLocalPath = Join-Path $repoRoot "frontend\.env.local"

function Resolve-SourceFile([string]$p) {
    if ($p -and (Test-Path -LiteralPath $p)) { return (Resolve-Path -LiteralPath $p).Path }
    $candidates = @(
        "C:\Windows\System32\Claude Keys.txt",
        "$env:USERPROFILE\Downloads\Claude Keys.txt",
        "$env:USERPROFILE\OneDrive\Documents\Claude Keys.txt"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return (Resolve-Path -LiteralPath $c).Path }
    }
    return $null
}

function Parse-ClaudeKeys([string]$raw) {
    $map = @{}
    $pending = $null
    foreach ($line in ($raw -split "`r?`n")) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        if ($t -match '^(?i)smpl-(local|sandbox|prod)\s*$') {
            $pending = "smpl-$($Matches[1].ToLower())"
            continue
        }
        if ($t -match '(?i)^ANTHROPIC_API_KEY(?:_(?:LOCAL|SANDBOX|PROD))?\s*=\s*(\S+)\s*$') {
            $key = $Matches[1].Trim().Trim('"').Trim("'")
            if ($pending) {
                $map[$pending] = $key
                $pending = $null
            }
            elseif ($t -match '_SANDBOX') { $map["smpl-sandbox"] = $key }
            elseif ($t -match '_PROD') { $map["smpl-prod"] = $key }
            else { $map["smpl-local"] = $key }
            continue
        }
        if ($t -match '^(sk-ant-[A-Za-z0-9_\-\.]+)$' -and $pending) {
            $map[$pending] = $Matches[1]
            $pending = $null
        }
    }
    return $map
}

function Read-EnvMap([string]$path) {
    $existing = @{}
    if (-not (Test-Path -LiteralPath $path)) { return $existing }
    foreach ($line in Get-Content -LiteralPath $path) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        if ($t -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $existing[$Matches[1]] = $Matches[2]
        }
    }
    return $existing
}

function Write-EnvFile([string]$path, [hashtable]$vars, [string[]]$keyOrder) {
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Updated by import-anthropic-keys.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    foreach ($name in $keyOrder) {
        if ($vars.ContainsKey($name)) {
            $lines.Add("$name=$($vars[$name])")
        }
    }
    foreach ($entry in ($vars.GetEnumerator() | Sort-Object Name)) {
        if ($keyOrder -contains $entry.Key) { continue }
        $lines.Add("$($entry.Key)=$($entry.Value)")
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, ($lines -join "`n") + "`n", $utf8NoBom)
}

function Upsert-EnvLines([string]$path, [hashtable]$updates, [string]$header) {
    $lines = @()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]]@((Get-Content -LiteralPath $path))
    }
    else {
        $lines = New-Object System.Collections.Generic.List[string]
    }

    $existingKeys = @{}
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=') {
            $existingKeys[$Matches[1]] = $i
        }
    }

    foreach ($entry in $updates.GetEnumerator()) {
        $pair = "$($entry.Key)=$($entry.Value)"
        if ($existingKeys.ContainsKey($entry.Key)) {
            $lines[$existingKeys[$entry.Key]] = $pair
        }
        else {
            if ($lines.Count -gt 0 -and $lines[$lines.Count - 1].Trim() -ne "") {
                $lines.Add("")
            }
            if ($header -and -not ($lines -join "`n" -match [regex]::Escape($header))) {
                $lines.Add($header)
            }
            $lines.Add($pair)
        }
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, ($lines -join "`n").TrimEnd() + "`n", $utf8NoBom)
}

$source = Resolve-SourceFile $Path
if (-not $source) {
    Write-Host "Claude Keys file not found." -ForegroundColor Red
    Write-Host "Pass -Path to your keys file, e.g.:"
    Write-Host '  .\scripts\import-anthropic-keys.ps1 -Path "C:\Windows\System32\Claude Keys.txt"'
    exit 1
}

$raw = Get-Content -LiteralPath $source -Raw
$keys = Parse-ClaudeKeys $raw

if (-not $keys["smpl-local"]) {
    Write-Host "No smpl-local key found in: $source" -ForegroundColor Red
    exit 1
}

$secrets = Read-EnvMap $secretsPath
$secrets["ANTHROPIC_API_KEY"] = $keys["smpl-local"]
if (-not $secrets.ContainsKey("ANTHROPIC_MODEL")) {
    $secrets["ANTHROPIC_MODEL"] = "claude-sonnet-4-20250514"
}
if (-not $secrets.ContainsKey("OPENAI_API_KEY")) {
    $backendEnv = Read-EnvMap (Join-Path $backendRoot ".env")
    if ($backendEnv.ContainsKey("OPENAI_API_KEY")) {
        $secrets["OPENAI_API_KEY"] = $backendEnv["OPENAI_API_KEY"]
    }
}
if (-not $secrets.ContainsKey("OPENAI_MODEL")) {
    $secrets["OPENAI_MODEL"] = "gpt-4o-mini"
}

Write-EnvFile $secretsPath $secrets @(
    "OPENAI_API_KEY"
    "OPENAI_MODEL"
    "ANTHROPIC_API_KEY"
    "ANTHROPIC_MODEL"
)

$envUpdates = @{
    ANTHROPIC_API_KEY         = $keys["smpl-local"]
    ANTHROPIC_MODEL           = "claude-sonnet-4-20250514"
    ANTHROPIC_KEYS_FILE       = $source
}
if ($keys["smpl-sandbox"]) { $envUpdates["ANTHROPIC_API_KEY_SANDBOX"] = $keys["smpl-sandbox"] }
if ($keys["smpl-prod"]) { $envUpdates["ANTHROPIC_API_KEY_PROD"] = $keys["smpl-prod"] }

Upsert-EnvLines $envLocalPath $envUpdates "# Anthropic (Claude) - local dev + Railway reference keys"

Write-Host "Wrote backend/secrets.env (ANTHROPIC_API_KEY = smpl-local)" -ForegroundColor Green
Write-Host "Updated frontend/.env.local with Anthropic keys section" -ForegroundColor Green
Write-Host "Source: $source" -ForegroundColor DarkGray
if ($keys["smpl-sandbox"]) { Write-Host "  smpl-sandbox: ready for Railway sfi-api-staging" -ForegroundColor DarkGray }
if ($keys["smpl-prod"]) { Write-Host "  smpl-prod: ready for Railway sfi-api" -ForegroundColor DarkGray }
Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  .\scripts\set-railway-anthropic-keys.ps1" -ForegroundColor White
Write-Host "  Restart API: .\start-api.ps1" -ForegroundColor White
