# Shared DATABASE_URL normalization for Alembic / SQLAlchemy (psycopg).

function Convert-ToAlembicDatabaseUrl {
    param([string]$Url)

    $normalized = $Url.Trim().Trim('"').Trim("'")
    if ($normalized -match "^postgresql://") {
        $normalized = $normalized -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($normalized -match "^postgres://") {
        $normalized = $normalized -replace "^postgres://", "postgresql+psycopg://"
    }
    # Neon copy/paste often includes channel_binding=require; psycopg fails with it locally.
    $normalized = $normalized -replace "[?&]channel_binding=require", ""
    $normalized = $normalized -replace "\?&", "?"
    $normalized = $normalized.TrimEnd("?").TrimEnd("&")
    return $normalized
}

function Get-DatabaseUrlHost {
    param([string]$Url)

    if ($Url -match "@([^/]+)/") {
        return $Matches[1]
    }
    return "(unknown host)"
}
