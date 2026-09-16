. "$PSScriptRoot\common.ps1"
& $FlymesPython -m flymes.cli doctor
if ($LASTEXITCODE -ne 0) { throw 'Diagnosis failed' }
