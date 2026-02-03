param(
  [string]$ScanJson = ".\out\scan_report.json",
  [string]$OutCsv   = ".\out\risk_report.csv"
)

$ErrorActionPreference="Stop"

# 1) Build base risk report
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "$PSScriptRoot\make_risk_report_ps5.ps1" `
  -InPath $ScanJson -OutPath $OutCsv

# 2) Apply ignore lists
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "$PSScriptRoot\apply_ignore_to_csv.ps1"

# 3) Excel-friendly CSV (UTF-8 with BOM)
$excelOut = [IO.Path]::ChangeExtension((Resolve-Path $OutCsv).Path, ".excel.csv")
$csv = Get-Content -LiteralPath $OutCsv -Raw
[IO.File]::WriteAllText($excelOut, $csv, (New-Object System.Text.UTF8Encoding($true)))
Write-Host "Saved (Excel): $excelOut"

# 4) Sanity check
Import-Csv $OutCsv |
  Where-Object { $_.ignored -eq "True" } |
  Select-Object peer_type,peer_id,title,ignored_reason,ignored_source |
  Format-Table -AutoSize
