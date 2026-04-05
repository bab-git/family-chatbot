Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "FamilyChat.Common.ps1")

$repoRoot = Get-FamilyChatRepoRoot -ScriptDirectory $PSScriptRoot
$startupDir = [Environment]::GetFolderPath("Startup")
$startupLauncher = Join-Path $startupDir "Open Family Chat.cmd"
$startScript = Join-Path $repoRoot "scripts\windows\start-family-chat.ps1"

$content = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File ""$startScript"" -NoBrowser -Quiet`r`n"
Set-Content -LiteralPath $startupLauncher -Value $content -Encoding ASCII

Write-Host "Created startup launcher at:"
Write-Host $startupLauncher
Write-Host "Family Chat will now start automatically after the Windows user logs in."
