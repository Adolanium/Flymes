from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request

from flymes.runner import atomic_json
from flymes.paths import hermes_home, state_root

ROOT = Path(__file__).resolve().parents[1]


def home():
    return hermes_home()


def service_path():
    return home()/"plugins"/"flymes"/"service.json"


def rpc(path, body=None):
    config = json.loads(service_path().read_text(encoding="utf-8"))
    req = urllib.request.Request(f"http://127.0.0.1:{config['port']}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer "+config["token"], "Content-Type": "application/json"})
    timeout = 10 if path == "state" or (body or {}).get("command") == "stop" else 120
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as response:
        return json.load(response)


def install():
    hermes_python = os.environ.get("FLYMES_HERMES_PYTHON")
    if not hermes_python or not Path(hermes_python).is_file():
        raise RuntimeError("Set FLYMES_HERMES_PYTHON to the Hermes interpreter before installing.")
    target = home()/"plugins"/"flymes"
    if ROOT.resolve() != target.resolve() and (target / '.hermes-catalog.json').exists():
        raise RuntimeError("Run setup from the installed catalog package; update it through Hermes.")
    config_path = home()/"config.yaml"
    # Preserve all host settings and make a byte-for-byte backup before the
    # single plugin allow-list change. YAML's comments are preserved by ruamel.
    code = """from pathlib import Path
import sys
import shutil
from ruamel.yaml import YAML
p=Path(sys.argv[1]); y=YAML(); y.preserve_quotes=True
text=p.read_text(encoding='utf-8') if p.exists() else ''; d=y.load(text) or {}
if not isinstance(d, dict): raise ValueError('Hermes config must be a mapping')
plugins=d.setdefault('plugins', {})
if not isinstance(plugins, dict): raise ValueError('plugins must be a mapping')
enabled=plugins.setdefault('enabled', [])
disabled=plugins.get('disabled', [])
if not isinstance(enabled, list) or not isinstance(disabled, list):
    raise ValueError('Plugin enabled and disabled settings must be lists')
if sys.argv[2] == 'check': sys.exit(0)
if 'flymes' not in enabled: enabled.append('flymes')
if 'flymes' in disabled: disabled.remove('flymes')
# The demo command now belongs to flymes. Disable the legacy duplicate.
if 'flymes-worker' in enabled: enabled.remove('flymes-worker')
if (p.parent/'plugins/flymes-worker').exists():
    disabled=plugins.setdefault('disabled', [])
    if 'flymes-worker' not in disabled: disabled.append('flymes-worker')
backup=p.with_name('config.yaml.flymes-backup')
if p.exists() and not backup.exists(): shutil.copy2(p, backup)
p.parent.mkdir(parents=True, exist_ok=True)
temp=p.with_name('config.yaml.flymes-tmp')
with temp.open('w', encoding='utf-8') as f: y.dump(d,f)
temp.replace(p)
"""
    subprocess.run([hermes_python, "-c", code, str(config_path), "check"], check=True)
    if ROOT.resolve() != target.resolve():
        files = ('__init__.py', 'plugin_init.py', 'plugin_worker.py', 'plugin.yaml',
                 'dashboard/manifest.json', 'dashboard/plugin_api.py', 'desktop/plugin.js')
        for name in files:
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing plugin file: {name}")
        for name in files:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
    subprocess.run([hermes_python, "-c", code, str(config_path), "apply"], check=True)
    print(f"Installed {target}. Restart the Hermes gateway to load its Python routes.")


