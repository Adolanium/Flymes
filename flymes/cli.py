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

ROOT = Path(__file__).resolve().parents[1]


def home():
    return Path(os.environ.get("HERMES_HOME", Path.home()/".hermes"))


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
    target = home()/"plugins"/"flymes"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT/'dashboard', target/'dashboard', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (target/'desktop').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'desktop/plugin.js', target/'desktop/plugin.js')
    shutil.copy2(ROOT/"plugin.yaml", target/"plugin.yaml")
    shutil.copy2(ROOT/"plugin_init.py", target/"__init__.py")
    shutil.copytree(ROOT/"agent-plugin", home()/"plugins/flymes-worker", dirs_exist_ok=True)
    config_path = home()/"config.yaml"
    # Preserve all host settings and make a byte-for-byte backup before the
    # single plugin allow-list change. YAML's comments are preserved by ruamel.
    hermes_python = os.environ.get("FLYMES_HERMES_PYTHON")
    if not hermes_python:
        raise RuntimeError("Set FLYMES_HERMES_PYTHON before installing the backend allow-list.")
    code = """from pathlib import Path
import sys
from ruamel.yaml import YAML
p=Path(sys.argv[1]); y=YAML(); y.preserve_quotes=True
text=p.read_text(encoding='utf-8'); d=y.load(text) or {}
plugins=d.setdefault('plugins', {})
enabled=plugins.setdefault('enabled', [])
for name in ('flymes', 'flymes-worker'):
    if name not in enabled: enabled.append(name)
    if name in plugins.get('disabled', []): plugins['disabled'].remove(name)
backup=p.with_name('config.yaml.flymes-backup')
if not backup.exists(): backup.write_text(text, encoding='utf-8')
with p.open('w', encoding='utf-8') as f: y.dump(d,f)
"""
    subprocess.run([hermes_python, "-c", code, str(config_path)], check=True)
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
    report["worker_plugin_installed"] = (home()/"plugins/flymes-worker/__init__.py").is_file()
    source = Path(os.environ.get("FLYMES_HERMES_ROOT", "missing"))
    try:
        revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        report["hermes_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        report["hermes_commit"] = None
    report["tested_commit_match"] = report["hermes_commit"] == "ad03f20dd61919ca2135d6904e787a94284aacaf"
    metadata_path = dataset/"metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        report["loaded_dataset_record"] = {key: metadata.get(key) for key in ("dataset", "mode", "neurons", "connections", "synapses")}
    try:
        import yaml
        config = yaml.safe_load((home()/"config.yaml").read_text(encoding="utf-8"))
        enabled = config.get("plugins", {}).get("enabled", [])
        disabled = config.get("plugins", {}).get("disabled", [])
        report["backend_allowlisted"] = all(name in enabled and name not in disabled for name in ("flymes", "flymes-worker"))
    except (OSError, ValueError):
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
        (report["tested_commit_match"], "Hermes source differs from tested version; verify docs/integration.md interfaces"),
        (report["companion"] != "unreachable; run scripts/launch.ps1", "Run scripts/launch.ps1")) if not ok]
    print(json.dumps(report, indent=2))
    return report


async def run_demo(dataset, mode, steps):
    from flymes.runner import Runner
    runner = Runner(ROOT, dataset, max_steps=steps, lease_seconds=3600)
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
    parser.add_argument("command", choices=["prepare-data", "doctor", "install", "serve", "run-demo", "run-controls", "state", "stop", "export"])
    parser.add_argument("--dataset", type=Path, default=ROOT/"data/malecns-v1/prepared-full")
    parser.add_argument("--cache", type=Path, default=ROOT/"data/malecns-v1")
    parser.add_argument("--max-neurons", type=int)
    parser.add_argument("--port", type=int, default=8742)
    parser.add_argument("--mode", choices=["REAL", "SHUFFLED", "SILENCED", "HEURISTIC", "LESIONED"], default="REAL")
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    if args.command == "prepare-data":
        from flymes.data import prepare_data
        print(prepare_data(args.cache, max_neurons=args.max_neurons))
    elif args.command == "install":
        install()
    elif args.command == "doctor":
        doctor(args.dataset)
    elif args.command == "serve":
        import uvicorn
        from flymes.server import create_app
        if service_path().exists():
            config = json.loads(service_path().read_text())
        else:
            config = {"token": secrets.token_urlsafe(48), "port": args.port}
        config["port"] = args.port
        atomic_json(service_path(), config)
        uvicorn.run(create_app(ROOT, args.dataset, config["token"]), host="127.0.0.1", port=args.port, timeout_graceful_shutdown=3)
    elif args.command == "run-demo":
        result = asyncio.run(run_demo(args.dataset, args.mode, args.steps))
        if result["status"] == "error":
            raise SystemExit(1)
    elif args.command == "run-controls":
        async def compare():
            from flymes.runner import Runner
            runner = Runner(ROOT, args.dataset)
            await runner.start()
            await runner.control("lesion", percent=20, seed=7)
            report = await runner.compare()
            atomic_json(ROOT/"artifacts/open-loop-controls.json", report)
            print(json.dumps({k: {"action": v["action"], "scores": v["scores"]} for k,v in report["results"].items()}, indent=2))
        asyncio.run(compare())
    elif args.command == "export":
        if args.run is None:
            parser.error("--run path to replay.json is required")
        from flymes.export import export_replay
        print(export_replay(args.run, ROOT/"artifacts/replay.json"))
    elif args.command == "state":
        print(json.dumps(rpc("state"), indent=2))
    elif args.command == "stop":
        try:
            print(rpc("control", {"command": "stop"})["status"])
        except (OSError, TimeoutError):
            print("Companion is unavailable; no stop acknowledgement received.")


if __name__ == "__main__":
    main()
