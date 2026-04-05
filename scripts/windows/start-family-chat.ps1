param(
    [switch]$NoBrowser,
    [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "FamilyChat.Common.ps1")

$repoRoot = Get-FamilyChatRepoRoot -ScriptDirectory $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "No .env file was found. Run 'Setup Family Chat.cmd' first."
}

$uvExe = Require-FamilyChatCommand -Name "uv" -InstallHint "Install uv and reopen PowerShell."
$ollamaExe = Require-FamilyChatCommand -Name "ollama" -InstallHint "Install Ollama for Windows and reopen PowerShell."
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Push-Location $repoRoot
    try {
        if (-not $Quiet) {
            Write-Host "Creating the local Python environment with uv sync..."
        }
        & $uvExe sync
        if ($LASTEXITCODE -ne 0) {
            throw "uv sync failed."
        }
    } finally {
        Pop-Location
    }
}

$config = Get-FamilyChatRuntimeConfig -RepoRoot $repoRoot

Start-FamilyChatOllamaIfNeeded -RepoRoot $repoRoot -OllamaExe $ollamaExe -Quiet:$Quiet
Start-FamilyChatServerIfNeeded -RepoRoot $repoRoot -PythonExe $pythonExe -SettingsUrl $config.SettingsUrl -Quiet:$Quiet

if (-not $NoBrowser) {
    Start-Process $config.AppUrl | Out-Null
}

if (-not $Quiet) {
    Write-Host "Family Chat is ready at $($config.AppUrl)"
}
