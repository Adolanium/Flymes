. "$PSScriptRoot\common.ps1"
if ([IO.Path]::GetFullPath($FlymesRoot).TrimEnd('\') -eq [IO.Path]::GetFullPath((Join-Path $env:HERMES_HOME 'plugins\flymes')).TrimEnd('\')) {
    throw 'For repository or catalog installs, run scripts/stop.ps1, then hermes plugins uninstall flymes from outside the plugin directory. Experiment data is retained in FLYMES_STATE_DIR.'
}
. "$PSScriptRoot\stop.ps1"
# Remove only the explicit Flymes plugin directory; retain datasets and runs.
$FlymesTarget = [IO.Path]::GetFullPath((Join-Path $env:HERMES_HOME 'plugins\flymes'))
$FlymesExpected = [IO.Path]::GetFullPath((Join-Path $env:HERMES_HOME 'plugins')) + [IO.Path]::DirectorySeparatorChar
if (-not $FlymesTarget.StartsWith($FlymesExpected, [StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $FlymesTarget) -ne 'flymes') { throw 'Unsafe uninstall target' }
if (Test-Path -LiteralPath $FlymesTarget) { Remove-Item -LiteralPath $FlymesTarget -Recurse -Force }
$FlymesWorkerTarget = [IO.Path]::GetFullPath((Join-Path $env:HERMES_HOME 'plugins\flymes-worker'))
if (-not $FlymesWorkerTarget.StartsWith($FlymesExpected, [StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $FlymesWorkerTarget) -ne 'flymes-worker') { throw 'Unsafe worker uninstall target' }
if (Test-Path -LiteralPath $FlymesWorkerTarget) { Remove-Item -LiteralPath $FlymesWorkerTarget -Recurse -Force }
$FlymesUninstallCode = @'
import os
from pathlib import Path
from ruamel.yaml import YAML
p=Path(os.environ['HERMES_HOME'])/'config.yaml'
y=YAML(); y.preserve_quotes=True; d=y.load(p.read_text(encoding='utf-8'))
for name in ('flymes','flymes-worker'):
    for key in ('enabled','disabled'):
        values=d.get('plugins',{}).get(key,[])
        if name in values: values.remove(name)
with p.open('w',encoding='utf-8') as f: y.dump(d,f)
'@
& $env:FLYMES_HERMES_PYTHON -c $FlymesUninstallCode
if ($LASTEXITCODE -ne 0) { throw 'Plugin files removed, but allow-list cleanup failed.' }
Write-Output 'Flymes plugin removed. Restart the Hermes gateway. Cached data and experiment records remain in FLYMES_STATE_DIR.'
