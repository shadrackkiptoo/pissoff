param(
    [switch]$SkipVersionBump
)

$ErrorActionPreference = "Stop"
$clientPath = Join-Path $PSScriptRoot "client.py"
$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw "Virtual environment Python was not found at $pythonPath"
}

$clientSource = [System.IO.File]::ReadAllText($clientPath)
$versionPattern = '(?m)^APP_VERSION = "(\d+)\.(\d+)\.(\d+)"\r?$'
$versionMatch = [regex]::Match($clientSource, $versionPattern)
if (-not $versionMatch.Success) {
    throw "Could not find a semantic APP_VERSION in client.py"
}

$currentVersion = [version]::new(
    [int]$versionMatch.Groups[1].Value,
    [int]$versionMatch.Groups[2].Value,
    [int]$versionMatch.Groups[3].Value
)
$nextVersion = $currentVersion
if (-not $SkipVersionBump) {
    $nextVersion = [version]::new(
        $currentVersion.Major,
        $currentVersion.Minor,
        $currentVersion.Build + 1
    )
    $replacement = 'APP_VERSION = "{0}"' -f $nextVersion.ToString()
    $updatedSource = [regex]::Replace($clientSource, $versionPattern, $replacement, 1)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($clientPath, $updatedSource, $utf8NoBom)
    Write-Host "Client version: $currentVersion -> $nextVersion"
} else {
    Write-Host "Client version: $currentVersion"
}

& $pythonPath -m PyInstaller --clean --noconfirm (Join-Path $PSScriptRoot "KeyboardService.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Built dist\KeyboardService.exe for client version $nextVersion"
