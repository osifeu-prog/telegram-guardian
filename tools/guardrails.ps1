param([switch]$StrictCRLF)
$ErrorActionPreference="Stop"

function Get-StagedFiles {
  $raw = git diff --cached --name-only --diff-filter=ACMRD
  if (-not $raw) { @() } else { $raw | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
}

function ShouldCheck([string]$rel) {
  $p = $rel.ToLowerInvariant()
  if ($p -like ".venv/*" -or $p -like "out/*" -or $p -like "logs/*" -or $p -like "node_modules/*" -or
      $p -like "dist/*" -or $p -like "build/*" -or $p -like "__pycache__/*") { return $false }

  return (
    $p -like "*.py" -or $p -like "*.ps1" -or $p -like "*.md" -or $p -like "*.txt" -or
    $p -like "*.yml" -or $p -like "*.yaml" -or $p -like "*.json" -or
    $p -eq ".editorconfig" -or $p -eq ".gitattributes"
  )
}

$badBom=@(); $badCrlf=@(); $badConflict=@()

$staged = Get-StagedFiles | Where-Object { ShouldCheck $_ }

foreach ($rel in $staged) {
  if (-not (Test-Path -LiteralPath $rel)) { continue }

  $bytes = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $rel).Path)
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { $badBom += $rel }

  $text = [Text.Encoding]::UTF8.GetString($bytes)
  if ($text -match '(?m)^(<<<<<<<|=======|>>>>>>>)') { $badConflict += $rel }
  if ($StrictCRLF -and ($text -match "`r`n")) { $badCrlf += $rel }
}

if ($badConflict.Count) { Write-Host "`nCONFLICT:" -ForegroundColor Red; $badConflict | Sort -Unique | % { Write-Host "CONFLICT: $_" -ForegroundColor Red }; exit 1 }
if ($badBom.Count)      { Write-Host "`nBOM:"      -ForegroundColor Yellow; $badBom      | Sort -Unique | % { Write-Host "BOM: $_"      -ForegroundColor Yellow }; exit 1 }
if ($StrictCRLF -and $badCrlf.Count) { Write-Host "`nCRLF:" -ForegroundColor Yellow; $badCrlf | Sort -Unique | % { Write-Host "CRLF: $_" -ForegroundColor Yellow }; exit 1 }

Write-Host "Guardrails OK." -ForegroundColor Green
exit 0