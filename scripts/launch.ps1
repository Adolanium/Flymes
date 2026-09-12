. "$PSScriptRoot\common.ps1"
$FlymesProbe = & $FlymesPython -c "from flymes.cli import rpc; print(rpc('state')['status'])" 2>$null
if ($LASTEXITCODE -eq 0) { Write-Output "Flymes companion is already running ($FlymesProbe)."; exit 0 }
$FlymesLogDir = Join-Path $FlymesRoot '.flymes'
New-Item -ItemType Directory -Path $FlymesLogDir -Force | Out-Null
$FlymesProcess = Start-Process -FilePath $FlymesPython -ArgumentList @('-m', 'flymes.cli', 'serve') -WorkingDirectory $FlymesRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $FlymesLogDir 'server.out.log') -RedirectStandardError (Join-Path $FlymesLogDir 'server.err.log')
Set-Content -LiteralPath (Join-Path $FlymesLogDir 'server.pid') -Value $FlymesProcess.Id
Write-Output 'Flymes companion launched on loopback port 8742. Open the Flymes pane in Hermes Desktop.'
