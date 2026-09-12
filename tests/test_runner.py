import asyncio
import json
from pathlib import Path
import shutil

import numpy as np
from scipy import sparse
from fastapi.testclient import TestClient

from flymes.data import Connectome
from flymes.neural import Simulator
from flymes.runner import Runner
from flymes.server import create_app
from flymes.verifier import verify


class RecordingAdapter:
    calls = []
    def __init__(self, workspace, verifier):
        self.workspace = workspace
    async def execute(self, action, task, run_id, step_id, **kwargs):
        self.calls.append((run_id, step_id, action))
        return {"action": action, "exit_code": 0}
    def cancel(self):
        pass


def make_runner(tmp_path):
    fixture = Path(__file__).parents[1]/"demo/fixture"
    shutil.copytree(fixture, tmp_path/"demo/fixture")
    graph = Connectome(sparse.eye(12, format="csr"), np.arange(12), {}, {"mode":"TEST FIXTURE"})
    return Runner(tmp_path, tmp_path/"unused", simulator_factory=lambda: Simulator(graph),
                  adapter_factory=RecordingAdapter, max_steps=2)


def test_neural_selection_is_dispatched_and_logged(tmp_path):
    async def run():
        runner = make_runner(tmp_path)
        await runner.control("start", request_id="one")
        first_id = runner.state["run_id"]
        duplicate = await runner.control("start", request_id="one")
        assert duplicate["run_id"] == first_id
        cp = runner.sim.checkpoint()
        predicted = runner.sim.decide(runner.state["observation"], ["SEARCH","INSPECT","IMPLEMENT","TEST","REVIEW","FINISH"])
        runner.sim.restore(cp)
        await runner.control("step")
        await runner.task
        assert runner.history[0]["selected_action"] == predicted["action"]
        assert RecordingAdapter.calls[-1][2] == predicted["action"]
        assert (runner.outdir/"checkpoints/before-1.json").exists()
        assert json.loads((runner.outdir/"replay.json").read_text())["label"] == "LIVE"
        await runner.control("lesion", percent=100)
        result = await runner.compare(next(iter(runner.checkpoints)))
        assert result["results"]["LESIONED"]["activity"]["mean"] == 0
        assert result["results"]["REAL"]["activity"]["mean"] > 0
        await runner.control("stop")
        assert runner.state["status"] == "stopped"
    asyncio.run(run())


def test_auth_origin_and_message_validation(tmp_path):
    runner = make_runner(tmp_path)
    app = create_app(tmp_path, tmp_path, "x"*48, runner)
    with TestClient(app) as client:
        assert client.get("/state").status_code == 401
        headers={"Authorization":"Bearer "+"x"*48}
        assert client.get("/state", headers=headers).status_code == 200
        assert client.get("/state", headers={**headers,"Origin":"https://evil.example"}).status_code == 403
        assert client.post("/control", headers=headers,json={"command":"start","workspace":"C:/"}).status_code == 422
        assert client.post("/control", headers=headers,json={"command":"lesion","percent":101}).status_code == 422
        assert client.post("/control", headers=headers,json={"command":"stop","reason":"panel_unmounted"}).status_code == 200


def test_independent_verifier_rejects_code_escape(tmp_path):
    (tmp_path/"app.py").write_text('import os\n')
    result = verify(tmp_path)
    assert result["boundary_rejected"] and not result["verified"]
    (tmp_path/"app.py").write_text('def visible_items(items, query):\n    return [item for item in items if query.casefold() in item.casefold()]\n')
    result = verify(tmp_path)
    assert result["verified"] and result["passed"] == 5


def test_budget_stop_is_not_neural_finish(tmp_path):
    async def run():
        runner = make_runner(tmp_path)
        runner.max_steps = 0
        # start avoids observation division by zero for a legitimate configured budget
        runner.max_steps = 1
        await runner.start()
        runner.state["step"] = 1
        await runner._step()
        assert runner.state["status"] == "stopped"
        assert not runner.history
        assert 'run budget exhausted' in (runner.outdir/"events.jsonl").read_text()
    asyncio.run(run())


def test_cancelled_worker_result_cannot_be_accepted(tmp_path):
    class LateAdapter(RecordingAdapter):
        async def execute(self, *args, **kwargs):
            try:
                await asyncio.sleep(20)
            except asyncio.CancelledError:
                return {"action": args[0], "status": "cancelled"}
    async def run():
        runner = make_runner(tmp_path)
        runner.adapter_factory = LateAdapter
        await runner.start()
        await runner.control("step")
        await asyncio.sleep(.03)
        await runner.stop()
        assert runner.state["status"] == "stopped"
        assert not runner.history
    asyncio.run(run())


def test_export_drops_worker_prose_and_private_paths(tmp_path):
    from flymes.export import export_replay
    source = tmp_path/"raw.json"
    source.write_text(json.dumps({"workspace":"C:/private", "history":[{
        "result":{"summary":"secret-token", "operations":[{"operation":"read", "request":{"path":"private"}}]},
        "verification":{"passed":0,"failed":1,"failures":[{"error":"secret-token"}]}
    }]}))
    target = tmp_path/"public.json"
    export_replay(source,target)
    assert "secret-token" not in target.read_text()
    assert "C:/private" not in target.read_text()


def test_full_recorded_comparison_fits_native_transport(tmp_path):
    root = Path(__file__).parents[1]
    recorded = json.loads((root/"artifacts/replay-real.json").read_text())
    comparison = json.loads((root/"artifacts/open-loop-controls.json").read_text())
    runner = make_runner(tmp_path)
    runner.state.update(recorded, comparisons=comparison)
    runner.history = recorded["history"] * 3
    compact = runner.telemetry()
    assert len(json.dumps(compact, separators=(',', ':')).encode()) < 60000
    assert compact["decision"]["sample"] == recorded["decision"]["sample"]
    assert len(compact["history"]) == 8
    assert compact["history_total"] == 18
    assert compact["comparisons"]["results"]["REAL"]["scores"] == comparison["results"]["REAL"]["scores"]


def test_loopback_comparison_response_finishes(tmp_path):
    import socket
    import threading
    import time
    import httpx
    import uvicorn
    root = Path(__file__).parents[1]
    runner = make_runner(tmp_path)
    recorded = json.loads((root/"artifacts/replay-real.json").read_text())
    runner.state.update(recorded, comparisons=json.loads((root/"artifacts/open-loop-controls.json").read_text()))
    runner.history = recorded["history"] * 3
    app = create_app(tmp_path, tmp_path, "test-token-"*5, runner)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', timeout_graceful_shutdown=1))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic()+5
        while not server.started and time.monotonic() < deadline:
            time.sleep(.01)
        assert server.started
        with httpx.Client(trust_env=False, timeout=3) as client:
            response = client.get(f'http://127.0.0.1:{port}/state', headers={'Authorization':'Bearer '+'test-token-'*5})
        assert response.status_code == 200
        assert response.json()['comparisons']['results']['REAL']['action'] == 'INSPECT'
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
    assert not thread.is_alive()
