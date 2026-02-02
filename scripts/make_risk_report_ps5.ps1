param(
  [string]$InPath  = ".\out\scan_report.json",
  [string]$OutPath = ".\out\risk_report.csv"
)

$ErrorActionPreference = "Stop"

# Always run relative to repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot | Out-Null

# Normalize paths
$InPathResolved = (Resolve-Path $InPath).Path
$outFull = Join-Path (Get-Location) $OutPath

# Ensure output folder exists
$outDir = Split-Path -Parent $outFull
New-Item -ItemType Directory -Force $outDir | Out-Null

# UTF-8 console (nice-to-have)
try {
  chcp 65001 | Out-Null
  $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch {}

if (-not (Test-Path $InPathResolved)) { throw "Missing: $InPathResolved" }

function Fix-Mojibake([string]$s) {
  if ([string]::IsNullOrWhiteSpace($s)) { return $s }

  function Score([string]$x) {
    if ([string]::IsNullOrEmpty($x)) { return 999999 }
    $bad = 0
    foreach ($ch in $x.ToCharArray()) {
      if ($ch -eq [char]0xFFFD) { $bad += 8 }   # 
      elseif ($ch -eq '?')      { $bad += 1 }
    }
    $bad += ([regex]::Matches($x, "Ã|Â|â|×|").Count * 2)
    return $bad
  }

  $candidates = New-Object System.Collections.Generic.List[string]
  $candidates.Add($s)

  try {
    $bytes = [Text.Encoding]::GetEncoding(1252).GetBytes($s)
    $candidates.Add([Text.Encoding]::UTF8.GetString($bytes))
  } catch {}

  try {
    $bytes = [Text.Encoding]::GetEncoding(1255).GetBytes($s)  # Hebrew
    $candidates.Add([Text.Encoding]::UTF8.GetString($bytes))
  } catch {}

  try {
    $bytes = [Text.Encoding]::GetEncoding(1256).GetBytes($s)  # Arabic
    $candidates.Add([Text.Encoding]::UTF8.GetString($bytes))
  } catch {}

  $best = $s
  $bestScore = Score $s
  foreach ($c in ($candidates | Select-Object -Unique)) {
    $sc = Score $c
    if ($sc -lt $bestScore) { $best = $c; $bestScore = $sc }
  }
  return $best
}

$report = Get-Content $InPathResolved -Raw | ConvertFrom-Json

$riskWords = @(
  "signal","signals","pump","pumps","vip","insider","leak","leaks","futures","margin","scalp","scalping",
  "binance","bybit","kucoin","forex","gold","btc","bitcoin","alt","alts","profit","profits",
  "airdrop","notcoin","launch","pre-sale","presale","ico","ido"
)

$safeWords = @("family","work","dev","engineering","admin","team","support","friends")

$highUnread = 200
$veryHighUnread = 800

$rows = foreach ($d in $report.dialogs) {
  $rawTitle = [string]$d.title
  $title    = Fix-Mojibake $rawTitle
  if ($null -eq $title) { $title = "" }
  $titleNorm = $title.ToLowerInvariant()

  $hit = @()
  foreach ($w in $riskWords) {
    if ($titleNorm -match [regex]::Escape($w.ToLowerInvariant())) { $hit += $w }
  }

  $safeHit = @()
  foreach ($w in $safeWords) {
    if ($titleNorm -match [regex]::Escape($w.ToLowerInvariant())) { $safeHit += $w }
  }

  $unread = 0
  try { $unread = [int]$d.unread_count } catch { $unread = 0 }

  $score = 0
  if ($d.is_channel -and -not $d.is_group) { $score += 2 }
  if ($d.is_group) { $score += 1 }

  $score += [math]::Min(10, ($hit | Select-Object -Unique | Measure-Object).Count)

  if ($unread -ge $veryHighUnread) { $score += 5 }
  elseif ($unread -ge $highUnread) { $score += 3 }
  elseif ($unread -ge 50)          { $score += 1 }

  $score = [math]::Max(0, $score - [math]::Min(3, ($safeHit | Select-Object -Unique | Measure-Object).Count))

  $riskLevel = "MIN"
  if ($score -ge 12) { $riskLevel = "HIGH" }
  elseif ($score -ge 7) { $riskLevel = "MED" }
  elseif ($score -ge 3) { $riskLevel = "LOW" }

  [pscustomobject]@{
    risk_level   = $riskLevel
    risk_score   = $score
    peer_type    = $d.peer_type
    peer_id      = $d.peer_id
    title        = $title
    unread_count = $unread
    is_group     = [bool]$d.is_group
    is_channel   = [bool]$d.is_channel
    is_user      = [bool]$d.is_user
    risk_hits    = (($hit | Select-Object -Unique) -join ";")
    safe_hits    = (($safeHit | Select-Object -Unique) -join ";")
  }
}

$rows |
  Sort-Object -Property `
    @{Expression="risk_score"; Descending=$true}, `
    @{Expression="unread_count"; Descending=$true} |
  Export-Csv $outFull -NoTypeInformation -Encoding UTF8

if (-not (Test-Path $outFull)) { throw "Export failed; file not created: $outFull" }
Write-Host "Saved: $outFull"

# Excel-friendly copy (UTF8 BOM) in SAME folder
$excelOut = [IO.Path]::ChangeExtension($outFull, ".excel.csv")
$csv = Get-Content $outFull -Raw
[IO.File]::WriteAllText($excelOut, $csv, (New-Object Text.UTF8Encoding($true)))
Write-Host "Saved (Excel): $excelOut"
