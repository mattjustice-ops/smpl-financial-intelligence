# Import latest Downloads/aio_chunks.json into AIO
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $root 'tmp'))) { $root = $PSScriptRoot }
# script lives in frontend/scripts → root is frontend
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$dlDir = Join-Path $env:USERPROFILE 'Downloads'
# Prefer newest file that is NOT already renamed as imported
$src = Get-ChildItem -Path $dlDir -Filter 'aio_chunks*.json' |
  Where-Object { $_.Name -notlike 'aio_chunks_imported_*' } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if (-not $src) { Write-Error 'No aio_chunks*.json in Downloads'; exit 1 }
# Optional: require queryId match
$wantId = $env:AIO_EXPECT_QUERY_ID
$parsed = Get-Content $src.FullName -Raw | ConvertFrom-Json
if ($wantId -and $parsed.queryId -ne $wantId) {
  Write-Error "Expected $wantId but download has $($parsed.queryId) ($($src.Name))"
  exit 2
}
$dest = Join-Path $root 'tmp\aio_chunks.json'
Copy-Item $src.FullName $dest -Force
Write-Host "copied $($src.FullName) queryId=$($parsed.queryId) ($($src.Length) bytes)"
Push-Location $root
try {
  node scripts/aio-save-import-one.mjs
  $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
  Rename-Item $src.FullName "aio_chunks_imported_$($parsed.queryId)_$stamp.json" -ErrorAction SilentlyContinue
} finally {
  Pop-Location
}
