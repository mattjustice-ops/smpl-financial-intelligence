# Fetch exact DNS records for smpl-ai.com from Resend (gl-2).
# Run from repo root:
#   .\scripts\print-resend-dns-records.ps1
#
# Requires a Resend API key with Domains access (not Sending-only).
# If you only have Sending access, use Resend dashboard -> Domains -> smpl-ai.com -> Records.

param(
    [string]$Domain = "smpl-ai.com",
    [string]$TokenFile = "C:\Users\mattj\OneDrive\Documents\Resend Token.txt",
    [switch]$CreateIfMissing
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ResendApiKey.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"
$key = Resolve-ResendApiKey -TokenFile $TokenFile -EnvLocal $envLocal

if (-not $key) {
    Write-Host "No Resend API key found." -ForegroundColor Red
    Write-Host "Run: .\scripts\setup-resend-email.ps1"
    exit 1
}

function Invoke-Resend {
    param([string]$Method, [string]$Uri, [object]$Body = $null)
    $params = @{
        Uri = $Uri
        Method = $Method
        Headers = @{ Authorization = "Bearer $key" }
        ErrorAction = "Stop"
    }
    if ($Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 5)
    }
    return Invoke-RestMethod @params
}

function Get-DnsHostName {
    param([string]$RecordName, [string]$DomainName)
    $suffix = ".$DomainName"
    if ($RecordName -eq $DomainName -or $RecordName -eq "@") {
        return "@"
    }
    if ($RecordName.EndsWith($suffix)) {
        return $RecordName.Substring(0, $RecordName.Length - $suffix.Length)
    }
    return $RecordName
}

Write-Host ""
Write-Host "=== Resend DNS records for $Domain ===" -ForegroundColor Cyan
Write-Host ""

try {
    $list = Invoke-Resend -Method Get -Uri "https://api.resend.com/domains"
}
catch {
    $detail = $_.ErrorDetails.Message
    if (-not $detail) { $detail = $_.Exception.Message }
    if ($detail -match "restricted_api_key|only send emails") {
        Write-Host "Your API key is Sending-only (cannot read domains)." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Option A (easiest): Resend dashboard -> Domains -> $Domain -> copy Records tab" -ForegroundColor White
        Write-Host "Option B: Create a Full Access API key at https://resend.com/api-keys" -ForegroundColor White
        Write-Host "          Re-run this script" -ForegroundColor White
        Write-Host ""
        Write-Host "Option C (Cloudflare): On the domain in Resend, click 'Sign in to Cloudflare' for auto-setup." -ForegroundColor White
        exit 1
    }
    throw
}

$match = $list.data | Where-Object { $_.name -eq $Domain } | Select-Object -First 1

if (-not $match -and $CreateIfMissing) {
    Write-Host "Domain not in Resend yet. Creating $Domain ..." -ForegroundColor Yellow
    $created = Invoke-Resend -Method Post -Uri "https://api.resend.com/domains" -Body @{ name = $Domain }
    $match = @{ id = $created.id; name = $Domain; status = $created.status }
}

if (-not $match) {
    Write-Host "Domain '$Domain' not found in Resend." -ForegroundColor Yellow
    Write-Host "Add it at https://resend.com/domains or re-run with -CreateIfMissing" -ForegroundColor White
    exit 1
}

$detail = Invoke-Resend -Method Get -Uri "https://api.resend.com/domains/$($match.id)"
Write-Host "Status: $($detail.status)" -ForegroundColor $(if ($detail.status -eq "verified") { "Green" } else { "Yellow" })
Write-Host ""

$sendingRecords = @($detail.records | Where-Object {
    $_.record -in @("SPF", "DKIM") -or ($_.record -eq "MX" -and $_.name -match "^send\.")
})

if ($sendingRecords.Count -eq 0) {
    $sendingRecords = @($detail.records | Where-Object { $_.record -ne "Receiving" })
}

Write-Host "Add these in your DNS provider (sending only - no inbound mail):" -ForegroundColor Cyan
Write-Host ""

$i = 1
foreach ($rec in $sendingRecords) {
    $hostName = Get-DnsHostName -RecordName $rec.name -DomainName $Domain
    Write-Host ("--- Record {0}: {1} ---" -f $i, $rec.record) -ForegroundColor DarkGray
    Write-Host ("  Type:     {0}" -f $rec.type)
    Write-Host ("  Host:     {0}" -f $hostName)
    if ($rec.priority) {
        Write-Host ("  Priority: {0}" -f $rec.priority)
    }
    Write-Host ("  Value:    {0}" -f $rec.value)
    Write-Host ("  Status:   {0}" -f $rec.status)
    Write-Host ""
    $i++
}

Write-Host "Recommended DMARC (optional, add manually):" -ForegroundColor Cyan
Write-Host "  Type:  TXT"
Write-Host "  Host:  _dmarc"
Write-Host "  Value: v=DMARC1; p=none;"
Write-Host ""
Write-Host "Cloudflare tip: use Host 'send' not 'send.smpl-ai.com'. Proxy = DNS only." -ForegroundColor DarkGray
Write-Host "After adding records: Resend -> Domains -> Verify DNS Records" -ForegroundColor Yellow
Write-Host ""
