$ErrorActionPreference="Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "..") | Out-Null

$src = "out\sessions\poc.session*"
$dstDir = "out\sessions_backup"
New-Item -ItemType Directory -Force $dstDir | Out-Null

Copy-Item $src $dstDir -Force
Write-Host "Backed up to $dstDir"
