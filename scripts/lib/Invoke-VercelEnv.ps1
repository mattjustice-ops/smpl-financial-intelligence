# Safe Vercel env pull (avoids accidental `vercel deploy`).
# Usage: dot-source from scripts or call functions directly.

function Get-VercelNpxBaseArgs {
    param(
        [string]$Scope = "smplai",
        [string]$Project = "smpl-financial-intelligence"
    )

    $args = @("--yes", "vercel@latest", "--scope", $Scope, "--project", $Project)
    if ($env:VERCEL_TOKEN) {
        $args += @("--token", $env:VERCEL_TOKEN)
    }
    return $args
}

function Test-VercelCliOutputLooksLikeDeploy {
    param([string]$Text)

    return (
        $Text -match "Deploying outputs" -or
        $Text -match "Build Completed in /vercel/output" -or
        $Text -match "Uploading \[" -or
        $Text -match "Ready in \d"
    )
}

function Invoke-VercelEnvPull {
    param(
        [string]$FrontendDir,
        [string]$OutFile,
        [ValidateSet("production", "preview", "development")]
        [string]$Environment = "preview",
        [string]$Scope = "smplai",
        [string]$Project = "smpl-financial-intelligence"
    )

    if (-not (Test-Path -LiteralPath $FrontendDir)) {
        throw "Frontend directory not found: $FrontendDir"
    }

    $npxArgs = Get-VercelNpxBaseArgs -Scope $Scope -Project $Project
    # IMPORTANT: environment is a POSITIONAL arg after filename (not --environment).
    # Wrong flags cause Vercel CLI to run `deploy` instead of `env pull`.
    $pullArgs = $npxArgs + @("env", "pull", $OutFile, $Environment, "--yes")

    Push-Location $FrontendDir
    try {
        $output = & npx @pullArgs 2>&1 | ForEach-Object { "$_" }
        $joined = $output -join "`n"

        if (Test-VercelCliOutputLooksLikeDeploy -Text $joined) {
            throw "Vercel CLI ran deploy instead of env pull. Use: npx vercel env pull <file> $Environment --yes (from frontend/)"
        }

        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $OutFile)) {
            if ($joined) {
                throw "vercel env pull failed (exit $LASTEXITCODE):`n$joined"
            }
            throw "vercel env pull failed (exit $LASTEXITCODE)."
        }

        return @{
            Output = $joined
            File   = $OutFile
        }
    }
    finally {
        Pop-Location
    }
}

function Get-EnvFileValue {
    param(
        [string]$FilePath,
        [string]$Key
    )

    if (-not (Test-Path -LiteralPath $FilePath)) { return $null }
    foreach ($line in Get-Content -LiteralPath $FilePath) {
        if ($line -match "^$([regex]::Escape($Key))=(.+)$") {
            $value = $Matches[1].Trim().Trim('"').Trim("'")
            if ($value) { return $value }
        }
    }
    return $null
}

function Set-VercelPreviewEnvValue {
    param(
        [string]$FrontendDir,
        [string]$Name,
        [string]$Value,
        [string]$Scope = "smplai",
        [string]$Project = "smpl-financial-intelligence"
    )

    $npxArgs = Get-VercelNpxBaseArgs -Scope $Scope -Project $Project
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        Push-Location $FrontendDir
        try {
            $out = Get-Content -LiteralPath $tempFile -Raw | & npx @npxArgs env add $Name preview --yes --force 2>&1 | ForEach-Object { "$_" }
            $joined = ($out -join "`n").Trim()
            if (Test-VercelCliOutputLooksLikeDeploy -Text $joined) {
                throw "Vercel CLI ran deploy instead of env add."
            }
            if ($LASTEXITCODE -ne 0) {
                if ($joined) {
                    throw "vercel env add $Name preview failed (exit $LASTEXITCODE):`n$joined"
                }
                throw "vercel env add $Name preview failed (exit $LASTEXITCODE)."
            }
            return $true
        }
        finally {
            Pop-Location
        }
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}
