param(
  [string[]]$IncludeExt = @("*.py","*.ps1","*.md","*.txt","*.yml","*.yaml","*.json")
)

$ErrorActionPreference="Stop"

function ShouldSkip([string]$path) {
  $p = $path.ToLowerInvariant()
  return
    ($p -like "*\.git\*") -or
    ($p -like "*\.venv\*") -or
    ($p -like "*\out\*") -or
    ($p -like "*\node_modules\*") -or
    ($p -like "*\dist\*") -or
    ($p -like "*\build\*") -or
    ($p -like "*\__pycache__\*")
}

$targets = Get-ChildItem -Recurse -File -Include $IncludeExt |
  Where-Object { -not (ShouldSkip $_.FullName) }

$fixed = @()

foreach ($f in $targets) {
  $p = $f.FullName
  $bytes = [IO.File]::ReadAllBytes($p)

  $hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
  if (-not $hasBom) { continue }

  if ($bytes.Length -le 3) { $rest = @() } else { $rest = $bytes[3..($bytes.Length-1)] }

  $text = [Text.Encoding]::UTF8.GetString($rest)
  $utf8NoBom = New-Object Text.UTF8Encoding($false)
  [IO.File]::WriteAllText($p, $text, $utf8NoBom)

  $fixed += $p
}

Write-Host ("BOM stripped from: " + $fixed.Count + " files") -ForegroundColor Green
$fixed | Sort-Object | ForEach-Object { Write-Host ("  FIXED: " + $_) -ForegroundColor Green }
