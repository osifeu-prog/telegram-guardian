$ErrorActionPreference="Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot | Out-Null

powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\guardrails.ps1"