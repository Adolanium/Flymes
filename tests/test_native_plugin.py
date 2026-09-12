import json
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location('native_plugin', Path(__file__).parents[1] / 'plugin_init.py')
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    directory = tmp_path / 'plugins/flymes'
    directory.mkdir(parents=True)
    (directory / 'native-gate.json').write_text(json.dumps({'session_id': 'host', 'workspace': str(tmp_path)}))
    ctx = Mock()
    plugin.register(ctx)
    hooks = dict(call.args for call in ctx.register_hook.call_args_list)
    handler = ctx.register_tool.call_args.kwargs['handler']
    rpc = Mock(return_value={'allowed': True, 'gated': True, 'decision_id': 'd1'})
    monkeypatch.setattr(plugin, '_rpc', rpc)
    return handler, hooks, rpc


def proposals():
    return {'session_id': 'forged', 'preferred_index': 0, 'candidates': [
        {'action': 'SEARCH', 'tool': 'terminal', 'args': {'command': 'ls'}, 'reason': 'Find files'},
        {'action': 'INSPECT', 'tool': 'read_file', 'args': {'path': 'README.md'}, 'reason': 'Read context'}]}


def test_native_schema_discovery_does_not_need_a_selection(bridge):
    _, hooks, rpc = bridge
    for name in ('tool_describe', 'tool_search'):
        assert hooks['pre_tool_call'](session_id='host', tool_name=name, args={}) is None
    rpc.assert_not_called()


def test_compression_child_cannot_silently_escape_gate(bridge):
    import sqlite3
    choose, hooks, rpc = bridge
    db = plugin._directory().parents[1] / 'state.db'
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE sessions (id TEXT, parent_session_id TEXT)')
        connection.execute('INSERT INTO sessions VALUES (?, ?)', ('continuation', 'host'))
    blocked = hooks['pre_tool_call'](session_id='continuation', tool_name='terminal', args={})
    assert blocked['action'] == 'block' and 'session ID' in blocked['message']
    assert 'error' in json.loads(choose(proposals(), session_id='continuation'))
    assert hooks['pre_tool_call'](session_id='unrelated', tool_name='terminal', args={}) is None
    rpc.assert_not_called()


def test_nonmatching_session_has_no_network(bridge):
    choose, hooks, rpc = bridge
    for name, hook in hooks.items():
        assert hook(session_id='other', tool_name='terminal', args={}) is None
    assert 'error' in json.loads(choose(proposals(), session_id='other'))
    rpc.assert_not_called()


def test_proposal_uses_host_identity_and_string_result(bridge):
    choose, _, rpc = bridge
    result = choose(proposals(), session_id='host')
    assert isinstance(result, str)
    assert rpc.call_args.args[0]['session_id'] == 'host'
    assert rpc.call_args.args[1] == 120


def test_offline_gate_blocks(bridge):
    _, hooks, rpc = bridge
    rpc.side_effect = OSError('offline')
    assert hooks['pre_tool_call'](session_id='host', tool_name='terminal', args={})['action'] == 'block'


def test_backend_restart_cannot_silently_ungate(bridge):
    _, hooks, rpc = bridge
    rpc.return_value = {'allowed': True, 'gated': False}
    assert hooks['pre_tool_call'](session_id='host', tool_name='terminal', args={})['action'] == 'block'


def test_current_selection_uses_host_identity(bridge):
    choose, hooks, rpc = bridge
    choose({'command': 'current', 'session_id': 'forged'}, session_id='host')
    assert rpc.call_args.args[0] == {'command': 'selection', 'session_id': 'host'}
    assert 'context' in hooks['pre_llm_call'](session_id='host')


def test_authorization_preserves_host_approval_and_correlates_result(bridge):
    _, hooks, rpc = bridge
    args = {'command': 'pytest'}
    assert hooks['pre_tool_call'](session_id='host', tool_name='terminal', args=args, tool_call_id='t1') is None
    hooks['post_tool_call'](session_id='host', tool_name='terminal', args=args,
                            tool_call_id='t1', result={'exit_code': 0, 'output': 'ok'})
    body = rpc.call_args.args[0]
    assert body['decision_id'] == 'd1'
    assert body['exit_code'] == 0
    calls = rpc.call_count
    hooks['post_tool_call'](session_id='host', tool_name='terminal', tool_call_id='ungranted', result='ok')
    assert rpc.call_count == calls


def test_prevent_hidden_execution_and_duplicate_categories(bridge):
    choose, hooks, rpc = bridge
    args = proposals()
    args['candidates'][0]['tool'] = 'delegate_task'
    assert 'error' in json.loads(choose(args, session_id='host'))
    args = proposals()
    args['candidates'][1]['action'] = 'SEARCH'
    assert 'error' in json.loads(choose(args, session_id='host'))
    assert hooks['pre_tool_call'](session_id='host', tool_name='batch', args={})['action'] == 'block'
    rpc.assert_not_called()


def test_blocked_result_does_not_report_success(bridge):
    _, hooks, rpc = bridge
    hooks['pre_tool_call'](session_id='host', tool_name='terminal', args={}, tool_call_id='t1')
    hooks['post_tool_call'](session_id='host', tool_name='terminal', args={}, tool_call_id='t1',
                           status='blocked', result={'exit_code': 0})
    body = rpc.call_args.args[0]
    assert 'exit_code' not in body
    assert body['result'].startswith('Blocked')
    assert body['status'] == 'blocked'


def test_json_result_exit_code_and_status(bridge):
    _, hooks, rpc = bridge
    hooks['pre_tool_call'](session_id='host', tool_name='terminal', args={}, tool_call_id='t1')
    hooks['post_tool_call'](session_id='host', tool_name='terminal', args={}, tool_call_id='t1',
                           status='error', result='{"exit_code": 2, "output": "failed"}')
    body = rpc.call_args.args[0]
    assert body['exit_code'] == 2
    assert body['status'] == 'error'


def test_unreported_result_retries_before_selection(bridge):
    choose, hooks, rpc = bridge
    hooks['pre_tool_call'](session_id='host', tool_name='terminal', args={}, tool_call_id='t1')
    rpc.side_effect = OSError('offline')
    hooks['post_tool_call'](session_id='host', tool_name='terminal', args={}, tool_call_id='t1', result='done')
    assert 'unreported' in json.loads(choose(proposals(), session_id='host'))['error']
    rpc.reset_mock()
    rpc.side_effect = None
    rpc.return_value = {'ok': True}
    choose(proposals(), session_id='host')
    assert [call.args[0]['command'] for call in rpc.call_args_list] == ['result', 'propose']
    rpc.reset_mock()
    choose({'command': 'current'}, session_id='host')
    assert [call.args[0]['command'] for call in rpc.call_args_list] == ['selection']
