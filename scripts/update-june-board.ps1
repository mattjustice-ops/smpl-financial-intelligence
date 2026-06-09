# Copy June 2026 board HTML + export files into frontend/public/board for local + Vercel.
param(
    [string]$HtmlSrc = "C:\Users\mattj\Downloads\SMPL_Board_Platform_June2026 (6).html",
    [string]$PptxSrc = "",
    [string]$XlsxSrc = ""
)

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "..\frontend" | Resolve-Path
Push-Location $frontend
try {
    if ($HtmlSrc) { $env:SMPL_BOARD_HTML_SRC = $HtmlSrc }
    if ($PptxSrc) { $env:SMPL_BOARD_PPTX_SRC = $PptxSrc }
    if ($XlsxSrc) { $env:SMPL_MDA_XLSX_SRC = $XlsxSrc }

    Write-Host "Updating board package from $frontend" -ForegroundColor Cyan
    npm run update:board-june
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Export files missing. Either:" -ForegroundColor Yellow
        Write-Host "  1. Copy files into frontend\public\board\exports\ manually:"
        Write-Host "       SMPL_Board_Review_Q2_2026.pptx"
        Write-Host "       SMPL_MDA_Package_June2026.xlsx"
        Write-Host "  2. Re-run with local paths:"
        Write-Host "       .\scripts\update-june-board.ps1 -PptxSrc 'C:\path\SMPL_Board_Review_Q2_2026.pptx' -XlsxSrc 'C:\path\SMPL_MDA_Package_June2026.xlsx'"
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "Board assets updated." -ForegroundColor Green
    Write-Host "  Local:  http://localhost:3002/board"
    Write-Host "  Deploy: cd .. ; .\scripts\deploy-frontend-vercel.ps1 -CommitPush -CommitMessage 'Update June 2026 board demo and export files'"
} finally {
    Pop-Location
}
