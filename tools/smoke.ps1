param(
  [string]$Base = "https://telegram-guardian-production.up.railway.app",
  [string]$Secret = "",
  [int]$ChatId = 0,
  [int]$FromUserId = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$msg) { throw $msg }
function Ok([string]$msg)   { Write-Host ("OK: " + $msg) -ForegroundColor Green }
function Info([string]$msg) { Write-Host ("INFO: " + $msg) -ForegroundColor Cyan }

if (-not $Secret) { Fail "Secret missing (pass -Secret ...)" }

Info "Base=$Base"

# 1) ops health (db + sha)
Info "GET /ops/health"
$ops = (curl.exe -sS "$Base/ops/health") | ConvertFrom-Json
if (-not $ops.ok) { Fail ("/ops/health not ok: " + ($ops | ConvertTo-Json -Compress)) }
Ok ("/ops/health ok; sha=" + $ops.railway_git_commit_sha + " stamp=" + $ops.app_build_stamp + " db_ok=" + $ops.db.ok)

# 2) tg last (discover chat_id)
Info "GET /tg/last"
$last = (curl.exe -sS "$Base/tg/last" -H "X-Telegram-Bot-Api-Secret-Token: $Secret") | ConvertFrom-Json
if (-not $last.ok) { Fail ("/tg/last failed: " + ($last | ConvertTo-Json -Compress)) }
Ok ("last=" + ($last.last | ConvertTo-Json -Compress))

if ($ChatId -le 0) {
  $ChatId = [int]($last.last.chat_id)
}
if ($FromUserId -le 0) {
  $FromUserId = [int]($last.last.from_user_id)
}
if ($ChatId -le 0 -or $FromUserId -le 0) {
  Fail "Missing ChatId/FromUserId. Send /start to the bot, then rerun. (We read them from /tg/last)"
}

Info "Resolved ChatId=$ChatId FromUserId=$FromUserId"

# 3) outbound ping
Info "POST /tg/ping"
$msg = [uri]::EscapeDataString(("smoke ping ✅ " + (Get-Date).ToString("s")))
$pingUrl = "$Base/tg/ping?chat_id=$ChatId&text=$msg"
$ping = (curl.exe -sS -X POST "$pingUrl" -H "X-Telegram-Bot-Api-Secret-Token: $Secret") | ConvertFrom-Json
if (-not $ping.ok) { Fail ("/tg/ping failed: " + ($ping | ConvertTo-Json -Compress)) }
Ok ("/tg/ping ok bot=@"+$ping.bot.username)

# 4) inbound simulate -> /whoami
Info "POST /tg/simulate"
$simText = [uri]::EscapeDataString("/whoami")
$simUrl = "$Base/tg/simulate?chat_id=$ChatId&from_user_id=$FromUserId&text=$simText"
$sim = (curl.exe -sS -X POST "$simUrl" -H "X-Telegram-Bot-Api-Secret-Token: $Secret") | ConvertFrom-Json
if (-not $sim.ok) { Fail ("/tg/simulate failed: " + ($sim | ConvertTo-Json -Compress)) }
Ok "/tg/simulate ok"
