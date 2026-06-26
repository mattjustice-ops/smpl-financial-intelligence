# Copy the Q2 2026 board template into backend/templates/board for Railway Docker builds.
$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$dstDir = Join-Path $repoRoot "backend\templates\board"
$dst = Join-Path $dstDir "SMPL_Board_Review_Template.pptx"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

$sources = @(
    $env:SMPL_BOARD_PPTX_SRC,
    "$env:USERPROFILE\OneDrive\SMPL_Board_Review_Q2_2026.pptx",
    (Join-Path $repoRoot "frontend\public\board\exports\SMPL_Board_Review_Q2_2026.pptx")
) | Where-Object { $_ -and (Test-Path $_) }

if (-not $sources) {
    Write-Error "Template not found. Set SMPL_BOARD_PPTX_SRC or place SMPL_Board_Review_Q2_2026.pptx in OneDrive."
}
Copy-Item -Force $sources[0] $dst
Write-Host "Synced $((Get-Item $dst).Length) bytes from $($sources[0]) to $dst"
Write-Host "Commit backend/templates/board/SMPL_Board_Review_Template.pptx and redeploy Railway."
