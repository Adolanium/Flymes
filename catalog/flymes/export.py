"""Export a public replay of numeric telemetry, excluding worker prose and paths."""
import json
from pathlib import Path
from flymes.runner import atomic_json


def export_replay(source: Path, target: Path):
    original = json.loads(source.read_text(encoding="utf-8"))
    allowed = ["status", "run_id", "step", "mode", "observation", "simulation_time", "wall_time", "health", "updated_at", "limits"]
    output = {key: original.get(key) for key in allowed}
    output.update(label="REPLAY", workspace="Demo fixture", task="Case-insensitive shopping-list search", model=original.get("model"))
    output["dataset"] = {k: v for k,v in original.get("dataset", {}).items()
                         if k in {"dataset", "neurons", "connections", "synapses", "mode", "filter", "license", "credit"}}
    output["decision"] = original.get("decision", {})
    output["comparisons"] = original.get("comparisons")
    output["history"] = [{k: row.get(k) for k in ("step", "selected_action", "scores", "observation", "decision", "verification")}
                         for row in original.get("history", [])]
    for exported, row in zip(output["history"], original.get("history", [])):
        verification = row.get("verification")
        exported["verification"] = {key: verification.get(key) for key in ("passed", "failed", "verified", "exit_code", "timeout")} if verification else None
        result = row.get("result", {})
        exported["result"] = {k: result.get(k) for k in ("action", "status", "model_calls", "duration_s", "verified", "exit_code")}
        exported["result"]["operations"] = [{"operation": op.get("operation"),
            "rejected": bool(op.get("rejected")), "changed": op.get("result", {}).get("changed")}
            for op in result.get("operations", [])]
    atomic_json(target, output)
    return target
