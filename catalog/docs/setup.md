# Setup and removal

Flymes supports a local Windows Hermes Desktop and gateway with combined plugin
packages, plugin tool hooks, and the Desktop SDK. Python 3.11 through
3.13, uv, Git, and a configured Hermes provider are required. The plugin bridge
uses only Python's standard library; the companion installs its scientific and
HTTP dependencies into its own `.venv` using `uv.lock`.

## Choose the Hermes installation

Run PowerShell from the Flymes source checkout or the installed package directory.
Use the same home as the gateway. The scripts default to `%LOCALAPPDATA%\hermes`;
set `HERMES_HOME` explicitly for a different home or profile.

```powershell
$env:HERMES_HOME = Join-Path $env:LOCALAPPDATA 'hermes'
$env:FLYMES_HERMES_ROOT = Join-Path $env:HERMES_HOME 'hermes-agent'
$env:FLYMES_HERMES_PYTHON = Join-Path $env:FLYMES_HERMES_ROOT '.venv\Scripts\python.exe'
.\scripts\setup.ps1
.\scripts\prepare-data.ps1
.\scripts\launch.ps1
.\scripts\doctor.ps1
```

If Hermes uses another interpreter, set its actual path. The scripts also detect
a sibling `hermes-agent` checkout with a `.venv`. No administrator access, WSL,
Docker, or CUDA is needed. Data preparation downloads about 1.11 GB before derived
files; see [data requirements](data.md) for storage and memory measurements.

Restart the Hermes gateway after setup, enable Flymes in Desktop's
**Capabilities > Plugins**, and open its right pane. If the pane is missing,
run **Reload desktop plugins** from the command palette. `doctor.ps1` needs a
running companion and exits unsuccessfully when a required check fails.

Setup enables only `flymes` and preserves unrelated plugin settings. It saves
the original configuration as `config.yaml.flymes-backup`. The old separate
`flymes-worker` plugin is disabled if present because its command now belongs to
Flymes. A normal catalog install already contains every plugin file; setup runs
in place and does not replace the pinned source.

## Storage and existing experiments

The default state directory is `$HERMES_HOME\flymes`. Set `FLYMES_STATE_DIR`
before running any scripts to change it. Use an absolute path outside
`$HERMES_HOME\plugins\flymes` so a plugin update cannot remove it.

| Content | Path under the state directory |
| --- | --- |
| Downloaded and prepared graph | `data/malecns-v1/` |
| Native decision logs and checkpoints | `.flymes/native-runs/` |
| Built-in demo logs and checkpoints | `.flymes/runs/` |
| Arena episodes and comparison reports | `.flymes/arena/` |
| Disposable demo workspaces | `demo/workspaces/` |
| Exported numeric replay | `artifacts/replay.json` |
| Companion logs and process ID | `.flymes/` |

Versions before 0.2.0 kept these files in the source checkout. Nothing migrates
or deletes existing data automatically. To keep using it, set
`$env:FLYMES_STATE_DIR` to that checkout's absolute path. Do not point it at a
catalog installation. Alternatively copy the existing `data`, `.flymes`, and
`demo/workspaces` directories into the new state directory while Flymes is stopped.

The local bearer token and active-session marker remain in
`$HERMES_HOME\plugins\flymes\service.json` and `native-gate.json`. Do not share
them. Raw logs contain tool arguments, outputs, and local project paths.

## Update or remove

First choose **Return control to Hermes** for any active Fly Mode session, then
run `scripts/stop.ps1`. Stop the companion before updating its code. Repository
installs use `hermes plugins update flymes`; a future catalog install adopts only
its reviewed commit. Rerun setup after an update to sync the locked dependencies.
Flymes has no code downloader or in-app self-updater.

For repository or catalog installs, change to a directory outside the plugin and
run `hermes plugins uninstall flymes`. For a source checkout installed through
`setup.ps1`, run `scripts/uninstall.ps1` from that source checkout instead. Restart
the gateway and reload Desktop plugins. State and downloaded data remain in
`FLYMES_STATE_DIR`.

Keep only one Desktop copy. Move an older manually installed
`desktop-plugins/flymes` folder out of Hermes before switching to the combined
package; Hermes can otherwise keep loading the older copy.
