# Run in PowerShell:  .\scripts\test-deferred-api.ps1
# Or:  powershell -File "C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend\scripts\test-deferred-api.ps1"

$orgId = "8571e520-0687-4516-bdee-379f37c58c1f"
$base = "http://127.0.0.1:8000"

Write-Host "1. Testing backend health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 5
    Write-Host "   Health OK:" $health.status -ForegroundColor Green
} catch {
    Write-Host "   FAILED - backend is not running on port 8000." -ForegroundColor Red
    Write-Host "   Start it first:" -ForegroundColor Yellow
    Write-Host '   cd ...\backend' 
    Write-Host '   .\.venv312\Scripts\Activate.ps1'
    Write-Host '   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000'
    exit 1
}

Write-Host "2. Calling deferred-revenue API (may take up to 30s)..." -ForegroundColor Cyan
$uri = "$base/api/v1/waterfalls/deferred-revenue?organization_id=$orgId&scenario=Combined&start_period=2026-01&end_period=2026-12"

try {
    $response = Invoke-WebRequest -Uri $uri -TimeoutSec 60 -UseBasicParsing
    Write-Host "   Status:" $response.StatusCode -ForegroundColor Green
    Write-Host "   Response length:" $response.Content.Length "bytes"
    $json = $response.Content | ConvertFrom-Json
    Write-Host "   Rows returned:" $json.rows.Count
} catch {
    Write-Host "   FAILED" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   HTTP status:" ([int]$_.Exception.Response.StatusCode) -ForegroundColor Yellow
    }
    if ($_.ErrorDetails.Message) {
        Write-Host "   Server said:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message
    } elseif ($_.Exception.Response) {
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $body = $reader.ReadToEnd()
        if ($body) {
            Write-Host "   Server said:" -ForegroundColor Yellow
            Write-Host $body
        }
    }
    if (-not $_.ErrorDetails.Message) {
        Write-Host "   Error:" $_.Exception.Message -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "   Also check the uvicorn terminal window for a Python traceback." -ForegroundColor Cyan
    exit 1
}

Write-Host "Done." -ForegroundColor Green
