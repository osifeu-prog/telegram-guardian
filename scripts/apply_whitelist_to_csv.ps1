param(
  [string]$InCsv,
  [string]$OutCsv,
  [string]$WhiteFiles
)

$ErrorActionPreference="Stop"

# Resolve repo root safely
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if ([string]::IsNullOrWhiteSpace($InCsv))  { $InCsv  = Join-Path $repoRoot "out\risk_report.csv" }
if ([string]::IsNullOrWhiteSpace($OutCsv)) { $OutCsv = Join-Path $repoRoot "out\risk_report.csv" }

# Default whitelist file list (comma-separated)
if ([string]::IsNullOrWhiteSpace($WhiteFiles)) {
  $WhiteFiles = @(
    (Join-Path $repoRoot "policy\whitelist_defaults.txt"),
    (Join-Path $repoRoot "policy\whitelist.local.txt")
  ) -join ","
}

if (-not (Test-Path -LiteralPath $InCsv)) { throw "Input CSV not found: $InCsv" }

# Parse whitelist rules
$wlExact  = @{}   # key => reason (key can be "peer_type:peer_id" OR "peer_id")
$wlSource = @{}   # key => file path
$wlRx     = @()   # @{ rx = <regex>; reason=<reason>; source=<file> }

$files = $WhiteFiles -split '\s*,\s*' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

foreach ($f in $files) {
  $fp = $f
  if (-not (Test-Path -LiteralPath $fp)) { continue }

  foreach ($line in (Get-Content -LiteralPath $fp -ErrorAction Stop)) {
    $x = ($line -replace '#.*$','').Trim()
    if ([string]::IsNullOrWhiteSpace($x)) { continue }

    $parts  = $x -split '\s+', 2
    $key    = $parts[0].Trim()
    $reason = ""
    if ($parts.Count -ge 2) { $reason = $parts[1].Trim() }
    if ([string]::IsNullOrWhiteSpace($key)) { continue }

    if ($key -like "title_regex:*") {
      $rx = $key.Substring("title_regex:".Length)
      if ([string]::IsNullOrWhiteSpace($rx)) { continue }
      $wlRx += [pscustomobject]@{ rx = $rx; reason = $reason; source = $fp }
      continue
    }

    $wlExact[$key]  = $reason
    $wlSource[$key] = $fp
  }
}

$rows = Import-Csv -LiteralPath $InCsv

foreach ($r in $rows) {
  $peerType = [string]$r.peer_type
  $peerId   = [string]$r.peer_id
  $peerKey  = ("{0}:{1}" -f $peerType, $peerId)

  $isWl = $false
  $why  = ""
  $src  = ""

  if ($wlExact.ContainsKey($peerKey)) {
    $isWl = $true
    $why  = [string]$wlExact[$peerKey]
    if ([string]::IsNullOrWhiteSpace($why)) { $why = "whitelisted by peer key" }
    $src  = [string]$wlSource[$peerKey]
  }
  elseif ($wlExact.ContainsKey($peerId)) {
    $isWl = $true
    $why  = [string]$wlExact[$peerId]
    if ([string]::IsNullOrWhiteSpace($why)) { $why = "whitelisted by peer_id" }
    $src  = [string]$wlSource[$peerId]
  }
  else {
    $title = [string]$r.title
    foreach ($rule in $wlRx) {
      try {
        if ($title -match $rule.rx) {
          $isWl = $true
          $why  = [string]$rule.reason
          if ([string]::IsNullOrWhiteSpace($why)) { $why = "whitelisted by title regex" }
          $src  = [string]$rule.source
          break
        }
      } catch {
        # ignore bad regex, keep pipeline alive
      }
    }
  }

  $r | Add-Member whitelisted $isWl -Force
  $r | Add-Member whitelist_reason $(if($isWl){$why}else{""}) -Force
  $r | Add-Member whitelist_source $(if($isWl){$src}else{""}) -Force

  if ($isWl) {
    # hard override: trusted -> MIN
    $r.risk_level = "MIN"
  }
}

$rows | Export-Csv -LiteralPath $OutCsv -NoTypeInformation -Encoding UTF8
Write-Host "OK: applied whitelist => $OutCsv" -ForegroundColor Green
