"""One neural decision, one bounded worker unit, one measured observation."""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import difflib
import json
from pathlib import Path
import shutil
import time
import uuid

from flymes.verifier import verify

ACTIONS = ["SEARCH", "INSPECT", "IMPLEMENT", "TEST", "REVIEW", "FINISH"]
TASK = "Fix visible_items in app.py: case-insensitive substring search, preserving order and inputs. Empty query returns all items."


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


class Runner:
    def __init__(self, root: Path, dataset: Path, *, max_steps=18, runtime=900,
                 adapter_factory=None, simulator_factory=None, lease_seconds=15, state_root=None):
        self.root = root.resolve()
        self.state_root = Path(state_root).resolve() if state_root is not None else self.root
        self.dataset = dataset.resolve()
        self.max_steps = max_steps
        self.runtime = runtime
        self.adapter_factory = adapter_factory
        self.simulator_factory = simulator_factory
        self.lease_seconds = lease_seconds
        self.lock = asyncio.Lock()
        self.task = None
        self.adapter = None
        self.sim = None
        self.history = []
        self.seen = {}
        self.checkpoints = {}
        self.state = {"status": "idle", "run_id": None, "step": 0, "mode": "REAL",
                      "dataset": {}, "decision": {}, "observation": {}, "history": [],
                      "simulation_time": 0, "wall_time": 0, "model": "Hermes configured provider",
                      "health": "not loaded", "error": None, "updated_at": now(),
                      "workspace": None, "task": TASK, "label": "LIVE",
                      "limits": {"max_steps": max_steps, "runtime_s": runtime}}
        self.lease = time.monotonic()
        self.started = time.monotonic()
        self.finished = None
        self.workspace = None
        self.initial = b""
        self.outdir = None

    def snapshot(self):
        result = dict(self.state)
        result["history"] = self.history[-100:]
        result["checkpoints"] = list(self.checkpoints)
        result["wall_time"] = (self.finished or time.monotonic())-self.started if self.state["run_id"] else 0
        return result

    def telemetry(self):
        """Bound renderer traffic; full evidence remains in events and replays."""
        state = self.snapshot()
        def compact_decision(decision, samples=False):
            fields = ("action", "mode", "scores", "readout", "valid_actions", "valid_action_mask",
                      "meaningful_choice", "encoder", "simulated_ms", "decision_ms", "activity", "health")
            result = {key: decision[key] for key in fields if key in decision}
            if samples:
                result.update({key: decision.get(key) for key in ("sample", "sample_edges", "sample_layout")})
            return result
        state["decision"] = compact_decision(state.get("decision", {}), samples=True)
        state["history_total"] = len(self.history)
        state["history"] = []
        for row in self.history[-8:]:
            result = row["result"]
            state["history"].append({"step": row["step"], "selected_action": row["selected_action"],
                "scores": row["scores"], "observation": row["observation"],
                "result": {"status": result.get("status"), "model_calls": result.get("model_calls"),
                           "duration_s": result.get("duration_s"), "verified": result.get("verified"),
                           "operations": [{"operation": op.get("operation"), "rejected": bool(op.get("rejected")),
                                           "changed": op.get("result", {}).get("changed")}
                                          for op in result.get("operations", [])]},
                "verification": {key: row["verification"].get(key) for key in ("passed", "failed", "verified")}
                                 if row.get("verification") else None})
        if state.get("comparisons"):
            state["comparisons"] = {**state["comparisons"], "results": {
                mode: compact_decision(decision) for mode, decision in state["comparisons"]["results"].items()}}
        state["telemetry_note"] = "Latest 8 results; complete checkpoints and operations are in the run log."
        return state

    def event(self, kind, **fields):
        record = {"kind": kind, "run_id": self.state["run_id"], "step": self.state["step"],
                  "timestamp": now(), **fields}
        if self.outdir:
            with (self.outdir / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, allow_nan=False)+"\n")
        self.state["updated_at"] = now()
        return record

    def observe(self, verification=None, result=None):
        content = (self.workspace / "app.py").read_bytes()
        previous = self.state.get("observation", {})
        counts = Counter(r["selected_action"] for r in self.history)
        v = verification or {}
        return {"tests_passed": v.get("passed", previous.get("tests_passed")),
                "tests_failed": v.get("failed", previous.get("tests_failed")),
                "last_exit_code": (result or v).get("exit_code"),
                "repeated_actions": counts.get(self.history[-1]["selected_action"], 0) if self.history else 0,
                "changed_files": int(content != self.initial),
                "diff_lines": sum(1 for line in difflib.unified_diff(self.initial.decode().splitlines(), content.decode().splitlines()) if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))),
                "elapsed_steps": self.state["step"],
                "verified": bool(v.get("verified")) if verification else False,
                "remaining_budget": max(0, self.max_steps-self.state["step"]),
                "remaining_budget_fraction": max(0, 1-self.state["step"]/self.max_steps)}

    async def start(self, mode="REAL", seed=7):
        if self.task and not self.task.done():
            raise ValueError("A run is already active. Stop it before starting a new run.")
        from flymes.data import Connectome
        from flymes.neural import Simulator
        from flymes.hermes_adapter import HermesAdapter
        self.sim = await asyncio.to_thread(self.simulator_factory or (lambda: Simulator(Connectome.load(self.dataset), seed=seed)))
        if mode == "LESIONED":
            self.sim.lesion(30, seed=seed)
        run_id = uuid.uuid4().hex
        self.workspace = self.state_root / "demo" / "workspaces" / run_id
        shutil.copytree(self.root / "demo" / "fixture", self.workspace)
        self.initial = (self.workspace / "app.py").read_bytes()
        self.outdir = self.state_root / ".flymes" / "runs" / run_id
        self.outdir.mkdir(parents=True)
        self.adapter = (self.adapter_factory or HermesAdapter)(self.workspace, verifier=verify)
        self.history, self.checkpoints = [], {}
        self.started = self.lease = time.monotonic()
        self.finished = None
        metadata = getattr(getattr(self.sim, "graph", None), "metadata", {})
        self.state.update(status="paused", run_id=run_id, step=0, mode=mode, dataset=metadata,
                          error=None, workspace=str(self.workspace), label="LIVE", decision={},
                          health="ready", simulation_time=0, comparisons=None)
        baseline = await asyncio.to_thread(verify, self.workspace)
        self.state["observation"] = self.observe(baseline)
        self.event("baseline", verification=baseline, task=TASK,
                   dataset=metadata, seed=seed, mode=mode,
                   limits=self.state["limits"],
                   source_sha256={file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                                  for file in (self.root/"flymes").glob("*.py")},
                   initial_sha256=hashlib.sha256(self.initial).hexdigest())
        await self.checkpoint()
        return self.snapshot()

    async def checkpoint(self):
        if self.sim is None:
            raise ValueError("Start a run before checkpointing.")
        if self.task and not self.task.done():
            raise ValueError("Pause and wait for the in-flight action before checkpointing.")
        key = f"step-{self.state['step']}-{len(self.checkpoints)}"
        saved = {"simulator": self.sim.checkpoint(), "observation": self.state["observation"],
                 "step": self.state["step"], "mode": self.state["mode"],
                 "source_run": self.state["run_id"], "created_at": now()}
        self.checkpoints[key] = saved
        atomic_json(self.outdir / "checkpoints" / (key+".json"), saved)
        self.event("checkpoint", checkpoint_id=key)
        return {"checkpoint_id": key}

    async def compare(self, checkpoint_id=None):
        if self.sim is None or (self.task and not self.task.done()):
            raise ValueError("Pause and wait for work to finish before comparing.")
        current = self.sim.checkpoint()
        saved = self.checkpoints.get(checkpoint_id) if checkpoint_id else None
        base = saved["simulator"] if saved else current
        obs = saved["observation"] if saved else self.state["observation"]
        results = {}
        try:
            for mode in ("REAL", "SHUFFLED", "SILENCED", "HEURISTIC", "LESIONED"):
                # Use the historical neural state/observation with the user's
                # current lesion mask for the intervention branch.
                branch = {**base, "lesioned": current["lesioned"]} if mode == "LESIONED" else base
                self.sim.restore(branch)
                results[mode] = await asyncio.to_thread(self.sim.decide, obs, ACTIONS, mode)
        finally:
            self.sim.restore(current)
        self.state["comparisons"] = {"kind": "open-loop sensitivity", "observation": obs,
                                     "checkpoint_id": checkpoint_id, "results": results}
        self.event("comparison", comparison=self.state["comparisons"])
        return self.state["comparisons"]

    async def _step(self):
        if self.state["step"] >= self.max_steps or time.monotonic()-self.started >= self.runtime:
            self.state["status"] = "stopped"
            self.event("safety_override", reason="run budget exhausted")
            return
        if time.monotonic()-self.lease > self.lease_seconds:
            self.state["status"] = "paused"
            self.event("safety_override", reason="controller lease expired")
            return
        self.state["step"] += 1
        step = self.state["step"]
        observation = dict(self.state["observation"])
        checkpoint = self.sim.checkpoint()
        ref = f"before-{step}.json"
        atomic_json(self.outdir / "checkpoints" / ref, checkpoint)
        decision = await asyncio.to_thread(self.sim.decide, observation, ACTIONS, self.state["mode"])
        action = decision["action"]
        if action not in ACTIONS:
            raise ValueError("Decoder selected an invalid action")
        self.state["decision"] = decision
        self.state["simulation_time"] = decision.get("simulated_ms", 0) / 1000
        self.state["health"] = decision.get("health", "unknown")
        self.event("decision", observation=observation, checkpoint=ref, decision=decision,
                   valid_actions=ACTIONS, forced_choice=False)
        result = await self.adapter.execute(action, TASK, self.state["run_id"], str(step),
                                            session_id="flymes-"+self.state["run_id"],
                                            evidence={"observation": observation, "recent_history": [
                                                {"action": row["selected_action"], "status": row["result"].get("status"),
                                                 "verification": row.get("verification")}
                                                for row in self.history[-3:]]})
        if self.state["status"] == "stopped":
            self.event("discarded_result", reason="run stopped before accepting worker result", action=action)
            return
        if result.get("model"):
            self.state["model"] = str(result.get("provider", ""))+" / "+str(result["model"])
        verification = result.get("verification")
        if action in ("TEST", "FINISH"):
            verification = await asyncio.to_thread(verify, self.workspace)
        record = {"step": step, "selected_action": action, "scores": decision["scores"],
                  "observation": observation, "checkpoint": ref, "decision": decision,
                  "result": result, "verification": verification}
        self.history.append(record)
        self.state["observation"] = self.observe(verification, result)
        self.event("result", **record, next_observation=self.state["observation"])
        if action == "FINISH" and verification and verification["verified"]:
            self.state["status"] = "completed"
            self.event("independent_completion", verification=verification)
        atomic_json(self.outdir / "replay.json", self.snapshot())

    async def _work(self, continuous):
        try:
            while self.state["status"] == "running":
                remaining = self.runtime - (time.monotonic()-self.started)
                if remaining <= 0:
                    self.state["status"] = "stopped"
                    self.event("safety_override", reason="run runtime exhausted")
                    break
                await asyncio.wait_for(self._step(), timeout=remaining)
                if not continuous:
                    break
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self.event("safety_override", reason="cancelled by user or connection watchdog")
            raise
        except TimeoutError:
            self.state["status"] = "stopped"
            if self.adapter:
                self.adapter.cancel()
            self.event("safety_override", reason="run runtime exhausted")
        except Exception as exc:
            self.state.update(status="error", error=f"{type(exc).__name__}: {exc}")
            self.event("failure", error=self.state["error"])
        finally:
            if self.state["status"] == "running":
                self.state["status"] = "paused"
            if self.state["status"] in ("stopped", "completed", "error") and self.finished is None:
                self.finished = time.monotonic()
            if self.outdir:
                atomic_json(self.outdir / "replay.json", self.snapshot())

    async def stop(self, reason="user stop"):
        self.state["status"] = "stopped"
        if self.finished is None:
            self.finished = time.monotonic()
        if self.adapter:
            result = self.adapter.cancel()
            if hasattr(result, "__await__"):
                await result
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.event("safety_override", reason=reason)
        if self.outdir:
            atomic_json(self.outdir / "replay.json", self.snapshot())

    async def control(self, command, **args):
        async with self.lock:
            self.lease = time.monotonic()
            request_id = args.pop("request_id", None)
            if request_id and request_id in self.seen:
                prior = self.seen[request_id]
                if prior[0] != (command, args):
                    raise ValueError("Request id reused with different parameters")
                return prior[1]
            if command == "start":
                await self.start(args.get("mode", "REAL"), args.get("seed", 7))
            elif command in ("step", "resume"):
                if self.sim is None or self.state["status"] not in ("paused",):
                    raise ValueError("A paused live run is required.")
                if self.task and not self.task.done():
                    raise ValueError("An action is already in flight.")
                self.lease = time.monotonic()
                self.state["status"] = "running"
                self.task = asyncio.create_task(self._work(command == "resume"))
            elif command == "pause":
                if self.state["status"] not in ("running", "paused"):
                    raise ValueError("Only a live run can be paused")
                self.state["status"] = "paused"
                self.event("safety_override", reason="pause after in-flight action")
            elif command == "stop":
                await self.stop(args.get("reason", "user stop"))
            elif command == "checkpoint":
                await self.checkpoint()
            elif command in ("compare", "replay"):
                await self.compare(args.get("checkpoint_id"))
            elif command in ("lesion", "clear_lesions"):
                if self.sim is None or (self.task and not self.task.done()):
                    raise ValueError("Pause and wait before changing neurons.")
                if command == "lesion":
                    self.sim.lesion(args.get("percent", 10), population=args.get("population"), seed=args.get("seed",7))
                    self.state["mode"] = "LESIONED"
                else:
                    self.sim.clear_lesions()
                    self.state["mode"] = "REAL"
                self.event("intervention", command=command, parameters=args, scope="current neural state")
            elif command != "heartbeat":
                raise ValueError("Unknown command")
            response = self.snapshot()
            if request_id:
                if len(self.seen) >= 1000:
                    self.seen.pop(next(iter(self.seen)))
                self.seen[request_id] = ((command, args), response)
            return response
