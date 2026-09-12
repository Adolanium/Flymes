"""Authenticated loopback companion. Gateway proxy keeps token out of renderer."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import json
import os
from pathlib import Path
import time
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from flymes.runner import Runner
from flymes.native_controller import NativeController


class Control(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: Literal["start", "resume", "pause", "step", "stop", "checkpoint", "replay", "lesion", "clear_lesions", "compare", "heartbeat"]
    mode: Literal["REAL", "SHUFFLED", "SILENCED", "HEURISTIC", "LESIONED"] = "REAL"
    seed: int = Field(7, ge=0, le=2**32-1)
    percent: float = Field(10, ge=0, le=100)
    population: str | None = Field(None, max_length=120)
    checkpoint_id: str | None = Field(None, max_length=80, pattern=r"^[\w-]+$")
    request_id: str | None = Field(None, max_length=100)
    reason: str | None = Field(None, max_length=120)


def create_app(root: Path, dataset: Path, token: str, runner=None):
    if len(token) < 32:
        raise ValueError("A random control token of at least 32 characters is required")
    engine = runner or Runner(root, dataset)
    native = NativeController(root, dataset)

    async def authorize(request: Request, authorization: str = Header(default="")):
        # A native proxy has no browser origin. Browsers must go through Hermes.
        if request.headers.get("origin"):
            raise HTTPException(403, "Use the authenticated Hermes plugin proxy")
        if not hmac.compare_digest(authorization, "Bearer "+token):
            raise HTTPException(401, "Invalid Flymes control token")

    async def watchdog():
        while True:
            await asyncio.sleep(1)
            if engine.state["status"] == "running" and time.monotonic()-engine.lease > engine.lease_seconds:
                await engine.stop("controller lease expired")
            elif engine.state["status"] == "running" and time.monotonic()-engine.started > engine.runtime:
                await engine.stop("run runtime exhausted")

    @asynccontextmanager
    async def lifespan(app):
        watch = asyncio.create_task(watchdog())
        yield
        watch.cancel()
        await engine.stop("backend shutdown")

    app = FastAPI(title="Flymes loopback companion", lifespan=lifespan,
                  dependencies=[Depends(authorize)], docs_url=None, redoc_url=None, openapi_url=None)
    app.state.runner = engine
    app.state.native = native

    @app.get('/native/state')
    async def native_state():
        return await asyncio.to_thread(native.handle, {'command': 'status'})

    @app.post('/native')
    async def native_command(request: Request):
        raw = await request.body()
        if len(raw) > 131072:
            raise HTTPException(413, 'Native command too large')
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError('Native command must be an object')
            if body.get('command') == 'enable' and engine.state['status'] == 'running':
                raise ValueError('Stop the built-in demo before enabling a real task')
            result = await asyncio.to_thread(native.handle, body)
            gate = Path(os.environ.get('HERMES_HOME', Path.home()/'.hermes'))/'plugins/flymes/native-gate.json'
            if body.get('command') == 'enable':
                from flymes.runner import atomic_json
                atomic_json(gate, {'session_id': body['session_id'], 'workspace': body['workspace']})
            elif body.get('command') == 'release' and gate.exists():
                marker = json.loads(gate.read_text(encoding='utf-8'))
                if marker.get('session_id') == body.get('session_id'):
                    gate.unlink()
            if body.get('command') in ('propose', 'selection'):
                # Tool callers need the selected operation, not the panel's graph.
                # Keep the response below the Windows loopback transport budget.
                return {key: result.get(key) for key in ('status', 'session_id', 'decision_id', 'tool', 'args', 'mode')} | {
                    'action': (result.get('decision') or {}).get('action'),
                    'scores': (result.get('decision') or {}).get('scores'),
                    'instruction': 'Execute this exact tool and args once. If paused, wait for the user to resume, then fetch command current.'}
            if body.get('command') == 'apply_comparison':
                result.pop('args', None)
            return result
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/state")
    async def state():
        engine.lease = time.monotonic()
        return engine.telemetry()

    @app.post("/control")
    async def control(body: Control):
        try:
            values = body.model_dump(exclude_none=True)
            await engine.control(values.pop("command"), **values)
            return engine.telemetry()
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(409, str(exc)) from exc

    return app
