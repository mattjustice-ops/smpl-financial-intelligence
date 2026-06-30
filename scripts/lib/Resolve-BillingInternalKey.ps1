# Resolve BILLING_INTERNAL_API_KEY for local ops scripts.
# Checks env, frontend env files, and optionally Vercel production pull.

function Resolve-BillingInternalKey {
    param(
        [string]$RepoRoot = "",
        [switch]$TryVercelPull
    )

    if (-not $RepoRoot) {
        $RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        if (-not (Test-Path (Join-Path $RepoRoot "frontend"))) {
            $RepoRoot = Split-Path $PSScriptRoot -Parent
        }
    }

    $fromEnv = $env:BILLING_INTERNAL_API_KEY
    if ($fromEnv -and $fromEnv.Trim()) {
        return @{ Key = $fromEnv.Trim(); Source = "environment variable" }
    }

    . (Join-Path $PSScriptRoot "Invoke-VercelEnv.ps1")
    $frontendDir = Join-Path $RepoRoot "frontend"
    $candidateFiles = @(
        (Join-Path $frontendDir ".env.local"),
        (Join-Path $frontendDir ".env.production.local"),
        (Join-Path $frontendDir ".env.neon-production.local"),
        (Join-Path $RepoRoot "backend\.env"),
        (Join-Path $RepoRoot "backend\secrets.env")
    )

    foreach ($file in $candidateFiles) {
        $value = Get-EnvFileValue -FilePath $file -Key "BILLING_INTERNAL_API_KEY"
        if ($value) {
            return @{ Key = $value; Source = $file }
        }
    }

    if ($TryVercelPull) {
        $pullFile = Join-Path $frontendDir ".env.vercel.ops-pull.local"
        try {
            Invoke-VercelEnvPull -FrontendDir $frontendDir -OutFile $pullFile -Environment "production" | Out-Null
            $value = Get-EnvFileValue -FilePath $pullFile -Key "BILLING_INTERNAL_API_KEY"
            if ($value) {
                return @{ Key = $value; Source = "vercel env pull (production)" }
            }
        }
        catch {
            Write-Host "Vercel env pull skipped: $($_.Exception.Message)" -ForegroundColor DarkYellow
        }
        finally {
            Remove-Item -LiteralPath $pullFile -Force -ErrorAction SilentlyContinue
        }
    }

    return $null
}

function Write-BillingInternalKeyHelp {
    Write-Host ""
    Write-Host "BILLING_INTERNAL_API_KEY is required for API mode." -ForegroundColor Yellow
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  1. Local Neon (no API key):" -ForegroundColor White
    Write-Host "     .\scripts\collect-ops-storage-snapshot.ps1 -Local" -ForegroundColor DarkGray
    Write-Host "  2. Pull from Vercel (requires vercel login):" -ForegroundColor White
    Write-Host "     .\scripts\collect-ops-storage-snapshot.ps1 -TryVercelPull" -ForegroundColor DarkGray
    Write-Host "  3. Add to frontend/.env.local (same value as Vercel Production)" -ForegroundColor White
    Write-Host "  4. One-off env var:" -ForegroundColor White
    Write-Host '     $env:BILLING_INTERNAL_API_KEY = "your-key"; .\scripts\collect-ops-storage-snapshot.ps1' -ForegroundColor DarkGray
    Write-Host ""
}
