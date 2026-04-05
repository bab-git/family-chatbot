param(
    [switch]$InstallStartup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "FamilyChat.Common.ps1")

$repoRoot = Get-FamilyChatRepoRoot -ScriptDirectory $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"
$exampleEnvPath = Join-Path $repoRoot ".env.example"

if (-not (Test-Path -LiteralPath $envPath)) {
    if (-not (Test-Path -LiteralPath $exampleEnvPath)) {
        throw ".env.example is missing. Cannot create a local .env file."
    }

    Copy-Item -LiteralPath $exampleEnvPath -Destination $envPath
    Write-Host "Created .env from .env.example"
}

$currentKey = Get-FamilyChatEnvValue -EnvPath $envPath -Key "LANGGRAPH_AES_KEY" -Default ""
if ($currentKey.Length -notin @(16, 24, 32)) {
    $newKey = [guid]::NewGuid().ToString("N")
    Set-FamilyChatEnvValue -EnvPath $envPath -Key "LANGGRAPH_AES_KEY" -Value $newKey
    Write-Host "Generated a local LANGGRAPH_AES_KEY in .env"
}

$uvExe = Require-FamilyChatCommand -Name "uv" -InstallHint "Install uv and reopen PowerShell."
$ollamaExe = Require-FamilyChatCommand -Name "ollama" -InstallHint "Install Ollama for Windows and reopen PowerShell."

Push-Location $repoRoot
try {
    Write-Host "Installing Python dependencies with uv sync..."
    & $uvExe sync
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed."
    }
} finally {
    Pop-Location
}

$config = Get-FamilyChatRuntimeConfig -RepoRoot $repoRoot

Start-FamilyChatOllamaIfNeeded -RepoRoot $repoRoot -OllamaExe $ollamaExe
Ensure-FamilyChatModelInstalled -OllamaExe $ollamaExe -ModelName $config.ChatModel
if ($config.GuardModel -and $config.GuardModel -ne $config.ChatModel) {
    Ensure-FamilyChatModelInstalled -OllamaExe $ollamaExe -ModelName $config.GuardModel
}

if ($InstallStartup) {
    & (Join-Path $PSScriptRoot "install-startup.ps1")
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next time, start the app by double-clicking 'Open Family Chat.cmd'."
if (-not $InstallStartup) {
    Write-Host "If you want it to start automatically after login, run 'Enable Family Chat Auto Start.cmd' once."
}
