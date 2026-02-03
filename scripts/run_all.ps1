param(
  [switch]$NoOpen
)

$ErrorActionPreference="Stop"

# 1) Full pipeline: scan -> risk -> ignore -> excel
powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\run_scan_and_risk.ps1" -NoOpen

powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\make_risk_report_with_ignore.ps1"

Write-Host ""
Write-Host "DONE. Outputs:" -ForegroundColor Green
Write-Host " - out\scan_report.json"
Write-Host " - out\risk_report.csv"
Write-Host " - out\risk_report.excel.csv"

if (-not $NoOpen) {
  $p = (Resolve-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "out\risk_report.excel.csv")).Path
  Start-Process $p
}
