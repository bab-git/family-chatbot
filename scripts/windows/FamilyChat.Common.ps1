Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-FamilyChatRepoRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptDirectory
    )

    return Split-Path -Parent (Split-Path -Parent $ScriptDirectory)
}

function Get-FamilyChatEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvPath,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [string]$Default = ""
    )

    if (-not (Test-Path -LiteralPath $EnvPath)) {
        return $Default
    }

    foreach ($rawLine in Get-Content -LiteralPath $EnvPath) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }

        $parts = $line.Split("=", 2)
        if ($parts[0].Trim() -ne $Key) {
            continue
        }

        $value = $parts[1].Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        return $value
    }

    return $Default
}

function Set-FamilyChatEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvPath,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $lines = @()
    if (Test-Path -LiteralPath $EnvPath) {
        $lines = [System.Collections.Generic.List[string]]::new()
        foreach ($line in Get-Content -LiteralPath $EnvPath) {
            $null = $lines.Add($line)
        }
    } else {
        $lines = [System.Collections.Generic.List[string]]::new()
    }

    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i += 1) {
        $line = $lines[$i].Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }

        $parts = $line.Split("=", 2)
        if ($parts[0].Trim() -eq $Key) {
            $lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $null = $lines.Add("$Key=$Value")
    }

    Set-Content -LiteralPath $EnvPath -Value $lines -Encoding ASCII
}

function Get-FamilyChatRuntimeConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $envPath = Join-Path $RepoRoot ".env"
    $host = Get-FamilyChatEnvValue -EnvPath $envPath -Key "FAMILY_CHAT_HOST" -Default "127.0.0.1"
    $port = Get-FamilyChatEnvValue -EnvPath $envPath -Key "FAMILY_CHAT_PORT" -Default "8080"
    $browserHost = if ($host -in @("0.0.0.0", "::")) { "127.0.0.1" } else { $host }

    return [pscustomobject]@{
        RepoRoot    = $RepoRoot
        EnvPath     = $envPath
        Host        = $host
        Port        = $port
        BrowserHost = $browserHost
        AppUrl      = "http://$browserHost`:$port"
        SettingsUrl = "http://$browserHost`:$port/api/settings"
        ChatModel   = Get-FamilyChatEnvValue -EnvPath $envPath -Key "FAMILY_CHAT_CHAT_MODEL" -Default "llama3.2:1b"
        GuardModel  = Get-FamilyChatEnvValue -EnvPath $envPath -Key "FAMILY_CHAT_GUARD_MODEL" -Default "llama-guard3:1b"
    }
}

function Require-FamilyChatCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$InstallHint
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "$Name was not found. $InstallHint"
    }

    return $command.Source
}

function Test-FamilyChatHttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSec = 2
    )

    try {
        $null = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec
        return $true
    } catch {
        return $false
    }
}

function Wait-FamilyChatHttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$Attempts = 45,
        [int]$DelaySeconds = 1
    )

    for ($attempt = 0; $attempt -lt $Attempts; $attempt += 1) {
        if (Test-FamilyChatHttpEndpoint -Url $Url) {
            return $true
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    return $false
}

function Start-FamilyChatOllamaIfNeeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$OllamaExe,
        [switch]$Quiet
    )

    if (Test-FamilyChatHttpEndpoint -Url "http://127.0.0.1:11434/api/tags") {
        return
    }

    $logsDir = Join-Path $RepoRoot "logs"
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
    $ollamaLog = Join-Path $logsDir "ollama.log"
    $ollamaErr = Join-Path $logsDir "ollama.err.log"

    if (-not $Quiet) {
        Write-Host "Starting Ollama..."
    }

    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WorkingDirectory $RepoRoot -WindowStyle Hidden -RedirectStandardOutput $ollamaLog -RedirectStandardError $ollamaErr | Out-Null

    if (-not (Wait-FamilyChatHttpEndpoint -Url "http://127.0.0.1:11434/api/tags")) {
        throw "Ollama did not start. See $ollamaErr"
    }
}

function Start-FamilyChatServerIfNeeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$SettingsUrl,
        [switch]$Quiet
    )

    if (Test-FamilyChatHttpEndpoint -Url $SettingsUrl) {
        return
    }

    $logsDir = Join-Path $RepoRoot "logs"
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
    $serverLog = Join-Path $logsDir "family-chat.log"
    $serverErr = Join-Path $logsDir "family-chat.err.log"

    if (-not $Quiet) {
        Write-Host "Starting Family Chat server..."
    }

    Start-Process -FilePath $PythonExe -ArgumentList "-m", "family_chat.server" -WorkingDirectory $RepoRoot -WindowStyle Hidden -RedirectStandardOutput $serverLog -RedirectStandardError $serverErr | Out-Null

    if (-not (Wait-FamilyChatHttpEndpoint -Url $SettingsUrl)) {
        throw "Family Chat did not start. See $serverErr"
    }
}

function Get-FamilyChatInstalledModels {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OllamaExe
    )

    $output = & $OllamaExe list 2>$null
    if ($LASTEXITCODE -ne 0) {
        return @()
    }

    return @(
        $output |
            Select-Object -Skip 1 |
            ForEach-Object {
                $parts = ($_ -split "\s+") | Where-Object { $_ }
                if ($parts.Count -gt 0) { $parts[0] }
            } |
            Where-Object { $_ }
    )
}

function Ensure-FamilyChatModelInstalled {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OllamaExe,
        [Parameter(Mandatory = $true)]
        [string]$ModelName,
        [switch]$Quiet
    )

    if (-not $ModelName) {
        return
    }

    $installed = Get-FamilyChatInstalledModels -OllamaExe $OllamaExe
    if ($installed -contains $ModelName) {
        if (-not $Quiet) {
            Write-Host "$ModelName is already installed."
        }
        return
    }

    Write-Host "Pulling $ModelName ..."
    & $OllamaExe pull $ModelName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to pull $ModelName."
    }
}
