. "$PSScriptRoot\common.ps1"
& $FlymesPython -m flymes.cli run-controls
if ($LASTEXITCODE -ne 0) { throw 'Control experiment failed' }
