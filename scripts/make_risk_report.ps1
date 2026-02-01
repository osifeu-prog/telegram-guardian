param(
  [string]$InPath  = ".\out\scan_report.json",
  [string]$OutPath = ".\out\risk_report.csv"
)

$ErrorActionPreference="Stop"
if (-not (Test-Path $InPath)) { throw "Missing: $InPath" }

function Fix-Mojibake([string]$s) {
  if ([string]::IsNullOrWhiteSpace($s)) { return $s }

  # heuristic: if it contains common mojibake markers, try to repair
  if ($s -match "Ã|Â|â|×") {
    try {
      $bytes = [Text.Encoding]::GetEncoding(1252).GetBytes($s)
      $fixed = [Text.Encoding]::UTF8.GetString($bytes)

      # if repair produced more readable text, use it
      if ($fixed -and ($fixed -notmatch "Ã|Â|â|×")) { return $fixed }
      return $fixed
    } catch {
      return $s
    }
  }
  return $s
}

$report = Get-Content $InPath -Raw | ConvertFrom-Json

# --- keywords (אפשר לערוך פה) ---
$riskWords = @(
  "signal","signals","pump","pumps","vip","insider","leak","leaks","futures","margin","scalp","scalping",
  "binance","bybit","kucoin","forex","gold","btc","bitcoin","alt","alts","profit","profits",
  "airdrop","notcoin","launch","pre-sale","presale","ico","ido",
  # hebrew/russian extras
  "סיגנל","סיגנלים","פאמפ","פאמפים","מסחר","חוזים","עתידיים","מינוף","סקאלפ","בינאנס","בייביט","קוקוין","פורקס","זהב","ביטקוין",
  "памп","сигнал","фьючерс","биржа"
)

# whitelists: מילים “מרגיעות” סיכון
$safeWords = @(
  "family","work","dev","engineering","admin","team","support","friends",
  "משפחה","עבודה","פיתוח","מנהל","ניהול","צוות","תמיכה","חברים"
)

$highUnread = 200
$veryHighUnread = 800

$rows = foreach ($d in $report.dialogs) {
  $rawTitle  = [string]$d.title
  $title     = Fix-Mojibake $rawTitle
  $titleNorm = ((if ($null -eq $title) { "" } else { [string]$title })).ToLowerInvariant()

  $hit = foreach ($w in $riskWords) { if ($titleNorm -match [regex]::Escape($w.ToLowerInvariant())) { $w } }
  $safeHit = foreach ($w in $safeWords) { if ($titleNorm -match [regex]::Escape($w.ToLowerInvariant())) { $w } }

  $unread = [int]$d.unread_count
  $score = 0

  if ($d.is_channel -and -not $d.is_group) { $score += 2 }
  if ($d.is_group) { $score += 1 }

  $score += [math]::Min(10, ($hit | Measure-Object).Count)

  if ($unread -ge $veryHighUnread) { $score += 5 }
  elseif ($unread -ge $highUnread) { $score += 3 }
  elseif ($unread -ge 50)          { $score += 1 }

  $score = [math]::Max(0, $score - [math]::Min(3, ($safeHit | Measure-Object).Count))

  $riskLevel =
    if ($score -ge 12) { "HIGH" }
    elseif ($score -ge 7) { "MED" }
    elseif ($score -ge 3) { "LOW" }
    else { "MIN" }

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
    risk_hits    = ($hit | Select-Object -Unique) -join ";"
    safe_hits    = ($safeHit | Select-Object -Unique) -join ";"
  }
}

$rows |
  Sort-Object -Property `
    @{Expression="risk_score"; Descending=$true}, `
    @{Expression="unread_count"; Descending=$true} |
  Export-Csv $OutPath -NoTypeInformation -Encoding UTF8

if (-not (Test-Path $OutPath)) { throw "Export failed; file not created: $OutPath" }
Write-Host "Saved: $OutPath"

# Optional: Excel-friendly copy (UTF8 BOM) אם צריך
$excelOut = [IO.Path]::ChangeExtension($OutPath, ".excel.csv")
$csv = Get-Content $OutPath -Raw
[IO.File]::WriteAllText($excelOut, $csv, (New-Object Text.UTF8Encoding($true)))
Write-Host "Saved (Excel): $excelOut"

