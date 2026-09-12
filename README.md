# Flymes

Flymes lets a MaleCNS connectome simulation select proposed tool calls in a real
Hermes conversation. Hermes proposes concrete alternatives, the controller picks
one, and Hermes executes it through its normal tool and permission pipeline.

Select **Hermes task** in the panel for this native integration. The older
fixture remains under **Built-in demo**. See [native Fly Mode](docs/native-mode.md)
for setup, session control, interventions and the limits of the experiment.

In the recorded six-step comparison, REAL stopped with 3/5 checks passing;
HEURISTIC completed with 5/5. The controller's failures are preserved alongside
its outputs. See [measured results](docs/results.md).

## Windows setup

Run in PowerShell from this repository. Python 3.11–3.13, uv, and a configured
Hermes installation are required. No WSL, Docker, CUDA or administrator account
is required. The scripts use a sibling Hermes checkout with a `.venv` when one
exists; otherwise set these paths to your Hermes runtime:

```powershell
$env:FLYMES_HERMES_ROOT = 'E:\Dev\Hermes\hermes-agent'
$env:FLYMES_HERMES_PYTHON = 'E:\Dev\Hermes\hermes-agent\.venv\Scripts\python.exe'
.\scripts\setup.ps1
.\scripts\prepare-data.ps1
.\scripts\doctor.ps1
.\scripts\launch.ps1
```

Setup pins Python dependencies through `uv.lock`, installs the Desktop pane and
backend under `$env:HERMES_HOME\plugins\flymes`, and adds only Flymes to the
backend allow-list. It preserves a config backup. Restart the Hermes gateway
after installation so it imports the backend. Enable Flymes in Desktop's
Capabilities → Plugins, then open the Flymes right pane. Prepare a run, then
Step or Run. Pause waits for the in-flight action; Stop cancels it.
If disk plugins remain at "copying", run "Reload desktop plugins" from the
command palette. That cleared the installed app's scan delay during validation.

The companion listens on `127.0.0.1:8742`. Its token lives only in the local
plugin's `service.json`. The native pane uses Hermes' authenticated proxy.
Do not share the service file or `.flymes` raw logs.

## Reproduce experiments

```powershell
.\scripts\run-demo.ps1 -Mode REAL -Steps 8
.\scripts\run-controls.ps1
.\scripts\run-demo.ps1 -Mode HEURISTIC -Steps 8
.\scripts\run-demo.ps1 -Mode SHUFFLED -Steps 8
.\scripts\run-demo.ps1 -Mode SILENCED -Steps 8
.\scripts\run-demo.ps1 -Mode LESIONED -Steps 8
.venv\Scripts\python.exe -m pytest -q
node --test desktop/plugin.test.mjs
```

Each closed-loop run starts from a fresh fixture snapshot. Default LESIONED
runs silence a seeded 30%. The `run-controls` command instead compares
identical observations without running Hermes and writes
`artifacts/open-loop-controls.json`. The run budget, model, interface and
verifier must match when comparing closed-loop results. No calibration or
training is performed, and no evaluation advantage is claimed.

These CLI experiments own separate runners and write replay files. To watch
live execution in the Desktop pane, use its Prepare run, Step and Run controls;
the pane follows the companion's run, not an independent CLI experiment.

The default conservative bound is 18 steps and 900 seconds. Each action has its
own model-call and time limit. The initial regression result is 3 passed and 2
failed. A failed FINISH or an exhausted budget never becomes a solved task.

## Data and outputs

The prepared graph lives in `data/malecns-v1/prepared-full`. Downloading the
necessary sources takes about 1.11 GB before derived files. Data stays outside
Git. Re-running preparation resumes downloads and verifies cached content.
`prepare-data.ps1 -MaxNeurons 5000` builds a visibly labeled development subset.
Point the Python command's `--dataset` option at that prepared subset to use it.

| Output | Location |
| --- | --- |
| Full graph benchmark | `docs/full-data-benchmark.json` |
| Private run logs and neural checkpoints | `.flymes/runs/<run-id>/` |
| Editable task copies | `demo/workspaces/<run-id>/` |
| Public replay | `artifacts/replay.json` |
| Read-only replay viewer | `desktop/harness.html` |
| Recording script and draft posts | `docs/demo.md` |

Export a numeric replay without worker prose or workspace paths:

```powershell
.venv\Scripts\python.exe -m flymes.cli export --run '.flymes\runs\RUN_ID\replay.json'
```

Open the replay viewer and select that exported file. The viewer labels it
REPLAY; it never fabricates activity or executes a model request.

Read [architecture](docs/architecture.md), [model assumptions](docs/modeling.md),
[data provenance](docs/data.md), [Desktop contract](docs/desktop.md), and
[recording guidance](docs/demo.md). `scripts/uninstall.ps1` removes the installed
Flymes plugin while preserving datasets and experiment records.
