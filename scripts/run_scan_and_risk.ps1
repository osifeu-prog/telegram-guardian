param(
  [string]$Phone = "",
  [switch]$NoOpen
)

$ErrorActionPreference="Stop"

# Always run relative to repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot | Out-Null

# Env
$env:PYTHONPATH = "packages\tg_engine\src"
if ($Phone) { $env:TG_PHONE = $Phone }

# Quick sanity
if (-not (Test-Path "packages\tg_engine\src\tg_engine\poc_scan.py")) { throw "Missing poc_scan.py" }

$riskScript = $null
if (Test-Path "scripts\make_risk_report_ps5.ps1") {
  $riskScript = ".\scripts\make_risk_report_ps5.ps1"
} elseif (Test-Path "scripts\make_risk_report.ps1") {
  $riskScript = ".\scripts\make_risk_report.ps1"
} else {
  throw "Missing risk report script (make_risk_report_ps5.ps1 or make_risk_report.ps1)"
}

Write-Host "== Compile ==" -ForegroundColor Cyan
python -m py_compile "packages\tg_engine\src\tg_engine\poc_scan.py"

Write-Host "== Run scan ==" -ForegroundColor Cyan
python -m tg_engine.poc_scan

if (-not (Test-Path ".\out\scan_report.json")) { throw "scan_report.json missing after run" }

Write-Host "== Risk report ==" -ForegroundColor Cyan

Write-Host "== Parse risk script ==" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -Command "param([string]`$p) [ScriptBlock]::Create((Get-Content -Raw -LiteralPath `$p)) | Out-Null" -Args (Resolve-Path $riskScript).Path

& $riskScript -InPath ".\out\scan_report.json" -OutPath ".\out\risk_report.csv"

Write-Host "== Investor report ==" -ForegroundColor Cyan
if (Test-Path ".\scripts\make_investor_status.ps1") {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\make_investor_status.ps1
}

Write-Host "== Top results ==" -ForegroundColor Cyan
Import-Csv .\out\risk_report.csv |
  Select-Object -First 30 risk_level,risk_score,unread_count,peer_type,peer_id,title,risk_hits,safe_hits |
  Format-Table -AutoSize

if (-not $NoOpen) {
  Write-Host "Opening out\ folder..." -ForegroundColor Cyan
  Start-Process explorer.exe (Resolve-Path ".\out").Path
}

Write-Host "DONE." -ForegroundColor Green
