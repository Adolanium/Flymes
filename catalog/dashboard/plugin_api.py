"""Hermes-authenticated namespace proxy; computation runs in the companion."""
import asyncio
import http.client
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _forward(path, body=None, _attempt=0):
    config_path = Path(os.environ.get("HERMES_HOME", Path.home()/".hermes")) / "plugins" / "flymes" / "service.json"
    if not config_path.exists():
        raise HTTPException(503, "Flymes companion is not configured. Run scripts/launch.ps1.")
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    port = int(config["port"])
    if not 1024 <= port <= 65535:
        raise HTTPException(503, "Invalid Flymes companion port")
    request = urllib.request.Request(f"http://127.0.0.1:{port}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer "+config["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=10 if path == "state" else 120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise HTTPException(exc.code, exc.read(2000).decode(errors="replace")) from exc
    except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        if body is None and _attempt < 2:
            time.sleep(.05)
            return _forward(path, None, _attempt + 1)
        # Windows can raise ConnectionResetError directly, outside URLError.
        # Do not retry controls: the operation may already have been accepted.
        raise HTTPException(503, "Flymes companion disconnected. The panel will reconnect automatically; if it stays offline, run scripts/launch.ps1.") from exc


@router.get("/state")
async def state():
    return await asyncio.to_thread(_forward, "state")


@router.post("/control")
async def control(body: dict):
    if len(json.dumps(body)) > 4096:
        raise HTTPException(413, "Control request too large")
    return await asyncio.to_thread(_forward, "control", body)


@router.get('/native/state')
async def native_state():
    gate = Path(os.environ.get('HERMES_HOME', Path.home()/'.hermes'))/'plugins/flymes/native-gate.json'
    marker = json.loads(gate.read_text(encoding='utf-8')) if gate.exists() else {}
    try:
        result = await asyncio.to_thread(_forward, 'native/state')
    except HTTPException as exc:
        if exc.status_code == 503 and marker:
            return {'kind': 'native', 'status': 'offline', 'offline': True, **marker}
        raise
    if marker and not result.get('enabled'):
        return {**result, **marker, 'status': 'recovery_required', 'notice': 'Companion restarted. Return control, then enable a fresh run.'}
    return result


@router.post('/native')
async def native_command(body: dict):
    if len(json.dumps(body).encode('utf-8')) > 131072:
        raise HTTPException(413, 'Native command too large')
    if body.get('command') == 'release':
        # User-owned escape hatch works even when the companion is offline.
        gate = Path(os.environ.get('HERMES_HOME', Path.home()/'.hermes'))/'plugins/flymes/native-gate.json'
        removed = False
        if gate.exists():
            marker = json.loads(gate.read_text(encoding='utf-8'))
            if marker.get('session_id') == body.get('session_id'):
                gate.unlink()
                removed = True
            else:
                raise HTTPException(409, 'This session does not own the Flymes gate')
        try:
            return await asyncio.to_thread(_forward, 'native', body)
        except HTTPException as exc:
            if exc.status_code == 503 or (removed and exc.status_code == 409):
                return {'kind': 'native', 'status': 'released', 'session_id': body.get('session_id'), 'notice': 'Control returned to Hermes. Companion is offline.'}
            raise
    return await asyncio.to_thread(_forward, 'native', body)
