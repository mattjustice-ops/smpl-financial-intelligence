function Resolve-ResendApiKey {
  param(
    [string]$TokenFile = "C:\Users\mattj\OneDrive\Documents\Resend Token.txt",
    [string]$EnvLocal = ""
  )

  if ($env:AUTH_RESEND_KEY -match "^re_[a-zA-Z0-9_]+$") {
    return $env:AUTH_RESEND_KEY.Trim()
  }

  if ($EnvLocal -and (Test-Path $EnvLocal)) {
    $envLine = Get-Content $EnvLocal | Where-Object { $_ -match "^AUTH_RESEND_KEY=" } | Select-Object -First 1
    if ($envLine -match "^AUTH_RESEND_KEY=(re_[a-zA-Z0-9_]+)$") {
      return $Matches[1].Trim()
    }
  }

  if (Test-Path $TokenFile) {
    $lines = Get-Content $TokenFile
    foreach ($line in $lines) {
      $trimmed = $line.Trim()
      if ($trimmed -match "^re_[a-zA-Z0-9_]+$") {
        return $trimmed
      }
    }

    $content = Get-Content $TokenFile -Raw
    $matches = [regex]::Matches($content, "re_[a-zA-Z0-9_]+")
    if ($matches.Count -gt 0) {
      return $matches[$matches.Count - 1].Value.Trim()
    }
  }

  return $null
}

function Test-ResendApiKey {
  param([string]$Key)

  if (-not $Key) {
    return $false
  }

  try {
    $null = Invoke-RestMethod `
      -Uri "https://api.resend.com/domains" `
      -Method Get `
      -Headers @{ Authorization = "Bearer $Key" } `
      -ErrorAction Stop
    return $true
  } catch {
    $detail = $_.ErrorDetails.Message
    if (-not $detail) {
      $detail = $_.Exception.Message
    }

    # Sending-only keys cannot list domains, but they are valid for magic-link email.
    if ($detail -match "restricted_api_key" -or $detail -match "only send emails") {
      return $true
    }

    return $false
  }
}

function Get-ResendApiKeyError {
  param([string]$Key)

  try {
    $null = Invoke-RestMethod `
      -Uri "https://api.resend.com/domains" `
      -Method Get `
      -Headers @{ Authorization = "Bearer $Key" } `
      -ErrorAction Stop
    return $null
  } catch {
    $detail = $_.ErrorDetails.Message
    if (-not $detail) {
      $detail = $_.Exception.Message
    }

    if ($detail -match "restricted_api_key" -or $detail -match "only send emails") {
      return $null
    }

    return $detail
  }
}

function Test-ResendApiKeyIsSendingOnly {
  param([string]$Key)

  if (-not $Key) {
    return $false
  }

  try {
    $null = Invoke-RestMethod `
      -Uri "https://api.resend.com/domains" `
      -Method Get `
      -Headers @{ Authorization = "Bearer $Key" } `
      -ErrorAction Stop
    return $false
  } catch {
    $detail = $_.ErrorDetails.Message
    if (-not $detail) {
      $detail = $_.Exception.Message
    }
    return ($detail -match "restricted_api_key" -or $detail -match "only send emails")
  }
}
