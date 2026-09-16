param([ValidateSet('REAL','SHUFFLED','SILENCED','HEURISTIC','LESIONED')][string]$Mode = 'REAL', [int]$Steps = 18)
. "$PSScriptRoot\common.ps1"
& $FlymesPython -m flymes.cli run-demo --mode $Mode --steps $Steps
if ($LASTEXITCODE -ne 0) { throw 'Demo execution failed' }
