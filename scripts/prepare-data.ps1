param([int]$MaxNeurons = 0)
. "$PSScriptRoot\common.ps1"
$FlymesArgs = @('-m', 'flymes.cli', 'prepare-data')
if ($MaxNeurons -gt 0) { $FlymesArgs += @('--max-neurons', "$MaxNeurons") }
& $FlymesPython @FlymesArgs
if ($LASTEXITCODE -ne 0) { throw 'Data preparation failed; rerun to resume the download' }
