param(
  [string]$InCsv,
  [string]$OutCsv,
  [string[]]$IgnoreFiles
)

$ErrorActionPreference="Stop"

# Resolve script + repo root safely
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")

if ([string]::IsNullOrWhiteSpace($InCsv))  { $InCsv  = Join-Path $repoRoot "out\risk_report.csv" }
if ([string]::IsNullOrWhiteSpace($OutCsv)) { $OutCsv = Join-Path $repoRoot "out\risk_report.csv" }

if ($null -eq $IgnoreFiles -or $IgnoreFiles.Count -eq 0) {
  $IgnoreFiles = @(
    (Join-Path $repoRoot "policy\ignore_defaults.txt"),
    (Join-Path $repoRoot "policy\ignore.local.txt")
  )
}

if (-not (Test-Path -LiteralPath $InCsv)) { throw "Input CSV not found: $InCsv" }

# ignore maps
$ignoreExact = @{}        # key => reason  (key can be "peer_type:peer_id" OR "peer_id")
$ignoreSource = @{}       # key => file path
$titleRegexRules = @()    # @{ rx = <regex>; reason = <reason>; source = <file> }

foreach ($f in $IgnoreFiles) {
  if (-not (Test-Path -LiteralPath $f)) { continue }

  foreach ($line in (Get-Content -LiteralPath $f -ErrorAction Stop)) {
    $x = ($line -replace '#.*$','').Trim()
    if ([string]::IsNullOrWhiteSpace($x)) { continue }

    $parts = $x -split '\s+', 2
    $key = $parts[0].Trim()
    $reason = ""
    if ($parts.Count -ge 2) { $reason = $parts[1].Trim() }

    if ([string]::IsNullOrWhiteSpace($key)) { continue }

    if ($key -like "title_regex:*") {
      $rx = $key.Substring("title_regex:".Length)
      if ([string]::IsNullOrWhiteSpace($rx)) { continue }

      $titleRegexRules += [pscustomobject]@{
        rx     = $rx
        reason = $(if ([string]::IsNullOrWhiteSpace($reason)) { "ignored by title regex" } else { $reason })
        source = $f
      }
      continue
    }

    # Exact key (peer_type:peer_id) or just peer_id
    $ignoreExact[$key] = $reason
    $ignoreSource[$key] = $f
  }
}

$rows = Import-Csv -LiteralPath $InCsv

foreach ($r in $rows) {
  $peerType = [string]$r.peer_type
  $peerId   = [string]$r.peer_id
  $peerKey  = ("{0}:{1}" -f $peerType, $peerId)

  $ignored = $false
  $why = ""
  $src = ""

  # 1) Exact full key
  if ($ignoreExact.ContainsKey($peerKey)) {
    $ignored = $true
    $why = [string]$ignoreExact[$peerKey]
    if ([string]::IsNullOrWhiteSpace($why)) { $why = "ignored by list" }
    $src = [string]$ignoreSource[$peerKey]
  }
  # 2) peer_id only
  elseif ($ignoreExact.ContainsKey($peerId)) {
    $ignored = $true
    $why = [string]$ignoreExact[$peerId]
    if ([string]::IsNullOrWhiteSpace($why)) { $why = "ignored by peer_id" }
    $src = [string]$ignoreSource[$peerId]
  }
  # 3) title regex
  else {
    $title = [string]$r.title
    foreach ($rule in $titleRegexRules) {
      try {
        if ($title -match $rule.rx) {
          $ignored = $true
          $why = [string]$rule.reason
          $src = [string]$rule.source
          break
        }
      } catch {
        # ignore bad regex rule (keeps pipeline alive)
      }
    }
  }

  $r | Add-Member ignored $ignored -Force
  $r | Add-Member ignored_reason $(if ($ignored) { $why } else { "" }) -Force
  $r | Add-Member ignored_source $(if ($ignored) { $src } else { "" }) -Force
}

$rows | Export-Csv -LiteralPath $OutCsv -NoTypeInformation -Encoding UTF8
Write-Host "OK: applied ignore => $OutCsv" -ForegroundColor Green

