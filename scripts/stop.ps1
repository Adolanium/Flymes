. "$PSScriptRoot\common.ps1"
try { & $FlymesPython -m flymes.cli stop } catch { Write-Output 'Companion was already unreachable.' }
$FlymesPidFile = Join-Path $FlymesRoot '.flymes\server.pid'
if (Test-Path -LiteralPath $FlymesPidFile) {
    $FlymesServerPid = [int](Get-Content -LiteralPath $FlymesPidFile)
    $FlymesServer = Get-CimInstance Win32_Process -Filter "ProcessId = $FlymesServerPid"
    if ($FlymesServer -and $FlymesServer.ExecutablePath -eq $FlymesPython -and $FlymesServer.CommandLine -match 'flymes.cli\s+serve') {
        Stop-Process -Id $FlymesServerPid
    }
}
