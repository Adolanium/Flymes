import json

import numpy as np
from fastapi.testclient import TestClient
from scipy import sparse

from flymes.data import Connectome
from flymes.neural import Simulator
from flymes.server import create_app


def test_native_http_flow_and_gate_marker(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    app = create_app(tmp_path, tmp_path, 'x' * 32)
    graph = Connectome(sparse.eye(12, format='csr', dtype=np.float32), np.arange(12), {}, {})
    app.state.native.factory = lambda: Simulator(graph)
    headers = {'Authorization': 'Bearer ' + 'x' * 32}
    gate = tmp_path / 'plugins/flymes/native-gate.json'
    with TestClient(app) as client:
        def command(name, **values):
            response = client.post('/native', headers=headers, json={'command': name, 'session_id': 'chat', **values})
            assert response.status_code == 200, response.text
            return response.json()
        command('enable', workspace=str(tmp_path), review_each=True)
        assert json.loads(gate.read_text())['session_id'] == 'chat'
        selection = command('propose', preferred_index=0, candidates=[
            {'action': 'INSPECT', 'tool': 'read_file', 'args': {'path': 'a.py'}, 'reason': 'Read'},
            {'action': 'TEST', 'tool': 'terminal', 'args': {'command': 'pytest'}, 'reason': 'Test'}])
        assert selection['status'] == 'paused'
        assert 'sample' not in selection and 'args' in selection
        command('compare')
        command('apply_comparison', mode='HERMES')
        current = command('selection')
        assert current['tool'] == 'read_file'
        command('resume')
        allowed = command('authorize', tool=current['tool'], args=current['args'], tool_call_id='one')
        assert allowed['allowed']
        result = dict(decision_id=allowed['decision_id'], tool_call_id='one', status='ok', result='file contents')
        command('result', **result)
        command('result', **result)
        command('release')
        assert not gate.exists()


def test_offline_gateway_release_removes_only_owned_gate(tmp_path, monkeypatch):
    import asyncio
    import pytest
    from fastapi import HTTPException
    from dashboard import plugin_api
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    gate = tmp_path / 'plugins/flymes/native-gate.json'
    gate.parent.mkdir(parents=True)
    gate.write_text(json.dumps({'session_id': 'chat', 'workspace': str(tmp_path)}))
    def offline(*args):
        raise HTTPException(503, 'offline')
    monkeypatch.setattr(plugin_api, '_forward', offline)
    state = asyncio.run(plugin_api.native_state())
    assert state['offline'] and state['session_id'] == 'chat'
    with pytest.raises(HTTPException):
        asyncio.run(plugin_api.native_command({'command': 'release', 'session_id': 'other'}))
    assert gate.exists()
    state = asyncio.run(plugin_api.native_command({'command': 'release', 'session_id': 'chat'}))
    assert state['status'] == 'released' and not gate.exists()
