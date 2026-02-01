param(
  [switch]$StrictCRLF
)

$ErrorActionPreference="Stop"

function ShouldSkip([string]$path) {
  $p = $path.ToLowerInvariant()

  if ($p -like "*\.git\*") { return $true }
  if ($p -like "*\.venv\*") { return $true }
  if ($p -like "*\out\*") { return $true }
  if ($p -like "*\node_modules\*") { return $true }
  if ($p -like "*\dist\*") { return $true }
  if ($p -like "*\build\*") { return $true }
  if ($p -like "*\__pycache__\*") { return $true }

  return $false
}

$includeExt = @("*.py","*.ps1","*.md","*.txt","*.yml","*.yaml","*.json")

$files = Get-ChildItem -Recurse -File -Include $includeExt |
  Where-Object { -not (ShouldSkip $_.FullName) }

$badBom = @()
$badConflict = @()
$badCrlf = @()

foreach ($f in $files) {
  $p = $f.FullName
  $bytes = [IO.File]::ReadAllBytes($p)

  # UTF-8 BOM
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $badBom += $p
  }

  $text = [Text.Encoding]::UTF8.GetString($bytes)

  # REAL git conflict markers ONLY (start-of-line)
  if ($text -match '(?m)^(<<<<<<<|=======|>>>>>>>)') {
    $badConflict += $p
  }

  if ($StrictCRLF) {
    if ($text -match "`r`n") {
      $badCrlf += $p
    }
  }
}

if ($badConflict.Count -gt 0) {
  Write-Host "`nCONFLICT markers found:" -ForegroundColor Red
  $badConflict | Sort-Object -Unique | ForEach-Object { Write-Host "CONFLICT: $_" -ForegroundColor Red }
  throw "Guardrails failed: conflict markers exist"
}

if ($badBom.Count -gt 0) {
  Write-Host "`nBOM files detected (strip required):" -ForegroundColor Yellow
  $badBom | Sort-Object -Unique | ForEach-Object { Write-Host "BOM: $_" -ForegroundColor Yellow }
  throw "Guardrails failed: BOM detected"
}

if ($StrictCRLF -and $badCrlf.Count -gt 0) {
  Write-Host "`nCRLF files detected (LF required):" -ForegroundColor Yellow
  $badCrlf | Sort-Object -Unique | ForEach-Object { Write-Host "CRLF: $_" -ForegroundColor Yellow }
  throw "Guardrails failed: CRLF detected"
}

Write-Host "Guardrails OK." -ForegroundColor Green