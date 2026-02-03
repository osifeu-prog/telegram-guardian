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
    (Join-Path $repoRoot "out\ignore_peers.txt"),
    (Join-Path $repoRoot "out\ignore_peers.local.txt")
  )
}

if (-not (Test-Path -LiteralPath $InCsv)) {
  throw "Input CSV not found: $InCsv"
}

$ignore = @{}
$ignoreSource = @{}

foreach ($f in $IgnoreFiles) {
  if (-not (Test-Path -LiteralPath $f)) { continue }

  foreach ($line in (Get-Content -LiteralPath $f -ErrorAction Stop)) {
    $x = ($line -replace '#.*$','').Trim()
    if ([string]::IsNullOrWhiteSpace($x)) { continue }

    $parts = $x -split '\s+', 2
    $key = $parts[0].Trim()
    if ([string]::IsNullOrWhiteSpace($key)) { continue }

    $reason = ""
    if ($parts.Count -ge 2) { $reason = $parts[1].Trim() }

    $ignore[$key] = $reason
    $ignoreSource[$key] = $f
  }
}

$rows = Import-Csv -LiteralPath $InCsv

foreach ($r in $rows) {
  $peerKey = ("{0}:{1}" -f $r.peer_type, $r.peer_id)

  if ($ignore.ContainsKey($peerKey)) {
    $r | Add-Member ignored $true -Force
    $rr = [string]$ignore[$peerKey]
    if ([string]::IsNullOrWhiteSpace($rr)) { $rr = "ignored by list" }
    $r | Add-Member ignored_reason $rr -Force
    $r | Add-Member ignored_source ([string]$ignoreSource[$peerKey]) -Force
  }
  else {
    $r | Add-Member ignored $false -Force
    $r | Add-Member ignored_reason "" -Force
    $r | Add-Member ignored_source "" -Force
  }
}

$rows | Export-Csv -LiteralPath $OutCsv -NoTypeInformation -Encoding UTF8
Write-Host "OK: applied ignore => $OutCsv" -ForegroundColor Green
