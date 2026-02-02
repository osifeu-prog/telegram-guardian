param(
  [string]$ScanJson = ".\out\scan_report.json",
  [string]$RiskCsv  = ".\out\risk_report.csv",
  [string]$OutMd    = ".\out\INVESTOR_STATUS.md"
)

$ErrorActionPreference="Stop"

# Always run relative to repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot | Out-Null

if (-not (Test-Path $ScanJson)) { throw "Missing scan report: $ScanJson" }
if (-not (Test-Path $RiskCsv))  { throw "Missing risk report: $RiskCsv" }

$scan = Get-Content $ScanJson -Raw | ConvertFrom-Json
$rows = Import-Csv $RiskCsv

$generated = $scan.generated_at_utc
$counts = $scan.counts

# Distribution
$byLevel = $rows | Group-Object risk_level | Sort-Object Name
function GetCount($name){
  $g = $byLevel | Where-Object Name -eq $name | Select-Object -First 1
  if ($null -eq $g) { return 0 }
  return [int]$g.Count
}
$high = GetCount "HIGH"
$med  = GetCount "MED"
$low  = GetCount "LOW"
$min  = GetCount "MIN"

# Top findings
$top = $rows |
  Sort-Object @{Expression={[int]$_.risk_score}; Descending=$true}, @{Expression={[int]$_.unread_count}; Descending=$true} |
  Select-Object -First 15

# Markdown
$md = New-Object System.Collections.Generic.List[string]
$md.Add("# telegram-guardian  Investor Status Report")
$md.Add("")
$md.Add("- **Generated (UTC):** $generated")
$md.Add("- **Scope:** Local, read-only MTProto scan (Telethon)  JSON + risk CSV")
$md.Add("")
$md.Add("## Product Snapshot")
$md.Add("- **What it does:** Enumerates dialogs (groups/channels/users), unread counts, and produces a deterministic report.")
$md.Add("- **What it never does:** Sends messages / modifies Telegram state.")
$md.Add("")
$md.Add("## Current Milestones")
$md.Add("- **M0: Guardrails + ScanJSON (stable)** ")
$md.Add("- **M1: Risk scoring + Investor report**  (baseline ruleset)")
$md.Add("- **M2: Versioned schema + delta between scans + packaging (CLI/CI)**  next")
$md.Add("")
$md.Add("## Key Metrics")
$md.Add("- **Dialogs total:** $($counts.dialogs_total)")
$md.Add("- **Groups:** $($counts.groups)")
$md.Add("- **Channels:** $($counts.channels)")
$md.Add("- **Users:** $($counts.users)")
$md.Add("")
$md.Add("## Risk Distribution (current ruleset)")
$md.Add("- **HIGH:** $high")
$md.Add("- **MED:**  $med")
$md.Add("- **LOW:**  $low")
$md.Add("- **MIN:**  $min")
$md.Add("")
$md.Add("## Top Findings (Top 15)")
$md.Add("")
$md.Add("| risk_level | risk_score | unread | peer_type | peer_id | title | hits |")
$md.Add("|---|---:|---:|---|---:|---|---|")
foreach($r in $top){
  $title = ([string]$r.title -replace '\|','/').Trim()
  $hits  = ([string]$r.risk_hits -replace '\|','/').Trim()
  $md.Add("| $($r.risk_level) | $($r.risk_score) | $($r.unread_count) | $($r.peer_type) | $($r.peer_id) | $title | $hits |")
}
$md.Add("")
$md.Add("## Security Notes")
$md.Add("- Session artifacts are sensitive and must never be committed (excluded via .gitignore).")
$md.Add("- FloodWait is handled using sleep+retry.")
$md.Add("")
$md.Add("## Next Steps (Roadmap)")
$md.Add("1. Add `report_version` and schema validation for scan report.")
$md.Add("2. Add scan diff (`previous_scan_report.json`) and trend metrics.")
$md.Add("3. Package as CLI (`tg-guardian scan`, `tg-guardian report`) + CI release artifacts.")
$md.Add("")

# Write UTF-8 no BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($OutMd, ($md -join "`n"), $utf8NoBom)

Write-Host "Wrote: $OutMd" -ForegroundColor Green