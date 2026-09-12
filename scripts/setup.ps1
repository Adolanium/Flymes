param([switch]$SkipInstall)
. "$PSScriptRoot\common.ps1"
Push-Location $FlymesRoot
try {
    uv sync --frozen --extra test
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    if (-not $SkipInstall) {
        & $FlymesPython -m flymes.cli install
        if ($LASTEXITCODE -ne 0) { throw 'Plugin installation failed' }
    }
} finally { Pop-Location }
