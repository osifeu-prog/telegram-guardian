$ErrorActionPreference="Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot | Out-Null

Write-Host "== Python ==" -ForegroundColor Cyan
python --version
python -c "import sys; print(sys.executable)"

Write-Host "`n== venv ==" -ForegroundColor Cyan
$venv = $env:VIRTUAL_ENV
if ([string]::IsNullOrWhiteSpace($venv)) { $venv = "" }
Write-Host ("VIRTUAL_ENV=" + $venv)

Write-Host "`n== Import checks ==" -ForegroundColor Cyan
python -c "import telethon, sys; print('telethon:', telethon.__version__); print('sys.path[0:3]:', sys.path[0:3])"

Write-Host "`n== Project paths ==" -ForegroundColor Cyan
$env:PYTHONPATH="packages\tg_engine\src"
python -c "import tg_engine; import tg_engine.poc_scan; print('tg_engine OK')"

Write-Host "`n== Files ==" -ForegroundColor Cyan
"scan_report.json exists: " + (Test-Path ".\out\scan_report.json")
"risk_report.csv exists: " + (Test-Path ".\out\risk_report.csv")

Write-Host "`n== Repo scan (excluding .venv/.git/out/node_modules) ==" -ForegroundColor Cyan
$badBom = @()
$badConflict = @()

$files =
  Get-ChildItem -Recurse -File -Include *.py,*.ps1,*.md,*.txt,*.yml,*.yaml,*.json |
  Where-Object {
    $p = $_.FullName
    ($p -notmatch '\\\.venv\\') -and
    ($p -notmatch '\\\.git\\') -and
    ($p -notmatch '\\out\\') -and
    ($p -notmatch '\\node_modules\\') -and
    ($p -notmatch '\\dist\\') -and
    ($p -notmatch '\\build\\') -and
    ($p -notmatch '\\__pycache__\\')
  }

foreach ($f in $files) {
  $p = $f.FullName
  $bytes = [IO.File]::ReadAllBytes($p)

  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $badBom += $p
  }

  $text = [Text.Encoding]::UTF8.GetString($bytes)
  if ($text -match '(?m)^(<<<<<<<|=======|>>>>>>>)') {
    $badConflict += $p
  }
}

if ($badConflict.Count -gt 0) {
  Write-Host "`nCONFLICT markers found:" -ForegroundColor Red
  $badConflict | Sort-Object -Unique | ForEach-Object { Write-Host "CONFLICT: $_" -ForegroundColor Red }
  throw "Doctor failed: conflict markers exist"
}

if ($badBom.Count -gt 0) {
  Write-Host "`nBOM files (need stripping):" -ForegroundColor Yellow
  $badBom | Sort-Object -Unique | ForEach-Object { Write-Host "BOM: $_" -ForegroundColor Yellow }
} else {
  Write-Host "`nNo BOM files detected." -ForegroundColor Green
}

Write-Host "`nDoctor OK." -ForegroundColor Green