def doctor(dataset):
    import psutil
    report = {"python": sys.version.split()[0], "platform": sys.platform,
              "memory_available_gb": round(psutil.virtual_memory().available/1e9, 2),
              "disk_free_gb": round(shutil.disk_usage(ROOT).free/1e9, 2),
              "dataset": str(dataset), "dataset_exists": dataset.is_dir(),
              "hermes_python_exists": Path(os.environ.get("FLYMES_HERMES_PYTHON", "missing")).is_file(),
              "hermes_root_exists": Path(os.environ.get("FLYMES_HERMES_ROOT", "missing")).is_dir(),
              "plugin_installed": (home()/"plugins/flymes/desktop/plugin.js").is_file(),
              "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pyarrow", "fastapi")}}
    report["worker_plugin_installed"] = (home()/"plugins/flymes/plugin_worker.py").is_file()
    source = Path(os.environ.get("FLYMES_HERMES_ROOT", "missing"))
    try:
        revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        report["hermes_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        report["hermes_commit"] = None
    report["original_live_test_commit"] = "ad03f20dd61919ca2135d6904e787a94284aacaf"
    metadata_path = dataset/"metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        report["loaded_dataset_record"] = {key: metadata.get(key) for key in ("dataset", "mode", "neurons", "connections", "synapses")}
    try:
        import yaml
        config = yaml.safe_load((home()/"config.yaml").read_text(encoding="utf-8")) or {}
        if not isinstance(config, dict) or not isinstance(config.get("plugins", {}), dict):
            raise ValueError("Invalid plugin configuration")
        enabled = config.get("plugins", {}).get("enabled", [])
        disabled = config.get("plugins", {}).get("disabled", [])
        if not isinstance(enabled, list) or not isinstance(disabled, list):
            raise ValueError("Invalid plugin allow-list")
        report["backend_allowlisted"] = "flymes" in enabled and "flymes" not in disabled
    except (OSError, ValueError, yaml.YAMLError):
        report["backend_allowlisted"] = False
    try:
        state = rpc("state")
        report["companion"] = state["status"]
    except Exception:
        report["companion"] = "unreachable; run scripts/launch.ps1"
    report["desktop_validation"] = "SDK source verified; renderer load must be checked in Hermes Desktop"
    report["failures"] = [description for ok, description in (
        (report["dataset_exists"], "Run scripts/prepare-data.ps1"),
        (report["hermes_python_exists"], "Set FLYMES_HERMES_PYTHON to the configured Hermes interpreter"),
        (report["plugin_installed"] and report["worker_plugin_installed"] and report["backend_allowlisted"], "Run scripts/setup.ps1 and restart the Hermes gateway"),
        (report["companion"] != "unreachable; run scripts/launch.ps1", "Run scripts/launch.ps1")) if not ok]
    print(json.dumps(report, indent=2))
    return report


async def run_demo(dataset, mode, steps):
    from flymes.runner import Runner
    runner = Runner(ROOT, dataset, max_steps=steps, lease_seconds=3600, state_root=state_root())
    await runner.control("start", mode=mode)
    await runner.control("resume")
    await runner.task
    result = runner.snapshot()
    print(json.dumps({"run_id": result["run_id"], "status": result["status"],
                      "steps": result["step"], "observation": result["observation"],
                      "error": result["error"], "artifacts": str(runner.outdir)}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Flymes connectome experiment commands")
    parser.add_argument("command", choices=["prepare-data", "doctor", "install", "serve", "run-demo", "run-controls", "state", "stop", "export", "arena"])
    parser.add_argument("--dataset", type=Path, default=state_root()/"data/malecns-v1/prepared-full")
    parser.add_argument("--cache", type=Path, default=state_root()/"data/malecns-v1")
    parser.add_argument("--max-neurons", type=int)
    parser.add_argument("--port", type=int, default=8742)
    parser.add_argument("--mode", choices=["REAL", "SHUFFLED", "SILENCED", "HEURISTIC", "LESIONED"], default="REAL")
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--circuit-seed", type=int, default=7)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--arena-modes", nargs='+', choices=['REAL', 'SHUFFLED', 'SILENCED', 'LESIONED', 'GREEDY', 'RANDOM'],
                        default=['REAL', 'SHUFFLED', 'SILENCED', 'LESIONED', 'GREEDY', 'RANDOM'])
    parser.add_argument("--lesion-percent", type=int, default=30)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    if args.command == 'arena':
        from flymes.arena import Arena
        from flymes.server import ArenaCommand
        async def experiment():
            arena = Arena(args.dataset, state_root() / '.flymes' / 'arena')
            await arena.control(ArenaCommand(command='compare', modes=args.arena_modes, seed=args.seed,
                                            seeds=args.seeds, max_steps=args.steps, lesion_percent=args.lesion_percent,
                                            circuit_seed=args.circuit_seed))
            try:
                previous = -1
                while not arena.task.done():
                    arena.lease = time.monotonic()
                    if arena.state['progress'] != previous:
                        previous = arena.state['progress']
                        print(f"Arena: {previous}/{arena.state['total']} episodes", file=sys.stderr, flush=True)
                    await asyncio.sleep(.2)
                await arena.task
            finally:
                await arena.close()
            print(json.dumps(arena.report, indent=2))
            if arena.state['status'] != 'completed':
                raise SystemExit(1)
        asyncio.run(experiment())
    elif args.command == "prepare-data":
        from flymes.data import prepare_data
        print(prepare_data(args.cache, max_neurons=args.max_neurons))
    elif args.command == "install":
        install()
    elif args.command == "doctor":
        if doctor(args.dataset)["failures"]:
            raise SystemExit(1)
    elif args.command == "serve":
        import uvicorn
        from flymes.server import create_app
        if service_path().exists():
            config = json.loads(service_path().read_text())
        else:
            config = {"token": secrets.token_urlsafe(48), "port": args.port}
        config["port"] = args.port
        atomic_json(service_path(), config)
        uvicorn.run(create_app(ROOT, args.dataset, config["token"], state_root=state_root()), host="127.0.0.1", port=args.port, timeout_graceful_shutdown=3)
    elif args.command == "run-demo":
        result = asyncio.run(run_demo(args.dataset, args.mode, args.steps))
        if result["status"] == "error":
            raise SystemExit(1)
    elif args.command == "run-controls":
        async def compare():
            from flymes.runner import Runner
            runner = Runner(ROOT, args.dataset, state_root=state_root())
            await runner.start()
            await runner.control("lesion", percent=20, seed=7)
            report = await runner.compare()
            atomic_json(state_root()/"artifacts/open-loop-controls.json", report)
            print(json.dumps({k: {"action": v["action"], "scores": v["scores"]} for k,v in report["results"].items()}, indent=2))
        asyncio.run(compare())
    elif args.command == "export":
        if args.run is None:
            parser.error("--run path to replay.json is required")
        from flymes.export import export_replay
        print(export_replay(args.run, state_root()/"artifacts/replay.json"))
    elif args.command == "state":
        print(json.dumps(rpc("state"), indent=2))
    elif args.command == "stop":
        try:
            print(rpc("control", {"command": "stop"})["status"])
        except (OSError, TimeoutError):
            print("Companion is unavailable; no stop acknowledgement received.")


if __name__ == "__main__":
    main()
