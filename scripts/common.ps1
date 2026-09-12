$ErrorActionPreference = 'Stop'
$FlymesRoot = Split-Path -Parent $PSScriptRoot
$FlymesPython = Join-Path $FlymesRoot '.venv\Scripts\python.exe'
if (-not $env:HERMES_HOME) { $env:HERMES_HOME = Join-Path $env:LOCALAPPDATA 'hermes' }
if (-not $env:FLYMES_HERMES_ROOT) {
    $FlymesSibling = Join-Path (Split-Path -Parent $FlymesRoot) 'hermes-agent'
    if (Test-Path (Join-Path $FlymesSibling '.venv\Scripts\python.exe')) {
        $env:FLYMES_HERMES_ROOT = $FlymesSibling
    } else { $env:FLYMES_HERMES_ROOT = Join-Path $env:HERMES_HOME 'hermes-agent' }
}
if (-not $env:FLYMES_HERMES_PYTHON) {
    $env:FLYMES_HERMES_PYTHON = Join-Path $env:FLYMES_HERMES_ROOT '.venv\Scripts\python.exe'
}
